from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import comfy.model_management
import folder_paths
import node_helpers
import torch

from . import reference_photo_studio as studio
from .reference_photo_studio_v104 import _identity_scope_for_photo
from .scene_objects import count_scene_objects
from .social_photo_studio import _contact_sheet


PROMPT = (
    "Create a new candid smartphone photo of the same adult man shown in Pictures 1 through 4 "
    "walking down a busy city street. Use the pictures only to preserve his identity; do not copy "
    "their poses, clothing, framing, or backgrounds."
)
WIDTH = 896
HEIGHT = 1344
SEED = 8675311
REFERENCE_PIXELS = 409600  # 640 x 640
OUTPUT_ROOT = "flux2-model-benchmark"

KLEIN_9B_MODEL = "flux-2-klein-9b-kv-fp8.safetensors"
KLEIN_9B_CLIP = "qwen_3_8b_fp8mixed.safetensors"
KLEIN_9B_STEPS = 4

DEV_MODEL = "flux2_dev_fp8mixed.safetensors"
DEV_CLIP = "mistral_3_small_flux2_fp4_mixed.safetensors"
DEV_STEPS = 20
DEV_GUIDANCE = 4.0


def _condition_with_references(conditioning, reference_latents):
    return node_helpers.conditioning_set_values(
        conditioning,
        {"reference_latents": reference_latents},
        append=True,
    )


def _generate_model_candidate(
    prepared: dict,
    model_name: str,
    clip_name: str,
    steps: int,
    use_kv_cache: bool,
    guidance: float | None,
) -> tuple[torch.Tensor, dict]:
    started = time.perf_counter()
    model = clip = vae = None
    try:
        model = studio.comfy_nodes.UNETLoader().load_unet(model_name, "default")[0]
        if use_kv_cache:
            model = studio.baseline.FluxKVCache.execute(model)[0]
        model_loaded_at = time.perf_counter()
        clip = studio.comfy_nodes.CLIPLoader().load_clip(
            clip_name, "flux2", "default"
        )[0]
        vae = studio.comfy_nodes.VAELoader().load_vae(studio.baseline.VAE_NAME)[0]
        encoder_vae_loaded_at = time.perf_counter()

        resized_references = [
            studio.baseline._resize_reference(image, REFERENCE_PIXELS)
            for image in prepared["source_images"]
        ]
        reference_latents = [
            studio.comfy_nodes.VAEEncode().encode(vae, image)[0]["samples"]
            for image in resized_references
        ]
        positive = studio.comfy_nodes.CLIPTextEncode().encode(clip, PROMPT)[0]
        if guidance is not None:
            positive = node_helpers.conditioning_set_values(
                positive, {"guidance": float(guidance)}
            )
        positive = _condition_with_references(positive, reference_latents)
        conditioned_at = time.perf_counter()

        guider = studio.baseline.BasicGuider.execute(model, positive)[0]
        sampler = studio.KSamplerSelect.execute("euler")[0]
        sigmas = studio.Flux2Scheduler.execute(steps, WIDTH, HEIGHT)[0]
        latent = studio.EmptyFlux2LatentImage.execute(WIDTH, HEIGHT, 1)[0]
        noise = studio.RandomNoise.execute(SEED)[0]
        sampled = studio.SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent
        )[0]
        sampled_at = time.perf_counter()
        image = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        decoded_at = time.perf_counter()

        identity_scope = _identity_scope_for_photo(
            image,
            prepared["identity_centroid"],
            main_identity_minimum=0.0,
        )
        scene_objects = count_scene_objects(image)
        evaluated_at = time.perf_counter()
        report = {
            "model": model_name,
            "text_encoder": clip_name,
            "vae": studio.baseline.VAE_NAME,
            "steps": steps,
            "guidance": guidance,
            "kv_cache": use_kv_cache,
            "seconds": round(evaluated_at - started, 3),
            "timings_seconds": {
                "model_load": round(model_loaded_at - started, 3),
                "encoder_and_vae_load": round(
                    encoder_vae_loaded_at - model_loaded_at, 3
                ),
                "reference_and_prompt_conditioning": round(
                    conditioned_at - encoder_vae_loaded_at, 3
                ),
                "sampling": round(sampled_at - conditioned_at, 3),
                "vae_decode": round(decoded_at - sampled_at, 3),
                "evaluation": round(evaluated_at - decoded_at, 3),
            },
            "identity_scope": identity_scope,
            "scene_objects": scene_objects,
        }
        return image, report
    finally:
        del model, clip, vae
        comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()


