from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import folder_paths
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, ImageOps

import comfy.model_management
import comfy.utils
import nodes as comfy_nodes
from comfy_extras.nodes_custom_sampler import BasicGuider, KSamplerSelect, RandomNoise, SamplerCustomAdvanced
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler, FluxKVCache

from .identity_lock import _cosine, _embedding, _faces, _rgb_tensor, _select_subject, _tensor_rgb, _yaw
from .social_photo_core import (
    ASPECTS,
    CAMERA_LOOKS,
    CAMERA_RELATIONSHIPS,
    MODES,
    REFERENCE_ROLES,
    SCENE_PRESETS,
    build_prompt,
    identity_route,
    is_known_synthetic_identity_fixture,
    load_registry,
    resolve_count,
    resolve_resolution,
    resolve_scenes,
    sanitize_report,
    seed_for,
)


CATEGORY = "image/generation/Social Photo Studio"
SUBJECT_TYPE = "SOCIAL_PHOTO_SUBJECT"
SETTINGS_TYPE = "SOCIAL_PHOTO_SETTINGS"

MODEL_NAME = "flux-2-klein-9b-kv-fp8.safetensors"
MODEL_SHA256 = "33f7da5625a00798349a719742999d3c7dd20c1a7eda14663922c363640728f1"
CLIP_NAME = "qwen_3_8b_fp8mixed.safetensors"
CLIP_SHA256 = "abad16806e0cbabc54e0325d6565847443fe396d5f0be38bb3cd3fe75a1201d6"
VAE_NAME = "flux2-vae.safetensors"
VAE_SHA256 = "d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5"
NONE_REFERENCE = "[none]"
SAME_PERSON_THRESHOLD = 0.35
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
        return ["Upload reference 1", *choices]
    return [NONE_REFERENCE, *choices]


def _require_model(folder: str, filename: str) -> Path:
    resolved = folder_paths.get_full_path(folder, filename)
    if resolved is None:
        conventional = Path(folder_paths.models_dir) / folder / filename
        if conventional.is_file():
            resolved = str(conventional)
    if resolved is None:
        raise RuntimeError(
            f"Social Photo Studio requires {filename}. Run scripts/setup-social-photo-models.ps1 once, "
            "restart ComfyUI, and try again."
        )
    return Path(resolved)


def _largest_face(faces):
    return max(faces, key=lambda face: float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])))


def _face_area_ratio(face, rgb: np.ndarray) -> float:
    area = float(max(face.bbox[2] - face.bbox[0], 1) * max(face.bbox[3] - face.bbox[1], 1))
    return area / max(float(rgb.shape[0] * rgb.shape[1]), 1.0)


def _auto_role(face, rgb: np.ndarray) -> str:
    if _face_area_ratio(face, rgb) <= 0.035 and rgb.shape[0] > rgb.shape[1] * 1.08:
        return "Full Body"
    yaw = _yaw(face)
    if yaw < -15.0:
        return "Left"
    if yaw > 15.0:
        return "Right"
    return "Front"


def _load_reference(filename: str) -> torch.Tensor:
    return comfy_nodes.LoadImage().load_image(filename)[0][:1, :, :, :3]


def _tensor_hash(image: torch.Tensor) -> str:
    return hashlib.sha256(_tensor_rgb(image).tobytes()).hexdigest()[:12]


def _resize_reference(image: torch.Tensor, target_pixels: int = REFERENCE_PIXELS) -> torch.Tensor:
    height, width = image.shape[1:3]
    scale = math.sqrt(target_pixels / max(float(height * width), 1.0))
    target_width = max(64, round(width * scale / 16) * 16)
    target_height = max(64, round(height * scale / 16) * 16)
    return comfy.utils.common_upscale(
        image.movedim(-1, 1), target_width, target_height, "lanczos", "disabled"
    ).movedim(1, -1)


def _resize_output(image: torch.Tensor, width: int, height: int) -> torch.Tensor:
    if image.shape[2] == width and image.shape[1] == height:
        return image
    return comfy.utils.common_upscale(
        image.movedim(-1, 1), width, height, "lanczos", "disabled"
    ).movedim(1, -1)


