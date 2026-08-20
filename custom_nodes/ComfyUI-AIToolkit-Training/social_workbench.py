from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps

import nodes as comfy_nodes
import comfy.model_management
from comfy_extras.nodes_canny import Canny
from comfy_extras.nodes_model_advanced import ModelSamplingAuraFlow
from comfy_extras.nodes_model_patch import ModelPatchLoader, ZImageFunControlnet

from .social_pack import (
    CFG,
    CONTROL_NAME,
    LORA_STRENGTH,
    MODEL_NAME,
    NEGATIVE_PROMPT,
    SCENES,
    SHIFT,
    TEXT_ENCODER_NAME,
    TRIGGER,
    VAE_NAME,
    _aitk_loras,
    _require_model,
)


CONFIG_TYPE = "AITK_SOCIAL_CONFIG"
SCENE_TYPE = "AITK_SOCIAL_SCENE"

REFERENCE_PRESETS: dict[str, tuple[str, tuple[int, int, int, int]] | None] = {
    "None (prompt only)": None,
    "Cat — Ragdoll pose": ("reference-grid.jpg", (630, 8, 902, 369)),
    "Cat — tabby pose": ("reference-grid.jpg", (9, 463, 281, 823)),
    "Golf course pose": ("reference-grid.jpg", (320, 463, 592, 823)),
    "Amalfi balcony composition": ("reference-travel.jpg", (580, 338, 1050, 960)),
    "Lake boat composition": ("reference-travel.jpg", (1067, 338, 1536, 960)),
    "Restaurant composition": ("reference-travel.jpg", (1554, 338, 2025, 960)),
}


def _lora_choices() -> list[str]:
    choices = _aitk_loras()
    return choices or ["No completed AI-Toolkit Z-Image LoRA found"]


def _reference_tensor(preset: str, width: int, height: int) -> torch.Tensor:
    reference = REFERENCE_PRESETS.get(preset)
    if reference is None:
        raise RuntimeError(f"Reference preset is not configured: {preset}")
    filename, crop = reference
    source = Path(__file__).parent / "assets" / "social_pack" / filename
    with Image.open(source) as opened:
        image = opened.convert("RGB").crop(crop)
        image = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS)
        array = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(array).unsqueeze(0)


