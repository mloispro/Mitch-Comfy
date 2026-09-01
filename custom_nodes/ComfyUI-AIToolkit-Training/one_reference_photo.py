from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

import cv2
import folder_paths
import node_helpers
import numpy as np
import torch

import comfy.utils
import nodes as comfy_nodes
from comfy_extras.nodes_custom_sampler import (
    BasicGuider,
    CFGGuider,
    KSamplerSelect,
    RandomNoise,
    SamplerCustomAdvanced,
)
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler, FluxKVCache


MODEL_NAME = "flux-2-klein-9b-kv-fp8.safetensors"
CLIP_NAME = "qwen_3_8b_fp8mixed.safetensors"
MODEL_4B_BASE_NAME = "flux-2-klein-base-4b-fp8.safetensors"
CLIP_4B_NAME = "qwen_3_4b_fp8_mixed.safetensors"
VAE_NAME = "flux2-vae.safetensors"
IDENTITY_TOKEN = "m1tch_person"
PRODUCTION_LORA_NAME = r"aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors"
PRODUCTION_LORA_STRENGTH = 0.6
PRODUCTION_STEPS = 20
OUTPUT_WIDTH = 768
OUTPUT_HEIGHT = 1024
REFERENCE_PIXELS = 1024 * 1024
PRODUCTION_REFERENCE_PIXELS = 512 * 512
PRODUCTION_REFERENCE_STRATEGY = "Full + face crop 2.4x"
OUTPUT_ROOT = "flux2-one-reference"
EXPERIMENT_OUTPUT_ROOT = "flux2-identity-experiments"
PRODUCTION_SEED = 8675310

IDENTITY_STRATEGIES = {
    "Full photo": ("full", None),
    "Face crop 1.6x": ("face", 1.6),
    "Face crop 2.0x": ("face", 2.0),
    "Face crop 2.4x": ("face", 2.4),
    "Full + face crop 1.6x": ("full_plus_face", 1.6),
    "Full + face crop 2.0x": ("full_plus_face", 2.0),
    "Full + face crop 2.4x": ("full_plus_face", 2.4),
}

REFERENCE_PIXEL_OPTIONS = {
    "0.25 MP": 512 * 512,
    "0.40 MP": 640 * 640,
    "0.64 MP": 800 * 800,
    "1.00 MP": 1024 * 1024,
}

_FACE_ANALYZER = None
_FACE_ANALYZER_LOCK = Lock()

_REJECTED_GENERATED_REFERENCES = {
    "mitch-qwen-id-front.png",
    "mitch-qwen-id-left.png",
    "mitch-qwen-id-right.png",
    "mitch-workbench-qwen-id-front.png",
    "mitch-workbench-qwen-id-left.png",
    "mitch-workbench-qwen-id-right.png",
    "img_2961(1).jpg",
    "mitch-build-anchor-v1.png",
    "mitch-real-body-silhouette.png",
}
_REJECTED_REFERENCE_MARKERS = (
    "chatgpt image",
    "qwen",
    "sdxl",
    "mitch-workbench",
    "full-head",
    "reactor",
    "pulid",
    "identity-build",
    "identity-reference",
    "target",
    "template",
    "mask",
    "plate",
    "candidate",
    "social-photo",
)


def _looks_generated_reference(filename: str) -> bool:
    folded = Path(filename).name.casefold()
    return folded in _REJECTED_GENERATED_REFERENCES or any(
        marker in folded for marker in _REJECTED_REFERENCE_MARKERS
    )


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
        and not _looks_generated_reference(path.name)
    )


def _require_model(folder: str, filename: str) -> None:
    if folder_paths.get_full_path(folder, filename) is not None:
        return
    conventional = Path(folder_paths.models_dir) / folder / filename
    if conventional.is_file():
        return
    raise RuntimeError(f"Missing required FLUX.2 file: {filename}")


