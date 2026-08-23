from __future__ import annotations

import cv2
import numpy as np


HAZE_PARAMETERS = {
    "base_veil": 0.03,
    "highlight_veil": 0.11,
    "highlight_bloom": 0.03,
    "highlight_low": 0.68,
    "highlight_high": 0.92,
    "blur_fraction": 0.09,
}


def _smoothstep(low: float, high: float, values: np.ndarray | float):
    scaled = np.clip((values - low) / max(high - low, 1e-6), 0.0, 1.0)
    return scaled * scaled * (3.0 - (2.0 * scaled))


def apply_phone_lens_haze(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Apply a subtle, highlight-driven handled-phone-lens veil without blurring detail.

    The image must be RGB float data in the [0, 1] range. The operation is deterministic.
    It scatters bright-source color through a broad low-frequency mask while leaving the
    underlying pixels spatially sharp, so skin pores and identity detail are not smeared.
    """

    rgb = np.asarray(image, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("phone-lens haze expects an H x W x 3 RGB image")
    if not np.isfinite(rgb).all():
        raise ValueError("phone-lens haze input contains non-finite values")

    amount = float(np.clip(strength, 0.0, 2.0))
    if amount == 0.0:
        return np.clip(rgb, 0.0, 1.0).copy()

    rgb = np.clip(rgb, 0.0, 1.0)
    luminance = (
        (0.2126 * rgb[..., 0])
        + (0.7152 * rgb[..., 1])
        + (0.0722 * rgb[..., 2])
    )
    source_mask = _smoothstep(
        HAZE_PARAMETERS["highlight_low"],
        HAZE_PARAMETERS["highlight_high"],
        luminance,
    ).astype(np.float32)
    source_mask = np.power(source_mask, 1.35, dtype=np.float32)

    sigma = max(rgb.shape[:2]) * HAZE_PARAMETERS["blur_fraction"]
    local_field = cv2.GaussianBlur(
        source_mask,
        (0, 0),
        sigmaX=sigma,
        sigmaY=sigma,
        borderType=cv2.BORDER_REFLECT101,
    )
    field_scale = max(float(np.percentile(local_field, 99.5)), 0.04)
    local_field = np.clip(local_field / field_scale, 0.0, 1.0)

    bright_percentile = float(np.percentile(luminance, 98.5))
    highlight_presence = float(_smoothstep(0.68, 0.90, bright_percentile))

    weight_sum = float(source_mask.sum())
    if weight_sum > 1e-5:
        source_color = (
            (rgb * source_mask[..., None]).sum(axis=(0, 1)) / weight_sum
        )
    else:
        source_color = np.array([0.94, 0.95, 0.96], dtype=np.float32)
    source_color = np.clip(source_color, 0.72, 1.0).astype(np.float32)
    neutral_scatter = np.array([0.94, 0.95, 0.96], dtype=np.float32)
    veil_color = ((0.70 * source_color) + (0.30 * neutral_scatter)).astype(
        np.float32
    )

    veil = (
        HAZE_PARAMETERS["base_veil"]
        + (
            HAZE_PARAMETERS["highlight_veil"]
            * highlight_presence
            * local_field
        )
    ) * amount
    veil = np.clip(veil, 0.0, 0.22)
    result = (rgb * (1.0 - veil[..., None])) + (
        veil_color[None, None, :] * veil[..., None]
    )

    bright_rgb = rgb * source_mask[..., None]
    bloom = cv2.GaussianBlur(
        bright_rgb,
        (0, 0),
        sigmaX=sigma * 0.55,
        sigmaY=sigma * 0.55,
        borderType=cv2.BORDER_REFLECT101,
    )
    result += (
        HAZE_PARAMETERS["highlight_bloom"]
        * amount
        * highlight_presence
        * bloom
        * local_field[..., None]
    )
    return np.clip(result, 0.0, 1.0).astype(np.float32)
