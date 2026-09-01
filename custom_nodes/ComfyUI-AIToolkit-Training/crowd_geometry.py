from __future__ import annotations

import cv2
import numpy as np


MASK_INTERNAL_FACE = "internal_face_geometry_lock"
MASK_FULL_HEAD = "full_head_identity_lock"
FACE_HEIGHT_RATIO_RANGE = (0.90, 1.12)
FACE_WIDTH_RATIO_RANGE = (0.90, 1.12)
FACE_CENTER_SHIFT_MAXIMUM = 0.14


def build_internal_face_mask(
    image_shape,
    face_bbox,
    context_ring_pixels: int = 18,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Keep the plate's skull/body geometry and regenerate only internal features."""
    height, width = [int(value) for value in image_shape[:2]]
    x1, y1, x2, y2 = [float(value) for value in face_bbox]
    face_width = max(1.0, x2 - x1)
    face_height = max(1.0, y2 - y1)
    center = (
        int(round((x1 + x2) * 0.5)),
        int(round(y1 + face_height * 0.54)),
    )
    axes = (
        max(4, int(round(face_width * 0.39))),
        max(6, int(round(face_height * 0.43))),
    )
    hard = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(hard, center, axes, 0, 0, 360, 1, -1)

    ring = max(8, int(context_ring_pixels))
    outside = (1 - hard).astype(np.uint8)
    distance = cv2.distanceTransform(outside, cv2.DIST_L2, 5)
    soft = np.where(hard > 0, 1.0, np.clip(1.0 - distance / ring, 0.0, 1.0))
    soft = soft.astype(np.float32)
    hard_ys, hard_xs = np.where(hard > 0)
    soft_ys, soft_xs = np.where(soft > 0)
    return hard.astype(np.float32), soft, {
        "strategy": MASK_INTERNAL_FACE,
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
        "hard_area_fraction": round(float(hard.mean()), 4),
        "soft_area_fraction": round(float((soft > 0).mean()), 4),
        "context_ring_pixels": ring,
        "ellipse_center": list(center),
        "ellipse_axes": list(axes),
        "geometry_ownership": "plate owns skull silhouette, hair, ears, neck, body, clothing, pose, and contact shadow",
    }


def build_full_head_mask(
    image_shape,
    face_bbox,
    context_ring_pixels: int = 24,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Let the LoRA own the complete head/upper neck while locking the body and scene."""
    height, width = [int(value) for value in image_shape[:2]]
    x1, y1, x2, y2 = [float(value) for value in face_bbox]
    face_width = max(1.0, x2 - x1)
    face_height = max(1.0, y2 - y1)
    center = (
        int(round((x1 + x2) * 0.5)),
        int(round(y1 + face_height * 0.38)),
    )
    axes = (
        max(8, int(round(face_width * 0.78))),
        max(12, int(round(face_height * 1.00))),
    )
    hard = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(hard, center, axes, 0, 0, 360, 1, -1)

    ring = max(12, int(context_ring_pixels))
    outside = (1 - hard).astype(np.uint8)
    distance = cv2.distanceTransform(outside, cv2.DIST_L2, 5)
    soft = np.where(hard > 0, 1.0, np.clip(1.0 - distance / ring, 0.0, 1.0))
    soft = soft.astype(np.float32)
    hard_ys, hard_xs = np.where(hard > 0)
    soft_ys, soft_xs = np.where(soft > 0)
    return hard.astype(np.float32), soft, {
        "strategy": MASK_FULL_HEAD,
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
        "hard_area_fraction": round(float(hard.mean()), 4),
        "soft_area_fraction": round(float((soft > 0).mean()), 4),
        "context_ring_pixels": ring,
        "ellipse_center": list(center),
        "ellipse_axes": list(axes),
        "geometry_ownership": (
            "LoRA owns complete head and upper neck; plate owns shoulders, body, clothing, "
            "pose, hands, props, secondary people, and background"
        ),
    }


def face_geometry_metrics(plate_bbox, output_bbox) -> dict:
    if output_bbox is None:
        return {
            "status": "rejected",
            "failures": ["main_face_bbox_unavailable"],
        }
    px1, py1, px2, py2 = [float(value) for value in plate_bbox]
    ox1, oy1, ox2, oy2 = [float(value) for value in output_bbox]
    plate_width = max(1.0, px2 - px1)
    plate_height = max(1.0, py2 - py1)
    output_width = max(1.0, ox2 - ox1)
    output_height = max(1.0, oy2 - oy1)
    plate_center = np.array([(px1 + px2) * 0.5, (py1 + py2) * 0.5])
    output_center = np.array([(ox1 + ox2) * 0.5, (oy1 + oy2) * 0.5])
    center_shift = float(np.linalg.norm(output_center - plate_center) / plate_height)
    height_ratio = output_height / plate_height
    width_ratio = output_width / plate_width
    failures = []
    if not FACE_HEIGHT_RATIO_RANGE[0] <= height_ratio <= FACE_HEIGHT_RATIO_RANGE[1]:
        failures.append("face_height_changed_relative_to_plate")
    if not FACE_WIDTH_RATIO_RANGE[0] <= width_ratio <= FACE_WIDTH_RATIO_RANGE[1]:
        failures.append("face_width_changed_relative_to_plate")
    if center_shift > FACE_CENTER_SHIFT_MAXIMUM:
        failures.append("face_center_shifted_relative_to_plate")
    return {
        "status": "passed" if not failures else "rejected",
        "plate_bbox": [round(value, 1) for value in (px1, py1, px2, py2)],
        "output_bbox": [round(value, 1) for value in (ox1, oy1, ox2, oy2)],
        "face_height_ratio": round(height_ratio, 4),
        "face_width_ratio": round(width_ratio, 4),
        "face_center_shift_in_plate_face_heights": round(center_shift, 4),
        "height_ratio_range": list(FACE_HEIGHT_RATIO_RANGE),
        "width_ratio_range": list(FACE_WIDTH_RATIO_RANGE),
        "center_shift_maximum": FACE_CENTER_SHIFT_MAXIMUM,
        "failures": failures,
    }