def _resize_reference(image: torch.Tensor, target_pixels: int = REFERENCE_PIXELS) -> torch.Tensor:
    """Keep the entire photo while giving FLUX.2 a useful, bounded reference size."""
    height, width = image.shape[1:3]
    scale = math.sqrt(target_pixels / max(float(height * width), 1.0))
    target_width = max(64, round(width * scale / 16) * 16)
    target_height = max(64, round(height * scale / 16) * 16)
    return comfy.utils.common_upscale(
        image.movedim(-1, 1), target_width, target_height, "lanczos", "disabled"
    ).movedim(1, -1)


def _face_analyzer():
    global _FACE_ANALYZER
    with _FACE_ANALYZER_LOCK:
        if _FACE_ANALYZER is None:
            from insightface.app import FaceAnalysis

            model_root = Path.home() / ".insightface"
            recognition_model = model_root / "models" / "antelopev2" / "glintr100.onnx"
            if not recognition_model.is_file():
                raise RuntimeError(
                    "Automatic face focus requires the local AntelopeV2 model at "
                    f"{recognition_model}"
                )
            _FACE_ANALYZER = FaceAnalysis(
                name="antelopev2",
                root=str(model_root),
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection", "recognition", "landmark_3d_68"],
            )
            _FACE_ANALYZER.prepare(ctx_id=-1, det_size=(640, 640))
    return _FACE_ANALYZER


