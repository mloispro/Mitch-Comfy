from __future__ import annotations

import functools
from pathlib import Path

import cv2
import numpy as np


HUMAN_SEGMENTATION_MODEL = "u2net_human_seg.onnx"
HUMAN_SEGMENTATION_SHA256 = "01EB6A29A5C4D8EDB30B56ADAD9BB3A2A0535338E480724A213E0ACFD2D1C73C"
HUMAN_SEGMENTATION_INPUT_SIZE = (320, 320)
NATURAL_LENS_BLUR_PROFILE = "u2net_human_edge_safe_depth_ramp_v1"
FACE_INPAINT_STRENGTH = 1.00
BACKGROUND_INPAINT_STRENGTH = 1.00
SUBJECT_PROTECTION_DILATION_FRACTION = 0.008
MASK_FEATHER_FRACTION = 0.006
BACKGROUND_SUBJECT_THRESHOLD = 0.12
BACKGROUND_EXCLUSION_DILATION_FRACTION = 0.004
BACKGROUND_PROTECTION_DILATION_FRACTION = 0.006
BACKGROUND_FEATHER_SIGMA_FRACTION = 0.003
BACKGROUND_NEAR_SIGMA_FRACTION = 0.0022
BACKGROUND_FAR_SIGMA_FRACTION = 0.0055
BACKGROUND_DEPTH_RAMP_FRACTION = 0.18


@functools.lru_cache(maxsize=1)
def _segmentation_session(model_path: str):
    import onnxruntime as ort

    return ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])


def human_foreground_mask(rgb: np.ndarray, model_path: Path) -> np.ndarray:
    """Return the installed U2Net human foreground probability at source resolution."""
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("Expected one RGB image for human segmentation.")
    image = cv2.resize(
        rgb,
        HUMAN_SEGMENTATION_INPUT_SIZE,
        interpolation=cv2.INTER_LANCZOS4,
    ).astype(np.float32)
    image /= max(float(image.max()), 1e-6)
    mean = np.asarray((0.485, 0.456, 0.406), dtype=np.float32)
    std = np.asarray((0.229, 0.224, 0.225), dtype=np.float32)
    image = ((image - mean) / std).transpose(2, 0, 1)[None, ...]

    session = _segmentation_session(str(model_path))
    prediction = session.run(None, {session.get_inputs()[0].name: image})[0][0, 0]
    minimum = float(prediction.min())
    maximum = float(prediction.max())
    if maximum <= minimum:
        raise RuntimeError("Human segmentation returned a flat mask.")
    prediction = (prediction - minimum) / (maximum - minimum)
    height, width = rgb.shape[:2]
    return np.clip(
        cv2.resize(prediction, (width, height), interpolation=cv2.INTER_LANCZOS4),
        0.0,
        1.0,
    ).astype(np.float32)


def face_interior_mask(
    width: int,
    height: int,
    bbox: tuple[float, float, float, float] | list[float],
) -> np.ndarray:
    """Feathered facial-interior mask that leaves hairline and outer head geometry intact."""
    x1, y1, x2, y2 = (float(value) for value in bbox)
    face_width = max(1.0, x2 - x1)
    face_height = max(1.0, y2 - y1)
    center = (
        round((x1 + x2) * 0.5),
        round(y1 + face_height * 0.52),
    )
    axes = (
        max(1, round(face_width * 0.435)),
        max(1, round(face_height * 0.455)),
    )
    mask = np.zeros((height, width), dtype=np.float32)
    cv2.ellipse(mask, center, axes, 0.0, 0.0, 360.0, 1.0, thickness=-1)
    sigma = max(2.0, min(width, height) * MASK_FEATHER_FRACTION)
    return np.clip(cv2.GaussianBlur(mask, (0, 0), sigmaX=sigma, sigmaY=sigma), 0.0, 1.0)


def background_edit_mask(foreground: np.ndarray) -> np.ndarray:
    """Protect the segmented person plus a small safety rim and expose only the background."""
    height, width = foreground.shape
    protected = (foreground >= 0.20).astype(np.uint8)
    radius = max(3, round(min(width, height) * SUBJECT_PROTECTION_DILATION_FRACTION))
    kernel_size = radius * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    protected = cv2.dilate(protected, kernel, iterations=1).astype(np.float32)
    mask = 1.0 - protected
    sigma = max(2.0, min(width, height) * MASK_FEATHER_FRACTION)
    return np.clip(cv2.GaussianBlur(mask, (0, 0), sigmaX=sigma, sigmaY=sigma), 0.0, 1.0)


