from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import cv2
import folder_paths
import numpy as np
import torch
from PIL import Image

import comfy.model_management
import comfy.utils
from comfy_extras.nodes_model_advanced import ModelSamplingAuraFlow
from comfy_extras.nodes_sd3 import EmptySD3LatentImage

from . import reference_photo_studio as studio
from .scene_crop import face_aware_scene_crop
from .scene_constraints import (
    build_hard_scene_constraints,
    build_scene_topology,
    scene_object_targets,
)
from .scene_objects import count_scene_objects, object_count_error
from .scene_quality import apply_scene_guardrails


SCENE_MODEL = "z_image_bf16.safetensors"
SCENE_CLIP = "qwen_3_4b_fp8_mixed.safetensors"
SCENE_VAE = "ae.safetensors"
SCENE_STEPS = 25
SCENE_GUIDANCE = 4.0
SCENE_SAMPLING_SHIFT = 3.0
SCENE_ANCHOR_PIXELS = 192 * 288
SCENE_SEED_OFFSETS = (0, 101, 211)
COMPLEX_LORA_STRENGTH_BONUS = 0.15
COMPLEX_LORA_STRENGTH_MAX = 0.75
FINAL_SEED_OFFSETS = (1, 0, 2)
SCENE_CACHE_VERSION = 1
SUBJECT_MASK_MODEL = "u2net_human_seg"
SUBJECT_MASK_THRESHOLD = 0.35
SUBJECT_MASK_DILATION = 9
SUBJECT_MASK_FEATHER_SIGMA = 10.0

_REMBG_SESSION = None


def _scene_cache_paths(prompt: str, seed: int) -> tuple[Path, Path]:
    payload = json.dumps(
        {
            "version": SCENE_CACHE_VERSION,
            "model": SCENE_MODEL,
            "clip": SCENE_CLIP,
            "vae": SCENE_VAE,
            "steps": SCENE_STEPS,
            "guidance": SCENE_GUIDANCE,
            "shift": SCENE_SAMPLING_SHIFT,
            "width": studio.OUTPUT_WIDTH,
            "height": studio.OUTPUT_HEIGHT,
            "prompt": prompt,
            "seed": seed,
        },
        sort_keys=True,
    ).encode("utf-8")
    key = hashlib.sha256(payload).hexdigest()
    root = Path(folder_paths.get_temp_directory()) / "mitch-v104-layout-cache"
    return root / f"{key}.png", root / f"{key}.json"


