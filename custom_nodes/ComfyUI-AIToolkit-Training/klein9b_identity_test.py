from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path

import folder_paths
import node_helpers
import numpy as np
import torch

import comfy.model_management
import comfy.utils
import nodes as comfy_nodes
from comfy_extras.nodes_custom_sampler import BasicGuider, KSamplerSelect, RandomNoise, SamplerCustomAdvanced
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler, FluxKVCache

from .identity_lock import _cosine, _embedding, _faces, _tensor_rgb
from .social_photo_core import is_known_synthetic_identity_fixture


CATEGORY = "image/generation/Social Photo Studio/Proofs"
MODEL_NAME = "flux-2-klein-9b-kv-fp8.safetensors"
CLIP_NAME = "qwen_3_8b_fp8mixed.safetensors"
VAE_NAME = "flux2-vae.safetensors"
NONE_REFERENCE = "[none]"
REFERENCE_PIXELS = 640 * 640


def _available_input_images() -> list[str]:
    root = Path(folder_paths.get_input_directory())
    if not root.is_dir():
        return []
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.casefold() in extensions
        and not is_known_synthetic_identity_fixture(path.name)
    )


def _reference_choices(required: bool) -> list[str]:
    choices = _available_input_images()
    if required:
        return choices or ["Upload reference 1"]
    return [NONE_REFERENCE, *choices]


def _require_model(folder: str, filename: str) -> Path:
    resolved = folder_paths.get_full_path(folder, filename)
    if resolved is None:
        conventional = Path(folder_paths.models_dir) / folder / filename
        if conventional.is_file():
            resolved = str(conventional)
    if resolved is None:
        raise RuntimeError(
            f"9B KV identity proof requires {filename}. Run scripts/setup-social-photo-models.ps1, "
            "restart ComfyUI, and try again."
        )
    return Path(resolved)


def _load_reference(filename: str) -> torch.Tensor:
    return comfy_nodes.LoadImage().load_image(filename)[0][:1, :, :, :3]


def _resize_reference(image: torch.Tensor, target_pixels: int = REFERENCE_PIXELS) -> torch.Tensor:
    height, width = image.shape[1:3]
    scale = math.sqrt(target_pixels / max(float(height * width), 1.0))
    target_width = max(64, round(width * scale / 16) * 16)
    target_height = max(64, round(height * scale / 16) * 16)
    return comfy.utils.common_upscale(
        image.movedim(-1, 1), target_width, target_height, "lanczos", "disabled"
    ).movedim(1, -1)


def _largest_face(faces):
    return max(faces, key=lambda face: float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])))


