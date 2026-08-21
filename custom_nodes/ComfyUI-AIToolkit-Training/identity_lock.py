from __future__ import annotations

import json
import hashlib
import math
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

import cv2
import folder_paths
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter, ImageOps

import comfy.model_management
import comfy.utils
import nodes as comfy_nodes
from comfy_extras.nodes_model_advanced import ModelSamplingAuraFlow


IDENTITY_CONFIG_TYPE = "AITK_IDENTITY_LOCK_CONFIG"

QWEN_MODEL = "qwen_image_edit_2511_fp8mixed.safetensors"
QWEN_CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
QWEN_VAE = "qwen_image_vae.safetensors"
QWEN_LIGHTNING = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
QWEN_ANGLES = "qwen-image-edit-2511-multiple-angles-lora.safetensors"

REFERENCE_MODES = ["Automatic yaw", "Force front", "Force left", "Force right"]
IMAGE_SCOPES = ["All images", *[f"Image {index} only" for index in range(1, 10)]]
SUBJECT_POSITIONS = ["Auto identity match", "Center", "Left", "Right"]
SELECTION_MODES = ["Auto", "Original", "Candidate A", "Candidate B"]

DEFAULT_INSTRUCTION = (
    "Replace the central man in Picture 1 with the same man from Picture 2; preserve Picture 1's pose, expression, "
    "gaze, lighting, clothing, body, other people, background, and composition. Match Picture 2's identity and full "
    "head geometry, including skull silhouette, forehead, hairline, ears, jaw, chin, cheekbones, eyes, nose, and mouth. "
    "Do not add, remove, duplicate, or move any person. Return one photorealistic edited version of Picture 1."
)

_ANALYZER = None
_ANALYZER_LOCK = Lock()


def _require(folder: str, filename: str) -> None:
    if folder_paths.get_full_path(folder, filename) is None:
        raise RuntimeError(f"Identity Lock requires the existing model file: {filename}")


def _face_analyzer():
    global _ANALYZER
    with _ANALYZER_LOCK:
        if _ANALYZER is None:
            from insightface.app import FaceAnalysis

            model_root = Path.home() / ".insightface"
            if not (model_root / "models" / "antelopev2" / "glintr100.onnx").is_file():
                raise RuntimeError(
                    "InsightFace antelopev2 is not installed at "
                    f"{model_root / 'models' / 'antelopev2'}. Identity Lock will not download models automatically."
                )
            _ANALYZER = FaceAnalysis(
                name="antelopev2",
                root=str(model_root),
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection", "recognition", "landmark_3d_68"],
            )
            _ANALYZER.prepare(ctx_id=-1, det_size=(640, 640))
    return _ANALYZER


def _tensor_rgb(image: torch.Tensor) -> np.ndarray:
    tensor = image.detach().float().cpu()
    if tensor.ndim == 4:
        tensor = tensor[0]
    return np.clip(tensor.numpy() * 255.0, 0, 255).astype(np.uint8)


def _rgb_tensor(image: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(np.ascontiguousarray(image).astype(np.float32) / 255.0).unsqueeze(0)


def _faces(rgb: np.ndarray):
    return _face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def _embedding(face) -> np.ndarray:
    value = np.asarray(face.normed_embedding, dtype=np.float32)
    return value / max(float(np.linalg.norm(value)), 1e-8)


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right) / max(float(np.linalg.norm(left) * np.linalg.norm(right)), 1e-8))


def _reference_centroid(references: list[torch.Tensor]) -> tuple[np.ndarray, list[np.ndarray]]:
    embeddings = []
    rgbs = []
    for index, reference in enumerate(references, start=1):
        rgb = _tensor_rgb(reference)
        detected = _faces(rgb)
        if not detected:
            raise RuntimeError(f"No face found in genuine identity reference {index}.")
        face = max(detected, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
        embeddings.append(_embedding(face))
        rgbs.append(rgb)
    centroid = np.mean(np.stack(embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)
    return centroid, rgbs


def _position_prior(face, width: int, hint: str) -> float:
    center = float(face.bbox[0] + face.bbox[2]) * 0.5 / max(width, 1)
    if hint == "Center":
        target = 0.5
    elif hint == "Left":
        target = 0.25
    elif hint == "Right":
        target = 0.75
    else:
        return 0.0
    return max(-0.08, 0.08 - abs(center - target) * 0.32)


def _select_subject(faces, centroid: np.ndarray, width: int, hint: str):
    if not faces:
        raise RuntimeError("No face was detected in the generated scene.")
    ranked = []
    for face in faces:
        identity = _cosine(_embedding(face), centroid)
        area = float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]))
        size_bonus = min(area / max(width * width, 1), 0.1) * 0.12
        ranked.append((identity + _position_prior(face, width, hint) + size_bonus, identity, face))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][2], ranked[0][1]