def _face_crop(image: torch.Tensor, expansion: float) -> torch.Tensor:
    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    faces = _face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError("No face was detected in the uploaded reference photo.")
    face = max(
        faces,
        key=lambda item: float(
            (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
        ),
    )
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    face_width = x2 - x1
    face_height = y2 - y1
    side = max(face_width, face_height) * float(expansion)
    center_x = (x1 + x2) * 0.5
    center_y = (y1 + y2) * 0.5 - face_height * 0.12
    left = max(0, int(round(center_x - side * 0.5)))
    top = max(0, int(round(center_y - side * 0.5)))
    right = min(width, int(round(center_x + side * 0.5)))
    bottom = min(height, int(round(center_y + side * 0.5)))
    if right - left < 128 or bottom - top < 128:
        raise RuntimeError("The detected face is too small for automatic face focus.")
    return image[:, top:bottom, left:right, :]


def _face_embedding(image: torch.Tensor, label: str) -> tuple[np.ndarray, float]:
    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    faces = _face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError(f"No face was detected in {label}.")
    face = max(
        faces,
        key=lambda item: float(
            (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
        ),
    )
    embedding = np.asarray(face.normed_embedding, dtype=np.float32)
    embedding /= max(float(np.linalg.norm(embedding)), 1e-8)
    return embedding, float(face.det_score)


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    return float(
        np.dot(left, right)
        / max(float(np.linalg.norm(left) * np.linalg.norm(right)), 1e-8)
    )


def _strategy_references(
    image: torch.Tensor,
    strategy_name: str,
    target_pixels: int = REFERENCE_PIXELS,
) -> list[torch.Tensor]:
    strategy, expansion = IDENTITY_STRATEGIES[strategy_name]
    full = _resize_reference(image, target_pixels)
    if strategy == "full":
        return [full]
    face = _resize_reference(_face_crop(image, float(expansion)), target_pixels)
    if strategy == "face":
        return [face]
    return [full, face]


def _identity_prompt(
    scene_prompt: str,
    reference_count: int = 1,
    identity_token: str = "",
) -> str:
    scene = " ".join(scene_prompt.strip().split())
    if not scene:
        raise ValueError("Describe the new photo you want to create.")
    reference_description = (
        "Picture 1 shows the identity reference."
        if reference_count == 1
        else (
            "Pictures 1 and 2 show the same person from the same source photograph; Picture 2 is a "
            "closer identity view, not a second person."
        )
    )
    token_description = (
        f"The trained identity token for this person is {identity_token.strip()}. "
        if identity_token.strip()
        else ""
    )
    return (
        "Create a new photorealistic photo containing exactly one adult person: the exact same person "
        f"shown in the supplied identity reference. {token_description}{reference_description} "
        "Use the pictures as identity "
        "evidence only. Preserve his unmistakable facial "
        "identity and current apparent age exactly, including face proportions, eye shape and spacing, "
        "eyebrows, nose, mouth, ears, jawline, hairline, hair color, and natural skin texture. Do not age "
        "him up or down. Do not copy the reference background, clothing, pose, framing, lighting, or "
        "expression unless the scene request asks for it. "
        f"New photo request: {scene} "
        "The result must look like a genuine unedited photograph, with physically believable lighting, "
        "natural skin detail, and normal camera texture. No beauty filter, face smoothing, plastic skin, "
        "illustration, CGI, duplicate person, text, logo, or watermark."
    )


def _generate_photo(
    face_reference,
    scene_prompt,
    seed,
    strategy_name,
    output_root,
    reference_pixels=REFERENCE_PIXELS,
    steps=4,
    refine_pass=False,
    identity_retry_threshold=0.0,
    max_attempts=1,
    model_name=MODEL_NAME,
    clip_name=CLIP_NAME,
    lora_name="",
    lora_strength=0.0,
    use_kv_cache=True,
    identity_token="",
    guidance_scale=1.0,
):
    _require_model("diffusion_models", model_name)
    _require_model("text_encoders", clip_name)
    _require_model("vae", VAE_NAME)

    started = time.perf_counter()

    model = comfy_nodes.UNETLoader().load_unet(model_name, "default")[0]
    if use_kv_cache:
        model = FluxKVCache.execute(model)[0]
    if lora_name:
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, lora_name, float(lora_strength)
        )[0]
    clip = comfy_nodes.CLIPLoader().load_clip(clip_name, "flux2", "default")[0]
    vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]

    source_reference = comfy_nodes.LoadImage().load_image(face_reference)[0][:1, :, :, :3]
    references = _strategy_references(source_reference, strategy_name, int(reference_pixels))
    effective_prompt = _identity_prompt(scene_prompt, len(references), identity_token)
    reference_latents = [
        comfy_nodes.VAEEncode().encode(vae, reference)[0]["samples"]
        for reference in references
    ]

    positive = comfy_nodes.CLIPTextEncode().encode(clip, effective_prompt)[0]
    positive = node_helpers.conditioning_set_values(
        positive,
        {"reference_latents": reference_latents},
        append=True,
    )

    latent = EmptyFlux2LatentImage.execute(OUTPUT_WIDTH, OUTPUT_HEIGHT, 1)[0]
    def make_guider(conditioning):
        if float(guidance_scale) > 1.0:
            negative = comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
            return CFGGuider.execute(
                model, conditioning, negative, float(guidance_scale)
            )[0]
        return BasicGuider.execute(model, conditioning)[0]

    guider = make_guider(positive)
    sampler = KSamplerSelect.execute("euler")[0]
    sigmas = Flux2Scheduler.execute(int(steps), OUTPUT_WIDTH, OUTPUT_HEIGHT)[0]
    source_embedding, source_detection_confidence = _face_embedding(
        source_reference, "the uploaded reference photo"
    )

    def sample_photo(attempt_seed: int) -> torch.Tensor:
        noise = RandomNoise.execute(attempt_seed)[0]
        sampled = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        candidate = comfy_nodes.VAEDecode().decode(vae, sampled)[0]

        if not refine_pass:
            return candidate

        candidate_latent = comfy_nodes.VAEEncode().encode(vae, candidate)[0]["samples"]
        refine_prompt = (
            "Create one corrected photorealistic version of Picture 1. Keep Picture 1's location, "
            "composition, clothing, body, pose, gesture, gaze direction, expression, camera angle, "
            "lighting, and background unchanged. Correct only the person's full head and face so he "
            "is unmistakably the exact same person shown in Pictures 2 and 3. Pictures 2 and 3 show "
            "the same identity; Picture 3 is a closer crop, not another person. Match face proportions, "
            "eyes, eyebrows, nose, mouth, ears, jaw, hairline, hair color, current apparent age, and "
            "natural skin texture. Exactly one main person. No beauty filter, plastic skin, text, logo, "
            "or watermark."
        )
        refine_conditioning = comfy_nodes.CLIPTextEncode().encode(clip, refine_prompt)[0]
        refine_conditioning = node_helpers.conditioning_set_values(
            refine_conditioning,
            {"reference_latents": [candidate_latent, *reference_latents]},
            append=True,
        )
        refine_noise = RandomNoise.execute(attempt_seed ^ 0x9E3779B97F4A7C15)[0]
        refine_guider = make_guider(refine_conditioning)
        refine_latent = EmptyFlux2LatentImage.execute(OUTPUT_WIDTH, OUTPUT_HEIGHT, 1)[0]
        refined = SamplerCustomAdvanced.execute(
            refine_noise,
            refine_guider,
            sampler,
            sigmas,
            refine_latent,
        )[0]
        return comfy_nodes.VAEDecode().decode(vae, refined)[0]

    attempts = []
    selected_photo = None
    selected_score = -1.0
    selected_seed = int(seed)
    for offset in range(max(1, int(max_attempts))):
        attempt_seed = (int(seed) + offset) % (1 << 64)
        candidate = sample_photo(attempt_seed)
        try:
            candidate_embedding, detection_confidence = _face_embedding(
                candidate, f"generated candidate {offset + 1}"
            )
            similarity = _cosine_similarity(source_embedding, candidate_embedding)
            error = ""
        except RuntimeError as exc:
            similarity = -1.0
            detection_confidence = 0.0
            error = str(exc)
        attempts.append(
            {
                "attempt": offset + 1,
                "seed": attempt_seed,
                "similarity_to_uploaded_reference": round(similarity, 4),
                "face_detection_confidence": round(detection_confidence, 4),
                "error": error,
            }
        )
        if similarity > selected_score:
            selected_photo = candidate
            selected_score = similarity
            selected_seed = attempt_seed
        if similarity >= float(identity_retry_threshold):
            break

    if selected_photo is None or selected_score < 0:
        raise RuntimeError("No face was detected in any generated candidate.")
    photo = selected_photo

    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    strategy_slug = strategy_name.casefold().replace(" ", "-").replace("+", "plus")
    output_folder = f"{output_root}/{strategy_slug}/{run_stamp}"
    report = {
        "schema_version": 3,
        "purpose": (
            "one_reference_identity_lora_ranked"
            if lora_name
            else "one_reference_identity_native_ranked"
        ),
        "model": model_name,
        "text_encoder": clip_name,
        "vae": VAE_NAME,
        "lora_name": lora_name,
        "lora_strength": round(float(lora_strength), 3),
        "identity_token": identity_token,
        "kv_cache": bool(use_kv_cache),
        "guidance_scale": round(float(guidance_scale), 3),
        "face_reference": face_reference,
        "identity_strategy": strategy_name,
        "derived_reference_count": len(references),
        "reference_pixels_each": int(reference_pixels),
        "scene_prompt": scene_prompt.strip(),
        "effective_prompt": effective_prompt,
        "width": OUTPUT_WIDTH,
        "height": OUTPUT_HEIGHT,
        "steps": int(steps),
        "identity_refine_pass": bool(refine_pass),
        "generation_passes": len(attempts) * (2 if refine_pass else 1),
        "sampler": "euler",
        "seed": int(seed),
        "selected_seed": selected_seed,
        "identity_similarity_to_uploaded_reference": round(selected_score, 4),
        "identity_retry_threshold": round(float(identity_retry_threshold), 4),
        "identity_attempts": attempts,
        "source_face_detection_confidence": round(source_detection_confidence, 4),
        "seconds": round(time.perf_counter() - started, 3),
        "acceptance": "Held-out multi-photo identity evaluation is required.",
    }
    metadata = {"flux2_one_reference": report}
    saved = comfy_nodes.SaveImage().save_images(
        photo,
        f"{output_folder}/photo",
        extra_pnginfo=metadata,
    )
    report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return photo, effective_prompt, output_folder, saved


