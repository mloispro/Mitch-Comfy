from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path

import cv2
import folder_paths
import node_helpers
import numpy as np
import torch

import comfy.model_management
import nodes as comfy_nodes
from comfy_extras.nodes_custom_sampler import (
    CFGGuider,
    KSamplerSelect,
    RandomNoise,
    SamplerCustomAdvanced,
)
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler

from . import one_reference_photo as baseline
from . import reference_photo_studio as studio
from .camera_finish import apply_natural_phone_finish
from .complex_scene_route import _main_subject_component, _remove_anchor_identity
from .crowd_geometry import (
    FACE_CENTER_SHIFT_MAXIMUM,
    FACE_HEIGHT_RATIO_RANGE,
    FACE_WIDTH_RATIO_RANGE,
    MASK_INTERNAL_FACE,
    MASK_FULL_HEAD,
    build_full_head_mask,
    build_internal_face_mask,
    face_geometry_metrics,
)
from .head_integrity import build_head_protection_mask, measure_head_integrity
from .identity_leakage import evaluate_identity_scope
from .scene_objects import count_scene_objects


OUTPUT_ROOT = "crowd-proof/state-fair"
OUTPUT_WIDTH = 896
OUTPUT_HEIGHT = 1344
REFERENCE_PIXELS = 512 * 512
MODE_WHOLE_FRAME = "whole_frame_reference"
MODE_CONTEXTUAL = "contextual_inpaint"
MODES = (MODE_WHOLE_FRAME, MODE_CONTEXTUAL)
MASK_FULL_BODY = "contextual_full_body"
MASK_STRATEGIES = (MASK_FULL_BODY, MASK_INTERNAL_FACE, MASK_FULL_HEAD)
IDENTITY_MINIMUM = 0.75
DETECTION_MINIMUM = 0.75
FACE_HEIGHT_MINIMUM = 85.0
SECONDARY_DUPLICATE_MAXIMUM = 0.60
FACE_LOCAL_DETAIL_RATIO_RANGE = (0.65, 1.35)


def _image_tensor_from_path(path: Path) -> torch.Tensor:
    from PIL import Image

    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(rgb).unsqueeze(0)


def _rgb8(image: torch.Tensor) -> np.ndarray:
    return np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(
        np.uint8
    )


def _select_host_face(
    image: torch.Tensor, target_face_index_left_to_right: int | None = None
):
    rgb = _rgb8(image)
    height, width = rgb.shape[:2]
    faces = baseline._face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError("No host face was detected in the crowd plate.")

    candidates = []
    for index, face in enumerate(faces):
        x1, y1, x2, y2 = [float(value) for value in face.bbox]
        face_width = max(1.0, x2 - x1)
        face_height = max(1.0, y2 - y1)
        center_x = (x1 + x2) * 0.5
        center_y = (y1 + y2) * 0.5
        normalized_x = center_x / max(width, 1)
        normalized_y = center_y / max(height, 1)
        centrality = math.exp(-3.2 * abs(normalized_x - 0.5))
        foreground = math.exp(-2.2 * abs(normalized_y - 0.48))
        area = face_width * face_height
        eligible = 0.18 <= normalized_x <= 0.82 and 0.20 <= normalized_y <= 0.72
        score = area * (0.35 + 0.65 * centrality) * (0.55 + 0.45 * foreground)
        if not eligible:
            score *= 0.15
        candidates.append(
            {
                "index": index,
                "face": face,
                "bbox": [x1, y1, x2, y2],
                "face_height": face_height,
                "score": score,
                "eligible": eligible,
            }
        )
    left_to_right = sorted(
        candidates,
        key=lambda item: (item["bbox"][0] + item["bbox"][2]) * 0.5,
    )
    if target_face_index_left_to_right is None:
        selected = max(candidates, key=lambda item: item["score"])
        selected_left_to_right = next(
            index for index, item in enumerate(left_to_right) if item is selected
        )
        selection_method = "automatic_central_foreground"
    else:
        requested = int(target_face_index_left_to_right)
        if requested < 0 or requested >= len(left_to_right):
            raise RuntimeError(
                "Requested left-to-right face index "
                f"{requested}, but only {len(left_to_right)} face(s) were detected."
            )
        selected = left_to_right[requested]
        selected_left_to_right = requested
        selection_method = "explicit_left_to_right_index"
    report = {
        "selected_index": selected["index"],
        "selected_left_to_right_index": selected_left_to_right,
        "selection_method": selection_method,
        "selected_bbox": [round(value, 1) for value in selected["bbox"]],
        "selected_face_height": round(selected["face_height"], 1),
        "faces": [
            {
                "index": item["index"],
                "bbox": [round(value, 1) for value in item["bbox"]],
                "face_height": round(item["face_height"], 1),
                "score": round(float(item["score"]), 2),
                "eligible": item["eligible"],
            }
            for item in candidates
        ],
    }
    return selected["face"], report