def _head_crop(rgb: np.ndarray, face, expansion: float) -> tuple[np.ndarray, tuple[int, int, int, int], np.ndarray]:
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    face_width, face_height = x2 - x1, y2 - y1
    side = max(face_width, face_height) * expansion
    center_x = (x1 + x2) * 0.5
    center_y = (y1 + y2) * 0.5 - face_height * 0.15
    left = max(0, int(round(center_x - side * 0.5)))
    top = max(0, int(round(center_y - side * 0.5)))
    right = min(width, int(round(center_x + side * 0.5)))
    bottom = min(height, int(round(center_y + side * 0.5)))
    if right - left < 96 or bottom - top < 96:
        raise RuntimeError("Detected face is too small for a safe identity-lock crop.")
    crop = rgb[top:bottom, left:right].copy()

    mask = Image.new("L", (right - left, bottom - top), 0)
    draw = ImageDraw.Draw(mask)
    local_x1, local_x2 = x1 - left, x2 - left
    local_y1, local_y2 = y1 - top, y2 - top
    draw.ellipse(
        (
            local_x1 - face_width * 0.24,
            local_y1 - face_height * 0.40,
            local_x2 + face_width * 0.24,
            local_y2 + face_height * 0.08,
        ),
        fill=255,
    )
    return crop, (left, top, right, bottom), np.asarray(mask, dtype=np.uint8)


def _resize_square(rgb: np.ndarray, size: int) -> np.ndarray:
    image = Image.fromarray(rgb)
    return np.asarray(ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS), dtype=np.uint8)


def _yaw(face) -> float:
    pose = np.asarray(getattr(face, "pose", [0.0, 0.0, 0.0]), dtype=np.float32)
    return float(pose[1]) if pose.size >= 2 else 0.0


def _pitch(face) -> float:
    pose = np.asarray(getattr(face, "pose", [0.0, 0.0, 0.0]), dtype=np.float32)
    return float(pose[0]) if pose.size else 0.0


def _bank_signature(paths: list[Path], centroid: np.ndarray) -> str:
    digest = hashlib.sha256(centroid.astype(np.float32).tobytes())
    for path in paths:
        stat = path.stat()
        digest.update(path.name.encode("utf-8"))
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return digest.hexdigest()


