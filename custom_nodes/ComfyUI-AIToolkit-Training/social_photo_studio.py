from __future__ import annotations

import hashlib
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import folder_paths
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, ImageOps

import comfy.model_management
import comfy.utils
import nodes as comfy_nodes
from comfy_extras.nodes_custom_sampler import CFGGuider, KSamplerSelect, RandomNoise, SamplerCustomAdvanced
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler, FluxKVCache

from .identity_lock import (
    _composite,
    _cosine,
    _embedding,
    _faces,
    _head_crop,
    _rgb_tensor,
    _select_subject,
    _tensor_rgb,
    _yaw,
)
from .social_photo_core import (
    ASPECTS,
    CAMERA_LOOKS,
    CAMERA_RELATIONSHIPS,
    IDENTITY_FINISHES,
    MODES,
    NEGATIVE_PROMPT,
    REFERENCE_ROLES,
    SCENE_PRESETS,
    build_prompt,
    load_registry,
    resolve_count,
    resolve_resolution,
    resolve_scenes,
    sanitize_report,
    seed_for,
    validate_klein_4b_lora,
)


CATEGORY = "image/generation/Social Photo Studio"
SUBJECT_TYPE = "SOCIAL_PHOTO_SUBJECT"
SETTINGS_TYPE = "SOCIAL_PHOTO_SETTINGS"

MODEL_NAME = "flux-2-klein-4b-fp8.safetensors"
MODEL_SHA256 = "97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6"
CLIP_NAME = "qwen_3_4b_fp8_mixed.safetensors"
VAE_NAME = "flux2-vae.safetensors"
VAE_SHA256 = "d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5"
SWAP_MODEL = "inswapper_128.onnx"
FACE_RESTORE_MODEL = "GPEN-BFR-512.onnx"
NONE_REFERENCE = "[none]"
NONE_LORA = "None"
SAME_PERSON_THRESHOLD = 0.35
IDENTITY_IMPROVEMENT = 0.03


def _available_input_images() -> list[str]:
    root = Path(folder_paths.get_input_directory())
    if not root.is_dir():
        return []
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in extensions
    )


def _reference_choices(required: bool) -> list[str]:
    choices = _available_input_images()
    if required:
        return choices or ["Upload reference 1"]
    return [NONE_REFERENCE, *choices]


def _lora_choices() -> list[str]:
    names = folder_paths.get_filename_list("loras")
    preferred = sorted(
        names,
        key=lambda name: (
            "klein" not in name.casefold(),
            "mtch35" not in name.casefold(),
            name.casefold(),
        ),
    )
    return [NONE_LORA, *preferred]


def _require_model(folder: str, filename: str, setup_hint: str = "scripts/setup-social-photo-models.ps1") -> Path:
    resolved = folder_paths.get_full_path(folder, filename)
    if resolved is None:
        conventional = Path(folder_paths.models_dir) / folder / filename
        if conventional.is_file():
            resolved = str(conventional)
    if resolved is None:
        raise RuntimeError(
            f"Social Photo Studio requires {filename}. Run {setup_hint} once, restart ComfyUI, and try again."
        )
    return Path(resolved)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _largest_face(faces):
    return max(faces, key=lambda face: float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])))


