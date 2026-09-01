from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import folder_paths
import node_helpers
import nodes as comfy_nodes
from comfy_extras.nodes_custom_sampler import (
    BasicGuider,
    KSamplerSelect,
    RandomNoise,
    SamplerCustomAdvanced,
)
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler, FluxGuidance

from . import one_reference_photo as baseline
from .flux2_dev_mitch_studio_presets import (
    CAMERA_STYLES,
    CANVASES,
    FRAMINGS,
    MODE_PROMPT_ONLY,
    MODE_SCENE_RESTAGE,
    MOMENTS,
    NO_SCENE_IMAGE,
    SCENE_PRESETS,
    compose_effective_prompt,
)


MODEL_NAME = "flux2_dev_fp8mixed.safetensors"
CLIP_NAME = "mistral_3_small_flux2_fp4_mixed.safetensors"
VAE_NAME = "flux2-vae.safetensors"
LORA_NAME = r"flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors"
LORA_SHA256 = "7c0c4f1726189c51e19c8392c12fe3e03a26bd084fffb8d84b907c966a77cc3e"
REFERENCE_TARGET_PIXELS = 832 * 1248
OUTPUT_ROOT = "flux2-dev-mitch-scene-studio"

_VERIFIED_LORA_SIGNATURE: tuple[str, int, int] | None = None


def _scene_reference_choices() -> list[str]:
    # Scene plates are composition references, not identity evidence.  The
    # identity-reference picker deliberately hides generated images, but doing
    # that here also hid the nine supplied dating-scene plates.  FLUX.2 Dev is
    # allowed to restage any local image while the protected Dev LoRA supplies
    # Mitch's identity.
    input_root = Path(folder_paths.get_input_directory())
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    available = []
    if input_root.is_dir():
        available = sorted(
            str(path.relative_to(input_root)).replace("\\", "/")
            for path in input_root.rglob("*")
            if path.is_file() and path.suffix.casefold() in extensions
        )
    return [NO_SCENE_IMAGE, *available]


def _verify_lora() -> str:
    global _VERIFIED_LORA_SIGNATURE
    full_path = folder_paths.get_full_path("loras", LORA_NAME)
    if not full_path:
        raise RuntimeError(f"Missing protected step-1000 LoRA: {LORA_NAME}")
    path = Path(full_path)
    stat = path.stat()
    signature = (str(path.resolve()), int(stat.st_size), int(stat.st_mtime_ns))
    if _VERIFIED_LORA_SIGNATURE != signature:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(block)
        actual = digest.hexdigest().lower()
        if actual != LORA_SHA256:
            raise RuntimeError(
                f"Step-1000 LoRA hash mismatch. Expected {LORA_SHA256}, found {actual}."
            )
        _VERIFIED_LORA_SIGNATURE = signature
    return str(path)


def _output_dimensions(canvas: str, scene_image=None) -> tuple[int, int, object | None]:
    if scene_image is None:
        width, height = CANVASES[canvas]
        return width, height, None
    resized = baseline._resize_reference(scene_image, REFERENCE_TARGET_PIXELS)
    height, width = resized.shape[1:3]
    return int(width), int(height), resized