class Flux2OneReferencePhoto:
    """The smallest useful identity test: one genuine face photo and one scene prompt."""

    @classmethod
    def INPUT_TYPES(cls):
        choices = ["Upload one face photo", *_available_input_images()]
        return {
            "required": {
                "face_reference": (choices, {"image_upload": True}),
                "scene_prompt": (
                    "STRING",
                    {
                        "default": (
                            "A casual waist-up smartphone photo on a shaded city sidewalk in soft "
                            "afternoon daylight, wearing a fitted navy crew-neck T-shirt, relaxed posture, "
                            "small natural smile, looking at the camera."
                        ),
                        "multiline": True,
                    },
                ),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, face_reference, scene_prompt, seed=None):
        if face_reference == "Upload one face photo":
            return "Upload one genuine face photo."
        if _looks_generated_reference(face_reference):
            return "Use a genuine camera photo, not a generated or processed identity fixture."
        if not folder_paths.exists_annotated_filepath(face_reference):
            return f"Reference image is not available in ComfyUI input: {face_reference}"
        if not scene_prompt.strip():
            return "Describe the new photo you want to create."
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("photo", "effective_prompt", "output_folder")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity"
    OUTPUT_NODE = True

    def generate(self, face_reference, scene_prompt):
        photo, effective_prompt, output_folder, saved = _generate_photo(
            face_reference=face_reference,
            scene_prompt=scene_prompt,
            seed=PRODUCTION_SEED,
            # Compact paired views were the validated production setting: they keep
            # identity evidence without making the face look separately rendered.
            strategy_name=PRODUCTION_REFERENCE_STRATEGY,
            output_root=OUTPUT_ROOT,
            reference_pixels=PRODUCTION_REFERENCE_PIXELS,
            steps=PRODUCTION_STEPS,
            refine_pass=False,
            identity_retry_threshold=0.75,
            max_attempts=2,
            model_name=MODEL_4B_BASE_NAME,
            clip_name=CLIP_4B_NAME,
            lora_name=PRODUCTION_LORA_NAME,
            lora_strength=PRODUCTION_LORA_STRENGTH,
            use_kv_cache=False,
            identity_token=IDENTITY_TOKEN,
            guidance_scale=4.0,
        )

        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (f"Saved one-reference photo to ComfyUI/output/{output_folder}",),
            },
            "result": (photo, effective_prompt, output_folder),
        }