def _host_person_detection(image: torch.Tensor, face_bbox) -> tuple[list[int], dict]:
    """Select the tallest YOLO person box containing the chosen host face."""
    counts = count_scene_objects(image)
    height, width = image.shape[1:3]
    x1, y1, x2, y2 = [float(value) for value in face_bbox]
    face_center = ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
    candidates = []
    for item in counts.get("boxes", []):
        if item.get("class") != "person":
            continue
        left, top, right, bottom = [float(value) for value in item["bbox"]]
        contains = (
            left <= face_center[0] <= right and top <= face_center[1] <= bottom
        )
        overlap_left = max(left, x1)
        overlap_top = max(top, y1)
        overlap_right = min(right, x2)
        overlap_bottom = min(bottom, y2)
        face_overlap = max(0.0, overlap_right - overlap_left) * max(
            0.0, overlap_bottom - overlap_top
        )
        if not contains and face_overlap <= 0:
            continue
        box_width = max(1.0, right - left)
        box_height = max(1.0, bottom - top)
        score = box_width * box_height * (1.0 + box_height / max(height, 1))
        candidates.append((score, item))
    if not candidates:
        raise RuntimeError("No detected person box contains the selected host face.")
    selected = max(candidates, key=lambda value: value[0])[1]
    left, top, right, bottom = [float(value) for value in selected["bbox"]]
    # Keep the detector's full silhouette but prevent a connected U2Net crowd blob
    # from claiming unrelated foreground pedestrians.
    padding_x = max(4, int(round((right - left) * 0.025)))
    padding_y = max(4, int(round((bottom - top) * 0.010)))
    bbox = [
        max(0, int(math.floor(left)) - padding_x),
        max(0, int(math.floor(top)) - padding_y),
        min(width, int(math.ceil(right)) + padding_x),
        min(height, int(math.ceil(bottom)) + padding_y),
    ]
    return bbox, {
        "model": counts.get("model"),
        "detected_bbox": [round(left, 1), round(top, 1), round(right, 1), round(bottom, 1)],
        "restricted_bbox": bbox,
        "confidence": selected.get("confidence"),
        "candidate_count": len(candidates),
    }


def _restrict_component_to_host(
    component: np.ndarray, host_bbox: list[int]
) -> tuple[np.ndarray, dict]:
    original = (np.asarray(component) > 0).astype(np.uint8)
    gate = np.zeros_like(original)
    left, top, right, bottom = host_bbox
    gate[top:bottom, left:right] = 1
    restricted = original * gate
    if not np.any(restricted):
        raise RuntimeError("Host isolation removed the entire U2Net component.")
    return restricted, {
        "u2net_component_area_fraction": round(float(original.mean()), 4),
        "restricted_component_area_fraction": round(float(restricted.mean()), 4),
        "removed_component_fraction": round(
            1.0 - float(restricted.sum()) / max(1.0, float(original.sum())), 4
        ),
        "method": "face_selected_u2net_component_intersected_with_tallest_face_containing_person_box",
    }


