from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import folder_paths
import node_helpers
import nodes as comfy_nodes
import torch
from comfy_extras.nodes_custom_sampler import (
    CFGGuider,
    KSamplerSelect,
    RandomNoise,
    SamplerCustomAdvanced,
)
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler

from . import one_reference_photo as baseline
from .flux2_klein9b_appearance_polish import (
    APPEARANCE_POLISH_LABEL_OFF,
    APPEARANCE_POLISH_LABEL_ON,
)
from .flux2_klein9b_mitch_identity_studio_presets import (
    GROUP_PROFILE,
    PROMPTING_STRATEGY,
    REFERENCE_CATALOG,
    REFERENCE_PROFILES,
    compose_effective_prompt,
)
from .flux2_klein9b_smartphone_style import (
    SMARTPHONE_STYLE_LORA_NAME,
    SMARTPHONE_STYLE_LORA_STRENGTH,
    apply_smartphone_style_trigger,
    smartphone_style_report,
    verify_smartphone_style_lora,
)
from .flux2_klein9b_turbo import (
    TURBO_LORA_NAME,
    TURBO_LORA_STRENGTH,
    TURBO_MODE_LABEL_OFF,
    TURBO_MODE_LABEL_ON,
    sampling_settings,
    turbo_mode_report,
    verify_turbo_lora,
)


MODEL_NAME = "flux-2-klein-base-9b-bf16.safetensors"
CLIP_NAME = "qwen_3_8b_fp8mixed.safetensors"
VAE_NAME = "flux2-vae.safetensors"
LORA_NAME = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"
LORA_SHA256 = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
LORA_STRENGTH = 0.90
REFERENCE_TARGET_PIXELS = 512 * 512
WIDTH = 832
HEIGHT = 1216
STEPS = 50
GUIDANCE = 4.0
OUTPUT_ROOT = "flux2-klein9b-mitch-identity-studio-v1"

_VERIFIED_SIGNATURES: dict[str, tuple[str, int, int]] = {}


def _verify_sha256(path: Path, expected: str, label: str) -> str:
    signature = (str(path.resolve()), int(path.stat().st_size), int(path.stat().st_mtime_ns))
    cache_key = f"{label}:{path}"
    if _VERIFIED_SIGNATURES.get(cache_key) != signature:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(block)
        actual = digest.hexdigest().upper()
        if actual != expected.upper():
            raise RuntimeError(f"{label} hash mismatch. Expected {expected}, found {actual}.")
        _VERIFIED_SIGNATURES[cache_key] = signature
    return str(path)


def _verify_lora() -> str:
    full_path = folder_paths.get_full_path("loras", LORA_NAME)
    if not full_path:
        raise RuntimeError(f"Missing protected Klein 9B step-1600 LoRA: {LORA_NAME}")
    return _verify_sha256(Path(full_path), LORA_SHA256, "Klein 9B step-1600 LoRA")


def _verify_reference(key: str) -> str:
    record = REFERENCE_CATALOG[key]
    path = Path(folder_paths.get_input_directory()) / record["file"]
    if not path.is_file():
        raise RuntimeError(f"Missing protected genuine reference: {path}")
    return _verify_sha256(path, record["sha256"], f"Genuine reference {key}")


def _assert_rtx3090() -> str:
    if not torch.cuda.is_available():
        raise RuntimeError("FLUX.2 Klein 9B Mitch Identity Studio requires CUDA on the RTX 3090.")
    device_name = torch.cuda.get_device_name(torch.cuda.current_device())
    if "RTX 3090" not in device_name:
        raise RuntimeError(
            f"This workflow is locked to the RTX 3090; the active worker reports {device_name}."
        )
    return device_name