class Flux2DevMitchSceneStudio:
    """Prompt library plus optional FLUX.2 Dev scene restaging for the step-1000 Mitch LoRA."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scene_mode": ([MODE_PROMPT_ONLY, MODE_SCENE_RESTAGE],),
                "scene_reference": (_scene_reference_choices(), {"image_upload": True}),
                "scene_preset": (list(SCENE_PRESETS),),
                "custom_scene_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "Optional: add or replace creative direction.",
                    },
                ),
                "camera_style": (list(CAMERA_STYLES),),
                "framing": (list(FRAMINGS), {"default": "Waist-up"}),
                "moment": (list(MOMENTS), {"default": "Candid — looking away"}),
                "canvas": (list(CANVASES),),
                "lora_strength": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.8, "max": 1.1, "step": 0.05},
                ),
                "steps": ("INT", {"default": 28, "min": 20, "max": 50, "step": 1}),
                "guidance": (
                    "FLOAT",
                    {"default": 4.0, "min": 3.0, "max": 5.0, "step": 0.1},
                ),
                "seed": (
                    "INT",
                    {
                        "default": 8675310,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        scene_mode,
        scene_reference,
        scene_preset,
        custom_scene_prompt,
        camera_style,
        framing,
        moment,
        canvas,
        lora_strength,
        steps,
        guidance,
        seed,
    ):
        try:
            compose_effective_prompt(
                scene_mode,
                scene_preset,
                custom_scene_prompt,
                camera_style,
                framing,
                moment,
            )
        except ValueError as exc:
            return str(exc)
        if canvas not in CANVASES:
            return f"Unknown canvas: {canvas}"
        if scene_mode == MODE_SCENE_RESTAGE:
            if scene_reference == NO_SCENE_IMAGE:
                return "Upload or select a scene image for SCENE IMAGE mode."
            if not folder_paths.exists_annotated_filepath(scene_reference):
                return f"Scene image is not available in ComfyUI input: {scene_reference}"
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("photo", "effective_prompt", "output_folder", "report_json")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity"
    OUTPUT_NODE = True

    def generate(
        self,
        scene_mode,
        scene_reference,
        scene_preset,
        custom_scene_prompt,
        camera_style,
        framing,
        moment,
        canvas,
        lora_strength,
        steps,
        guidance,
        seed,
    ):
        validation = self.VALIDATE_INPUTS(
            scene_mode,
            scene_reference,
            scene_preset,
            custom_scene_prompt,
            camera_style,
            framing,
            moment,
            canvas,
            lora_strength,
            steps,
            guidance,
            seed,
        )
        if validation is not True:
            raise RuntimeError(validation)

        baseline._require_model("diffusion_models", MODEL_NAME)
        baseline._require_model("text_encoders", CLIP_NAME)
        baseline._require_model("vae", VAE_NAME)
        lora_path = _verify_lora()
        started = time.perf_counter()

        effective_prompt = compose_effective_prompt(
            scene_mode,
            scene_preset,
            custom_scene_prompt,
            camera_style,
            framing,
            moment,
        )
        scene_image = None
        active_scene_reference = None
        if scene_mode == MODE_SCENE_RESTAGE:
            scene_image = comfy_nodes.LoadImage().load_image(scene_reference)[0][:1, :, :, :3]
            active_scene_reference = scene_reference
        width, height, resized_scene = _output_dimensions(canvas, scene_image)

        model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, LORA_NAME, float(lora_strength)
        )[0]
        clip = comfy_nodes.CLIPLoader().load_clip(CLIP_NAME, "flux2", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]

        positive = comfy_nodes.CLIPTextEncode().encode(clip, effective_prompt)[0]
        positive = FluxGuidance.execute(positive, float(guidance))[0]
        reference_count = 0
        if resized_scene is not None:
            scene_latent = comfy_nodes.VAEEncode().encode(vae, resized_scene)[0]["samples"]
            positive = node_helpers.conditioning_set_values(
                positive,
                {"reference_latents": [scene_latent]},
                append=True,
            )
            reference_count = 1

        guider = BasicGuider.execute(model, positive)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        sigmas = Flux2Scheduler.execute(int(steps), width, height)[0]
        latent = EmptyFlux2LatentImage.execute(width, height, 1)[0]
        noise = RandomNoise.execute(int(seed))[0]
        sampled = SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent
        )[0]
        photo = comfy_nodes.VAEDecode().decode(vae, sampled)[0]

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        mode_slug = "scene-restage" if scene_mode == MODE_SCENE_RESTAGE else "prompt-only"
        output_folder = f"{OUTPUT_ROOT}/{mode_slug}/{run_stamp}"
        report = {
            "schema_version": 1,
            "purpose": "flux2_dev_step1000_identity_lora_scene_studio",
            "scene_mode": scene_mode,
            "scene_reference": active_scene_reference,
            "scene_reference_role": (
                "composition_location_pose_props_lighting_not_identity"
                if active_scene_reference
                else None
            ),
            "scene_preset": scene_preset,
            "custom_scene_prompt": custom_scene_prompt.strip(),
            "effective_prompt": effective_prompt,
            "camera_style": camera_style,
            "framing": framing,
            "moment": moment,
            "canvas": canvas,
            "width": width,
            "height": height,
            "model": MODEL_NAME,
            "text_encoder": CLIP_NAME,
            "vae": VAE_NAME,
            "lora": LORA_NAME,
            "lora_path": lora_path,
            "lora_sha256": LORA_SHA256,
            "lora_strength": round(float(lora_strength), 3),
            "steps": int(steps),
            "guidance": round(float(guidance), 3),
            "sampler": "euler",
            "seed": int(seed),
            "reference_latent_count": reference_count,
            "reference_conditioning": bool(reference_count),
            "face_swap": False,
            "mask": False,
            "restoration": False,
            "post_processing": False,
            "manual_review_required": [
                "identity at full size and thumbnail",
                "apparent age and hairline",
                "face geometry and skin texture",
                "scene integration and hand anatomy",
                "identity leakage into secondary people",
            ],
            "seconds": round(time.perf_counter() - started, 3),
        }
        saved = comfy_nodes.SaveImage().save_images(
            photo,
            f"{output_folder}/photo",
            extra_pnginfo={"flux2_dev_mitch_scene_studio": report},
        )
        report_json = json.dumps(report, indent=2)
        report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")

        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    f"Saved {mode_slug} result to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (photo, effective_prompt, output_folder, report_json),
        }