def _load_cached_anchor(prompt: str, seed: int) -> tuple[torch.Tensor, dict] | None:
    image_path, report_path = _scene_cache_paths(prompt, seed)
    if not image_path.is_file() or not report_path.is_file():
        return None
    try:
        rgb = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.float32) / 255.0
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["cache_hit"] = True
        report["seconds"] = 0.0
        return torch.from_numpy(rgb).unsqueeze(0), report
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _save_cached_anchor(prompt: str, seed: int, anchor: torch.Tensor, report: dict) -> None:
    image_path, report_path = _scene_cache_paths(prompt, seed)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.clip(anchor[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(rgb).save(image_path, format="PNG", compress_level=1)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def _layout_face(image: torch.Tensor):
    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    faces = studio.baseline._face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError("No central face was detected in the complex-scene layout pass.")
    return max(
        faces,
        key=lambda item: float(
            (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
        ),
    )


def _crop_layout_anchor(
    image: torch.Tensor, face, framing: str
) -> tuple[torch.Tensor, dict]:
    height, width = image.shape[1:3]
    crop = face_aware_scene_crop(
        width,
        height,
        [float(value) for value in face.bbox],
        framing,
        studio.OUTPUT_WIDTH,
        studio.OUTPUT_HEIGHT,
    )
    cropped = image[:, crop.top : crop.bottom, crop.left : crop.right, :]
    resized = comfy.utils.common_upscale(
        cropped.movedim(-1, 1),
        studio.OUTPUT_WIDTH,
        studio.OUTPUT_HEIGHT,
        "lanczos",
        "disabled",
    ).movedim(1, -1)
    return resized, {
        "framing": framing,
        "source_shape": [int(height), int(width)],
        "crop_bbox": [crop.left, crop.top, crop.right, crop.bottom],
        "crop_shape": [crop.height, crop.width],
        "output_shape": [studio.OUTPUT_HEIGHT, studio.OUTPUT_WIDTH],
        "method": "largest_face_aware_deterministic_scene_crop",
    }


def _main_subject_mask(image: torch.Tensor, face) -> tuple[torch.Tensor, dict]:
    global _REMBG_SESSION
    try:
        from rembg import new_session, remove
    except ImportError as exc:
        raise RuntimeError(
            "Complex multi-person isolation requires the installed local rembg package."
        ) from exc

    os.environ["U2NET_HOME"] = os.path.join(folder_paths.models_dir, "rembg")
    if _REMBG_SESSION is None:
        _REMBG_SESSION = new_session(SUBJECT_MASK_MODEL)

    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    raw = remove(
        Image.fromarray(rgb),
        session=_REMBG_SESSION,
        only_mask=True,
        post_process_mask=True,
    )
    probability = np.asarray(raw.convert("L"), dtype=np.float32) / 255.0
    binary = (probability >= SUBJECT_MASK_THRESHOLD).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    x1, y1, x2, y2 = [int(round(float(value))) for value in face.bbox]
    height, width = binary.shape
    x1, x2 = max(0, x1), min(width, x2)
    y1, y2 = max(0, y1), min(height, y2)
    if count <= 1 or x2 <= x1 or y2 <= y1:
        raise RuntimeError("Human segmentation did not find the main layout subject.")

    face_labels = labels[y1:y2, x1:x2]
    candidates = [label for label in range(1, count) if np.any(face_labels == label)]
    if not candidates:
        raise RuntimeError("Human segmentation did not overlap the detected main face.")
    selected_label = max(
        candidates,
        key=lambda label: int(np.count_nonzero(face_labels == label)),
    )
    selected = (labels == selected_label).astype(np.uint8)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (SUBJECT_MASK_DILATION * 2 + 1, SUBJECT_MASK_DILATION * 2 + 1),
    )
    selected = cv2.dilate(selected, kernel, iterations=1)
    feathered = cv2.GaussianBlur(
        selected.astype(np.float32),
        (0, 0),
        sigmaX=SUBJECT_MASK_FEATHER_SIGMA,
        sigmaY=SUBJECT_MASK_FEATHER_SIGMA,
    )
    feathered = np.clip(feathered, 0.0, 1.0)
    hard_area = float(selected.mean())
    if hard_area < 0.06 or hard_area > 0.72:
        raise RuntimeError(
            f"Main-subject segmentation covered an implausible {hard_area:.1%} of the frame."
        )
    ys, xs = np.where(selected > 0)
    mask = torch.from_numpy(feathered).unsqueeze(0).to(dtype=image.dtype)
    return mask, {
        "model": SUBJECT_MASK_MODEL,
        "selected_component": int(selected_label),
        "hard_area_fraction": round(hard_area, 4),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
        "threshold": SUBJECT_MASK_THRESHOLD,
        "dilation_pixels": SUBJECT_MASK_DILATION,
        "feather_sigma": SUBJECT_MASK_FEATHER_SIGMA,
    }


def _remove_anchor_identity(image: torch.Tensor, face) -> tuple[torch.Tensor, dict]:
    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    face_width = x2 - x1
    face_height = y2 - y1
    left = max(0, int(round(x1 - face_width * 0.45)))
    right = min(width, int(round(x2 + face_width * 0.45)))
    top = max(0, int(round(y1 - face_height * 0.65)))
    bottom = min(height, int(round(y2 + face_height * 0.45)))
    region = rgb[top:bottom, left:right]
    tiny = cv2.resize(region, (6, 8), interpolation=cv2.INTER_AREA)
    obscured = cv2.resize(
        tiny, (region.shape[1], region.shape[0]), interpolation=cv2.INTER_LINEAR
    )
    sigma = max(region.shape[0], region.shape[1]) * 0.10
    obscured = cv2.GaussianBlur(obscured, (0, 0), sigmaX=sigma, sigmaY=sigma)
    mask = np.zeros(region.shape[:2], dtype=np.float32)
    cv2.ellipse(
        mask,
        (region.shape[1] // 2, region.shape[0] // 2),
        (max(1, region.shape[1] // 2 - 2), max(1, region.shape[0] // 2 - 2)),
        0,
        0,
        360,
        1.0,
        -1,
    )
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=max(3.0, sigma * 0.25))[:, :, None]
    masked = rgb.astype(np.float32)
    masked_region = region.astype(np.float32) * (1.0 - mask) + obscured.astype(np.float32) * mask
    masked[top:bottom, left:right] = masked_region
    tensor = torch.from_numpy(masked / 255.0).unsqueeze(0).to(dtype=image.dtype)
    return tensor, {
        "face_bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
        "obscured_bbox": [left, top, right, bottom],
        "method": "strong_pixelation_blur_with_feathered_head_mask",
    }


def _scene_layout_prompt(composed_scene: str, contract: dict) -> str:
    guarded = apply_scene_guardrails(composed_scene, contract)
    hard_constraints = build_hard_scene_constraints(contract)
    topology = build_scene_topology(contract)
    return (
        "Create one ordinary, physically plausible deep-focus photograph, never a cinematic portrait. Put one generic "
        "adult man nearest the camera as the unmistakable main subject, near the center, and make him the largest human in "
        "the frame. His identity is unimportant because that subject will be regenerated later, but his complete pose, "
        "body placement, clothing, lighting, contact, and occlusion must already be coherent. Establish one camera "
        "projection and continuous depth structure for the whole frame. Resolve the near, middle, and far environment with "
        "natural distance-dependent detail instead of bokeh or background blur. Obey explicit counts and keep every "
        "secondary person, vehicle, table, chair, and building separate and complete. Treat every HARD constraint below as "
        "more important than decorative scene detail. "
        f"{hard_constraints} "
        f"{topology} "
        f"Photo request: {guarded}"
    )


def _final_identity_prompt(composed_scene: str, contract: dict) -> str:
    guarded = apply_scene_guardrails(composed_scene, contract)
    return (
        "Highest priority: the regenerated main subject must unmistakably be the exact current m1tchperson identity shown "
        "in Pictures 2 and 3, not a generic approximation. Keep healthy ordinary skin with subtle pores, faint uneven tone, "
        "and sparse stubble only. Do not add a rash, acne outbreak, sores, lesions, scratches, bruises, repeated red or dark "
        "spots, or conspicuous marks to the face, neck, hands, or arms. Create one coherent photorealistic photograph. "
        "Picture 1 is a very low-resolution scene-layout reference only and "
        "its central person's identity was intentionally obscured. Use its approximate location, camera viewpoint, "
        "composition, activity, body placement, lighting, and background logic, but reconstruct every person and object "
        "as new in-camera content rather than copying pixels. Do not copy the face or identity of its central person. "
        "Pictures 2 and 3 are identity evidence for the central person; Picture 3 is a closer crop of Picture 2, not another "
        "person. The trained identity token is m1tchperson. Render the central person as unmistakably the exact m1tchperson "
        "identity shown in Pictures 2 and 3, preserving current apparent age, facial proportions, eyes, eyebrows, nose, "
        "mouth, ears, jaw, hairline, hair color, and natural unretouched skin. Regenerate only the masked main-subject region "
        "as one continuous head, body, arms, and clothing under the existing scene light and camera optics. Preserve the "
        "unmasked scene, secondary people, vehicles, architecture, tables, and depth structure exactly. Blend the subject "
        "boundary as an ordinary in-camera occlusion with no face swap, pasted head, halo, sharpening seam, or cutout edge. "
        f"Requested result: {guarded}"
    )


def _generate_scene_anchor(
    prepared: dict, composed_scene: str, contract: dict, seed_offset: int = 0
) -> tuple[torch.Tensor, dict]:
    studio.baseline._require_model("diffusion_models", SCENE_MODEL)
    studio.baseline._require_model("text_encoders", SCENE_CLIP)
    studio.baseline._require_model("vae", SCENE_VAE)
    started = time.perf_counter()
    prompt = _scene_layout_prompt(composed_scene, contract)
    seed = (studio.baseline.PRODUCTION_SEED + seed_offset) % (1 << 64)
    cached = _load_cached_anchor(prompt, seed)
    if cached is not None:
        return cached
    model = clip = vae = None
    try:
        model = studio.comfy_nodes.UNETLoader().load_unet(SCENE_MODEL, "default")[0]
        model = ModelSamplingAuraFlow().patch_aura(model, SCENE_SAMPLING_SHIFT)[0]
        clip = studio.comfy_nodes.CLIPLoader().load_clip(
            SCENE_CLIP, "lumina2", "default"
        )[0]
        vae = studio.comfy_nodes.VAELoader().load_vae(SCENE_VAE)[0]
        positive = studio.comfy_nodes.CLIPTextEncode().encode(clip, prompt)[0]
        negative = studio.comfy_nodes.CLIPTextEncode().encode(
            clip,
            "cinematic portrait, shallow depth of field, bokeh, blurred background, portrait mode, fake HDR, "
            "oversharpened edges, repeated people, cloned faces, fused bodies, malformed cars, garbled text",
        )[0]
        latent = EmptySD3LatentImage.execute(
            studio.OUTPUT_WIDTH, studio.OUTPUT_HEIGHT, 1
        )[0]
        sampled = studio.comfy_nodes.KSampler().sample(
            model,
            seed,
            SCENE_STEPS,
            SCENE_GUIDANCE,
            "res_multistep",
            "simple",
            positive,
            negative,
            latent,
            1.0,
        )[0]
        anchor = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0].detach().cpu()
        report = {
            "model": SCENE_MODEL,
            "text_encoder": SCENE_CLIP,
            "vae": SCENE_VAE,
            "steps": SCENE_STEPS,
            "guidance": SCENE_GUIDANCE,
            "sampler": "res_multistep",
            "seed": seed,
            "sampling_shift": SCENE_SAMPLING_SHIFT,
            "reference": None,
            "effective_prompt": prompt,
            "cache_hit": False,
            "seconds": round(time.perf_counter() - started, 3),
        }
        _save_cached_anchor(prompt, seed, anchor, report)
        return anchor, report
    finally:
        del model, clip, vae
        comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()


def generate_complex_candidate(
    prepared: dict,
    composed_scene: str,
    contract: dict,
    profile: dict,
) -> dict:
    targets = scene_object_targets(contract)
    layout_attempts = []
    selected = None
    selected_error = float("inf")
    offsets = SCENE_SEED_OFFSETS if targets else SCENE_SEED_OFFSETS[:1]
    for seed_offset in offsets:
        try:
            candidate_anchor, candidate_report = _generate_scene_anchor(
                prepared, composed_scene, contract, seed_offset
            )
            initial_face = _layout_face(candidate_anchor)
            candidate_anchor, crop_report = _crop_layout_anchor(
                candidate_anchor,
                initial_face,
                contract.get("framing", "Prompt decides"),
            )
            counts = count_scene_objects(candidate_anchor)
            count_error = object_count_error(counts, targets)
            candidate_face = _layout_face(candidate_anchor)
            candidate_mask, candidate_mask_report = _main_subject_mask(
                candidate_anchor, candidate_face
            )
            candidate_report["composition_crop"] = crop_report
            candidate_report["object_counts"] = counts
            candidate_report["count_error"] = count_error
            candidate_report["subject_mask"] = candidate_mask_report
            candidate_report["error"] = ""
        except Exception as exc:
            candidate_anchor = None
            candidate_report = {
                "seed_offset": seed_offset,
                "count_error": 999,
                "error": str(exc),
            }
            count_error = 999
        layout_attempts.append(
            {
                "seed": candidate_report.get("seed"),
                "seed_offset": seed_offset,
                "object_counts": candidate_report.get("object_counts"),
                "count_error": candidate_report.get("count_error"),
                "subject_mask": candidate_report.get("subject_mask"),
                "composition_crop": candidate_report.get("composition_crop"),
                "seconds": candidate_report.get("seconds"),
                "error": candidate_report.get("error", ""),
            }
        )
        if candidate_anchor is not None and count_error < selected_error:
            selected = (
                candidate_anchor,
                candidate_report,
                candidate_face,
                candidate_mask,
                candidate_mask_report,
            )
            selected_error = count_error
        if selected_error == 0:
            break

    if selected is None:
        raise RuntimeError("No usable complex-scene layout was generated.")
    anchor, layout_report, face, subject_mask, subject_mask_report = selected
    if targets and selected_error != 0:
        raise RuntimeError(
            "Complex-scene object counts did not satisfy the explicit request after "
            f"{len(layout_attempts)} layout attempt(s): targets={targets}, "
            f"best_counts={layout_report.get('object_counts')}. No unsafe direct fallback was used."
        )
    layout_report["object_count_gate"] = {
        "status": "passed",
        "targets": targets,
        "selected_error": selected_error,
        "attempts": layout_attempts,
    }
    masked_anchor, identity_removal = _remove_anchor_identity(anchor, face)
    low_resolution_anchor = studio.baseline._resize_reference(
        masked_anchor, SCENE_ANCHOR_PIXELS
    )

    final_started = time.perf_counter()
    complex_lora_strength = min(
        COMPLEX_LORA_STRENGTH_MAX,
        profile["lora_strength"] + COMPLEX_LORA_STRENGTH_BONUS,
    )
    model = studio.comfy_nodes.UNETLoader().load_unet(
        studio.baseline.MODEL_4B_BASE_NAME, "default"
    )[0]
    model = studio.comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
        model, studio.baseline.PRODUCTION_LORA_NAME, complex_lora_strength
    )[0]
    clip = studio.comfy_nodes.CLIPLoader().load_clip(
        studio.baseline.CLIP_4B_NAME, "flux2", "default"
    )[0]
    vae = studio.comfy_nodes.VAELoader().load_vae(studio.baseline.VAE_NAME)[0]
    anchor_latent = studio.comfy_nodes.VAEEncode().encode(vae, low_resolution_anchor)[0]["samples"]
    identity_latents = [
        studio.comfy_nodes.VAEEncode().encode(vae, image)[0]["samples"]
        for image in prepared["latent_images"]
    ]
    prompt = _final_identity_prompt(composed_scene, contract)
    positive = studio.comfy_nodes.CLIPTextEncode().encode(clip, prompt)[0]
    positive = studio.node_helpers.conditioning_set_values(
        positive,
        {"reference_latents": [anchor_latent, *identity_latents]},
        append=True,
    )
    negative = studio.comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
    guider = studio.CFGGuider.execute(model, positive, negative, profile["guidance_scale"])[0]
    sampler = studio.KSamplerSelect.execute("euler")[0]
    sigmas = studio.Flux2Scheduler.execute(
        studio.baseline.PRODUCTION_STEPS, studio.OUTPUT_WIDTH, studio.OUTPUT_HEIGHT
    )[0]
    source_latent = studio.comfy_nodes.VAEEncode().encode(vae, anchor)[0]
    latent = studio.comfy_nodes.SetLatentNoiseMask().set_mask(
        source_latent, subject_mask
    )[0]

    attempts = []
    selected_photo = None
    selected_score = -1.0
    selected_confidence = 0.0
    selected_seed = studio.baseline.PRODUCTION_SEED + FINAL_SEED_OFFSETS[0]
    for offset in FINAL_SEED_OFFSETS:
        seed = (studio.baseline.PRODUCTION_SEED + offset) % (1 << 64)
        noise = studio.RandomNoise.execute(seed)[0]
        sampled = studio.SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        candidate = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        try:
            embedding, confidence = studio.baseline._face_embedding(
                candidate, f"complex-scene candidate {len(attempts) + 1}"
            )
            similarity = studio.baseline._cosine_similarity(
                prepared["identity_centroid"], embedding
            )
            error = ""
        except RuntimeError as exc:
            similarity = -1.0
            confidence = 0.0
            error = str(exc)
        attempts.append(
            {
                "attempt": len(attempts) + 1,
                "seed": seed,
                "similarity_to_reference_centroid": round(similarity, 4),
                "face_detection_confidence": round(confidence, 4),
                "error": error,
            }
        )
        if similarity > selected_score:
            selected_photo = candidate
            selected_score = similarity
            selected_confidence = confidence
            selected_seed = seed
        if similarity >= profile["identity_retry_threshold"]:
            break

    if selected_photo is None or selected_score < 0:
        raise RuntimeError("No face was detected in the complex-scene identity pass.")
    return {
        "photo": selected_photo,
        "effective_prompt": prompt,
        "similarity": selected_score,
        "detection_confidence": selected_confidence,
        "selected_seed": selected_seed,
        "attempts": attempts,
        "layout_stage": layout_report,
        "identity_stage": {
            "model": studio.baseline.MODEL_4B_BASE_NAME,
            "lora": studio.baseline.PRODUCTION_LORA_NAME,
            "lora_strength": complex_lora_strength,
            "steps": studio.baseline.PRODUCTION_STEPS,
            "anchor_pixels": SCENE_ANCHOR_PIXELS,
            "anchor_shape": list(low_resolution_anchor.shape),
            "anchor_identity_removal": identity_removal,
            "mode": "main_subject_only_latent_inpaint",
            "subject_mask": subject_mask_report,
            "background_owner": SCENE_MODEL,
            "seconds": round(time.perf_counter() - final_started, 3),
        },
    }