class Flux2Klein9BMitchIdentityStudioV1:
    """Locked Base-9B + step-1600 LoRA + genuine-reference production workflow."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_profile": (list(REFERENCE_PROFILES), {"default": GROUP_PROFILE}),
                "scene_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "Describe the complete new photograph, people, pose, clothing, and setting.",
                    },
                ),
                "appearance_polish": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": APPEARANCE_POLISH_LABEL_ON,
                        "label_off": APPEARANCE_POLISH_LABEL_OFF,
                    },
                ),
                "fast_turbo": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": TURBO_MODE_LABEL_ON,
                        "label_off": TURBO_MODE_LABEL_OFF,
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 8675411,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls, reference_profile, scene_prompt, appearance_polish, fast_turbo, seed
    ):
        try:
            compose_effective_prompt(reference_profile, scene_prompt, appearance_polish)
        except ValueError as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("photo", "effective_prompt", "output_folder", "report_json")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity"
    OUTPUT_NODE = True

    def generate(self, reference_profile, scene_prompt, appearance_polish, fast_turbo, seed):
        validation = self.VALIDATE_INPUTS(
            reference_profile, scene_prompt, appearance_polish, fast_turbo, seed
        )
        if validation is not True:
            raise RuntimeError(validation)

        gpu = _assert_rtx3090()
        baseline._require_model("diffusion_models", MODEL_NAME)
        baseline._require_model("text_encoders", CLIP_NAME)
        baseline._require_model("vae", VAE_NAME)
        lora_path = _verify_lora()
        smartphone_style_path = verify_smartphone_style_lora()
        turbo_path = verify_turbo_lora() if fast_turbo else None
        steps, guidance = sampling_settings(fast_turbo, STEPS, GUIDANCE)
        reference_keys = REFERENCE_PROFILES[reference_profile]
        reference_paths = {key: _verify_reference(key) for key in reference_keys}
        effective_prompt = apply_smartphone_style_trigger(
            compose_effective_prompt(reference_profile, scene_prompt, appearance_polish)
        )
        started = time.perf_counter()

        model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
        if fast_turbo:
            model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
                model, TURBO_LORA_NAME, TURBO_LORA_STRENGTH
            )[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, LORA_NAME, LORA_STRENGTH
        )[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, SMARTPHONE_STYLE_LORA_NAME, SMARTPHONE_STYLE_LORA_STRENGTH
        )[0]
        clip = comfy_nodes.CLIPLoader().load_clip(CLIP_NAME, "flux2", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]

        positive = comfy_nodes.CLIPTextEncode().encode(clip, effective_prompt)[0]
        negative = comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
        reference_report = []
        for key in reference_keys:
            record = REFERENCE_CATALOG[key]
            image = comfy_nodes.LoadImage().load_image(record["file"])[0][:1, :, :, :3]
            resized = baseline._resize_reference(image, REFERENCE_TARGET_PIXELS)
            latent = comfy_nodes.VAEEncode().encode(vae, resized)[0]["samples"]
            values = {"reference_latents": [latent]}
            positive = node_helpers.conditioning_set_values(positive, values, append=True)
            negative = node_helpers.conditioning_set_values(negative, values, append=True)
            reference_report.append(
                {
                    "key": key,
                    "file": record["file"],
                    "path": reference_paths[key],
                    "role": record["role"],
                    "sha256": record["sha256"],
                }
            )

        guider = CFGGuider.execute(model, positive, negative, guidance)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        sigmas = Flux2Scheduler.execute(steps, WIDTH, HEIGHT)[0]
        noise = RandomNoise.execute(int(seed))[0]
        latent_image = EmptyFlux2LatentImage.execute(WIDTH, HEIGHT, 1)[0]
        sampled = SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent_image
        )[0]
        photo = comfy_nodes.VAEDecode().decode(vae, sampled)[0]

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"{OUTPUT_ROOT}/{run_stamp}"
        lora_load_order = []
        if fast_turbo:
            lora_load_order.append(
                {
                    "name": TURBO_LORA_NAME,
                    "strength": TURBO_LORA_STRENGTH,
                    "role": "8-step acceleration",
                }
            )
        lora_load_order.extend(
            [
                {"name": LORA_NAME, "strength": LORA_STRENGTH, "role": "identity"},
                {
                    "name": SMARTPHONE_STYLE_LORA_NAME,
                    "strength": SMARTPHONE_STYLE_LORA_STRENGTH,
                    "role": "whole-frame smartphone realism",
                },
            ]
        )
        report = {
            "schema_version": 1,
            "purpose": "flux2_klein9b_mitch_identity_studio_v1",
            "gpu": gpu,
            "model": MODEL_NAME,
            "text_encoder": CLIP_NAME,
            "vae": VAE_NAME,
            "lora": LORA_NAME,
            "lora_path": lora_path,
            "lora_sha256": LORA_SHA256,
            "lora_strength": LORA_STRENGTH,
            "trigger": "m1tch_person",
            "turbo_mode": turbo_mode_report(fast_turbo, turbo_path, 1 if fast_turbo else None),
            "smartphone_style": {
                **smartphone_style_report(),
                "path": smartphone_style_path,
                "load_order": 3 if fast_turbo else 2,
            },
            "lora_load_order": lora_load_order,
            "reference_profile": reference_profile,
            "reference_count": len(reference_keys),
            "references": reference_report,
            "identity_mechanism": "Base-9B identity LoRA plus genuine-photo native reference latents",
            "prompting_strategy": PROMPTING_STRATEGY,
            "appearance_polish": bool(appearance_polish),
            "fast_turbo": bool(fast_turbo),
            "source_scene_conditioning": False,
            "identity_pass": False,
            "face_swap": False,
            "restoration": False,
            "sharpening": False,
            "scene_prompt": scene_prompt.strip(),
            "effective_prompt": effective_prompt,
            "width": WIDTH,
            "height": HEIGHT,
            "steps": steps,
            "guidance": guidance,
            "sampler": "euler",
            "scheduler": "Flux2Scheduler",
            "reference_megapixels_each": 0.25,
            "seed": int(seed),
            "seconds": round(time.perf_counter() - started, 3),
            "manual_review_required": [
                "identity at full size and thumbnail",
                "exactly one Mitch in group scenes",
                "apparent age, hairline, and face geometry",
                "complete limbs, coherent hands, and body proportions",
                "scene detail and whole-frame integration",
            ],
        }
        saved = comfy_nodes.SaveImage().save_images(
            photo,
            f"{output_folder}/photo",
            extra_pnginfo={"flux2_klein9b_mitch_identity_studio_v1": report},
        )
        report_json = json.dumps(report, indent=2)
        report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")

        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (f"Saved Klein 9B result to ComfyUI/output/{output_folder}",),
            },
            "result": (photo, effective_prompt, output_folder, report_json),
        }