def _load_identity_bank(centroid: np.ndarray) -> tuple[list[dict[str, Any]], Path, bool]:
    dataset = Path(folder_paths.get_output_directory()) / "lora-dataset"
    if not dataset.is_dir():
        raise RuntimeError(f"Identity portrait bank is missing: {dataset}")
    paths = sorted(
        path for path in dataset.iterdir()
        if path.is_file() and path.suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    synthetic = [path for path in paths if "original-" not in path.name.casefold()]
    genuine = [path for path in paths if "original-" in path.name.casefold()]
    if len(synthetic) != 15 or len(genuine) != 3:
        raise RuntimeError(
            f"Expected 15 Qwen angle portraits and 3 genuine photos in {dataset}; "
            f"found {len(synthetic)} and {len(genuine)}."
        )
    signature = _bank_signature(paths, centroid)
    cache_path = dataset / ".identity-lock-index.json"
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("signature") == signature and len(cached.get("entries", [])) == 18:
                return cached["entries"], cache_path, True
        except (OSError, ValueError, TypeError):
            pass

    entries = []
    for path in paths:
        with Image.open(path) as opened:
            rgb = np.asarray(opened.convert("RGB"), dtype=np.uint8)
        detected = _faces(rgb)
        if not detected:
            raise RuntimeError(f"No face detected while indexing identity portrait: {path.name}")
        face = max(detected, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
        box = np.asarray(face.bbox, dtype=np.float32)
        area = float(max(box[2] - box[0], 1.0) * max(box[3] - box[1], 1.0))
        entries.append(
            {
                "filename": path.name,
                "kind": "genuine" if "original-" in path.name.casefold() else "qwen_angle",
                "yaw": _yaw(face),
                "pitch": _pitch(face),
                "face_size": math.sqrt(area / max(float(rgb.shape[0] * rgb.shape[1]), 1.0)),
                "detection_quality": float(getattr(face, "det_score", 0.0)),
                "genuine_similarity": _cosine(_embedding(face), centroid),
            }
        )
    payload = {"version": 2, "signature": signature, "entries": entries}
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(cache_path)
    return entries, cache_path, False


def _select_bank_reference(entries: list[dict[str, Any]], mode: str, face) -> dict[str, Any]:
    target_yaw, target_pitch = _yaw(face), _pitch(face)
    candidates = [entry for entry in entries if entry["kind"] == "qwen_angle"]
    if mode == "Force front":
        candidates = [entry for entry in candidates if "-front_" in entry["filename"]]
    elif mode == "Force left":
        candidates = [entry for entry in candidates if "-left_" in entry["filename"]]
    elif mode == "Force right":
        candidates = [entry for entry in candidates if "-right_" in entry["filename"]]
    if not candidates:
        raise RuntimeError(f"No identity-bank portrait is available for {mode}.")
    return min(
        candidates,
        key=lambda entry: (
            abs(float(entry["yaw"]) - target_yaw)
            + 0.45 * abs(float(entry["pitch"]) - target_pitch)
            - 18.0 * float(entry["genuine_similarity"])
            - 2.0 * float(entry["detection_quality"])
            - 2.0 * float(entry["face_size"])
        ),
    )


def _bank_reference_tensor(entry: dict[str, Any], resolution: int) -> torch.Tensor:
    path = Path(folder_paths.get_output_directory()) / "lora-dataset" / entry["filename"]
    with Image.open(path) as opened:
        rgb = np.asarray(opened.convert("RGB"), dtype=np.uint8)
    detected = _faces(rgb)
    if not detected:
        raise RuntimeError(f"Selected identity reference no longer contains a detectable face: {path.name}")
    face = max(detected, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
    crop, _, _ = _head_crop(rgb, face, 1.75)
    return _rgb_tensor(_resize_square(crop, resolution))


def _resize_area(rgb: np.ndarray, target_pixels: int) -> np.ndarray:
    height, width = rgb.shape[:2]
    scale = math.sqrt(float(target_pixels * target_pixels) / max(width * height, 1))
    out_width = max(64, round(width * scale / 16.0) * 16)
    out_height = max(64, round(height * scale / 16.0) * 16)
    return np.asarray(Image.fromarray(rgb).resize((out_width, out_height), Image.Resampling.LANCZOS), dtype=np.uint8)


def _encode_identity_conditioning(clip, vae, prompt: str, target, identity_reference):
    """Official-style Qwen two-image edit: target scene plus exactly one pose-matched identity portrait."""
    images = [target, identity_reference]
    images_vl = []
    image_prompt = ""
    for index, image in enumerate(images):
        samples = image.movedim(-1, 1)
        vl_scale = math.sqrt((384 * 384) / (samples.shape[3] * samples.shape[2]))
        vl_width = round(samples.shape[3] * vl_scale)
        vl_height = round(samples.shape[2] * vl_scale)
        visual = comfy.utils.common_upscale(samples, vl_width, vl_height, "area", "disabled")
        images_vl.append(visual.movedim(1, -1))
        image_prompt += f"Picture {index + 1}: <|vision_start|><|image_pad|><|vision_end|>"

    ref_latents = []
    for image in images:
        latent_samples = image.movedim(-1, 1)
        latent_scale = math.sqrt((1024 * 1024) / (latent_samples.shape[3] * latent_samples.shape[2]))
        latent_width = round(latent_samples.shape[3] * latent_scale / 8.0) * 8
        latent_height = round(latent_samples.shape[2] * latent_scale / 8.0) * 8
        latent_image = comfy.utils.common_upscale(latent_samples, latent_width, latent_height, "area", "disabled")
        ref_latents.append(vae.encode(latent_image.movedim(1, -1)[:, :, :, :3]))

    template = (
        "<|im_start|>system\nDescribe the key features of the input image (color, shape, size, texture, "
        "objects, background), then explain how the user's text instruction should alter or modify the image. "
        "Generate a new image that meets the user's requirements while maintaining consistency with the original "
        "input where appropriate.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"
    )
    strict_prompt = (
        image_prompt
        + prompt
        + " Picture 2 is identity evidence only. Never render it beside, behind, or over Picture 1. Do not create a "
        "collage, split screen, ghost, duplicate head, or extra person. Output only the edited Picture 1."
    )
    tokens = clip.tokenize(strict_prompt, images=images_vl, llama_template=template)
    conditioning = clip.encode_from_tokens_scheduled(tokens)
    return node_helpers.conditioning_set_values(
        conditioning, {"reference_latents": ref_latents}, append=True
    )


def _pose(face) -> np.ndarray:
    return np.asarray(getattr(face, "pose", [0.0, 0.0, 0.0]), dtype=np.float32)


def _candidate_metrics(original_crop: np.ndarray, candidate: np.ndarray, centroid: np.ndarray) -> dict[str, Any]:
    original_faces = _faces(original_crop)
    candidate_faces = _faces(candidate)
    if not original_faces:
        return {"valid": False, "reason": "face_missing_from_original_crop", "identity": -1.0}
    if len(candidate_faces) != 1:
        return {
            "valid": False,
            "reason": "candidate_face_count_not_one",
            "identity": -1.0,
            "face_count": len(candidate_faces),
        }
    original = max(original_faces, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
    generated = candidate_faces[0]
    identity = _cosine(_embedding(generated), centroid)
    original_identity = _cosine(_embedding(original), centroid)
    pose_delta = float(np.linalg.norm(_pose(generated) - _pose(original)))
    obox = np.asarray(original.bbox, dtype=np.float32)
    gbox = np.asarray(generated.bbox, dtype=np.float32)
    ocenter = (obox[:2] + obox[2:]) * 0.5
    gcenter = (gbox[:2] + gbox[2:]) * 0.5
    osize = np.maximum(obox[2:] - obox[:2], 1.0)
    gsize = np.maximum(gbox[2:] - gbox[:2], 1.0)
    center_delta = float(np.linalg.norm((gcenter - ocenter) / osize))
    scale_delta = float(np.max(np.abs(gsize / osize - 1.0)))
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
    }


def _align_candidate(original_crop: np.ndarray, candidate: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    original_faces = _faces(original_crop)
    candidate_faces = _faces(candidate)
    if not original_faces or len(candidate_faces) != 1:
        return candidate, {"aligned": False, "reason": "face_count"}
    original = max(original_faces, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
    generated = candidate_faces[0]
    source = np.asarray(generated.kps, dtype=np.float32)
    target = np.asarray(original.kps, dtype=np.float32)
    matrix, inliers = cv2.estimateAffinePartial2D(source, target, method=cv2.LMEDS)
    if matrix is None:
        return candidate, {"aligned": False, "reason": "transform_failed"}
    aligned = cv2.warpAffine(
        candidate,
        matrix,
        (original_crop.shape[1], original_crop.shape[0]),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    scale = math.sqrt(float(matrix[0, 0] ** 2 + matrix[0, 1] ** 2))
    rotation = math.degrees(math.atan2(float(matrix[0, 1]), float(matrix[0, 0])))
    translation = math.hypot(float(matrix[0, 2]), float(matrix[1, 2]))
    return aligned, {
        "aligned": True,
        "scale": scale,
        "rotation_degrees": rotation,
        "translation_pixels": translation,
        "inliers": int(np.asarray(inliers).sum()) if inliers is not None else 0,
    }


def _composite(original: np.ndarray, candidate_square: np.ndarray, box: tuple[int, int, int, int], mask: np.ndarray, feather: int):
    left, top, right, bottom = box
    target_size = (right - left, bottom - top)
    candidate = np.asarray(
        Image.fromarray(candidate_square).resize(target_size, Image.Resampling.LANCZOS), dtype=np.uint8
    )
    soft = Image.fromarray(mask).filter(ImageFilter.GaussianBlur(radius=max(0, feather)))
    alpha = np.asarray(soft, dtype=np.float32)[..., None] / 255.0
    output = original.copy()
    region = output[top:bottom, left:right].astype(np.float32)
    blended = candidate.astype(np.float32) * alpha + region * (1.0 - alpha)
    output[top:bottom, left:right] = np.clip(blended, 0, 255).astype(np.uint8)
    full_mask = np.zeros(original.shape[:2], dtype=np.float32)
    full_mask[top:bottom, left:right] = alpha[..., 0]
    return output, full_mask


def _sample_qwen(model, clip, vae, negative, target: torch.Tensor, reference: torch.Tensor, prompt: str, seed: int, steps: int):
    conditioning = _encode_identity_conditioning(clip, vae, prompt, target, reference)
    height, width = int(target.shape[1]), int(target.shape[2])
    latent = comfy_nodes.EmptyLatentImage().generate(width, height, 1)[0]
    sampled = comfy_nodes.common_ksampler(
        model, seed, steps, 1.0, "euler", "simple", conditioning, negative, latent, denoise=1.0
    )[0]
    decoded = _tensor_rgb(comfy_nodes.VAEDecode().decode(vae, sampled)[0].detach().float().cpu())
    if decoded.shape[:2] != (height, width):
        decoded = np.asarray(Image.fromarray(decoded).resize((width, height), Image.Resampling.LANCZOS), dtype=np.uint8)
    return decoded


def _segmented_head_mask(candidate: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Extract face, ears, hair and skull silhouette while discarding a generated portrait background."""
    detected = _faces(candidate)
    if len(detected) != 1:
        return np.zeros(candidate.shape[:2], dtype=np.uint8), {"segmented": False, "reason": "face_count"}
    face = detected[0]
    height, width = candidate.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    face_w, face_h = x2 - x1, y2 - y1
    initialization = np.full((height, width), cv2.GC_BGD, dtype=np.uint8)
    probable = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(
        probable,
        (int((x1 + x2) * 0.5), int((y1 + y2) * 0.5 - face_h * 0.14)),
        (max(2, int(face_w * 0.76)), max(2, int(face_h * 0.90))),
        0, 0, 360, 255, -1,
    )
    initialization[probable > 0] = cv2.GC_PR_FGD
    inner = (
        max(0, int(x1 + face_w * 0.08)), max(0, int(y1 + face_h * 0.05)),
        min(width, int(x2 - face_w * 0.08)), min(height, int(y2 - face_h * 0.04)),
    )
    initialization[inner[1]:inner[3], inner[0]:inner[2]] = cv2.GC_FGD
    margin = max(2, int(min(height, width) * 0.025))
    initialization[:margin, :] = cv2.GC_BGD; initialization[-margin:, :] = cv2.GC_BGD
    initialization[:, :margin] = cv2.GC_BGD; initialization[:, -margin:] = cv2.GC_BGD
    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(candidate, initialization, None, background_model, foreground_model, 4, cv2.GC_INIT_WITH_MASK)
        foreground = np.where(
            (initialization == cv2.GC_FGD) | (initialization == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)
        foreground = cv2.bitwise_and(foreground, probable)
        kernel_size = max(3, int(round(min(height, width) * 0.012)) | 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)
        foreground = cv2.dilate(foreground, kernel, iterations=1)
        coverage = float(np.count_nonzero(foreground) / max(foreground.size, 1))
        valid = 0.08 <= coverage <= 0.65
        return foreground if valid else probable, {
            "segmented": valid, "reason": "ok" if valid else "coverage_fallback", "coverage": coverage
        }
    except cv2.error:
        return probable, {"segmented": False, "reason": "grabcut_failed"}


def _match_head_lighting(candidate: np.ndarray, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Match the edited head's color/contrast to the original scene without changing its geometry."""
    core = mask >= 160
    if np.count_nonzero(core) < 256:
        return candidate
    source_lab = cv2.cvtColor(candidate, cv2.COLOR_RGB2LAB).astype(np.float32)
    target_lab = cv2.cvtColor(target, cv2.COLOR_RGB2LAB).astype(np.float32)
    adjusted = source_lab.copy()
    for channel in range(3):
        source_values = source_lab[..., channel][core]
        target_values = target_lab[..., channel][core]
        source_mean, source_std = float(source_values.mean()), float(source_values.std())
        target_mean, target_std = float(target_values.mean()), float(target_values.std())
        scale = float(np.clip(target_std / max(source_std, 1.0), 0.72, 1.35))
        adjusted[..., channel] = (adjusted[..., channel] - source_mean) * scale + target_mean
    adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
    return cv2.cvtColor(adjusted, cv2.COLOR_LAB2RGB)


def _align_full_scene(original: np.ndarray, original_face, generated: np.ndarray, generated_face):
    source = np.asarray(generated_face.kps, dtype=np.float32)
    source[:, 0] *= original.shape[1] / generated.shape[1]
    source[:, 1] *= original.shape[0] / generated.shape[0]
    resized = np.asarray(
        Image.fromarray(generated).resize((original.shape[1], original.shape[0]), Image.Resampling.LANCZOS),
        dtype=np.uint8,
    )
    target = np.asarray(original_face.kps, dtype=np.float32)
    matrix, inliers = cv2.estimateAffinePartial2D(source, target, method=cv2.LMEDS)
    if matrix is None:
        return resized, {"aligned": False, "reason": "transform_failed"}
    aligned = cv2.warpAffine(
        resized,
        matrix,
        (original.shape[1], original.shape[0]),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    return aligned, {
        "aligned": True,
        "scale": math.sqrt(float(matrix[0, 0] ** 2 + matrix[0, 1] ** 2)),
        "rotation_degrees": math.degrees(math.atan2(float(matrix[0, 1]), float(matrix[0, 0]))),
        "translation_pixels": math.hypot(float(matrix[0, 2]), float(matrix[1, 2])),
        "inliers": int(np.asarray(inliers).sum()) if inliers is not None else 0,
    }


def _finalize_metrics(
    metric: dict[str, Any],
    original: np.ndarray,
    composite: np.ndarray,
    full_mask: np.ndarray,
    centroid: np.ndarray,
    hint: str,
    expected_faces: int,
) -> dict[str, Any]:
    composite_faces = _faces(composite)
    metric["composite_face_count"] = len(composite_faces)
    try:
        chosen, composite_identity = _select_subject(composite_faces, centroid, composite.shape[1], hint)
        metric["composite_identity"] = composite_identity
        metric["composite_yaw"] = _yaw(chosen)
    except RuntimeError:
        metric["composite_identity"] = -1.0
    outside = full_mask <= 0.0
    metric["outside_mask_changed_pixels"] = int(np.count_nonzero(np.any(composite[outside] != original[outside], axis=1)))
    edge = (full_mask > 0.01) & (full_mask < 0.20)
    metric["seam_score"] = (
        float(np.mean(np.abs(composite[edge].astype(np.float32) - original[edge].astype(np.float32))) / 255.0)
        if np.any(edge)
        else 0.0
    )
    hard_valid = (
        bool(metric.get("valid"))
        and metric["composite_face_count"] == expected_faces
        and metric["outside_mask_changed_pixels"] == 0
        and metric["seam_score"] <= 0.18
        and float(metric.get("mask_edge_coverage", 0.0)) <= 0.08
    )
    metric["hard_valid"] = hard_valid
    if not hard_valid and metric.get("reason") == "ok":
        metric["reason"] = "face_count_seam_or_mask_safety"
    metric["selection_score"] = float(metric.get("composite_identity", -1.0)) - metric["seam_score"] * 0.15
    return metric


def _contact_sheet(originals: list[np.ndarray], locked: list[np.ndarray]) -> np.ndarray:
    tile_w, tile_h = 256, 374
    canvas = Image.new("RGB", (tile_w * 6, tile_h * 3), (20, 20, 20))
    for index, (before, after) in enumerate(zip(originals, locked)):
        row, column = divmod(index, 3)
        for offset, image in enumerate((before, after)):
            tile = ImageOps.fit(Image.fromarray(image), (tile_w, tile_h), method=Image.Resampling.LANCZOS)
            canvas.paste(tile, ((column * 2 + offset) * tile_w, row * tile_h))
    return np.asarray(canvas, dtype=np.uint8)


class AIToolkitIdentityLockSettings:
    @classmethod
    def INPUT_TYPES(cls):
        position_inputs = {
            f"image_{index}_subject": (SUBJECT_POSITIONS, {"default": "Center" if index <= 2 else "Auto identity match"})
            for index in range(1, 10)
        }
        return {
            "required": {
                "identity_lock": ("BOOLEAN", {"default": True}),
                "image_scope": (IMAGE_SCOPES,),
                "selection_mode": (SELECTION_MODES,),
                "reference_mode": (REFERENCE_MODES,),
                "instruction": ("STRING", {"default": DEFAULT_INSTRUCTION, "multiline": True}),
                "crop_expansion": ("FLOAT", {"default": 1.65, "min": 1.3, "max": 2.5, "step": 0.05}),
                "mask_feather": ("INT", {"default": 48, "min": 0, "max": 160, "step": 4}),
                "qwen_resolution": ("INT", {"default": 768, "min": 512, "max": 1024, "step": 64}),
                "qwen_steps": ("INT", {"default": 4, "min": 4, "max": 12}),
                "candidate_a_seed": ("INT", {"default": 82419631, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "candidate_b_seed": ("INT", {"default": 82639089, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "minimum_identity_improvement": (
                    "FLOAT",
                    {"default": 0.03, "min": 0.0, "max": 0.25, "step": 0.01},
                ),
                "output_prefix": ("STRING", {"default": "zimg-social-pack/identity-lock"}),
                **position_inputs,
            }
        }

    RETURN_TYPES = (IDENTITY_CONFIG_TYPE,)
    RETURN_NAMES = ("identity_settings",)
    FUNCTION = "build"
    CATEGORY = "image/generation/AI-Toolkit Social Workbench"

    def build(self, **kwargs):
        positions = [kwargs.pop(f"image_{index}_subject") for index in range(1, 10)]
        config = dict(kwargs)
        config["subject_positions"] = positions
        config["output_prefix"] = config["output_prefix"].strip().strip("/\\") or "zimg-social-pack/identity-lock"
        config["instruction"] = config["instruction"].strip()
        if not config["instruction"]:
            raise RuntimeError("Identity Lock instruction cannot be empty.")
        return (config,)


class AIToolkitQwenIdentityLock:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "final_images": ("IMAGE",),
                "final_folder": ("STRING",),
                "front_reference": ("IMAGE",),
                "left_reference": ("IMAGE",),
                "right_reference": ("IMAGE",),
                "identity_settings": (IDENTITY_CONFIG_TYPE,),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = (
        "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "MASK", "IMAGE", "STRING", "STRING"
    )
    RETURN_NAMES = (
        "locked_images",
        "candidate_a",
        "candidate_b",
        "original_heads",
        "selected_references",
        "raw_candidate_a_heads",
        "raw_candidate_b_heads",
        "head_masks",
        "comparison_sheet",
        "output_folder",
        "status_json",
    )
    FUNCTION = "lock"
    CATEGORY = "image/generation/AI-Toolkit Social Workbench"
    OUTPUT_NODE = True

    def _off_result(self, final_images: torch.Tensor, message: str):
        images = final_images.detach().float().cpu()
        if images.ndim == 3:
            images = images.unsqueeze(0)
        masks = torch.zeros(images.shape[:3], dtype=torch.float32)
        heads = torch.nn.functional.interpolate(
            images.movedim(-1, 1), size=(768, 768), mode="bilinear", align_corners=False
        ).movedim(1, -1)
        originals = [_tensor_rgb(images[index : index + 1]) for index in range(images.shape[0])]
        sheet = _rgb_tensor(_contact_sheet(originals, originals))
        return {
            "ui": {"text": (message,)},
            "result": (
                images, images, images, heads, heads, heads, heads, masks, sheet,
                "IDENTITY LOCK OFF", json.dumps({"status": message}),
            ),
        }

    def lock(
        self,
        final_images,
        final_folder,
        front_reference,
        left_reference,
        right_reference,
        identity_settings,
        prompt=None,
        extra_pnginfo=None,
    ):
        if not identity_settings["identity_lock"]:
            return self._off_result(final_images, "Identity Lock is OFF; Stage 2 finals are unchanged.")
        if final_folder == "FINAL STAGE OFF":
            return self._off_result(final_images, "Stage 2 is OFF. Turn on Render Finals before Identity Lock can run.")
        for folder, filename in (
            ("diffusion_models", QWEN_MODEL), ("text_encoders", QWEN_CLIP), ("vae", QWEN_VAE),
            ("loras", QWEN_LIGHTNING), ("loras", QWEN_ANGLES),
        ):
            _require(folder, filename)

        images = final_images.detach().float().cpu()
        if images.ndim == 3:
            images = images.unsqueeze(0)
        originals = [_tensor_rgb(images[index:index + 1]) for index in range(images.shape[0])]
        centroid, _ = _reference_centroid([front_reference, left_reference, right_reference])
        bank, cache_path, cache_hit = _load_identity_bank(centroid)
        source_scene_indices = list(range(len(originals)))
        if isinstance(prompt, dict):
            for prompt_node in prompt.values():
                if isinstance(prompt_node, dict) and prompt_node.get("class_type") == "AIToolkitSocialPackFinals":
                    final_scope = str(prompt_node.get("inputs", {}).get("final_scope", ""))
                    if final_scope.startswith("Scene ") and final_scope.endswith(" only"):
                        try:
                            source_scene_indices = [int(final_scope.split()[1]) - 1]
                        except (IndexError, ValueError):
                            pass
                    break
        selected = set(range(len(originals)))
        if identity_settings["image_scope"] != "All images":
            selected = {int(identity_settings["image_scope"].split()[1]) - 1}

        comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        model = comfy_nodes.UNETLoader().load_unet(QWEN_MODEL, "fp8_e4m3fn")[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(model, QWEN_LIGHTNING, 1.0)[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(model, QWEN_ANGLES, 0.9)[0]
        model = ModelSamplingAuraFlow().patch_aura(model, 3.1)[0]
        clip = comfy_nodes.CLIPLoader().load_clip(QWEN_CLIP, "qwen_image", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(QWEN_VAE)[0]
        negative = comfy_nodes.CLIPTextEncode().encode(clip, "")[0]

        locked_rgbs, candidate_a_rgbs, candidate_b_rgbs = [], [], []
        original_heads, selected_refs, raw_a_heads, raw_b_heads, mask_arrays, reports = [], [], [], [], [], []
        resolution = int(identity_settings["qwen_resolution"])
        steps = int(identity_settings["qwen_steps"])

        try:
            for index, original in enumerate(originals):
                placeholder = _resize_square(original, resolution)
                if index not in selected:
                    locked_rgbs.append(original); candidate_a_rgbs.append(original); candidate_b_rgbs.append(original)
                    original_heads.append(placeholder); selected_refs.append(placeholder)
                    raw_a_heads.append(placeholder); raw_b_heads.append(placeholder)
                    mask_arrays.append(np.zeros(original.shape[:2], dtype=np.float32))
                    reports.append({"image": index + 1, "action": "not_selected"})
                    continue

                source_scene = source_scene_indices[index] if index < len(source_scene_indices) else index
                hint = identity_settings["subject_positions"][min(source_scene, 8)]
                scene_faces = _faces(original)
                face, original_identity = _select_subject(scene_faces, centroid, original.shape[1], hint)
                crop, box, hard_mask = _head_crop(original, face, float(identity_settings["crop_expansion"]))
                target_head = _resize_square(crop, resolution)
                entry = _select_bank_reference(bank, identity_settings["reference_mode"], face)
                reference_tensor = _bank_reference_tensor(entry, resolution)
                reference_rgb = _tensor_rgb(reference_tensor)
                feather = max(
                    1,
                    int(round(int(identity_settings["mask_feather"]) * min(crop.shape[:2]) / resolution)),
                )

                # Candidate A edits the complete scene so Qwen sees lighting, group membership, and composition.
                scene_target = _resize_area(original, resolution)
                generated_a = _sample_qwen(
                    model, clip, vae, negative, _rgb_tensor(scene_target), reference_tensor,
                    identity_settings["instruction"], int(identity_settings["candidate_a_seed"]) + index * 1009, steps,
                )
                generated_a_faces = _faces(generated_a)
                try:
                    generated_a_face, _ = _select_subject(generated_a_faces, centroid, generated_a.shape[1], hint)
                    aligned_scene, alignment_a = _align_full_scene(original, face, generated_a, generated_a_face)
                    left, top, right, bottom = box
                    aligned_a_head = aligned_scene[top:bottom, left:right]
                    metric_a = _candidate_metrics(crop, aligned_a_head, centroid)
                except RuntimeError:
                    aligned_scene, alignment_a = original.copy(), {"aligned": False, "reason": "subject_missing"}
                    aligned_a_head = crop.copy()
                    metric_a = {"valid": False, "reason": "subject_missing", "identity": -1.0}
                metric_a["method"] = "full_scene_two_picture_edit"
                metric_a["generated_face_count"] = len(generated_a_faces)
                metric_a["expected_face_count"] = len(scene_faces)
                metric_a["alignment"] = alignment_a
                if len(generated_a_faces) != len(scene_faces):
                    metric_a["valid"] = False
                    metric_a["reason"] = "generated_face_count_changed"
                composite_a, mask_a = _composite(original, aligned_a_head, box, hard_mask, feather)
                metric_a = _finalize_metrics(metric_a, original, composite_a, mask_a, centroid, hint, len(scene_faces))

                # Candidate B edits only the expanded head crop, maximizing useful face pixels.
                generated_b = _sample_qwen(
                    model, clip, vae, negative, _rgb_tensor(target_head), reference_tensor,
                    identity_settings["instruction"], int(identity_settings["candidate_b_seed"]) + index * 1009, steps,
                )
                generated_b = _resize_square(generated_b, resolution)
                generated_b_faces = _faces(generated_b)
                aligned_b, alignment_b = _align_candidate(target_head, generated_b)
                metric_b = _candidate_metrics(target_head, aligned_b, centroid)
                metric_b["method"] = "expanded_head_two_picture_edit"
                metric_b["generated_face_count"] = len(generated_b_faces)
                metric_b["expected_face_count"] = 1
                metric_b["alignment"] = alignment_b
                if len(generated_b_faces) != 1:
                    metric_b["valid"] = False
                    metric_b["reason"] = "generated_face_count_changed"
                segmented_square, segmentation_b = _segmented_head_mask(aligned_b)
                segmented_mask = np.asarray(
                    Image.fromarray(segmented_square).resize(
                        (hard_mask.shape[1], hard_mask.shape[0]), Image.Resampling.NEAREST
                    ),
                    dtype=np.uint8,
                )
                edge_width = max(2, int(min(segmented_mask.shape) * 0.04))
                edge_pixels = np.concatenate((
                    segmented_mask[:edge_width, :].ravel(), segmented_mask[-edge_width:, :].ravel(),
                    segmented_mask[:, :edge_width].ravel(), segmented_mask[:, -edge_width:].ravel(),
                ))
                metric_b["segmentation"] = segmentation_b
                metric_b["mask_edge_coverage"] = float(np.count_nonzero(edge_pixels) / max(edge_pixels.size, 1))
                aligned_b = _match_head_lighting(aligned_b, target_head, segmented_square)
                composite_b, mask_b = _composite(original, aligned_b, box, segmented_mask, feather)
                metric_b = _finalize_metrics(metric_b, original, composite_b, mask_b, centroid, hint, len(scene_faces))

                metrics = [metric_a, metric_b]
                composites, masks = [composite_a, composite_b], [mask_a, mask_b]
                mode = identity_settings["selection_mode"]
                if mode == "Original":
                    winner, accepted, reason = None, False, "manual_original"
                elif mode in {"Candidate A", "Candidate B"}:
                    winner = 0 if mode == "Candidate A" else 1
                    accepted = bool(metrics[winner].get("hard_valid"))
                    reason = "manual_candidate" if accepted else f"manual_rejected:{metrics[winner].get('reason')}"
                else:
                    winner = max(range(2), key=lambda item: float(metrics[item].get("selection_score", -99.0)))
                    improvement = float(metrics[winner].get("composite_identity", -1.0)) - float(original_identity)
                    accepted = bool(metrics[winner].get("hard_valid")) and improvement >= float(
                        identity_settings["minimum_identity_improvement"]
                    )
                    reason = "auto_accepted" if accepted else "auto_no_safe_identity_improvement"
                locked = composites[winner] if accepted and winner is not None else original
                chosen_mask = masks[winner] if accepted and winner is not None else np.zeros(original.shape[:2], dtype=np.float32)
                locked_rgbs.append(locked); candidate_a_rgbs.append(composite_a); candidate_b_rgbs.append(composite_b)
                original_heads.append(target_head); selected_refs.append(reference_rgb)
                raw_a_heads.append(_resize_square(aligned_a_head, resolution)); raw_b_heads.append(aligned_b)
                mask_arrays.append(chosen_mask)
                reports.append({
                    "image": index + 1,
                    "source_scene": source_scene + 1,
                    "action": "accepted" if accepted else "kept_original",
                    "selection_mode": mode,
                    "selection_reason": reason,
                    "subject_hint": hint,
                    "original_face_count": len(scene_faces),
                    "original_identity": original_identity,
                    "original_yaw": _yaw(face),
                    "original_pitch": _pitch(face),
                    "selected_reference": entry,
                    "winner": None if winner is None else ("Candidate A" if winner == 0 else "Candidate B"),
                    "candidate_heads_mean_absolute_difference": float(
                        np.mean(np.abs(_resize_square(aligned_a_head, resolution).astype(np.float32) - aligned_b.astype(np.float32))) / 255.0
                    ),
                    "minimum_improvement": identity_settings["minimum_identity_improvement"],
                    "candidates": {"Candidate A": metric_a, "Candidate B": metric_b},
                })
        finally:
            del model, clip, vae
            comfy.model_management.unload_all_models()
            comfy.model_management.soft_empty_cache()

        def batch(values):
            return torch.cat([_rgb_tensor(value) for value in values], dim=0)

        locked_batch, candidate_a_batch, candidate_b_batch = batch(locked_rgbs), batch(candidate_a_rgbs), batch(candidate_b_rgbs)
        original_heads_batch, selected_refs_batch = batch(original_heads), batch(selected_refs)
        raw_a_batch, raw_b_batch = batch(raw_a_heads), batch(raw_b_heads)
        masks_batch = torch.from_numpy(np.stack(mask_arrays)).float()
        sheet = _rgb_tensor(_contact_sheet(originals, locked_rgbs))
        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_folder = f"{identity_settings['output_prefix']}/{run_stamp}"
        ui_images = []
        save_batches = (
            ("originals", images), ("candidate-a-composites", candidate_a_batch),
            ("candidate-b-composites", candidate_b_batch), ("locked", locked_batch),
            ("original-heads", original_heads_batch), ("selected-references", selected_refs_batch),
            ("raw-candidate-a-heads", raw_a_batch), ("raw-candidate-b-heads", raw_b_batch),
        )
        for label, image_batch in save_batches:
            saved = comfy_nodes.SaveImage().save_images(
                image_batch, f"{output_folder}/{label}/{label}", prompt=prompt, extra_pnginfo=extra_pnginfo
            )
            if label == "locked":
                ui_images.extend(saved["ui"]["images"])
        sheet_saved = comfy_nodes.SaveImage().save_images(
            sheet, f"{output_folder}/comparison/contact-sheet-before-left-after-right", prompt=prompt,
            extra_pnginfo={**(extra_pnginfo or {}), "identity_lock_report": reports},
        )
        ui_images.extend(sheet_saved["ui"]["images"])
        accepted_count = sum(report.get("action") == "accepted" for report in reports)
        status = {
            "source_final_folder": final_folder,
            "output_folder": output_folder,
            "identity_bank": {"cache_path": str(cache_path), "cache_hit": cache_hit, "entries": len(bank)},
            "processed": len(selected.intersection(range(len(originals)))),
            "accepted": accepted_count,
            "kept_original": sum(report.get("action") == "kept_original" for report in reports),
            "reports": reports,
        }
        report_path = Path(folder_paths.get_output_directory()) / Path(output_folder) / "identity-lock-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(status, indent=2, default=float), encoding="utf-8")
        summary_lines = [
            f"Identity Lock: {accepted_count} accepted; {status['kept_original']} original(s) kept.",
            f"Identity bank: 15 generated angle fixtures + 3 genuine camera photos ({'cached' if cache_hit else 'indexed now'}).",
        ]
        for report in reports:
            if report.get("action") == "not_selected":
                continue
            ref = report["selected_reference"]["filename"]
            summary_lines.append(
                f"Image {report['image']}: {report['winner'] or 'Original'} — {report['selection_reason']}; reference {ref}."
            )
        summary_lines.append(f"Saved to ComfyUI/output/{output_folder}")
        return {
            "ui": {"images": ui_images, "text": ("\n".join(summary_lines),)},
            "result": (
                locked_batch, candidate_a_batch, candidate_b_batch, original_heads_batch, selected_refs_batch,
                raw_a_batch, raw_b_batch, masks_batch, sheet, output_folder,
                json.dumps(status, indent=2, default=float),
            ),
        }
