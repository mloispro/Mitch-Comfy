from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import cv2
import numpy as np


HEAD_PAD_X = 0.45
HEAD_PAD_TOP = 0.70
HEAD_PAD_BOTTOM = 0.45
MIN_CROWN_CLEARANCE_RATIO = 0.22
MIN_HEAD_CORE_COVERAGE = 0.60


@dataclass(frozen=True)
class HeadIntegrityReport:
    status: str
    face_bbox: list[float]
    head_core_bbox: list[int]
    crown_clearance_ratio: float
    left_clearance_ratio: float
    right_clearance_ratio: float
    back_side: str
    back_clearance_ratio: float
    head_core_coverage: float
    failures: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def _clamped_bbox(
    shape: tuple[int, int], face_bbox: Sequence[float]
) -> tuple[int, int, int, int]:
    height, width = shape
    x1, y1, x2, y2 = [float(value) for value in face_bbox]
    face_width = max(1.0, x2 - x1)
    face_height = max(1.0, y2 - y1)
    left = max(0, int(round(x1 - face_width * HEAD_PAD_X)))
    right = min(width, int(round(x2 + face_width * HEAD_PAD_X)))
    top = max(0, int(round(y1 - face_height * HEAD_PAD_TOP)))
    bottom = min(height, int(round(y2 + face_height * HEAD_PAD_BOTTOM)))
    return left, top, right, bottom


def build_head_protection_mask(
    shape: tuple[int, int], face_bbox: Sequence[float]
) -> tuple[np.ndarray, dict]:
    """Build a conservative full-head/neck support region around a detected face."""
    left, top, right, bottom = _clamped_bbox(shape, face_bbox)
    mask = np.zeros(shape, dtype=np.uint8)
    center = ((left + right) // 2, (top + bottom) // 2)
    axes = (max(1, (right - left) // 2), max(1, (bottom - top) // 2))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 1, -1)
    return mask, {
        "bbox": [left, top, right, bottom],
        "area_fraction": round(float(mask.mean()), 4),
        "face_padding": {
            "horizontal_face_widths": HEAD_PAD_X,
            "top_face_heights": HEAD_PAD_TOP,
            "bottom_face_heights": HEAD_PAD_BOTTOM,
        },
        "method": "full_head_and_neck_ellipse_union",
    }


def measure_head_integrity(
    person_mask: np.ndarray,
    face_bbox: Sequence[float],
    face_keypoints: np.ndarray | None = None,
) -> HeadIntegrityReport:
    """Measure whether a segmented subject contains a plausible complete head.

    This is intentionally a narrow structural gate. It does not claim to judge
    overall realism; it catches missing crown/back-of-head failures that a face
    embedding can still score highly.
    """
    binary = np.asarray(person_mask) > 0
    height, width = binary.shape
    x1, y1, x2, y2 = [float(value) for value in face_bbox]
    face_width = max(1.0, x2 - x1)
    face_height = max(1.0, y2 - y1)

    core_left = max(0, int(round(x1 - face_width * 0.18)))
    core_right = min(width, int(round(x2 + face_width * 0.18)))
    core_top = max(0, int(round(y1 - face_height * 0.42)))
    core_bottom = min(height, int(round(y2 - face_height * 0.08)))
    core = np.zeros_like(binary, dtype=np.uint8)
    center = ((core_left + core_right) // 2, (core_top + core_bottom) // 2)
    axes = (
        max(1, (core_right - core_left) // 2),
        max(1, (core_bottom - core_top) // 2),
    )
    cv2.ellipse(core, center, axes, 0, 0, 360, 1, -1)
    core_pixels = core > 0
    core_coverage = float(np.count_nonzero(binary & core_pixels)) / max(
        1, int(np.count_nonzero(core_pixels))
    )

    search_left = max(0, int(round(x1 - face_width * 0.8)))
    search_right = min(width, int(round(x2 + face_width * 0.8)))
    search_top = max(0, int(round(y1 - face_height * 0.9)))
    search_bottom = min(height, int(round(y1 + face_height * 0.45)))
    local = binary[search_top:search_bottom, search_left:search_right]
    ys, xs = np.where(local)
    if len(xs):
        subject_left = search_left + int(xs.min())
        subject_right = search_left + int(xs.max()) + 1
        subject_top = search_top + int(ys.min())
    else:
        subject_left = subject_right = int(round((x1 + x2) / 2.0))
        subject_top = int(round(y1))

    crown_clearance = max(0.0, y1 - subject_top) / face_height
    left_clearance = max(0.0, x1 - subject_left) / face_width
    right_clearance = max(0.0, subject_right - x2) / face_width

    back_side = "either"
    if face_keypoints is not None and len(face_keypoints) >= 3:
        points = np.asarray(face_keypoints, dtype=np.float32)
        eye_mid_x = float((points[0, 0] + points[1, 0]) * 0.5)
        eye_distance = max(1.0, abs(float(points[1, 0] - points[0, 0])))
        yaw_proxy = (float(points[2, 0]) - eye_mid_x) / eye_distance
        if yaw_proxy > 0.08:
            back_side = "left"
        elif yaw_proxy < -0.08:
            back_side = "right"
    if back_side == "left":
        back_clearance = left_clearance
    elif back_side == "right":
        back_clearance = right_clearance
    else:
        back_clearance = max(left_clearance, right_clearance)

    failures = []
    if crown_clearance < MIN_CROWN_CLEARANCE_RATIO:
        failures.append("insufficient_crown_clearance")
    if core_coverage < MIN_HEAD_CORE_COVERAGE:
        failures.append("incomplete_head_core")
    return HeadIntegrityReport(
        status="passed" if not failures else "rejected",
        face_bbox=[round(float(value), 1) for value in face_bbox],
        head_core_bbox=[core_left, core_top, core_right, core_bottom],
        crown_clearance_ratio=round(crown_clearance, 4),
        left_clearance_ratio=round(left_clearance, 4),
        right_clearance_ratio=round(right_clearance, 4),
        back_side=back_side,
        back_clearance_ratio=round(back_clearance, 4),
        head_core_coverage=round(core_coverage, 4),
        failures=failures,
    )