def compose_edit_masks(
    foreground: np.ndarray,
    face_mask: np.ndarray,
    detailed_background: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the face mask, combined preview mask, and isolated background mask."""
    background = background_edit_mask(foreground)
    active_background = background if detailed_background else np.zeros_like(background)
    combined = np.maximum(active_background, face_mask)
    return (
        np.clip(face_mask, 0.0, 1.0).astype(np.float32),
        np.clip(combined, 0.0, 1.0).astype(np.float32),
        background,
    )


def _normalized_background_blur(
    rgb: np.ndarray,
    known_background: np.ndarray,
    sigma: float,
) -> np.ndarray:
    """Blur only known background colors so the subject cannot bleed into the blur."""
    weights = known_background.astype(np.float32)
    denominator = cv2.GaussianBlur(
        weights, (0, 0), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_REFLECT_101
    )
    numerator = cv2.GaussianBlur(
        rgb * weights[..., None],
        (0, 0),
        sigmaX=sigma,
        sigmaY=sigma,
        borderType=cv2.BORDER_REFLECT_101,
    )
    return np.clip(
        numerator / np.maximum(denominator[..., None], 1e-5), 0.0, 1.0
    ).astype(np.float32)


def apply_natural_lens_background_blur(
    rgb: np.ndarray,
    foreground: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Apply mild edge-safe near-to-far background blur and keep the subject exact."""
    height, width = rgb.shape[:2]
    if foreground.shape != (height, width):
        raise ValueError(
            f"Foreground mask shape {foreground.shape} does not match image {(height, width)}."
        )
    source = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    subject_seed = (np.clip(foreground, 0.0, 1.0) >= BACKGROUND_SUBJECT_THRESHOLD).astype(
        np.uint8
    )
    minimum_edge = min(width, height)

    exclusion_radius = max(
        2, round(minimum_edge * BACKGROUND_EXCLUSION_DILATION_FRACTION)
    )
    exclusion_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (exclusion_radius * 2 + 1, exclusion_radius * 2 + 1)
    )
    excluded_subject = cv2.dilate(subject_seed, exclusion_kernel, iterations=1)
    known_background = 1.0 - excluded_subject.astype(np.float32)

    protection_radius = max(
        exclusion_radius + 1,
        round(minimum_edge * BACKGROUND_PROTECTION_DILATION_FRACTION),
    )
    protection_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (protection_radius * 2 + 1, protection_radius * 2 + 1)
    )
    protected_subject = cv2.dilate(subject_seed, protection_kernel, iterations=1)
    feather_sigma = max(1.5, minimum_edge * BACKGROUND_FEATHER_SIGMA_FRACTION)
    blur_alpha = 1.0 - cv2.GaussianBlur(
        protected_subject.astype(np.float32),
        (0, 0),
        sigmaX=feather_sigma,
        sigmaY=feather_sigma,
        borderType=cv2.BORDER_REFLECT_101,
    )
    blur_alpha[protected_subject > 0] = 0.0
    blur_alpha = np.clip(blur_alpha, 0.0, 1.0).astype(np.float32)

    near_sigma = max(1.5, minimum_edge * BACKGROUND_NEAR_SIGMA_FRACTION)
    far_sigma = max(near_sigma + 1.0, minimum_edge * BACKGROUND_FAR_SIGMA_FRACTION)
    near_blur = _normalized_background_blur(source, known_background, near_sigma)
    far_blur = _normalized_background_blur(source, known_background, far_sigma)

    distance = cv2.distanceTransform(1 - protected_subject, cv2.DIST_L2, 5)
    depth = np.clip(
        distance / max(minimum_edge * BACKGROUND_DEPTH_RAMP_FRACTION, 1.0),
        0.0,
        1.0,
    )
    depth = depth * depth * (3.0 - 2.0 * depth)
    optical_blur = near_blur + (far_blur - near_blur) * depth[..., None]
    output = source + (optical_blur - source) * blur_alpha[..., None]
    output[protected_subject > 0] = source[protected_subject > 0]
    output = np.clip(output, 0.0, 1.0).astype(np.float32)

    protected_error = np.abs(output[protected_subject > 0] - source[protected_subject > 0])
    changed = np.any(np.abs(output - source) > (0.5 / 255.0), axis=2)
    return output, blur_alpha, {
        "profile": NATURAL_LENS_BLUR_PROFILE,
        "method": "U2Net human matte plus subject-excluding normalized Gaussian blur",
        "near_sigma_pixels": round(float(near_sigma), 4),
        "far_sigma_pixels": round(float(far_sigma), 4),
        "depth_ramp_pixels": round(
            float(minimum_edge * BACKGROUND_DEPTH_RAMP_FRACTION), 4
        ),
        "subject_protection_radius_pixels": int(protection_radius),
        "subject_exclusion_radius_pixels": int(exclusion_radius),
        "active_background_fraction": round(float(np.mean(blur_alpha > 0.0)), 6),
        "changed_pixel_fraction": round(float(changed.mean()), 6),
        "protected_subject_max_error_0_to_255": round(
            float(protected_error.max(initial=0.0) * 255.0), 8
        ),
        "subject_colors_excluded_from_background_blur": True,
        "phone_on_path_unchanged": True,
    }


def blur_background(rgb: np.ndarray, foreground: np.ndarray) -> np.ndarray:
    """Compatibility wrapper for the natural lens background mode."""
    return apply_natural_lens_background_blur(rgb, foreground)[0]