def _crop_geometry_metrics(original_crop: np.ndarray, candidate_crop: np.ndarray, centroid: np.ndarray) -> dict[str, Any]:
    """Validate the edited subject while tolerating unchanged background faces."""
    original_faces = _faces(original_crop)
    candidate_faces = _faces(candidate_crop)
    if not original_faces or not candidate_faces:
        return {
            "valid": False,
            "reason": "edited_subject_face_missing",
            "original_face_count": len(original_faces),
            "candidate_face_count": len(candidate_faces),
        }
    original = _largest_face(original_faces)
    generated = _largest_face(candidate_faces)
    identity = _cosine(_embedding(generated), centroid)
    original_identity = _cosine(_embedding(original), centroid)
    original_pose = np.asarray(getattr(original, "pose", [0.0, 0.0, 0.0]), dtype=np.float32)
    generated_pose = np.asarray(getattr(generated, "pose", [0.0, 0.0, 0.0]), dtype=np.float32)
    pose_delta = float(np.linalg.norm(generated_pose - original_pose))
    original_box = np.asarray(original.bbox, dtype=np.float32)
    generated_box = np.asarray(generated.bbox, dtype=np.float32)
    original_center = (original_box[:2] + original_box[2:]) * 0.5
    generated_center = (generated_box[:2] + generated_box[2:]) * 0.5
    original_size = np.maximum(original_box[2:] - original_box[:2], 1.0)
    generated_size = np.maximum(generated_box[2:] - generated_box[:2], 1.0)
    center_delta = float(np.linalg.norm((generated_center - original_center) / original_size))
    scale_delta = float(np.max(np.abs(generated_size / original_size - 1.0)))
    valid = pose_delta <= 24.0 and center_delta <= 0.28 and scale_delta <= 0.38
    penalty = max(0.0, pose_delta - 7.0) * 0.0025 + center_delta * 0.08 + scale_delta * 0.08
    return {
        "valid": bool(valid),
        "reason": "ok" if valid else "pose_or_geometry_drift",
        "identity": identity,
        "original_identity": original_identity,
        "pose_delta": pose_delta,
        "center_delta": center_delta,
        "scale_delta": scale_delta,
        "selection_score": identity - penalty,
        "original_face_count": len(original_faces),
        "candidate_face_count": len(candidate_faces),
    }


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


def _head_reference(rgb: np.ndarray, face, size: int = 640) -> torch.Tensor:
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    face_width = max(x2 - x1, 1.0)
    face_height = max(y2 - y1, 1.0)
    side = max(face_width, face_height) * 2.05
    center_x = (x1 + x2) * 0.5
    center_y = (y1 + y2) * 0.5 - face_height * 0.12
    box = (
        max(0, int(center_x - side * 0.5)),
        max(0, int(center_y - side * 0.5)),
        min(width, int(center_x + side * 0.5)),
        min(height, int(center_y + side * 0.5)),
    )
    crop = Image.fromarray(rgb).crop(box)
    crop = ImageOps.fit(crop, (size, size), method=Image.Resampling.LANCZOS)
    return _rgb_tensor(np.asarray(crop, dtype=np.uint8))


