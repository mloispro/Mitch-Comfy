from __future__ import annotations

import threading

import cv2
import numpy as np
import torch


SOURCE_GAZE_LOCK_PROFILE = "mediapipe_refined_iris_source_lock_v1"
MAX_SHIFT_EYE_WIDTH = 0.18
MIN_SHIFT_PIXELS = 0.35
MIN_VERTICAL_COORDINATE_DELTA = 0.03

_EYES = (
    {
        "name": "subject_right",
        "corners": (33, 133),
        "upper": (160, 158),
        "lower": (144, 153),
        "contour": (33, 160, 158, 133, 153, 144),
        "iris_center": 468,
        "iris_ring": (469, 470, 471, 472),
    },
    {
        "name": "subject_left",
        "corners": (362, 263),
        "upper": (385, 387),
        "lower": (380, 373),
        "contour": (362, 385, 387, 263, 373, 380),
        "iris_center": 473,
        "iris_ring": (474, 475, 476, 477),
    },
)

_MESH = None
_MESH_LOCK = threading.Lock()


def _face_mesh():
    global _MESH
    with _MESH_LOCK:
        if _MESH is None:
            import mediapipe as mp

            _MESH = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )
    return _MESH


def _detect_refined_landmarks(rgb_uint8: np.ndarray) -> tuple[np.ndarray, str]:
    if rgb_uint8.ndim != 3 or rgb_uint8.shape[2] < 3:
        raise ValueError("Expected one RGB uint8 image for source-gaze detection.")
    import mediapipe as mp

    mesh = _face_mesh()
    with _MESH_LOCK:
        result = mesh.process(np.ascontiguousarray(rgb_uint8[:, :, :3]))
    if not result.multi_face_landmarks or len(result.multi_face_landmarks) != 1:
        raise RuntimeError(
            "Source gaze lock requires exactly one MediaPipe-detectable face in both source and output."
        )
    height, width = rgb_uint8.shape[:2]
    points = np.asarray(
        [
            [landmark.x * width, landmark.y * height]
            for landmark in result.multi_face_landmarks[0].landmark
        ],
        dtype=np.float32,
    )
    if points.shape != (478, 2):
        raise RuntimeError(
            f"Source gaze lock expected 478 refined face/iris landmarks; found {points.shape[0]}."
        )
    return points, str(mp.__version__)


def _eye_measurement(points: np.ndarray, definition: dict) -> dict:
    corners = points[list(definition["corners"])]
    order = np.argsort(corners[:, 0])
    image_left, image_right = corners[order[0]], corners[order[1]]
    horizontal = image_right - image_left
    upper = points[list(definition["upper"])].mean(axis=0)
    lower = points[list(definition["lower"])].mean(axis=0)
    vertical = lower - upper
    basis = np.column_stack((horizontal, vertical))
    iris_center = points[definition["iris_center"]]
    coordinate = np.linalg.lstsq(
        basis, iris_center - image_left, rcond=None
    )[0]
    ring = points[list(definition["iris_ring"])]
    radius = float(np.mean(np.linalg.norm(ring - iris_center, axis=1)))
    return {
        "image_left": image_left,
        "image_right": image_right,
        "horizontal": horizontal,
        "vertical": vertical,
        "iris_center": iris_center,
        "iris_radius": max(radius, 1.0),
        "coordinate": coordinate,
        "eye_width": float(np.linalg.norm(horizontal)),
    }


def _coordinate_in_fixed_eye_geometry(
    iris_center: np.ndarray, fixed_eye: dict
) -> np.ndarray:
    basis = np.column_stack((fixed_eye["horizontal"], fixed_eye["vertical"]))
    return np.linalg.lstsq(
        basis, iris_center - fixed_eye["image_left"], rcond=None
    )[0]


def _compact(measurement: dict) -> dict:
    return {
        "iris_center_pixels": [
            round(float(value), 4) for value in measurement["iris_center"]
        ],
        "normalized_horizontal": round(float(measurement["coordinate"][0]), 6),
        "normalized_vertical": round(float(measurement["coordinate"][1]), 6),
        "eye_width_pixels": round(float(measurement["eye_width"]), 4),
        "iris_radius_pixels": round(float(measurement["iris_radius"]), 4),
    }