class AIToolkitSocialPackSettings:
    """Editable global settings shared by Draft and Final stages."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lora_name": (_lora_choices(),),
                "trigger_word": ("STRING", {"default": TRIGGER}),
                "global_style": (
                    "STRING",
                    {
                        "default": (
                            "photorealistic candid lifestyle photography, authentic skin texture, natural anatomy, "
                            "believable smartphone or 35mm camera detail, no text or watermark"
                        ),
                        "multiline": True,
                    },
                ),
                "negative_prompt": ("STRING", {"default": NEGATIVE_PROMPT, "multiline": True}),
                "lora_strength": (
                    "FLOAT",
                    {"default": LORA_STRENGTH, "min": 0.0, "max": 2.0, "step": 0.05},
                ),
                "cfg": ("FLOAT", {"default": CFG, "min": 1.0, "max": 12.0, "step": 0.1}),
                "model_shift": ("FLOAT", {"default": SHIFT, "min": 0.0, "max": 12.0, "step": 0.1}),
                "draft_width": ("INT", {"default": 576, "min": 256, "max": 1536, "step": 32}),
                "draft_height": ("INT", {"default": 832, "min": 256, "max": 2048, "step": 32}),
                "draft_steps": ("INT", {"default": 10, "min": 4, "max": 50}),
                "final_width": ("INT", {"default": 832, "min": 256, "max": 1536, "step": 32}),
                "final_height": ("INT", {"default": 1216, "min": 256, "max": 2048, "step": 32}),
                "final_steps": ("INT", {"default": 25, "min": 4, "max": 80}),
                "output_prefix": ("STRING", {"default": "zimg-social-pack"}),
            }
        }

    RETURN_TYPES = (CONFIG_TYPE,)
    RETURN_NAMES = ("settings",)
    FUNCTION = "build"
    CATEGORY = "image/generation/AI-Toolkit Social Workbench"

    def build(
        self,
        lora_name: str,
        trigger_word: str,
        global_style: str,
        negative_prompt: str,
        lora_strength: float,
        cfg: float,
        model_shift: float,
        draft_width: int,
        draft_height: int,
        draft_steps: int,
        final_width: int,
        final_height: int,
        final_steps: int,
        output_prefix: str,
    ):
        if lora_name not in _aitk_loras():
            raise RuntimeError("Select a completed AI-Toolkit Z-Image LoRA.")
        if not trigger_word.strip():
            raise RuntimeError("Trigger word cannot be empty.")
        for label, value in {
            "draft_width": draft_width,
            "draft_height": draft_height,
            "final_width": final_width,
            "final_height": final_height,
        }.items():
            if value % 32:
                raise RuntimeError(f"{label} must be divisible by 32.")
        config = {
            "lora_name": lora_name,
            "trigger_word": trigger_word.strip(),
            "global_style": global_style.strip(),
            "negative_prompt": negative_prompt.strip(),
            "lora_strength": float(lora_strength),
            "cfg": float(cfg),
            "model_shift": float(model_shift),
            "draft": {"width": int(draft_width), "height": int(draft_height), "steps": int(draft_steps)},
            "final": {"width": int(final_width), "height": int(final_height), "steps": int(final_steps)},
            "output_prefix": output_prefix.strip().strip("/\\") or "zimg-social-pack",
        }
        return (config,)


class AIToolkitSocialScene:
    """One visible, editable scene card."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scene_name": ("STRING", {"default": "Scene"}),
                "prompt": ("STRING", {"default": f"{TRIGGER}, realistic lifestyle photo", "multiline": True}),
                "negative_additions": ("STRING", {"default": "", "multiline": True}),
                "seed": ("INT", {"default": 1, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "reference_preset": (list(REFERENCE_PRESETS),),
                "control_strength": (
                    "FLOAT",
                    {"default": 0.7, "min": 0.0, "max": 1.5, "step": 0.05},
                ),
                "enabled": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = (SCENE_TYPE,)
    RETURN_NAMES = ("scene",)
    FUNCTION = "build"
    CATEGORY = "image/generation/AI-Toolkit Social Workbench"

    def build(
        self,
        scene_name: str,
        prompt: str,
        negative_additions: str,
        seed: int,
        reference_preset: str,
        control_strength: float,
        enabled: bool,
    ):
        if enabled and not prompt.strip():
            raise RuntimeError(f"Prompt for {scene_name or 'scene'} cannot be empty.")
        return (
            {
                "name": scene_name.strip() or "scene",
                "prompt": prompt.strip(),
                "negative_additions": negative_additions.strip(),
                "seed": int(seed),
                "reference_preset": reference_preset,
                "control_strength": float(control_strength),
                "enabled": bool(enabled),
            },
        )


def _scene_inputs() -> dict[str, tuple[str]]:
    return {f"scene_{index}": (SCENE_TYPE,) for index in range(1, 10)}


SCENE_SCOPES = ["All enabled scenes", *[f"Scene {index} only" for index in range(1, 10)]]


def _select_scope(scenes: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    if scope == "All enabled scenes":
        return scenes
    try:
        index = int(scope.split()[1]) - 1
        return [scenes[index]]
    except (IndexError, ValueError):
        raise RuntimeError(f"Invalid scene scope: {scope}") from None


class _SocialPackRenderer:
    def _render(
        self,
        config: dict[str, Any],
        scenes: list[dict[str, Any]],
        quality: str,
        prompt_meta: Any,
        extra_pnginfo: Any,
    ):
        profile = config[quality]
        width, height, steps = profile["width"], profile["height"], profile["steps"]
        enabled = [scene for scene in scenes if scene["enabled"]]
        if not enabled:
            raise RuntimeError("At least one scene must be enabled.")

        _require_model("diffusion_models", MODEL_NAME)
        _require_model("text_encoders", TEXT_ENCODER_NAME)
        _require_model("vae", VAE_NAME)
        if any(scene["reference_preset"] != "None (prompt only)" for scene in enabled):
            _require_model("model_patches", CONTROL_NAME)

        base_model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            base_model, config["lora_name"], config["lora_strength"]
        )[0]
        model = ModelSamplingAuraFlow().patch_aura(model, config["model_shift"])[0]
        clip = comfy_nodes.CLIPLoader().load_clip(TEXT_ENCODER_NAME, "lumina2", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]
        model_patch = None
        if any(scene["reference_preset"] != "None (prompt only)" for scene in enabled):
            model_patch = ModelPatchLoader().load_model_patch(CONTROL_NAME)[0]

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_folder = f"{config['output_prefix']}/{quality}s/{run_stamp}"
        images: list[torch.Tensor] = []
        ui_images: list[dict[str, Any]] = []

        for index, scene in enumerate(enabled, start=1):
            scene_model = model
            preset = scene["reference_preset"]
            if preset != "None (prompt only)":
                reference = _reference_tensor(preset, width, height)
                control = Canny.detect_edge(reference, 0.25, 0.65)[0]
                scene_model = ZImageFunControlnet().diffsynth_controlnet(
                    model,
                    model_patch,
                    vae,
                    image=control,
                    strength=scene["control_strength"],
                )[0]

            trigger = config["trigger_word"]
            positive_text = scene["prompt"].replace("{trigger}", trigger)
            if trigger.casefold() not in positive_text.casefold():
                positive_text = f"{trigger}, {positive_text}"
            if config["global_style"]:
                positive_text = f"{positive_text}, {config['global_style']}"
            negative_text = config["negative_prompt"]
            if scene["negative_additions"]:
                negative_text = f"{negative_text}, {scene['negative_additions']}"

            positive = comfy_nodes.CLIPTextEncode().encode(clip, positive_text)[0]
            negative = comfy_nodes.CLIPTextEncode().encode(clip, negative_text)[0]
            latent = {
                "samples": torch.zeros(
                    [1, 16, height // 8, width // 8],
                    device=comfy.model_management.intermediate_device(),
                    dtype=comfy.model_management.intermediate_dtype(),
                ),
                "downscale_ratio_spacial": 8,
            }
            sampled = comfy_nodes.common_ksampler(
                scene_model,
                scene["seed"],
                steps,
                config["cfg"],
                "res_multistep",
                "simple",
                positive,
                negative,
                latent,
                denoise=1.0,
            )[0]
            image = comfy_nodes.VAEDecode().decode(vae, sampled)[0]
            images.append(image)
            safe_name = "".join(char if char.isalnum() or char in "-_" else "-" for char in scene["name"]).strip("-")
            saved = comfy_nodes.SaveImage().save_images(
                image,
                f"{output_folder}/{index:02d}-{safe_name or 'scene'}",
                prompt=prompt_meta,
                extra_pnginfo={
                    **(extra_pnginfo or {}),
                    "social_workbench": {
                        "stage": quality,
                        "scene": scene,
                        "resolved_prompt": positive_text,
                        "width": width,
                        "height": height,
                        "steps": steps,
                    },
                },
            )
            ui_images.extend(saved["ui"]["images"])

        batch = torch.cat(images, dim=0)
        status = f"{quality.title()} stage saved {len(images)} images to ComfyUI/output/{output_folder}"
        return {"ui": {"images": ui_images, "text": (status,)}, "result": (batch, output_folder)}


class AIToolkitSocialPackDrafts(_SocialPackRenderer):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "draft_scope": (SCENE_SCOPES,),
                "settings": (CONFIG_TYPE,),
                **_scene_inputs(),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("draft_images", "draft_folder")
    FUNCTION = "render"
    CATEGORY = "image/generation/AI-Toolkit Social Workbench"

    def render(self, draft_scope, settings, prompt=None, extra_pnginfo=None, **kwargs):
        scenes = [kwargs[f"scene_{index}"] for index in range(1, 10)]
        return self._render(settings, _select_scope(scenes, draft_scope), "draft", prompt, extra_pnginfo)


class AIToolkitSocialPackFinals(_SocialPackRenderer):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "render_final": ("BOOLEAN", {"default": False}),
                "final_scope": (SCENE_SCOPES,),
                "settings": (CONFIG_TYPE,),
                **_scene_inputs(),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("final_images", "final_folder")
    FUNCTION = "render"
    CATEGORY = "image/generation/AI-Toolkit Social Workbench"
    OUTPUT_NODE = True

    def render(self, render_final, final_scope, settings, prompt=None, extra_pnginfo=None, **kwargs):
        if not render_final:
            placeholder = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            status = "Final stage is OFF. Review Drafts, edit prompts/seeds/settings, then switch render_final ON."
            return {"ui": {"text": (status,)}, "result": (placeholder, "FINAL STAGE OFF")}
        scenes = [kwargs[f"scene_{index}"] for index in range(1, 10)]
        return self._render(settings, _select_scope(scenes, final_scope), "final", prompt, extra_pnginfo)


DEFAULT_SCENE_WIDGETS = tuple(
    {
        "scene_name": scene.label,
        "prompt": scene.prompt,
        "negative_additions": "",
        "seed": scene.seed,
        "reference_preset": preset,
        "control_strength": 0.7,
        "enabled": True,
    }
    for scene, preset in zip(
        SCENES,
        (
            "None (prompt only)",
            "None (prompt only)",
            "Cat — Ragdoll pose",
            "Cat — tabby pose",
            "Golf course pose",
            "Amalfi balcony composition",
            "Lake boat composition",
            "Restaurant composition",
            "None (prompt only)",
        ),
    )
)
