from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import folder_paths
import node_helpers

from . import reference_photo_studio as studio


PROMPT = "A candid smartphone photo of m1tch_person walking down a busy city street."
LORA_STRENGTH = 0.50
STEPS = 20
WIDTH = 896
HEIGHT = 1344
SEED = 8675311
REFERENCE_PIXELS = 512 * 512
OUTPUT_ROOT = "flux2-minimal-reality-test"


class Flux2MinimalRealityTest:
    """One untouched FLUX.2 frame for separating model realism from workflow logic."""

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
        names = [reference_1, reference_2, reference_3, reference_4]
        return studio._validate_reference_names(names)

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("raw_photo", "output_folder", "report_json")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity/Proofs"
    OUTPUT_NODE = True

    def generate(self, reference_1, reference_2, reference_3, reference_4):
        reference_names = [reference_1, reference_2, reference_3, reference_4]
        studio.baseline._require_model(
            "diffusion_models", studio.baseline.MODEL_4B_BASE_NAME
        )
        studio.baseline._require_model("text_encoders", studio.baseline.CLIP_4B_NAME)
        studio.baseline._require_model("vae", studio.baseline.VAE_NAME)
        started = time.perf_counter()

        prepared = studio._prepare_sources(
            reference_names,
            "Full photo",
            REFERENCE_PIXELS,
        )
        resized_references = [
            studio.baseline._resize_reference(image, REFERENCE_PIXELS)
            for image in prepared["source_images"]
        ]
        model = studio.comfy_nodes.UNETLoader().load_unet(
            studio.baseline.MODEL_4B_BASE_NAME, "default"
        )[0]
        model = studio.comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model,
            studio.baseline.PRODUCTION_LORA_NAME,
            LORA_STRENGTH,
        )[0]
        clip = studio.comfy_nodes.CLIPLoader().load_clip(
            studio.baseline.CLIP_4B_NAME, "flux2", "default"
        )[0]
        vae = studio.comfy_nodes.VAELoader().load_vae(studio.baseline.VAE_NAME)[0]
        reference_latents = [
            studio.comfy_nodes.VAEEncode().encode(vae, image)[0]["samples"]
            for image in resized_references
        ]
        positive = studio.comfy_nodes.CLIPTextEncode().encode(clip, PROMPT)[0]
        positive = node_helpers.conditioning_set_values(
            positive,
            {"reference_latents": reference_latents},
            append=True,
        )
        negative = studio.comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
        guider = studio.CFGGuider.execute(model, positive, negative, 4.0)[0]
        sampler = studio.KSamplerSelect.execute("euler")[0]
        sigmas = studio.Flux2Scheduler.execute(STEPS, WIDTH, HEIGHT)[0]
        latent = studio.EmptyFlux2LatentImage.execute(WIDTH, HEIGHT, 1)[0]
        noise = studio.RandomNoise.execute(SEED)[0]
        sampled = studio.SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent
        )[0]
        photo = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0]

        try:
            embedding, confidence = studio.baseline._face_embedding(
                photo, "minimal reality test"
            )
            identity_score = studio.baseline._cosine_similarity(
                prepared["identity_centroid"], embedding
            )
            identity_error = ""
        except RuntimeError as exc:
            identity_score = -1.0
            confidence = 0.0
            identity_error = str(exc)

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"{OUTPUT_ROOT}/{run_stamp}"
        report = {
            "schema_version": 1,
            "purpose": "untouched_single_pass_flux2_background_reality_test",
            "prompt": PROMPT,
            "model": studio.baseline.MODEL_4B_BASE_NAME,
            "text_encoder": studio.baseline.CLIP_4B_NAME,
            "vae": studio.baseline.VAE_NAME,
            "lora": studio.baseline.PRODUCTION_LORA_NAME,
            "lora_strength": LORA_STRENGTH,
            "steps": STEPS,
            "width": WIDTH,
            "height": HEIGHT,
            "seed": SEED,
            "guidance_scale": 4.0,
            "sampler": "euler",
            "source_references": reference_names,
            "model_reference_count": len(reference_latents),
            "reference_pixels_each": REFERENCE_PIXELS,
            "identity_similarity_to_reference_centroid": round(identity_score, 4),
            "identity_detection_confidence": round(confidence, 4),
            "identity_error": identity_error,
            "excluded": [
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
            "seconds": round(time.perf_counter() - started, 3),
        }
        saved = studio.comfy_nodes.SaveImage().save_images(
            photo,
            f"{output_folder}/raw",
            extra_pnginfo={"flux2_minimal_reality_test": report},
        )
        report_json = json.dumps(report, indent=2)
        report_path = (
            Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    f"Raw single-pass reality test; identity {identity_score:.4f}; "
                    f"saved to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (photo, output_folder, report_json),
        }