def _apply_with_landmarks(
    candidate_rgb: np.ndarray,
    source_points: np.ndarray,
    candidate_points: np.ndarray,
    strength: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Warp generated iris material toward source-relative coordinates only."""
    if candidate_rgb.ndim != 3 or candidate_rgb.shape[2] < 3:
        raise ValueError("Expected one RGB image for source-gaze correction.")
    if not 0.0 <= float(strength) <= 1.0:
        raise ValueError("Source-gaze strength must be between zero and one.")
    height, width = candidate_rgb.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    shift_x = np.zeros((height, width), dtype=np.float32)
    shift_y = np.zeros((height, width), dtype=np.float32)
    active = np.zeros((height, width), dtype=np.float32)
    eye_reports = []

    for definition in _EYES:
        source_eye = _eye_measurement(source_points, definition)
        candidate_eye = _eye_measurement(candidate_points, definition)
        vertical_delta = float(
            source_eye["coordinate"][1] - candidate_eye["coordinate"][1]
        )
        transfer_vertical = abs(vertical_delta) >= MIN_VERTICAL_COORDINATE_DELTA
        target_vertical = (
            source_eye["coordinate"][1]
            if transfer_vertical
            else candidate_eye["coordinate"][1]
        )
        target = (
            candidate_eye["image_left"]
            + candidate_eye["horizontal"] * source_eye["coordinate"][0]
            + candidate_eye["vertical"] * target_vertical
        )
        requested = (target - candidate_eye["iris_center"]) * float(strength)
        requested_length = float(np.linalg.norm(requested))
        maximum = candidate_eye["eye_width"] * MAX_SHIFT_EYE_WIDTH
        applied = requested.copy()
        if requested_length > maximum:
            applied *= maximum / requested_length

        contour = np.round(
            candidate_points[list(definition["contour"])]
        ).astype(np.int32)
        eye_interior = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(eye_interior, cv2.convexHull(contour), 255)
        eye_interior = cv2.erode(
            eye_interior, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        )
        destination = candidate_eye["iris_center"] + applied
        radius = candidate_eye["iris_radius"]
        sigma_x = max(radius * 1.45, candidate_eye["eye_width"] * 0.085)
        sigma_y = max(radius * 1.25, 2.0)
        local = np.exp(
            -0.5
            * (
                ((xx - destination[0]) / sigma_x) ** 2
                + ((yy - destination[1]) / sigma_y) ** 2
            )
        ).astype(np.float32)
        local *= eye_interior.astype(np.float32) / 255.0
        local[local < 0.002] = 0.0
        if float(np.linalg.norm(applied)) >= MIN_SHIFT_PIXELS:
            shift_x += float(applied[0]) * local
            shift_y += float(applied[1]) * local
            active = np.maximum(active, local)

        eye_reports.append(
            {
                "name": definition["name"],
                "source": _compact(source_eye),
                "candidate_before": _compact(candidate_eye),
                "target_center_pixels": [round(float(value), 4) for value in target],
                "vertical_coordinate_transferred": bool(transfer_vertical),
                "requested_shift_pixels": [
                    round(float(value), 4) for value in requested
                ],
                "applied_shift_pixels": [
                    round(float(value), 4) for value in applied
                ],
                "maximum_shift_pixels": round(float(maximum), 4),
                "shift_was_capped": bool(requested_length > maximum),
            }
        )

    warped = cv2.remap(
        candidate_rgb.astype(np.float32),
        xx - shift_x,
        yy - shift_y,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    selected = active > 0.0
    output = candidate_rgb.astype(np.float32).copy()
    output[selected] = warped[selected]
    report = {
        "profile": SOURCE_GAZE_LOCK_PROFILE,
        "method": "MediaPipe refined 478-landmark source-relative iris coordinate transfer",
        "strength": float(strength),
        "maximum_shift_eye_width_fraction": MAX_SHIFT_EYE_WIDTH,
        "minimum_vertical_coordinate_delta": MIN_VERTICAL_COORDINATE_DELTA,
        "eye_reports": eye_reports,
        "active_pixel_count": int(np.count_nonzero(selected)),
        "active_pixel_fraction": round(float(selected.mean()), 8),
        "source_pixels_copied": False,
        "eyelid_boundary_pixels_protected": True,
        "background_face_hair_and_eye_shape_protected": True,
    }
    return np.clip(output, 0.0, 1.0), active, report


def apply_source_gaze_lock(
    source_photo: torch.Tensor,
    generated_photo: torch.Tensor,
    strength: float = 1.0,
) -> tuple[torch.Tensor, torch.Tensor, dict]:
    """Match generated iris direction to the source without copying source pixels."""
    for label, image in (("source", source_photo), ("generated", generated_photo)):
        if image.ndim != 4 or image.shape[0] != 1 or image.shape[-1] < 3:
            raise ValueError(f"Expected exactly one RGB {label} image tensor.")
    source_rgb = (
        source_photo[0, :, :, :3]
        .detach()
        .float()
        .cpu()
        .clamp(0.0, 1.0)
        .numpy()
    )
    generated_rgb = (
        generated_photo[0, :, :, :3]
        .detach()
        .float()
        .cpu()
        .clamp(0.0, 1.0)
        .numpy()
    )
    source_uint8 = np.clip(source_rgb * 255.0, 0, 255).round().astype(np.uint8)
    generated_uint8 = (
        np.clip(generated_rgb * 255.0, 0, 255).round().astype(np.uint8)
    )
    source_points, mediapipe_version = _detect_refined_landmarks(source_uint8)
    generated_points, _ = _detect_refined_landmarks(generated_uint8)
    output, active, report = _apply_with_landmarks(
        generated_rgb, source_points, generated_points, strength
    )
    output_uint8 = np.clip(output * 255.0, 0, 255).round().astype(np.uint8)
    after_points, _ = _detect_refined_landmarks(output_uint8)

    for definition, eye_report in zip(_EYES, report["eye_reports"]):
        fixed_eye = _eye_measurement(generated_points, definition)
        after_eye = _eye_measurement(after_points, definition)
        fixed_coordinate = _coordinate_in_fixed_eye_geometry(
            after_eye["iris_center"], fixed_eye
        )
        eye_report["candidate_after"] = _compact(after_eye)
        eye_report["candidate_after_in_pixel_identical_eyelid_geometry"] = {
            "normalized_horizontal": round(float(fixed_coordinate[0]), 6),
            "normalized_vertical": round(float(fixed_coordinate[1]), 6),
        }
        before_error = abs(
            eye_report["candidate_before"]["normalized_horizontal"]
            - eye_report["source"]["normalized_horizontal"]
        )
        after_error = abs(
            eye_report["candidate_after_in_pixel_identical_eyelid_geometry"][
                "normalized_horizontal"
            ]
            - eye_report["source"]["normalized_horizontal"]
        )
        eye_report["horizontal_error_before"] = round(float(before_error), 6)
        eye_report["horizontal_error_after"] = round(float(after_error), 6)

    mean_before = float(
        np.mean(
            [item["horizontal_error_before"] for item in report["eye_reports"]]
        )
    )
    mean_after = float(
        np.mean(
            [item["horizontal_error_after"] for item in report["eye_reports"]]
        )
    )
    original = generated_rgb
    outside = ~(active > 0.0)
    outside_error = (
        np.abs(output[outside] - original[outside]) if np.any(outside) else np.zeros(1)
    )
    report.update(
        {
            "mediapipe_version": mediapipe_version,
            "mean_horizontal_error_before": round(mean_before, 6),
            "mean_horizontal_error_after": round(mean_after, 6),
            "horizontal_error_reduction_fraction": round(
                1.0 - mean_after / max(mean_before, 1e-8), 6
            ),
            "protected_pixel_max_error_0_to_255": round(
                float(outside_error.max() * 255.0), 8
            ),
        }
    )
    result = torch.from_numpy(output.astype(np.float32)).unsqueeze(0)
    preview = torch.from_numpy(
        np.repeat(active.astype(np.float32)[..., None], 3, axis=2)
    ).unsqueeze(0)
    return result, preview, report