def _label_font(size: int = 22):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _image_contact_sheet(images: list[torch.Tensor], labels: list[str], columns: int = 3) -> torch.Tensor:
    if not images:
        return torch.zeros((1, 256, 256, 3), dtype=torch.float32)
    thumb_width, thumb_height, label_height = 384, 384, 42
    rows = math.ceil(len(images) / columns)
    canvas = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "#141414")
    draw = ImageDraw.Draw(canvas)
    font = _label_font()
    for index, (tensor, label) in enumerate(zip(images, labels)):
        rgb = _tensor_rgb(tensor)
        thumb = ImageOps.fit(Image.fromarray(rgb), (thumb_width, thumb_height), method=Image.Resampling.LANCZOS)
        left = (index % columns) * thumb_width
        top = (index // columns) * (thumb_height + label_height)
        canvas.paste(thumb, (left, top))
        draw.text((left + 10, top + thumb_height + 9), label, fill="white", font=font)
    return _rgb_tensor(np.asarray(canvas, dtype=np.uint8))


def _load_reference(filename: str) -> torch.Tensor:
    return comfy_nodes.LoadImage().load_image(filename)[0][:1]


def _tensor_hash(image: torch.Tensor) -> str:
    return hashlib.sha256(_tensor_rgb(image).tobytes()).hexdigest()[:12]


def _resize_reference(image: torch.Tensor, target_pixels: int = 1024 * 1024) -> torch.Tensor:
    image = image[:1, :, :, :3]
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
    return comfy.utils.common_upscale(image.movedim(-1, 1), width, height, "lanczos", "disabled").movedim(1, -1)


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
            return "Upload at least one clear face reference."
        for index in range(1, 5):
            filename = kwargs.get(f"reference_{index}", NONE_REFERENCE)
            if filename == NONE_REFERENCE:
                continue
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
            image = _load_reference(filename)
            rgb = _tensor_rgb(image)
            detected = _faces(rgb)
            face = _largest_face(detected) if detected else None
            if face is None and override != "Full Body":
                raise RuntimeError(
                    f"No face was detected in reference {index}. Choose a clearer image, mark it Full Body, or Ignore it."
                )
            role = override if override != "Auto" else (_auto_role(face, rgb) if face is not None else "Full Body")
            entries.append(
                {
                    "slot": index,
                    "image": image,
                    "rgb": rgb,
                    "face": face,
                    "embedding": _embedding(face) if face is not None else None,
                    "role": role,
                    "override": override,
                    "hash": _tensor_hash(image),
                    "face_area_ratio": _face_area_ratio(face, rgb) if face is not None else 0.0,
                    "yaw": _yaw(face) if face is not None else None,
                }
            )

        detected_entries = [entry for entry in entries if entry["face"] is not None]
        if not detected_entries:
            raise RuntimeError("At least one reference must contain a detectable face.")
        primary = max(detected_entries, key=lambda entry: entry["face_area_ratio"])
        centroid_members = []
        for entry in detected_entries:
            similarity = _cosine(entry["embedding"], primary["embedding"])
            entry["primary_similarity"] = similarity
            if similarity < SAME_PERSON_THRESHOLD:
                raise RuntimeError(
                    f"Reference {entry['slot']} appears to show a different person "
                    f"(identity similarity {similarity:.2f}, required {SAME_PERSON_THRESHOLD:.2f})."
                )
            if entry["role"] != "Full Body":
                centroid_members.append(entry["embedding"])

        if not centroid_members:
            primary["role"] = "General"
            centroid_members.append(primary["embedding"])
            warnings.append("All references looked wide/full-body; the clearest detected face was promoted to General.")
        centroid = np.mean(np.stack(centroid_members), axis=0)
        centroid /= max(float(np.linalg.norm(centroid)), 1e-8)

        face_references = [
            _head_reference(entry["rgb"], entry["face"])
            for entry in entries
            if entry["face"] is not None and entry["role"] != "Full Body"
        ]
        body_entries = [entry for entry in entries if entry["role"] == "Full Body"]
        if not body_entries:
            body_status = "not_supplied"
        elif all(entry["face"] is not None for entry in body_entries):
            body_status = "reference_grounded"
        else:
            body_status = "reference_supplied_unverified"
            warnings.append("A full-body reference could not be face-verified and is treated as soft context only.")

        priority = {"Front": 0, "General": 1, "Left": 2, "Right": 3, "Full Body": 4}
        entries.sort(key=lambda entry: (priority.get(entry["role"], 5), entry["slot"]))
        labels = [f"Ref {entry['slot']} · {entry['role']}" for entry in entries]
        sheet = _image_contact_sheet([entry["image"] for entry in entries], labels, columns=2)
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
        subject = {
            "references": [entry["image"] for entry in entries],
            "face_references": face_references,
            "centroid": centroid,
            "body_status": body_status,
            "reference_report": report_entries,
            "warnings": warnings,
        }
        summary = [f"Accepted {len(entries)} reference(s); {len(face_references)} usable face angle(s)."]
        summary.append(f"Body identity status: {body_status.replace('_', ' ')}.")
        summary.extend(warnings)
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
                "identity_finish": (IDENTITY_FINISHES,),
                "identity_lora": (_lora_choices(),),
                "lora_strength": ("FLOAT", {"default": 0.85, "min": 0.0, "max": 1.5, "step": 0.05}),
                "lora_trigger": ("STRING", {"default": ""}),
                "save_debug_intermediates": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = (SETTINGS_TYPE, "STRING")
    RETURN_NAMES = ("settings", "summary")
    FUNCTION = "build"
    CATEGORY = CATEGORY

    def build(
        self,
        mode,
        brief,
        scene_preset,
        camera_look,
        camera_relationship,
        aspect,
        photo_count,
        seed,
        identity_finish,
        identity_lora,
        lora_strength,
        lora_trigger,
        save_debug_intermediates,
    ):
        count = resolve_count(mode, photo_count)
        settings = {
            "mode": mode,
            "brief": brief.strip(),
            "scene_preset": scene_preset,
            "camera_look": camera_look,
            "camera_relationship": camera_relationship,
            "aspect": aspect,
            "count_override": int(photo_count),
            "seed": int(seed),
            "identity_finish": identity_finish,
            "identity_lora": identity_lora,
            "lora_strength": float(lora_strength),
            "lora_trigger": lora_trigger.strip(),
            "save_debug_intermediates": bool(save_debug_intermediates),
        }
        width, height = resolve_resolution(aspect)
        summary = (
            f"{mode}: {count} photo(s) · {camera_look} · {camera_relationship} · {width}×{height}\n"
            f"Identity finish: {identity_finish} · LoRA: {identity_lora}"
        )
        return (settings, summary)


class SocialPhotoGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "subject": (SUBJECT_TYPE,),
                "settings": (SETTINGS_TYPE,),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

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
        negative = comfy_nodes.CLIPTextEncode().encode(clip, NEGATIVE_PROMPT)[0]
        positive = SocialPhotoGenerate._condition_with_references(positive, reference_latents)
        negative = SocialPhotoGenerate._condition_with_references(negative, reference_latents)
        latent = EmptyFlux2LatentImage.execute(width, height, 1)[0]
        noise = RandomNoise.execute(seed)[0]
        guider = CFGGuider.execute(model, positive, negative, 1.0)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        sigmas = Flux2Scheduler.execute(4, width, height)[0]
        sampled = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        return comfy_nodes.VAEDecode().decode(vae, sampled)[0]

    @staticmethod
    def _build_face_model(face_references: list[torch.Tensor]):
        node_class = comfy_nodes.NODE_CLASS_MAPPINGS.get("ReActorBuildFaceModel")
        if node_class is None:
            raise RuntimeError("ReActorBuildFaceModel is unavailable. Restart ComfyUI after installing ReActor.")
        images = torch.cat(face_references, dim=0)
        return node_class().blend_faces(False, False, "social-photo-runtime", "Mean", images=images)[0]

    @staticmethod
    def _identity_finish(image, face_model, centroid, mode: str, subject_hint: str):
        original_rgb = _tensor_rgb(image)
        original_faces = _faces(original_rgb)
        if not original_faces:
            return image, {
                "accepted": False,
                "reason": "native_face_not_detected",
                "native_identity": None,
                "final_identity": None,
            }
        target, native_identity = _select_subject(original_faces, centroid, original_rgb.shape[1], subject_hint)
        ordered = sorted(original_faces, key=lambda face: float(face.bbox[0]))
        target_index = next(index for index, face in enumerate(ordered) if face is target)
        target_crop, target_box, target_mask = _head_crop(original_rgb, target, 2.05)
        crop_tensor = _rgb_tensor(target_crop)

        options_class = comfy_nodes.NODE_CLASS_MAPPINGS.get("ReActorOptions")
        boost_class = comfy_nodes.NODE_CLASS_MAPPINGS.get("ReActorFaceBoost")
        swap_class = comfy_nodes.NODE_CLASS_MAPPINGS.get("ReActorFaceSwapOpt")
        weight_class = comfy_nodes.NODE_CLASS_MAPPINGS.get("ReActorSetWeight")
        if None in {options_class, boost_class, swap_class, weight_class}:
            raise RuntimeError("Required ReActor nodes are unavailable. Restart ComfyUI and run verification.")
        # Blend generated geometry with reference identity conservatively so the
        # finish strengthens recognition without stamping on a reference pose.
        _, adaptive_face_model = weight_class().set_weight(
            crop_tensor, "50%", face_model=face_model
        )
        options = options_class().execute(
            "large-small", "0", "no", "large-small", "0", "no", 0, True
        )[0]
        boost = boost_class().execute(True, FACE_RESTORE_MODEL, "Lanczos", 0.45, 0.5, False)[0]
        candidate = swap_class().execute(
            True,
            crop_tensor,
            SWAP_MODEL,
            "retinaface_resnet50",
            "none",
            1.0,
            0.5,
            face_model=adaptive_face_model,
            options=options,
            face_boost=boost,
        )[0]
        candidate_crop = _tensor_rgb(candidate)
        geometry = _crop_geometry_metrics(target_crop, candidate_crop, centroid)
        candidate_rgb, _ = _composite(original_rgb, candidate_crop, target_box, target_mask, feather=12)
        candidate = _rgb_tensor(candidate_rgb)
        candidate_faces = _faces(candidate_rgb)
        if not candidate_faces:
            return image, {
                "accepted": False,
                "reason": "finished_face_not_detected",
                "native_identity": native_identity,
                "final_identity": native_identity,
                "native_face_count": len(original_faces),
                "candidate_face_count": 0,
            }
        _, candidate_identity = _select_subject(candidate_faces, centroid, candidate_rgb.shape[1], subject_hint)
        improvement = candidate_identity - native_identity
        geometry_safe = bool(geometry.get("valid"))
        accepted = geometry_safe and (mode == "Force ReActor" or improvement >= IDENTITY_IMPROVEMENT)
        if not geometry_safe:
            reason = "pose_or_geometry_drift"
        elif accepted and mode == "Force ReActor":
            reason = "forced_safe_swap"
        elif accepted:
            reason = "identity_improved"
        else:
            reason = "no_safe_identity_improvement"
        return (candidate if accepted else image), {
            "accepted": accepted,
            "reason": reason,
            "native_identity": native_identity,
            "candidate_identity": candidate_identity,
            "final_identity": candidate_identity if accepted else native_identity,
            "improvement": improvement,
            "geometry": geometry,
            "target_left_to_right_index": target_index,
            "native_face_count": len(original_faces),
            "candidate_face_count": len(candidate_faces),
        }

    def generate(self, subject, settings, prompt=None, extra_pnginfo=None):
        model_path = _require_model("diffusion_models", MODEL_NAME)
        _require_model("text_encoders", CLIP_NAME)
        vae_path = _require_model("vae", VAE_NAME)
        if settings["identity_finish"] != "Native Only":
            _require_model("insightface", SWAP_MODEL)
            _require_model("facerestore_models", FACE_RESTORE_MODEL)
        scenes = resolve_scenes(settings, load_registry())
        width, height = resolve_resolution(settings["aspect"])

        model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
        lora_report = {"name": NONE_LORA, "strength": 0.0, "trigger": ""}
        if settings["identity_lora"] != NONE_LORA and settings["lora_strength"] > 0:
            lora_path = Path(folder_paths.get_full_path_or_raise("loras", settings["identity_lora"]))
            compatibility = validate_klein_4b_lora(lora_path)
            model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
                model, settings["identity_lora"], settings["lora_strength"]
            )[0]
            lora_report = {
                "name": settings["identity_lora"],
                "strength": settings["lora_strength"],
                "trigger": settings["lora_trigger"],
                "sha256": _sha256(lora_path),
                "compatibility": compatibility,
            }
        model = FluxKVCache.execute(model)[0]
        clip = comfy_nodes.CLIPLoader().load_clip(CLIP_NAME, "flux2", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]

        reference_latents = [
            comfy_nodes.VAEEncode().encode(vae, _resize_reference(reference))[0]
            for reference in subject["references"]
        ]
        face_model = None
        if settings["identity_finish"] != "Native Only":
            face_model = self._build_face_model(subject["face_references"])

        native_images: list[torch.Tensor] = []
        final_images: list[torch.Tensor] = []
        reports: list[dict[str, Any]] = []
        ui_images: list[dict[str, Any]] = []
        progress = comfy.utils.ProgressBar(len(scenes))
        run_started = time.perf_counter()
        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"social-photo-studio/{run_stamp}"

        try:
            for scene in scenes:
                scene_started = time.perf_counter()
                generated_width, generated_height = width, height
                used_oom_fallback = False
                scene_prompt = build_prompt(scene, settings, subject["body_status"])
                seed = seed_for(settings["seed"], scene["index"])
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

                finish_report = {
                    "accepted": False,
                    "reason": "native_only",
                    "native_identity": None,
                    "final_identity": None,
                }
                final = native
                if face_model is not None:
                    final, finish_report = self._identity_finish(
                        native, face_model, subject["centroid"], settings["identity_finish"], scene["subject_position"]
                    )
                else:
                    native_rgb = _tensor_rgb(native)
                    native_faces = _faces(native_rgb)
                    if native_faces:
                        _, native_identity = _select_subject(
                            native_faces, subject["centroid"], native_rgb.shape[1], scene["subject_position"]
                        )
                        finish_report.update(
                            {
                                "native_identity": native_identity,
                                "final_identity": native_identity,
                                "face_count": len(native_faces),
                            }
                        )
                native = _resize_output(native, width, height)
                final = _resize_output(final, width, height)
                native_images.append(native)
                final_images.append(final)

                metadata = {
                    **(extra_pnginfo or {}),
                    "social_photo_studio": {
                        "scene": scene["key"],
                        "label": scene["label"],
                        "seed": seed,
                        "prompt": scene_prompt,
                        "body_status": subject["body_status"],
                        "identity_finish": finish_report,
                    },
                }
                saved = comfy_nodes.SaveImage().save_images(
                    final,
                    f"{output_folder}/final/{scene['index'] + 1:02d}-{scene['key']}",
                    prompt=prompt,
                    extra_pnginfo=metadata,
                )
                ui_images.extend(saved["ui"]["images"])
                if settings["save_debug_intermediates"]:
                    comfy_nodes.SaveImage().save_images(
                        native,
                        f"{output_folder}/debug-native/{scene['index'] + 1:02d}-{scene['key']}",
                        prompt=prompt,
                        extra_pnginfo=metadata,
                    )
                reports.append(
                    {
                        "index": scene["index"] + 1,
                        "scene": scene["key"],
                        "label": scene["label"],
                        "seed": seed,
                        "prompt": scene_prompt,
                        "resolution": [generated_width, generated_height],
                        "oom_fallback": used_oom_fallback,
                        "identity_finish": finish_report,
                        "seconds": round(time.perf_counter() - scene_started, 3),
                    }
                )
                progress.update(1)
        finally:
            del model, clip, vae
            comfy.model_management.unload_all_models()
            comfy.model_management.soft_empty_cache()

        native_batch = torch.cat(native_images, dim=0)
        final_batch = torch.cat(final_images, dim=0)
        labels = [f"{report['index']:02d} · {report['label']}" for report in reports]
        contact_sheet = _image_contact_sheet(final_images, labels)
        sheet_saved = comfy_nodes.SaveImage().save_images(
            contact_sheet,
            f"{output_folder}/contact-sheet",
            prompt=prompt,
            extra_pnginfo=extra_pnginfo,
        )
        ui_images.extend(sheet_saved["ui"]["images"])

        run_report = sanitize_report(
            {
                "schema_version": 1,
                "output_folder": output_folder,
                "mode": settings["mode"],
                "settings": settings,
                "models": {
                    "diffusion": {"name": model_path.name, "sha256": MODEL_SHA256},
                    "text_encoder": {"name": CLIP_NAME},
                    "vae": {"name": vae_path.name, "sha256": VAE_SHA256},
                    "identity_lora": lora_report,
                    "face_finish": {"swap": SWAP_MODEL, "restorer": FACE_RESTORE_MODEL},
                },
                "reference_report": subject["reference_report"],
                "body_status": subject["body_status"],
                "warnings": subject["warnings"],
                "images": reports,
                "total_seconds": round(time.perf_counter() - run_started, 3),
            }
        )
        report_json = json.dumps(run_report, indent=2, default=float)
        report_path = Path(folder_paths.get_output_directory()) / Path(output_folder) / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")
        accepted = sum(bool(item["identity_finish"].get("accepted")) for item in reports)
        summary = (
            f"Generated {len(final_images)} photo(s) in {run_report['total_seconds']:.1f}s. "
            f"Identity finish accepted on {accepted}. Saved to ComfyUI/output/{output_folder}"
        )
        return {
            "ui": {"images": ui_images, "text": (summary,)},
            "result": (final_batch, native_batch, contact_sheet, output_folder, report_json),
        }