class Flux2IdentityStrategyExperiment(Flux2OneReferencePhoto):
    """Internal A/B harness; deliberately absent from the user workflow."""

    @classmethod
    def INPUT_TYPES(cls):
        choices = ["Upload one face photo", *_available_input_images()]
        return {
            "required": {
                "face_reference": (choices, {"image_upload": True}),
                "scene_prompt": (
                    "STRING",
                    {
                        "default": (
                            "A casual waist-up smartphone photo on a shaded city sidewalk in soft "
                            "afternoon daylight, wearing a fitted navy crew-neck T-shirt, relaxed posture, "
                            "small natural smile, looking at the camera."
                        ),
                        "multiline": True,
                    },
                ),
                "identity_strategy": (list(IDENTITY_STRATEGIES),),
                "reference_resolution": (list(REFERENCE_PIXEL_OPTIONS),),
                "steps": ("INT", {"default": 4, "min": 4, "max": 12, "step": 1}),
                "identity_refine_pass": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": 8675310, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        face_reference,
        scene_prompt,
        identity_strategy,
        reference_resolution,
        steps,
        identity_refine_pass,
        seed,
    ):
        if identity_strategy not in IDENTITY_STRATEGIES:
            return f"Unknown identity strategy: {identity_strategy}"
        if reference_resolution not in REFERENCE_PIXEL_OPTIONS:
            return f"Unknown reference resolution: {reference_resolution}"
        return Flux2OneReferencePhoto.VALIDATE_INPUTS(
            face_reference,
            scene_prompt,
            seed,
        )

    RETURN_NAMES = ("photo", "effective_prompt", "output_folder")
    FUNCTION = "generate_experiment"
    CATEGORY = "image/generation/FLUX.2 Identity/Experiments"

    def generate_experiment(
        self,
        face_reference,
        scene_prompt,
        identity_strategy,
        reference_resolution,
        steps,
        identity_refine_pass,
        seed,
    ):
        validation = self.VALIDATE_INPUTS(
            face_reference,
            scene_prompt,
            identity_strategy,
            reference_resolution,
            steps,
            identity_refine_pass,
            seed,
        )
        if validation is not True:
            raise RuntimeError(validation)
        photo, effective_prompt, output_folder, saved = _generate_photo(
            face_reference,
            scene_prompt,
            seed,
            identity_strategy,
            EXPERIMENT_OUTPUT_ROOT,
            REFERENCE_PIXEL_OPTIONS[reference_resolution],
            steps,
            identity_refine_pass,
        )
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (f"Completed identity strategy: {identity_strategy}",),
            },
            "result": (photo, effective_prompt, output_folder),
        }