def build_contextual_subject_mask(
    component: np.ndarray,
    face_bbox,
    dilation_pixels: int = 18,
    context_ring_pixels: int = 36,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Build a full-body core plus a soft, diffusion-owned transition ring."""
    selected = (np.asarray(component) > 0).astype(np.uint8)
    if selected.ndim != 2 or not np.any(selected):
        raise RuntimeError("The host component is empty.")
    height, width = selected.shape
    raw_ys, raw_xs = np.where(selected > 0)
    head_support, head_report = build_head_protection_mask(selected.shape, face_bbox)
    selected = np.maximum(selected, head_support.astype(np.uint8))

    body_left = int(raw_xs.min())
    body_right = int(raw_xs.max()) + 1
    body_top = int(raw_ys.min())
    body_bottom = int(raw_ys.max()) + 1
    body_width = max(1, body_right - body_left)
    body_height = max(1, body_bottom - body_top)
    contact = np.zeros_like(selected)
    contact_center = (
        int(round((body_left + body_right) * 0.5)),
        min(height - 1, body_bottom - 1),
    )
    contact_axes = (
        max(8, int(round(body_width * 0.34))),
        max(5, int(round(body_height * 0.026))),
    )
    cv2.ellipse(contact, contact_center, contact_axes, 0, 0, 360, 1, -1)
    selected = np.maximum(selected, contact)

    dilation = max(0, int(dilation_pixels))
    if dilation:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (dilation * 2 + 1, dilation * 2 + 1)
        )
        hard = cv2.dilate(selected, kernel, iterations=1)
    else:
        hard = selected.copy()

    ring = max(1, int(context_ring_pixels))
    outside = (1 - hard).astype(np.uint8)
    distance = cv2.distanceTransform(outside, cv2.DIST_L2, 5)
    soft = np.where(hard > 0, 1.0, np.clip(1.0 - distance / ring, 0.0, 1.0))
    soft = soft.astype(np.float32)
    hard_ys, hard_xs = np.where(hard > 0)
    soft_ys, soft_xs = np.where(soft > 0)
    hard_area = float(hard.mean())
    soft_area = float((soft > 0).mean())
    if hard_area < 0.05 or soft_area > 0.82:
        raise RuntimeError(
            f"Implausible contextual mask area: hard={hard_area:.1%}, soft={soft_area:.1%}."
        )
    return hard.astype(np.float32), soft, {
        "raw_component_bbox": [body_left, body_top, body_right, body_bottom],
        "hard_bbox": [
            int(hard_xs.min()),
            int(hard_ys.min()),
            int(hard_xs.max()) + 1,
            int(hard_ys.max()) + 1,
        ],
        "soft_bbox": [
            int(soft_xs.min()),
            int(soft_ys.min()),
            int(soft_xs.max()) + 1,
            int(soft_ys.max()) + 1,
        ],
        "hard_area_fraction": round(hard_area, 4),
        "soft_area_fraction": round(soft_area, 4),
        "dilation_pixels": dilation,
        "context_ring_pixels": ring,
        "contact_support": {
            "center": list(contact_center),
            "axes": list(contact_axes),
        },
        "head_protection": head_report,
    }


def _remove_internal_face_identity(
    image: torch.Tensor,
    face_bbox,
    soft_mask: np.ndarray,
    *,
    method: str = "internal_face_only_pixelation_blur_with_soft_transition",
    preserved: str = "skull silhouette, hair, ears, neck, body, clothing, pose, and contact shadow",
) -> tuple[torch.Tensor, dict]:
    rgb = _rgb8(image)
    ys, xs = np.where(soft_mask > 0)
    left, top = int(xs.min()), int(ys.min())
    right, bottom = int(xs.max()) + 1, int(ys.max()) + 1
    region = rgb[top:bottom, left:right]
    tiny_width = max(3, min(6, region.shape[1] // 8))
    tiny_height = max(4, min(8, region.shape[0] // 8))
    tiny = cv2.resize(region, (tiny_width, tiny_height), interpolation=cv2.INTER_AREA)
    obscured = cv2.resize(
        tiny, (region.shape[1], region.shape[0]), interpolation=cv2.INTER_LINEAR
    )
    obscured = cv2.GaussianBlur(obscured, (0, 0), sigmaX=3.0, sigmaY=3.0)
    alpha = soft_mask[top:bottom, left:right, None].astype(np.float32)
    result = rgb.astype(np.float32)
    result[top:bottom, left:right] = (
        region.astype(np.float32) * (1.0 - alpha)
        + obscured.astype(np.float32) * alpha
    )
    tensor = torch.from_numpy(result / 255.0).unsqueeze(0).to(dtype=image.dtype)
    return tensor, {
        "face_bbox": [round(float(value), 1) for value in face_bbox],
        "obscured_bbox": [left, top, right, bottom],
        "method": method,
        "preserved": preserved,
    }


def _mask_image(mask: np.ndarray) -> torch.Tensor:
    tensor = torch.from_numpy(np.asarray(mask, dtype=np.float32)).unsqueeze(0).unsqueeze(-1)
    return tensor.repeat(1, 1, 1, 3)


def _diagnostic_overlay(image: torch.Tensor, hard: np.ndarray, soft: np.ndarray) -> torch.Tensor:
    rgb = image.detach().float().cpu().clone()
    hard_tensor = torch.from_numpy(hard).unsqueeze(0).unsqueeze(-1)
    soft_tensor = torch.from_numpy(soft).unsqueeze(0).unsqueeze(-1)
    red = torch.zeros_like(rgb)
    red[..., 0] = 1.0
    green = torch.zeros_like(rgb)
    green[..., 1] = 1.0
    overlay = rgb * (1.0 - soft_tensor * 0.32) + green * soft_tensor * 0.20
    overlay = overlay * (1.0 - hard_tensor * 0.22) + red * hard_tensor * 0.22
    return torch.clamp(overlay, 0.0, 1.0)


def _identity_scope(
    image: torch.Tensor, identity_centroid: np.ndarray, expected_host_bbox: list[int]
) -> dict:
    rgb = _rgb8(image)
    faces = baseline._face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    scope = evaluate_identity_scope(
        [np.asarray(face.normed_embedding, dtype=np.float32) for face in faces],
        [face.bbox for face in faces],
        [float(face.det_score) for face in faces],
        identity_centroid,
        IDENTITY_MINIMUM,
        secondary_duplicate_maximum=SECONDARY_DUPLICATE_MAXIMUM,
    ).as_dict()
    main_index = scope.get("main_face_index")
    main_height = 0.0
    if main_index is not None and 0 <= int(main_index) < len(faces):
        bbox = faces[int(main_index)].bbox
        main_height = float(bbox[3] - bbox[1])
        center_x = float(bbox[0] + bbox[2]) * 0.5
        center_y = float(bbox[1] + bbox[3]) * 0.5
        left, top, right, bottom = expected_host_bbox
        in_expected_host = left <= center_x <= right and top <= center_y <= bottom
    else:
        in_expected_host = False
    scope["main_face_height"] = round(main_height, 1)
    scope["main_face_in_expected_host"] = bool(in_expected_host)
    if not in_expected_host:
        scope["failures"].append("identity_match_outside_expected_host")
        scope["status"] = "rejected"
    return scope


def _detail_metrics(image: torch.Tensor, hard_mask: np.ndarray) -> dict:
    rgb = _rgb8(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge_response = cv2.magnitude(gradient_x, gradient_y)
    subject = hard_mask > 0.5
    ring_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (65, 65))
    outer = cv2.dilate(subject.astype(np.uint8), ring_kernel, iterations=1) > 0
    neighbor = outer & ~subject
    background = ~outer
    subject_edge = float(edge_response[subject].mean()) if np.any(subject) else 0.0
    neighbor_edge = float(edge_response[neighbor].mean()) if np.any(neighbor) else 0.0
    background_edge = float(edge_response[background].mean()) if np.any(background) else 0.0
    ratio = subject_edge / max(neighbor_edge, 1e-6)
    return {
        "method": "mean_3x3_sobel_gradient_magnitude",
        "subject_edge_mean": round(subject_edge, 4),
        "same_depth_neighbor_edge_mean": round(neighbor_edge, 4),
        "background_edge_mean": round(background_edge, 4),
        "subject_to_neighbor_edge_ratio": round(ratio, 4),
        "diagnostic_laplacian_subject_mean": round(
            float(laplacian[subject].mean()) if np.any(subject) else 0.0, 4
        ),
        "diagnostic_laplacian_neighbor_mean": round(
            float(laplacian[neighbor].mean()) if np.any(neighbor) else 0.0, 4
        ),
    }


def _main_face_bbox(scope: dict) -> list[float] | None:
    for face in scope.get("faces", []):
        if face.get("role") == "main":
            return [float(value) for value in face["bbox"]]
    return None


def _face_local_detail(image: torch.Tensor, face_bbox) -> dict:
    rgb = _rgb8(image)
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face_bbox]
    left = max(0, int(math.floor(x1)))
    top = max(0, int(math.floor(y1)))
    right = min(width, int(math.ceil(x2)))
    bottom = min(height, int(math.ceil(y2)))
    crop = rgb[top:bottom, left:right]
    if crop.size == 0:
        return {"sobel_mean": 0.0, "laplacian_mean": 0.0}
    crop = cv2.resize(crop, (96, 128), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    yy, xx = np.ogrid[:128, :96]
    internal = ((xx - 47.5) / 40.0) ** 2 + ((yy - 64.0) / 54.0) ** 2 <= 1.0
    laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    sobel = cv2.magnitude(gradient_x, gradient_y)
    return {
        "method": "normalized_internal_face_ellipse_at_96x128",
        "sobel_mean": round(float(sobel[internal].mean()), 4),
        "laplacian_mean": round(float(laplacian[internal].mean()), 4),
    }


def _face_detail_comparison(
    plate: torch.Tensor,
    plate_bbox,
    output: torch.Tensor,
    output_bbox,
) -> dict:
    if output_bbox is None:
        return {
            "status": "rejected",
            "failures": ["main_face_bbox_unavailable"],
        }
    plate_detail = _face_local_detail(plate, plate_bbox)
    output_detail = _face_local_detail(output, output_bbox)
    sobel_ratio = float(output_detail["sobel_mean"]) / max(
        float(plate_detail["sobel_mean"]), 1e-6
    )
    laplacian_ratio = float(output_detail["laplacian_mean"]) / max(
        float(plate_detail["laplacian_mean"]), 1e-6
    )
    failures = []
    low, high = FACE_LOCAL_DETAIL_RATIO_RANGE
    if not low <= sobel_ratio <= high or not low <= laplacian_ratio <= high:
        failures.append("localized_face_texture_mismatch")
    return {
        "status": "passed" if not failures else "rejected",
        "plate": plate_detail,
        "output": output_detail,
        "output_to_plate_sobel_ratio": round(sobel_ratio, 4),
        "output_to_plate_laplacian_ratio": round(laplacian_ratio, 4),
        "ratio_range": list(FACE_LOCAL_DETAIL_RATIO_RANGE),
        "failures": failures,
    }


def _whole_frame_prompt() -> str:
    return (
        "Picture 1 is the complete state-fair scene and composition. Preserve its dense irregular crowd, independent "
        "pedestrian directions, varied ordinary clothing, food stalls, umbrellas, Ferris wheel, pavement, daylight, "
        "deep phone-camera focus, and depth order. The central host's face is intentionally obscured. Pictures 2 and 3 "
        "show the same man, m1tch_person; Picture 3 is only a closer crop. Recreate one whole candid smartphone photograph "
        "with m1tch_person replacing the central host at the same scale and position, walking naturally in a fitted navy "
        "crew-neck T-shirt and dark casual pants. Keep every bystander unrelated and occupied with the fair. The entire "
        "frame must share one exposure, perspective, focus progression, edge response, skin response, sensor texture, and "
        "compression. No portrait blur, parade, staged row, pasted boundary, selective sharpening, logo, or watermark."
    )


def _contextual_prompt(scene_context: str | None = None) -> str:
    if scene_context:
        return (
            "Picture 1 is the exact complete scene, composition, host pose, clothing, camera response, and lighting "
            f"reference for this requested setting: {scene_context.strip()} The selected host identity in Picture 1 "
            "is the only invalid element. Pictures 2 and 3 show the same man, m1tch_person, with Picture 3 as a closer "
            "crop. Inside the editable region, regenerate one complete m1tch_person continuously from hair and ears "
            "through shoes and contact shadow, preserving his current face, short light-brown hair and hairline, apparent "
            "age, and lean build while retaining the plate host's scale, pose, clothing, gaze direction, and occlusions. "
            "Match the existing exposure, white balance, phone-camera focus, edge softness, noise, shadows, and depth. "
            "Preserve every person and scene element outside the editable transition exactly. No face swap, pasted head "
            "or body, halo, selective sharpening, portrait blur, logo, or watermark."
        )
    return (
        "Picture 1 is the exact state-fair scene and lighting reference; only its central host identity is invalid. "
        "Pictures 2 and 3 show the same man, m1tch_person, with Picture 3 as a closer crop. Inside the editable region, "
        "regenerate one complete m1tch_person from hair and ears through shoes and contact shadow, preserving his current "
        "face, short light-brown hair and hairline, apparent age, and lean build. Keep the host's scale and natural stride, "
        "wearing a fitted navy crew-neck T-shirt and dark casual pants. Match the existing daylight, phone-camera focus, "
        "edge softness, noise, shadows, and occlusion. Preserve the crowd and fair outside the editable transition exactly. "
        "No face swap, pasted head or body, halo, selective sharpening, portrait blur, logo, or watermark."
    )


def _internal_face_prompt(scene_context: str | None = None) -> str:
    setting = (
        f" The setting is {scene_context.strip()}." if scene_context else ""
    )


def _full_head_prompt(scene_context: str | None = None) -> str:
    setting = f" The setting is {scene_context.strip()}." if scene_context else ""
    return (
        "Pictures 2 and 3 show the exact current m1tch_person identity, with Picture 3 as a closer crop. "
        "Picture 1 is the exact immutable photograph, camera response, and pose reference. Only its selected man's "
        "complete head and upper neck are obscured and invalid. Reconstruct one coherent current m1tch_person head from "
        "crown through hairline, forehead, eyes, nose, mouth, ears, jaw, and upper neck, preserving his apparent age, "
        "short light-brown hair, natural skin, and recognizable proportions. Keep Picture 1's head angle, down/up pitch, "
        "left/right turn, gaze direction, expression scale, head center, lighting, softness, noise, and occlusion. The "
        "shoulders, body, clothing, pose, hands, props, secondary people, and background are already correct and must "
        "remain unchanged. Do not create a pasted head, halo, beauty filter, selective sharpness, duplicate identity, "
        "or a second m1tch_person."
        f"{setting}"
    )
    return (
        "Picture 1 is the exact immutable photograph and camera response. Its existing skull size, head silhouette, hair, "
        "ears, neck, shoulders, body, clothing, pose, hands, legs, shoes, contact shadow, crowd, and background are all "
        "already correct and must remain unchanged. Only the internal facial features are obscured and invalid. Pictures "
        "2 and 3 show the same man, m1tch_person; Picture 3 is a closer crop. Reconstruct his recognizable current eyes, "
        "nose, mouth, jaw cues, apparent age, and natural skin only inside the original face footprint. Keep the detected "
        "face height, width, center, perspective, expression scale, lighting, softness, noise, and color response equal to "
        "Picture 1. Do not enlarge or reposition the face, redraw the skull, invent hair, deepen wrinkles, over-render skin, "
        "or create mottled patches, a face boundary, halo, beauty filter, or selective sharpness."
        f"{setting}"
    )


def _acceptance(
    scope: dict,
    detail: dict,
    plate_counts: dict,
    output_counts: dict,
    plate_face_height: float,
    face_geometry: dict,
    face_detail: dict,
) -> dict:
    failures = list(scope.get("failures", []))
    if float(plate_face_height) < FACE_HEIGHT_MINIMUM:
        failures.append("plate_host_face_too_small_for_identity_lock")
    if float(scope.get("main_detection_confidence", 0.0)) < DETECTION_MINIMUM:
        failures.append("main_detection_confidence_below_threshold")
    if float(scope.get("main_face_height", 0.0)) < FACE_HEIGHT_MINIMUM:
        failures.append("main_face_too_small")
    ratio = float(detail.get("subject_to_neighbor_edge_ratio", 0.0))
    if ratio < 0.75 or ratio > 1.35:
        failures.append("subject_neighbor_edge_mismatch")
    plate_people = max(1, int(plate_counts.get("person", 0)))
    output_people = int(output_counts.get("person", 0))
    crowd_ratio = output_people / plate_people
    if crowd_ratio < 0.65:
        failures.append("crowd_count_collapsed")
    failures.extend(face_geometry.get("failures", []))
    failures.extend(face_detail.get("failures", []))
    failures = list(dict.fromkeys(failures))
    return {
        "status": "passed" if not failures else "rejected",
        "failures": failures,
        "identity_minimum": IDENTITY_MINIMUM,
        "detection_minimum": DETECTION_MINIMUM,
        "face_height_minimum": FACE_HEIGHT_MINIMUM,
        "plate_face_height": round(float(plate_face_height), 1),
        "face_height_ratio_range": list(FACE_HEIGHT_RATIO_RANGE),
        "face_width_ratio_range": list(FACE_WIDTH_RATIO_RANGE),
        "face_center_shift_maximum": FACE_CENTER_SHIFT_MAXIMUM,
        "face_local_detail_ratio_range": list(FACE_LOCAL_DETAIL_RATIO_RANGE),
        "edge_ratio_range": [0.75, 1.35],
        "crowd_preservation_ratio": round(crowd_ratio, 4),
        "visual_review_required": True,
    }


def _generate(
    scene_plate_path: str,
    reference_names: list[str],
    mode: str,
    lora_strength: float,
    seed: int,
    context_ring_pixels: int,
    scene_context: str | None = None,
    mask_strategy: str = MASK_FULL_BODY,
    denoise_strength: float = 1.0,
    preserve_plate_dimensions: bool = False,
    target_face_index_left_to_right: int | None = None,
    lora_name: str | None = None,
    apply_phone_finish: bool = True,
):
    started = time.perf_counter()
    plate_path = Path(scene_plate_path).expanduser().resolve()
    plate = _image_tensor_from_path(plate_path)
    if preserve_plate_dimensions:
        output_height, output_width = [int(value) for value in plate.shape[1:3]]
    else:
        output_height, output_width = OUTPUT_HEIGHT, OUTPUT_WIDTH
    if tuple(plate.shape[1:3]) != (output_height, output_width):
        plate = baseline._resize_reference(plate, OUTPUT_WIDTH * OUTPUT_HEIGHT)
        if tuple(plate.shape[1:3]) != (output_height, output_width):
            plate = torch.nn.functional.interpolate(
                plate.movedim(-1, 1),
                size=(output_height, output_width),
                mode="bilinear",
                align_corners=False,
            ).movedim(1, -1)

    prepared = studio._prepare_sources(
        reference_names, "Full + face crop 2.4x", REFERENCE_PIXELS
    )
    host_face, host_report = _select_host_face(
        plate, target_face_index_left_to_right
    )
    plate_counts = count_scene_objects(plate)
    host_person_bbox, host_person_report = _host_person_detection(
        plate, host_face.bbox
    )
    component, component_label = _main_subject_component(plate, host_face)
    component, isolation_report = _restrict_component_to_host(
        component, host_person_bbox
    )
    if mask_strategy == MASK_INTERNAL_FACE:
        hard_mask, soft_mask, mask_report = build_internal_face_mask(
            plate.shape[1:3],
            host_face.bbox,
            context_ring_pixels=context_ring_pixels,
        )
    elif mask_strategy == MASK_FULL_HEAD:
        hard_mask, soft_mask, mask_report = build_full_head_mask(
            plate.shape[1:3],
            host_face.bbox,
            context_ring_pixels=context_ring_pixels,
        )
    else:
        hard_mask, soft_mask, mask_report = build_contextual_subject_mask(
            component,
            host_face.bbox,
            dilation_pixels=18,
            context_ring_pixels=context_ring_pixels,
        )
        mask_report["strategy"] = MASK_FULL_BODY
    mask_report["selected_component"] = int(component_label)
    mask_report["host_person_detection"] = host_person_report
    mask_report["component_isolation"] = isolation_report
    if mask_strategy == MASK_INTERNAL_FACE:
        obscured_plate, identity_removal = _remove_internal_face_identity(
            plate, host_face.bbox, soft_mask
        )
    elif mask_strategy == MASK_FULL_HEAD:
        obscured_plate, identity_removal = _remove_internal_face_identity(
            plate,
            host_face.bbox,
            soft_mask,
            method="complete_head_pixelation_blur_with_soft_transition",
            preserved="shoulders, body, clothing, pose, hands, props, secondary people, and background",
        )
    else:
        obscured_plate, identity_removal = _remove_anchor_identity(plate, host_face)
    diagnostic = _diagnostic_overlay(plate, hard_mask, soft_mask)

    model = clip = vae = None
    raw = final = None
    try:
        baseline._require_model("diffusion_models", baseline.MODEL_4B_BASE_NAME)
        baseline._require_model("text_encoders", baseline.CLIP_4B_NAME)
        baseline._require_model("vae", baseline.VAE_NAME)
        model = comfy_nodes.UNETLoader().load_unet(
            baseline.MODEL_4B_BASE_NAME, "default"
        )[0]
        active_lora_name = lora_name or baseline.PRODUCTION_LORA_NAME
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, active_lora_name, float(lora_strength)
        )[0]
        clip = comfy_nodes.CLIPLoader().load_clip(
            baseline.CLIP_4B_NAME, "flux2", "default"
        )[0]
        vae = comfy_nodes.VAELoader().load_vae(baseline.VAE_NAME)[0]

        scene_reference = baseline._resize_reference(obscured_plate, REFERENCE_PIXELS)
        reference_images = [scene_reference, *prepared["latent_images"]]
        reference_latents = [
            comfy_nodes.VAEEncode().encode(vae, image)[0]["samples"]
            for image in reference_images
        ]
        if mode == MODE_WHOLE_FRAME:
            prompt = _whole_frame_prompt()
        elif mask_strategy == MASK_INTERNAL_FACE:
            prompt = _internal_face_prompt(scene_context)
        elif mask_strategy == MASK_FULL_HEAD:
            prompt = _full_head_prompt(scene_context)
        else:
            prompt = _contextual_prompt(scene_context)
        positive = comfy_nodes.CLIPTextEncode().encode(clip, prompt)[0]
        positive = node_helpers.conditioning_set_values(
            positive, {"reference_latents": reference_latents}, append=True
        )
        negative = comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
        guider = CFGGuider.execute(model, positive, negative, 4.0)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        full_sigmas = Flux2Scheduler.execute(20, output_width, output_height)[0]
        if mode == MODE_CONTEXTUAL and float(denoise_strength) < 1.0:
            retained_steps = max(1, int(round(20 * float(denoise_strength))))
            sigmas = full_sigmas[-(retained_steps + 1) :]
        else:
            retained_steps = 20
            sigmas = full_sigmas
        if mode == MODE_WHOLE_FRAME:
            latent = EmptyFlux2LatentImage.execute(output_width, output_height, 1)[0]
        else:
            source_latent = comfy_nodes.VAEEncode().encode(vae, plate)[0]
            latent = comfy_nodes.SetLatentNoiseMask().set_mask(
                source_latent, torch.from_numpy(soft_mask).unsqueeze(0)
            )[0]
        noise = RandomNoise.execute(int(seed))[0]
        sampled = SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent
        )[0]
        raw = comfy_nodes.VAEDecode().decode(vae, sampled)[0].detach().cpu()
        if apply_phone_finish:
            final, finish_report = apply_natural_phone_finish(raw)
        else:
            final = raw
            finish_report = {
                "status": "disabled",
                "reason": "exact_scene_source_tone_preservation",
            }
    finally:
        del model, clip, vae
        comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()

    scope = _identity_scope(
        final, prepared["identity_centroid"], host_person_bbox
    )
    raw_scope = _identity_scope(
        raw, prepared["identity_centroid"], host_person_bbox
    )
    output_counts = count_scene_objects(final)
    detail = _detail_metrics(final, hard_mask)
    plate_detail = _detail_metrics(plate, hard_mask)
    output_main_bbox = _main_face_bbox(scope)
    face_geometry = face_geometry_metrics(host_face.bbox, output_main_bbox)
    face_detail = _face_detail_comparison(
        plate, host_face.bbox, final, output_main_bbox
    )
    head_integrity = {}
    try:
        output_face, _ = _select_host_face(
            final, target_face_index_left_to_right
        )
        output_component, _ = _main_subject_component(final, output_face)
        head_integrity = measure_head_integrity(
            output_component, output_face.bbox, getattr(output_face, "kps", None)
        ).as_dict()
    except RuntimeError as exc:
        head_integrity = {
            "status": "rejected",
            "failures": ["head_integrity_analysis_failed"],
            "error": str(exc),
        }
    acceptance = _acceptance(
        scope,
        detail,
        plate_counts,
        output_counts,
        float(host_report["selected_face_height"]),
        face_geometry,
        face_detail,
    )
    if head_integrity.get("status") != "passed":
        acceptance["failures"].append("head_integrity_rejected")
        acceptance["status"] = "rejected"

    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    strength_label = f"{float(lora_strength):.2f}".replace(".", "p")
    strategy_label = {
        MASK_INTERNAL_FACE: "face-lock",
        MASK_FULL_HEAD: "head-lock",
    }.get(mask_strategy, "full-body")
    output_root = (
        "flux2-generated-photo-identity-edit"
        if preserve_plate_dimensions
        else OUTPUT_ROOT
    )
    output_folder = f"{output_root}/{mode}-{strategy_label}-lora-{strength_label}/{run_stamp}"
    report = {
        "schema_version": 1,
        "purpose": (
            "generated_photo_identity_edit"
            if preserve_plate_dimensions
            else "state_fair_crowd_identity_proof"
        ),
        "mode": mode,
        "mask_strategy": mask_strategy,
        "scene_plate": str(plate_path),
        "model": baseline.MODEL_4B_BASE_NAME,
        "text_encoder": baseline.CLIP_4B_NAME,
        "vae": baseline.VAE_NAME,
        "lora": lora_name or baseline.PRODUCTION_LORA_NAME,
        "lora_strength": round(float(lora_strength), 4),
        "steps": 20,
        "effective_sampling_steps": int(retained_steps),
        "denoise_strength": round(float(denoise_strength), 4),
        "guidance": 4.0,
        "sampler": "euler",
        "seed": int(seed),
        "width": output_width,
        "height": output_height,
        "prompt": prompt,
        "scene_context": scene_context or "fixed_state_fair_proof",
        "reference_order": ["face-obscured scene", "genuine full photo", "genuine face crop"],
        "source_references": reference_names,
        "selected_identity_reference": prepared["selected_reference"],
        "host_selection": host_report,
        "anchor_identity_removal": identity_removal,
        "subject_mask": mask_report,
        "identity": scope,
        "identity_before_phone_finish": raw_scope,
        "head_integrity": head_integrity,
        "face_geometry": face_geometry,
        "face_local_detail": face_detail,
        "plate_counts": plate_counts,
        "output_counts": output_counts,
        "plate_detail": plate_detail,
        "output_detail": detail,
        "phone_finish": finish_report,
        "acceptance": acceptance,
        "seconds": round(time.perf_counter() - started, 3),
    }
    saved_final = comfy_nodes.SaveImage().save_images(
        final, f"{output_folder}/final", extra_pnginfo={"crowd_proof": report}
    )
    comfy_nodes.SaveImage().save_images(raw, f"{output_folder}/raw")
    comfy_nodes.SaveImage().save_images(obscured_plate, f"{output_folder}/obscured-plate")
    comfy_nodes.SaveImage().save_images(_mask_image(hard_mask), f"{output_folder}/host-core-mask")
    comfy_nodes.SaveImage().save_images(_mask_image(soft_mask), f"{output_folder}/transition-mask")
    comfy_nodes.SaveImage().save_images(diagnostic, f"{output_folder}/diagnostic-overlay")
    report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return final, _mask_image(soft_mask), diagnostic, report, output_folder, saved_final


class Flux2CrowdProofExperiment:
    """Internal state-fair harness for whole-frame and contextual identity routes."""

    @classmethod
    def INPUT_TYPES(cls):
        references = ["Upload one face photo", *baseline._available_input_images()]
        optional_references = [studio.NO_REFERENCE, *baseline._available_input_images()]
        return {
            "required": {
                "scene_plate_path": (
                    "STRING",
                    {
                        "default": str(
                            Path("C:/projects/AI-Tools/Mitch-Comfy/output/")
                            / "scene-first-state-fair-plate-seed-8675401.png"
                        )
                    },
                ),
                "face_reference": (references, {"image_upload": True}),
                "reference_2": (optional_references, {"image_upload": True}),
                "reference_3": (optional_references, {"image_upload": True}),
                "reference_4": (optional_references, {"image_upload": True}),
                "mode": (list(MODES),),
                "mask_strategy": (list(MASK_STRATEGIES),),
                "denoise_strength": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.2, "max": 1.0, "step": 0.05},
                ),
                "lora_strength": (
                    "FLOAT",
                    {"default": 0.50, "min": 0.0, "max": 1.2, "step": 0.05},
                ),
                "seed": (
                    "INT",
                    {"default": 8675310, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
                "context_ring_pixels": (
                    "INT",
                    {"default": 36, "min": 8, "max": 96, "step": 4},
                ),
            },
            "optional": {
                "scene_context": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                    },
                ),
                "preserve_plate_dimensions": (
                    "BOOLEAN",
                    {"default": False},
                ),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        scene_plate_path,
        face_reference,
        reference_2,
        reference_3,
        reference_4,
        mode,
        mask_strategy,
        denoise_strength,
        lora_strength,
        seed,
        context_ring_pixels,
        scene_context="",
        preserve_plate_dimensions=False,
    ):
        plate = Path(scene_plate_path).expanduser()
        if not plate.is_file():
            return f"Crowd plate is not available: {plate}"
        names = studio.selected_reference_names(
            face_reference, reference_2, reference_3, reference_4
        )
        validation = studio._validate_reference_names(names)
        if validation is not True:
            return validation
        if mode not in MODES:
            return f"Unknown crowd proof mode: {mode}"
        if mask_strategy not in MASK_STRATEGIES:
            return f"Unknown crowd proof mask strategy: {mask_strategy}"
        if mode == MODE_WHOLE_FRAME and mask_strategy != MASK_FULL_BODY:
            return "Whole-frame mode does not use the internal-face geometry lock."
        if not 0.2 <= float(denoise_strength) <= 1.0:
            return "Denoise strength must be between 0.2 and 1.0."
        if not 0.0 <= float(lora_strength) <= 1.2:
            return "LoRA strength must be between 0 and 1.2."
        if int(context_ring_pixels) < 8:
            return "Context ring must be at least 8 pixels."
        if bool(preserve_plate_dimensions):
            from PIL import Image

            with Image.open(plate) as source:
                width, height = source.size
            if width < 512 or height < 512:
                return "The preserved plate must be at least 512 pixels on both axes."
            if width % 16 or height % 16:
                return "Preserved plate dimensions must be divisible by 16."
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("photo", "transition_mask", "diagnostic", "report_json", "output_folder")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity/Experiments"
    OUTPUT_NODE = True

    def generate(
        self,
        scene_plate_path,
        face_reference,
        reference_2,
        reference_3,
        reference_4,
        mode,
        mask_strategy,
        denoise_strength,
        lora_strength,
        seed,
        context_ring_pixels,
        scene_context="",
        preserve_plate_dimensions=False,
    ):
        names = studio.selected_reference_names(
            face_reference, reference_2, reference_3, reference_4
        )
        validation = self.VALIDATE_INPUTS(
            scene_plate_path,
            face_reference,
            reference_2,
            reference_3,
            reference_4,
            mode,
            mask_strategy,
            denoise_strength,
            lora_strength,
            seed,
            context_ring_pixels,
            scene_context,
            preserve_plate_dimensions,
        )
        if validation is not True:
            raise RuntimeError(validation)
        photo, mask, diagnostic, report, output_folder, saved = _generate(
            scene_plate_path,
            names,
            mode,
            lora_strength,
            seed,
            context_ring_pixels,
            scene_context=scene_context.strip() or None,
            mask_strategy=mask_strategy,
            denoise_strength=denoise_strength,
            preserve_plate_dimensions=preserve_plate_dimensions,
        )
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    f"Crowd proof {mode}; automated {report['acceptance']['status']}; "
                    f"identity {report['identity']['main_identity_similarity']:.4f}. "
                    f"Saved to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (
                photo,
                mask,
                diagnostic,
                json.dumps(report, indent=2),
                output_folder,
            ),
        }