def _label_font(size: int = 22):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _contact_sheet(images: list[torch.Tensor], labels: list[str], columns: int = 3) -> torch.Tensor:
    if not images:
        return torch.zeros((1, 256, 256, 3), dtype=torch.float32)
    thumb_width, thumb_height, label_height = 384, 384, 42
    columns = max(1, min(columns, len(images)))
    rows = math.ceil(len(images) / columns)
    canvas = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "#141414")
    draw = ImageDraw.Draw(canvas)
    font = _label_font()
    for index, (tensor, label) in enumerate(zip(images, labels)):
        thumb = ImageOps.fit(
            Image.fromarray(_tensor_rgb(tensor)),
            (thumb_width, thumb_height),
            method=Image.Resampling.LANCZOS,
        )
        left = (index % columns) * thumb_width
        top = (index // columns) * (thumb_height + label_height)
        canvas.paste(thumb, (left, top))
        draw.text((left + 10, top + thumb_height + 9), label, fill="white", font=font)
    return _rgb_tensor(np.asarray(canvas, dtype=np.uint8))


def _identity_diagnostic(image: torch.Tensor, centroid: np.ndarray, subject_hint: str) -> dict[str, Any]:
    rgb = _tensor_rgb(image)
    detected = _faces(rgb)
    if not detected:
        return {
            "score": None,
            "face_count": 0,
            "scope": "InsightFace cosine diagnostic only; visual likeness approval is still required.",
        }
    _, score = _select_subject(detected, centroid, rgb.shape[1], subject_hint)
    return {
        "score": round(float(score), 4),
        "face_count": len(detected),
        "scope": "InsightFace cosine diagnostic only; visual likeness approval is still required.",
    }


class SocialPhotoSubjectReferences:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_1": (_reference_choices(True), {"image_upload": True}),
                "reference_1_role": (REFERENCE_ROLES,),
                "reference_2": (_reference_choices(False), {"image_upload": True}),
                "reference_2_role": (REFERENCE_ROLES,),
                "reference_3": (_reference_choices(False), {"image_upload": True}),
                "reference_3_role": (REFERENCE_ROLES,),
                "reference_4": (_reference_choices(False), {"image_upload": True}),
                "reference_4_role": (REFERENCE_ROLES,),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        first = kwargs.get("reference_1", "")
        if first in {"", NONE_REFERENCE, "Upload reference 1"}:
            return "Upload at least one clear genuine face reference."
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

    RETURN_TYPES = (SUBJECT_TYPE, "IMAGE", "STRING")
    RETURN_NAMES = ("subject", "reference_sheet", "validation")
    FUNCTION = "build"
    CATEGORY = CATEGORY

    def build(self, **kwargs):
        entries: list[dict[str, Any]] = []
        warnings: list[str] = []
        for index in range(1, 5):
            filename = kwargs[f"reference_{index}"]
            override = kwargs[f"reference_{index}_role"]
            if filename == NONE_REFERENCE or override == "Ignore":
                continue
            if is_known_synthetic_identity_fixture(filename):
                raise RuntimeError(
                    f"Reference {index} is a generated identity fixture. Use a genuine camera original."
                )
            image = _load_reference(filename)
            rgb = _tensor_rgb(image)
            detected = _faces(rgb)
            face = _largest_face(detected) if detected else None
            if face is None and override != "Full Body":
                raise RuntimeError(
                    f"No face was detected in reference {index}. Choose a clearer photo, mark it Full Body, or Ignore it."
                )
            role = override if override != "Auto" else (_auto_role(face, rgb) if face is not None else "Full Body")
            entries.append(
                {
                    "slot": index,
                    "image": image,
                    "face": face,
                    "embedding": _embedding(face) if face is not None else None,
                    "role": role,
                    "hash": _tensor_hash(image),
                    "face_area_ratio": _face_area_ratio(face, rgb) if face is not None else 0.0,
                    "yaw": _yaw(face) if face is not None else None,
                }
            )

        detected_entries = [entry for entry in entries if entry["face"] is not None]
        if not detected_entries:
            raise RuntimeError("At least one reference must contain a detectable face.")
        primary = max(detected_entries, key=lambda entry: entry["face_area_ratio"])
        for entry in detected_entries:
            similarity = _cosine(entry["embedding"], primary["embedding"])
            entry["primary_similarity"] = similarity
            if similarity < SAME_PERSON_THRESHOLD:
                raise RuntimeError(
                    f"Reference {entry['slot']} appears to show a different person "
                    f"(identity similarity {similarity:.2f}, required {SAME_PERSON_THRESHOLD:.2f})."
                )

        face_entries = [entry for entry in detected_entries if entry["role"] != "Full Body"]
        if not face_entries:
            face_entries = [primary]
            warnings.append("The clearest face in the full-body references was also used as the identity anchor.")
        centroid = np.mean(np.stack([entry["embedding"] for entry in face_entries]), axis=0)
        centroid /= max(float(np.linalg.norm(centroid)), 1e-8)

        body_entries = [entry for entry in entries if entry["role"] == "Full Body"]
        if not body_entries:
            body_status = "not_supplied"
        elif all(entry["face"] is not None for entry in body_entries):
            body_status = "reference_grounded"
        else:
            body_status = "reference_supplied_unverified"
            warnings.append("A full-body reference could not be face-verified and is treated as soft proportion context.")

        priority = {"Front": 0, "General": 1, "Left": 2, "Right": 3, "Full Body": 4}
        face_entries.sort(key=lambda entry: (priority.get(entry["role"], 5), entry["slot"]))
        body_entries.sort(key=lambda entry: entry["slot"])
        face_reference_items = [
            {"slot": entry["slot"], "role": entry["role"], "image": entry["image"]}
            for entry in face_entries
        ]
        body_reference_items = [
            {
                "slot": entry["slot"],
                "role": entry["role"],
                "image": entry["image"],
                "face_verified": entry["face"] is not None,
            }
            for entry in body_entries
        ]
        report_entries = [
            {
                "slot": entry["slot"],
                "role": entry["role"],
                "hash": entry["hash"],
                "yaw": None if entry["yaw"] is None else round(entry["yaw"], 2),
                "face_area_ratio": round(entry["face_area_ratio"], 4),
                "primary_similarity": round(entry.get("primary_similarity", 0.0), 4),
            }
            for entry in entries
        ]
        labels = [f"Ref {entry['slot']} · {entry['role']}" for entry in entries]
        sheet = _contact_sheet([entry["image"] for entry in entries], labels, columns=2)
        subject = {
            "face_reference_items": face_reference_items,
            "body_reference_items": body_reference_items,
            "centroid": centroid,
            "body_status": body_status,
            "reference_report": report_entries,
            "warnings": warnings,
        }
        summary = [
            f"Accepted {len(entries)} genuine reference(s); {len(face_reference_items)} face identity view(s).",
            f"Body reference: {body_status.replace('_', ' ')}.",
            *warnings,
        ]
        return (subject, sheet, "\n".join(summary))


class SocialPhotoSettings:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (MODES,),
                "brief": (
                    "STRING",
                    {
                        "default": "Warm, confident, approachable, current clothing, believable location and moment.",
                        "multiline": True,
                    },
                ),
                "scene_preset": (SCENE_PRESETS,),
                "camera_look": (CAMERA_LOOKS,),
                "camera_relationship": (CAMERA_RELATIONSHIPS,),
                "aspect": (ASPECTS,),
                "photo_count": ("INT", {"default": 0, "min": 0, "max": 9}),
                "seed": ("INT", {"default": 8675309, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = (SETTINGS_TYPE, "STRING")
    RETURN_NAMES = ("settings", "summary")
    FUNCTION = "build"
    CATEGORY = CATEGORY

    def build(self, mode, brief, scene_preset, camera_look, camera_relationship, aspect, photo_count, seed):
        count = resolve_count(mode, photo_count)
        width, height = resolve_resolution(aspect)
        settings = {
            "mode": mode,
            "brief": brief.strip(),
            "scene_preset": scene_preset,
            "camera_look": camera_look,
            "camera_relationship": camera_relationship,
            "aspect": aspect,
            "count_override": int(photo_count),
            "seed": int(seed),
        }
        summary = (
            f"{mode}: {count} photo(s) · {camera_look} · {camera_relationship} · {width}×{height}\n"
            "Native identity: FLUX.2 Klein 9B KV · no LoRA · no face swap"
        )
        return (settings, summary)


class SocialPhotoGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"subject": (SUBJECT_TYPE,), "settings": (SETTINGS_TYPE,)},
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("final_images", "native_images", "contact_sheet", "output_folder", "report_json")
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

    @staticmethod
    def _sample(model, clip, vae, reference_latents, text, seed, width, height):
        positive = comfy_nodes.CLIPTextEncode().encode(clip, text)[0]
        positive = SocialPhotoGenerate._condition_with_references(positive, reference_latents)
        latent = EmptyFlux2LatentImage.execute(width, height, 1)[0]
        noise = RandomNoise.execute(seed)[0]
        guider = BasicGuider.execute(model, positive)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        sigmas = Flux2Scheduler.execute(4, width, height)[0]
        sampled = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        return comfy_nodes.VAEDecode().decode(vae, sampled)[0]

    def generate(self, subject, settings, prompt=None, extra_pnginfo=None):
        model_path = _require_model("diffusion_models", MODEL_NAME)
        clip_path = _require_model("text_encoders", CLIP_NAME)
        vae_path = _require_model("vae", VAE_NAME)
        scenes = resolve_scenes(settings, load_registry())
        width, height = resolve_resolution(settings["aspect"])

        model = clip = vae = None
        final_images: list[torch.Tensor] = []
        reports: list[dict[str, Any]] = []
        ui_images: list[dict[str, Any]] = []
        run_started = time.perf_counter()
        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"social-photo-studio/{run_stamp}"
        progress = comfy.utils.ProgressBar(len(scenes))

        try:
            model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
            model = FluxKVCache.execute(model)[0]
            clip = comfy_nodes.CLIPLoader().load_clip(CLIP_NAME, "flux2", "default")[0]
            vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]
            face_latents = [
                {
                    **item,
                    "latent": comfy_nodes.VAEEncode().encode(vae, _resize_reference(item["image"]))[0],
                }
                for item in subject["face_reference_items"]
            ]
            body_latents = [
                {
                    **item,
                    "latent": comfy_nodes.VAEEncode().encode(vae, _resize_reference(item["image"]))[0],
                }
                for item in subject["body_reference_items"]
            ]

            for scene in scenes:
                scene_started = time.perf_counter()
                generated_width, generated_height = width, height
                used_oom_fallback = False
                selected = list(face_latents)
                selected_slots = {item["slot"] for item in selected}
                body_reference_applied = bool(scene.get("body_reference")) and bool(body_latents)
                if body_reference_applied:
                    selected.extend(item for item in body_latents if item["slot"] not in selected_slots)
                scene_body_status = subject["body_status"] if body_reference_applied else "not_supplied"
                prompt_settings = {
                    **settings,
                    "face_reference_count": len(face_latents),
                    "body_reference_picture": len(selected) if body_reference_applied and len(selected) > len(face_latents) else None,
                }
                scene_prompt = build_prompt(scene, prompt_settings, scene_body_status)
                seed = seed_for(settings["seed"], scene["index"])
                reference_latents = [item["latent"] for item in selected]
                try:
                    native = self._sample(
                        model, clip, vae, reference_latents, scene_prompt, seed, generated_width, generated_height
                    )
                except (torch.cuda.OutOfMemoryError, RuntimeError) as error:
                    if "out of memory" not in str(error).casefold():
                        raise
                    used_oom_fallback = True
                    comfy.model_management.soft_empty_cache()
                    generated_width, generated_height = resolve_resolution(settings["aspect"], fallback=True)
                    native = self._sample(
                        model, clip, vae, reference_latents, scene_prompt, seed, generated_width, generated_height
                    )

                diagnostic = _identity_diagnostic(native, subject["centroid"], scene["subject_position"])
                final = _resize_output(native, width, height)
                final_images.append(final)
                metadata = {
                    **(extra_pnginfo or {}),
                    "social_photo_studio": {
                        "engine": "FLUX.2 Klein 9B KV FP8",
                        "scene": scene["key"],
                        "label": scene["label"],
                        "seed": seed,
                        "prompt": scene_prompt,
                        "identity_diagnostic": diagnostic,
                    },
                }
                saved = comfy_nodes.SaveImage().save_images(
                    final,
                    f"{output_folder}/final/{scene['index'] + 1:02d}-{scene['key']}",
                    prompt=prompt,
                    extra_pnginfo=metadata,
                )
                ui_images.extend(saved["ui"]["images"])
                reports.append(
                    {
                        "index": scene["index"] + 1,
                        "scene": scene["key"],
                        "label": scene["label"],
                        "seed": seed,
                        "prompt": scene_prompt,
                        "resolution": [generated_width, generated_height],
                        "oom_fallback": used_oom_fallback,
                        "reference_conditioning": {
                            "strategy": "native_flux2_multi_reference_kv_cache",
                            "reference_count": len(selected),
                            "face_reference_count": len(face_latents),
                            "body_reference_applied": body_reference_applied,
                            "reference_pixels_each": REFERENCE_PIXELS,
                        },
                        "identity_diagnostic": diagnostic,
                        "post_processing": "none",
                        "seconds": round(time.perf_counter() - scene_started, 3),
                    }
                )
                progress.update(1)
        finally:
            del model, clip, vae
            comfy.model_management.unload_all_models()
            comfy.model_management.soft_empty_cache()

        final_batch = torch.cat(final_images, dim=0)
        labels = [f"{item['index']:02d} · {item['label']}" for item in reports]
        sheet = _contact_sheet(final_images, labels)
        sheet_saved = comfy_nodes.SaveImage().save_images(
            sheet,
            f"{output_folder}/contact-sheet",
            prompt=prompt,
            extra_pnginfo=extra_pnginfo,
        )
        ui_images.extend(sheet_saved["ui"]["images"])
        route = identity_route(
            [item["identity_diagnostic"].get("score") for item in reports],
            len(subject["face_reference_items"]),
        )
        run_report = sanitize_report(
            {
                "schema_version": 2,
                "output_folder": output_folder,
                "mode": settings["mode"],
                "settings": settings,
                "models": {
                    "diffusion": {"name": model_path.name, "sha256": MODEL_SHA256},
                    "text_encoder": {"name": clip_path.name, "sha256": CLIP_SHA256},
                    "vae": {"name": vae_path.name, "sha256": VAE_SHA256},
                },
                "engine": {
                    "name": "FLUX.2 Klein 9B KV FP8",
                    "steps": 4,
                    "sampler": "euler",
                    "kv_cache": True,
                    "lora": None,
                    "face_swap": None,
                    "post_processing": None,
                },
                "reference_report": subject["reference_report"],
                "body_status": subject["body_status"],
                "warnings": subject["warnings"],
                "identity_route": route,
                "images": reports,
                "total_seconds": round(time.perf_counter() - run_started, 3),
            }
        )
        report_json = json.dumps(run_report, indent=2, default=float)
        report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")
        summary = (
            f"Generated {len(final_images)} native 9B KV photo(s) in {run_report['total_seconds']:.1f}s. "
            f"{route['recommendation']} Saved to ComfyUI/output/{output_folder}"
        )
        return {
            "ui": {"images": ui_images, "text": (summary,)},
            "result": (final_batch, final_batch, sheet, output_folder, report_json),
        }