class Flux2IdentityLoraExperiment(Flux2OneReferencePhoto):
    """Internal checkpoint/strength harness for the public Klein 4B fallback."""

    @classmethod
    def INPUT_TYPES(cls):
        choices = ["Upload one face photo", *_available_input_images()]
        loras = folder_paths.get_filename_list("loras")
        identity_loras = [
            name
            for name in loras
            if "m1tch-flux2-klein-4b-identity-v1" in name.casefold()
        ]
        return {
            "required": {
                "face_reference": (choices, {"image_upload": True}),
                "scene_prompt": (
                    "STRING",
                    {
                        "default": (
                            "A casual waist-up smartphone photo on a shaded city sidewalk in soft "
                            "afternoon daylight, wearing a fitted navy crew-neck T-shirt, relaxed posture, "
                            "small natural smile, looking at the camera."
                        ),
                        "multiline": True,
                    },
                ),
                "lora_name": (identity_loras or ["Publish a checkpoint first"],),
                "lora_strength": (
                    "FLOAT",
                    {"default": 0.8, "min": 0.0, "max": 2.0, "step": 0.05},
                ),
                "steps": ("INT", {"default": 50, "min": 20, "max": 80, "step": 5}),
                "guidance_scale": (
                    "FLOAT",
                    {"default": 4.0, "min": 1.0, "max": 8.0, "step": 0.1},
                ),
                "seed": (
                    "INT",
                    {"default": 8675310, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        face_reference,
        scene_prompt,
        lora_name,
        lora_strength,
        steps,
        guidance_scale,
        seed,
    ):
        validation = Flux2OneReferencePhoto.VALIDATE_INPUTS(
            face_reference, scene_prompt, seed
        )
        if validation is not True:
            return validation
        if folder_paths.get_full_path("loras", lora_name) is None:
            return f"LoRA is not available in ComfyUI: {lora_name}"
        if int(steps) < 20:
            return "FLUX.2 Klein Base evaluation requires at least 20 steps."
        if float(guidance_scale) < 1.0:
            return "guidance_scale must be at least 1.0."
        return True

    RETURN_NAMES = ("photo", "effective_prompt", "output_folder")
    FUNCTION = "generate_lora_experiment"
    CATEGORY = "image/generation/FLUX.2 Identity/Experiments"

    def generate_lora_experiment(
        self,
        face_reference,
        scene_prompt,
        lora_name,
        lora_strength,
        steps,
        guidance_scale,
        seed,
    ):
        validation = self.VALIDATE_INPUTS(
            face_reference,
            scene_prompt,
            lora_name,
            lora_strength,
            steps,
            guidance_scale,
            seed,
        )
        if validation is not True:
            raise RuntimeError(validation)
        photo, effective_prompt, output_folder, saved = _generate_photo(
            face_reference=face_reference,
            scene_prompt=scene_prompt,
            seed=seed,
            strategy_name="Full + face crop 2.0x",
            output_root=f"{EXPERIMENT_OUTPUT_ROOT}/lora-4b",
            reference_pixels=REFERENCE_PIXEL_OPTIONS["1.00 MP"],
            steps=steps,
            refine_pass=False,
            identity_retry_threshold=0.0,
            max_attempts=1,
            model_name=MODEL_4B_BASE_NAME,
            clip_name=CLIP_4B_NAME,
            lora_name=lora_name,
            lora_strength=lora_strength,
            use_kv_cache=False,
            identity_token=IDENTITY_TOKEN,
            guidance_scale=guidance_scale,
        )
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (f"Completed LoRA experiment: {lora_name} @ {lora_strength:.2f}",),
            },
            "result": (photo, effective_prompt, output_folder),
        }