class Flux2ModelBenchmark:
    """Isolated native-reference comparison of Klein 9B KV and FLUX.2 Dev."""

    @classmethod
    def INPUT_TYPES(cls):
        choices = studio._reference_choices()
        return {
            "required": {
                "reference_1": (choices, {"image_upload": True}),
                "reference_2": (choices, {"image_upload": True}),
                "reference_3": (choices, {"image_upload": True}),
                "reference_4": (choices, {"image_upload": True}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, reference_1, reference_2, reference_3, reference_4):
        return studio._validate_reference_names(
            [reference_1, reference_2, reference_3, reference_4]
        )

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = (
        "klein_9b",
        "flux2_dev",
        "comparison_sheet",
        "output_folder",
        "report_json",
    )
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity/Proofs"
    OUTPUT_NODE = True

    def generate(self, reference_1, reference_2, reference_3, reference_4):
        reference_names = [reference_1, reference_2, reference_3, reference_4]
        for folder, filename in (
            ("diffusion_models", KLEIN_9B_MODEL),
            ("text_encoders", KLEIN_9B_CLIP),
            ("diffusion_models", DEV_MODEL),
            ("text_encoders", DEV_CLIP),
            ("vae", studio.baseline.VAE_NAME),
        ):
            studio.baseline._require_model(folder, filename)

        prepared = studio._prepare_sources(
            reference_names,
            "Full photo",
            REFERENCE_PIXELS,
        )
        benchmark_started = time.perf_counter()
        klein_image, klein_report = _generate_model_candidate(
            prepared=prepared,
            model_name=KLEIN_9B_MODEL,
            clip_name=KLEIN_9B_CLIP,
            steps=KLEIN_9B_STEPS,
            use_kv_cache=True,
            guidance=None,
        )
        dev_image, dev_report = _generate_model_candidate(
            prepared=prepared,
            model_name=DEV_MODEL,
            clip_name=DEV_CLIP,
            steps=DEV_STEPS,
            use_kv_cache=False,
            guidance=DEV_GUIDANCE,
        )

        sheet = _contact_sheet(
            [klein_image, dev_image],
            [
                f"Klein 9B KV | {KLEIN_9B_STEPS} steps",
                f"FLUX.2 Dev | {DEV_STEPS} steps",
            ],
            columns=2,
        )
        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"{OUTPUT_ROOT}/{run_stamp}"
        report = {
            "schema_version": 1,
            "purpose": "native_flux2_model_reality_identity_benchmark",
            "comparison_scope": (
                "Same prompt, seed, output size, four genuine identity references, VAE, "
                "sampler, and untouched single-pass output. Each model uses its official "
                "native step/guidance regime."
            ),
            "prompt": PROMPT,
            "width": WIDTH,
            "height": HEIGHT,
            "seed": SEED,
            "sampler": "euler",
            "source_references": reference_names,
            "model_reference_count": len(reference_names),
            "reference_pixels_each": REFERENCE_PIXELS,
            "identity_lora": None,
            "models": {
                "klein_9b_kv": klein_report,
                "flux2_dev": dev_report,
            },
            "total_seconds": round(time.perf_counter() - benchmark_started, 3),
            "excluded": [
                "identity LoRA",
                "scene constraints",
                "object count rules",
                "assigned bystander appearances",
                "scene topology rules",
                "compositing",
                "refiner",
                "background post-processing",
                "phone finish",
                "candidate ranking",
            ],
            "interpretation_note": (
                "Automated metrics cover detected identity, identity leakage, duplicate "
                "secondary faces, people/vehicle counts, and speed. Photorealism and scene "
                "coherence still require side-by-side visual inspection."
            ),
        }
        report_json = json.dumps(report, indent=2)
        metadata = {"flux2_model_benchmark": report}
        saved_klein = studio.comfy_nodes.SaveImage().save_images(
            klein_image, f"{output_folder}/klein-9b-kv", extra_pnginfo=metadata
        )
        saved_dev = studio.comfy_nodes.SaveImage().save_images(
            dev_image, f"{output_folder}/flux2-dev", extra_pnginfo=metadata
        )
        saved_sheet = studio.comfy_nodes.SaveImage().save_images(
            sheet, f"{output_folder}/comparison", extra_pnginfo=metadata
        )
        report_path = (
            Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")

        klein_identity = klein_report["identity_scope"]["main_identity_similarity"]
        dev_identity = dev_report["identity_scope"]["main_identity_similarity"]
        summary = (
            f"9B identity {klein_identity:.4f} in {klein_report['seconds']:.1f}s; "
            f"Dev identity {dev_identity:.4f} in {dev_report['seconds']:.1f}s; "
            f"saved to ComfyUI/output/{output_folder}"
        )
        return {
            "ui": {
                "images": [
                    *saved_sheet["ui"]["images"],
                    *saved_klein["ui"]["images"],
                    *saved_dev["ui"]["images"],
                ],
                "text": (summary,),
            },
            "result": (
                klein_image,
                dev_image,
                sheet,
                output_folder,
                report_json,
            ),
        }