def _identity_diagnostic(image: torch.Tensor, references: list[torch.Tensor]) -> dict:
    reference_embeddings = []
    for reference in references:
        detected = _faces(_tensor_rgb(reference))
        if detected:
            reference_embeddings.append(_embedding(_largest_face(detected)))
    generated_faces = _faces(_tensor_rgb(image))
    if not reference_embeddings or not generated_faces:
        return {
            "score": None,
            "usable_reference_faces": len(reference_embeddings),
            "generated_face_detected": bool(generated_faces),
            "scope": "InsightFace cosine diagnostic only; visual likeness approval is still required.",
        }
    centroid = np.mean(np.stack(reference_embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)
    generated = _largest_face(generated_faces)
    return {
        "score": round(_cosine(_embedding(generated), centroid), 4),
        "usable_reference_faces": len(reference_embeddings),
        "generated_face_detected": True,
        "scope": "InsightFace cosine diagnostic only; visual likeness approval is still required.",
    }


class Klein9BKVIdentityProof:
    """Minimal native FLUX.2 Klein 9B KV identity test.

    This deliberately excludes LoRAs, face swapping, restorers, enhancement passes,
    style stacks, and batch orchestration. It exists to prove native reference
    fidelity before the production workflow is allowed to depend on the model.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_1": (_reference_choices(True), {"image_upload": True}),
                "reference_2": (_reference_choices(False), {"image_upload": True}),
                "reference_3": (_reference_choices(False), {"image_upload": True}),
                "reference_4": (_reference_choices(False), {"image_upload": True}),
                "prompt": (
                    "STRING",
                    {
                        "default": (
                            "Create a new realistic smartphone portrait of the same adult man shown in Picture 1. "
                            "Preserve his identity exactly: face shape, eyes, nose, mouth, ears, hairline, apparent age, "
                            "and natural skin texture. He is wearing a fitted dark navy crew-neck T-shirt, standing on "
                            "a shaded city sidewalk in soft afternoon daylight, waist-up, relaxed posture, slight natural "
                            "smile, looking at the camera. Ordinary recent phone photo, subtle sensor noise, realistic "
                            "skin, no beauty filter, no studio retouching. Do not copy the reference background or clothing."
                        ),
                        "multiline": True,
                    },
                ),
                "width": ("INT", {"default": 768, "min": 512, "max": 1536, "step": 16}),
                "height": ("INT", {"default": 1024, "min": 512, "max": 1536, "step": 16}),
                "seed": ("INT", {"default": 8675309, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        first = kwargs.get("reference_1", "")
        if first in {"", NONE_REFERENCE, "Upload reference 1"}:
            return "Upload at least one genuine reference photo."
        for index in range(1, 5):
            filename = kwargs.get(f"reference_{index}", NONE_REFERENCE)
            if filename == NONE_REFERENCE:
                continue
            if is_known_synthetic_identity_fixture(filename):
                return f"Reference {index} is a generated identity fixture. Use a genuine camera original."
            if not folder_paths.exists_annotated_filepath(filename):
                return f"Reference {index} is not available in ComfyUI input: {filename}"
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("native_image", "output_folder", "report_json")
    FUNCTION = "generate"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True

    @staticmethod
    def _condition_with_references(conditioning, reference_latents):
        result = conditioning
        for latent in reference_latents:
            result = node_helpers.conditioning_set_values(
                result, {"reference_latents": [latent["samples"]]}, append=True
            )
        return result

    def generate(self, reference_1, reference_2, reference_3, reference_4, prompt, width, height, seed):
        model_path = _require_model("diffusion_models", MODEL_NAME)
        clip_path = _require_model("text_encoders", CLIP_NAME)
        vae_path = _require_model("vae", VAE_NAME)
        reference_names = [
            name
            for name in (reference_1, reference_2, reference_3, reference_4)
            if name != NONE_REFERENCE
        ]
        if not reference_names:
            raise RuntimeError("At least one genuine reference photo is required.")

        started = time.perf_counter()
        model = clip = vae = None
        try:
            model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
            model = FluxKVCache.execute(model)[0]
            clip = comfy_nodes.CLIPLoader().load_clip(CLIP_NAME, "flux2", "default")[0]
            vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]

            references = [_load_reference(name) for name in reference_names]
            reference_latents = [
                comfy_nodes.VAEEncode().encode(vae, _resize_reference(reference))[0]
                for reference in references
            ]
            positive = comfy_nodes.CLIPTextEncode().encode(clip, prompt.strip())[0]
            positive = self._condition_with_references(positive, reference_latents)
            latent = EmptyFlux2LatentImage.execute(int(width), int(height), 1)[0]
            noise = RandomNoise.execute(int(seed))[0]
            guider = BasicGuider.execute(model, positive)[0]
            sampler = KSamplerSelect.execute("euler")[0]
            sigmas = Flux2Scheduler.execute(4, int(width), int(height))[0]
            sampled = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
            image = comfy_nodes.VAEDecode().decode(vae, sampled)[0]
            identity_diagnostic = _identity_diagnostic(image, references)

            run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            output_folder = f"klein9b-kv-identity-proof/{run_stamp}"
            report = {
                "schema_version": 1,
                "purpose": "native_identity_proof",
                "model": model_path.name,
                "text_encoder": clip_path.name,
                "vae": vae_path.name,
                "kv_cache": True,
                "steps": 4,
                "sampler": "euler",
                "width": int(width),
                "height": int(height),
                "seed": int(seed),
                "reference_count": len(reference_names),
                "reference_pixels_each": REFERENCE_PIXELS,
                "prompt": prompt.strip(),
                "identity_diagnostic": identity_diagnostic,
                "excluded": ["LoRA", "face swap", "face restoration", "enhancement pass", "style stack"],
                "seconds": round(time.perf_counter() - started, 3),
            }
            report_json = json.dumps(report, indent=2)
            metadata = {"klein9b_kv_identity_proof": report}
            saved = comfy_nodes.SaveImage().save_images(
                image,
                f"{output_folder}/native",
                extra_pnginfo=metadata,
            )
            report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_json, encoding="utf-8")
            summary = (
                f"Native 9B KV proof completed with {len(reference_names)} reference(s) in "
                f"{report['seconds']:.1f}s. Saved to ComfyUI/output/{output_folder}"
            )
            return {
                "ui": {"images": saved["ui"]["images"], "text": (summary,)},
                "result": (image, output_folder, report_json),
            }
        finally:
            del model, clip, vae
            comfy.model_management.unload_all_models()
            comfy.model_management.soft_empty_cache()
