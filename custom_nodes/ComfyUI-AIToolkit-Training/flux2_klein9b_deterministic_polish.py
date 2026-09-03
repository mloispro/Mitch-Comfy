from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
import torch


POLISH_PROFILE = "deterministic_face_and_hair_local_v4"
MOUTH_CORNER_LIFT_FACE_HEIGHT = 0.009
SKIN_TEXTURE_BLEND = 0.12
FOREHEAD_WRINKLE_BLEND = 0.25
UNDER_EYE_TEXTURE_BLEND = 0.20
EYE_DETAIL_GAIN = 0.18
EYE_BRIGHTEN_GAIN = 0.012
STUBBLE_DETAIL_GAIN = 0.12
BONE_LIGHTING_GAIN = 0.045
CHEEK_HIGHLIGHT_GAIN = 0.018
JAW_CONTOUR_GAIN = 0.012
FRECKLE_RESPONSE_THRESHOLD = 0.0105
FRECKLE_COMPONENT_MAX_AREA = 72
FRECKLE_COMPONENT_MAX_DIAMETER = 13
FRECKLE_LOCAL_MEDIAN_DIAMETER = 7
HAIR_PARSER_MODEL = "facedetection/parsing_parsenet.pth"
HAIR_PARSER_SHA256 = "3D558D8D0E42C20224F13CF5A29C79EBA2D59913419F945545D8CF7B72920DE2"
HAIR_MID_FREQUENCY_GAIN = 0.42
HAIR_MICRO_FREQUENCY_GAIN = 1.30
HAIR_CHROMA_FREQUENCY_GAIN = 0.68
HAIR_HIGHLIGHT_LUMA_GAIN = 4.0
HAIR_HIGHLIGHT_WARMTH_GAIN = 0.8

_HAIR_PARSER = None
_HAIR_PARSER_LOCK = Lock()


def _gaussian(
    height: int,
    width: int,
    center_x: float,
    center_y: float,
    sigma_x: float,
    sigma_y: float,
) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    result = np.exp(
        -0.5
        * (
            ((xx - float(center_x)) / max(float(sigma_x), 1.0)) ** 2
            + ((yy - float(center_y)) / max(float(sigma_y), 1.0)) ** 2
        )
    )
    result[result < 0.002] = 0.0
    return result.astype(np.float32)


def _ellipse_mask(
    height: int,
    width: int,
    center: tuple[float, float],
    axes: tuple[float, float],
    blur_sigma: float = 0.0,
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.float32)
    cv2.ellipse(
        mask,
        (round(center[0]), round(center[1])),
        (max(1, round(axes[0])), max(1, round(axes[1]))),
        0,
        0,
        360,
        1.0,
        thickness=-1,
    )
    if blur_sigma > 0:
        mask = cv2.GaussianBlur(mask, (0, 0), blur_sigma)
        mask[mask < 0.002] = 0.0
    return np.clip(mask, 0.0, 1.0)


def _blend(source: np.ndarray, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
    amount = np.clip(mask, 0.0, 1.0)[..., None]
    return source + (target - source) * amount


def _verify_file_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest().upper()
    if actual != expected:
        raise RuntimeError(
            f"Hair parser model hash mismatch for {path}. Expected {expected}, found {actual}."
        )


def _hair_parser():
    """Load the existing local ReActor/CodeFormer ParseNet once, on CPU."""
    global _HAIR_PARSER
    with _HAIR_PARSER_LOCK:
        if _HAIR_PARSER is None:
            import folder_paths

            comfy_root = Path(folder_paths.__file__).resolve().parent
            reactor_root = comfy_root / "custom_nodes" / "ComfyUI-ReActor"
            parser_source = reactor_root / "r_facelib" / "parsing" / "parsenet.py"
            weights = Path(folder_paths.models_dir) / Path(HAIR_PARSER_MODEL)
            if not parser_source.is_file():
                raise RuntimeError(
                    "Handsome polish hair material correction requires the installed "
                    f"ComfyUI-ReActor ParseNet source at {parser_source}."
                )
            if not weights.is_file():
                raise RuntimeError(
                    "Handsome polish hair material correction requires the local ParseNet "
                    f"weights at {weights}."
                )
            _verify_file_sha256(weights, HAIR_PARSER_SHA256)
            if str(reactor_root) not in sys.path:
                sys.path.insert(0, str(reactor_root))
            from r_facelib.parsing.parsenet import ParseNet

            model = ParseNet(in_size=512, out_size=512, parsing_ch=19)
            model.load_state_dict(
                torch.load(weights, map_location="cpu", weights_only=True), strict=True
            )
            model.eval()
            _HAIR_PARSER = model
    return _HAIR_PARSER


def build_semantic_hair_mask(
    rgb_uint8: np.ndarray,
    face_bbox: np.ndarray | list[float] | tuple[float, float, float, float],
) -> np.ndarray:
    """Return the largest semantic hair component around the detected face."""
    if rgb_uint8.ndim != 3 or rgb_uint8.shape[2] < 3:
        raise ValueError("Expected an RGB uint8 image for semantic hair parsing.")
    height, width = rgb_uint8.shape[:2]
    x1, y1, x2, y2 = np.asarray(face_bbox, dtype=np.float32)
    face_height = max(float(y2 - y1), 1.0)
    side = max(64, round(face_height * 1.46))
    side = min(side, height, width)
    center_x = float((x1 + x2) * 0.5)
    center_y = float((y1 + y2) * 0.5 - face_height * 0.08)
    left = max(0, min(round(center_x - side * 0.5), width - side))
    top = max(0, min(round(center_y - side * 0.5), height - side))
    crop = rgb_uint8[top : top + side, left : left + side, :3]
    resized = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_AREA)
    tensor = torch.from_numpy(resized.transpose(2, 0, 1).copy()).float().div_(255.0)
    tensor = tensor.sub_(0.5).div_(0.5).unsqueeze(0)
    parser = _hair_parser()
    with _HAIR_PARSER_LOCK, torch.inference_mode():
        labels_512 = (
            parser(tensor)[0]
            .argmax(dim=1)
            .squeeze(0)
            .numpy()
            .astype(np.uint8)
        )
    hair_crop = cv2.resize(
        np.where(labels_512 == 17, 255, 0).astype(np.uint8),
        (side, side),
        interpolation=cv2.INTER_NEAREST,
    )
    hair = np.zeros((height, width), dtype=np.uint8)
    hair[top : top + side, left : left + side] = hair_crop
    hair = cv2.morphologyEx(hair, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(hair)
    if count <= 1:
        raise RuntimeError("The semantic parser did not detect a hair region.")
    selected = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(labels == selected, 255, 0).astype(np.uint8)


def _attenuate_freckles(
    rgb: np.ndarray,
    face_bbox: np.ndarray,
    points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Remove isolated dark cheek/nose dots while leaving unselected texture exact."""
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = np.asarray(face_bbox, dtype=np.float32)
    face_width = max(float(x2 - x1), 1.0)
    face_height = max(float(y2 - y1), 1.0)
    left_eye, right_eye, nose, left_mouth, right_mouth = points
    cheeks = np.maximum(
        _ellipse_mask(
            height,
            width,
            (float(left_eye[0]), float(y1 + face_height * 0.49)),
            (face_width * 0.17, face_height * 0.13),
        ),
        _ellipse_mask(
            height,
            width,
            (float(right_eye[0]), float(y1 + face_height * 0.49)),
            (face_width * 0.17, face_height * 0.13),
        ),
    )
    roi = np.maximum(
        cheeks,
        _ellipse_mask(
            height,
            width,
            tuple(nose),
            (face_width * 0.12, face_height * 0.16),
        ),
    )
    eye_guard = np.maximum(
        _ellipse_mask(
            height,
            width,
            tuple(left_eye),
            (face_width * 0.14, face_height * 0.07),
            face_width * 0.004,
        ),
        _ellipse_mask(
            height,
            width,
            tuple(right_eye),
            (face_width * 0.14, face_height * 0.07),
            face_width * 0.004,
        ),
    )
    mouth_center = tuple(((left_mouth + right_mouth) * 0.5).tolist())
    mouth_guard = _ellipse_mask(
        height,
        width,
        mouth_center,
        (face_width * 0.28, face_height * 0.10),
        face_width * 0.004,
    )
    uint8 = np.clip(rgb * 255.0, 0, 255).round().astype(np.uint8)
    ycrcb = cv2.cvtColor(uint8, cv2.COLOR_RGB2YCrCb)
    skin = cv2.inRange(
        ycrcb,
        np.array([20, 118, 72], dtype=np.uint8),
        np.array([250, 185, 145], dtype=np.uint8),
    ).astype(np.float32) / 255.0
    roi = roi * skin * (1.0 - np.clip(eye_guard + mouth_guard, 0.0, 1.0))

    luma = cv2.cvtColor(uint8, cv2.COLOR_RGB2LAB)[:, :, 0].astype(np.float32) / 255.0
    local = cv2.GaussianBlur(luma, (0, 0), 2.1)
    dark_residual = np.maximum(local - luma, 0.0)
    candidate = ((dark_residual > FRECKLE_RESPONSE_THRESHOLD) & (roi > 0.5)).astype(
        np.uint8
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
    accepted = np.zeros_like(candidate)
    component_count = 0
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        component_width = int(stats[label, cv2.CC_STAT_WIDTH])
        component_height = int(stats[label, cv2.CC_STAT_HEIGHT])
        if (
            1 <= area <= FRECKLE_COMPONENT_MAX_AREA
            and max(component_width, component_height) <= FRECKLE_COMPONENT_MAX_DIAMETER
        ):
            accepted[labels == label] = 1
            component_count += 1
    spot = cv2.dilate(
        accepted, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    )
    soft = cv2.GaussianBlur(spot.astype(np.float32), (0, 0), 0.55)
    core_strength = np.clip((dark_residual - 0.004) / 0.015, 0.0, 1.0)
    neighborhood_strength = cv2.dilate(
        core_strength,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    alpha = np.clip(soft * neighborhood_strength * roi * 0.94, 0.0, 0.94)
    target = (
        cv2.medianBlur(uint8, FRECKLE_LOCAL_MEDIAN_DIAMETER).astype(np.float32)
        / 255.0
    )
    output = _blend(rgb, target, alpha)

    selected = accepted > 0
    before_response = float(dark_residual[selected].mean()) if np.any(selected) else 0.0
    output_luma = (
        cv2.cvtColor(
            np.clip(output * 255.0, 0, 255).round().astype(np.uint8),
            cv2.COLOR_RGB2LAB,
        )[:, :, 0].astype(np.float32)
        / 255.0
    )
    output_response = np.maximum(
        cv2.GaussianBlur(output_luma, (0, 0), 2.1) - output_luma, 0.0
    )
    after_response = float(output_response[selected].mean()) if np.any(selected) else 0.0
    return output, alpha, {
        "detected_spot_components": component_count,
        "detected_spot_pixels": int(accepted.sum()),
        "treated_spot_neighborhood_pixels": int(np.count_nonzero(alpha > 0.0)),
        "replacement": f"local_{FRECKLE_LOCAL_MEDIAN_DIAMETER}x{FRECKLE_LOCAL_MEDIAN_DIAMETER}_median",
        "mean_dark_spot_response_before": round(before_response, 6),
        "mean_dark_spot_response_after": round(after_response, 6),
        "response_reduction_fraction": round(
            1.0 - after_response / max(before_response, 1e-8), 6
        ),
        "unselected_skin_texture_untouched_by_freckle_operation": True,
        "stubble_region_excluded": True,
    }


def _naturalize_hair(
    rgb: np.ndarray, semantic_hair_mask: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Reduce wide synthetic grooves only inside the eroded semantic hair region."""
    height, width = rgb.shape[:2]
    hair = np.asarray(semantic_hair_mask)
    if hair.shape != (height, width):
        raise ValueError(
            f"Semantic hair mask shape {hair.shape} does not match image {(height, width)}."
        )
    hair = np.where(hair > 127, 255, 0).astype(np.uint8)
    # Use a wider inner seed for the feather, then hard-zero the first eight
    # semantic-hair pixels. This makes the visible hairline/silhouette exact,
    # while the correction ramps up smoothly farther inside the material.
    inner = cv2.erode(
        hair, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    )
    alpha = cv2.GaussianBlur(inner.astype(np.float32) / 255.0, (0, 0), 2.0)
    alpha[hair == 0] = 0.0
    distance_inside_hair = cv2.distanceTransform(hair, cv2.DIST_L2, 5)
    alpha[distance_inside_hair <= 8.0] = 0.0

    uint8 = np.clip(rgb * 255.0, 0, 255).round().astype(np.uint8)
    lab = cv2.cvtColor(uint8, cv2.COLOR_RGB2LAB).astype(np.float32)
    luma = lab[:, :, 0]
    low = cv2.GaussianBlur(luma, (0, 0), 3.2)
    fine_base = cv2.GaussianBlur(luma, (0, 0), 0.68)
    mid = fine_base - low
    micro = luma - fine_base
    selected = alpha > 0.5
    if np.any(selected):
        low_values = low[selected]
        low_floor = float(np.percentile(low_values, 42.0))
        low_ceiling = float(np.percentile(low_values, 88.0))
    else:
        low_floor = 0.0
        low_ceiling = 255.0
    highlight_select = np.clip(
        (low - low_floor) / max(low_ceiling - low_floor, 1.0), 0.0, 1.0
    )
    highlight_select = cv2.GaussianBlur(highlight_select, (0, 0), 2.2)
    highlight_select = np.clip(highlight_select, 0.0, 1.0)

    corrected = lab.copy()
    rebuilt_luma = low + mid * HAIR_MID_FREQUENCY_GAIN + micro * HAIR_MICRO_FREQUENCY_GAIN
    corrected[:, :, 0] = np.clip(
        rebuilt_luma + highlight_select * HAIR_HIGHLIGHT_LUMA_GAIN,
        0.0,
        255.0,
    )
    for channel in (1, 2):
        broad = cv2.GaussianBlur(lab[:, :, channel], (0, 0), 2.4)
        corrected[:, :, channel] = broad + (
            lab[:, :, channel] - broad
        ) * HAIR_CHROMA_FREQUENCY_GAIN
    corrected[:, :, 2] = np.clip(
        corrected[:, :, 2] + highlight_select * HAIR_HIGHLIGHT_WARMTH_GAIN,
        0.0,
        255.0,
    )
    corrected_rgb = (
        cv2.cvtColor(corrected.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
        / 255.0
    )
    output = _blend(rgb, corrected_rgb, alpha)

    after_luma = cv2.cvtColor(
        np.clip(output * 255.0, 0, 255).round().astype(np.uint8),
        cv2.COLOR_RGB2LAB,
    )[:, :, 0].astype(np.float32)
    after_mid = cv2.GaussianBlur(after_luma, (0, 0), 0.68) - cv2.GaussianBlur(
        after_luma, (0, 0), 3.2
    )
    after_micro = after_luma - cv2.GaussianBlur(after_luma, (0, 0), 0.68)
    return output, alpha, {
        "parser": "CodeFormer ParseNet / CelebAMask-HQ hair class 17",
        "parser_model": HAIR_PARSER_MODEL,
        "parser_model_sha256": HAIR_PARSER_SHA256,
        "semantic_hair_pixels": int(np.count_nonzero(hair)),
        "active_inner_hair_pixels": int(np.count_nonzero(alpha > 0.0)),
        "hairline_and_silhouette_protected_pixels": 8,
        "mid_frequency_std_before": round(
            float(np.std(mid[selected])) if np.any(selected) else 0.0, 6
        ),
        "mid_frequency_std_after": round(
            float(np.std(after_mid[selected])) if np.any(selected) else 0.0, 6
        ),
        "micro_frequency_std_before": round(
            float(np.std(micro[selected])) if np.any(selected) else 0.0, 6
        ),
        "micro_frequency_std_after": round(
            float(np.std(after_micro[selected])) if np.any(selected) else 0.0, 6
        ),
        "highlight_luma_gain_0_to_255": HAIR_HIGHLIGHT_LUMA_GAIN,
        "highlight_mean_weight_in_active_hair": round(
            float(np.mean(highlight_select[selected])) if np.any(selected) else 0.0,
            6,
        ),
        "highlights_follow_existing_hair_luminance": True,
    }


def apply_deterministic_face_polish(
    photo: torch.Tensor,
    face_bbox: np.ndarray | list[float] | tuple[float, float, float, float],
    keypoints: np.ndarray | list[list[float]],
    semantic_hair_mask: np.ndarray | None = None,
) -> tuple[torch.Tensor, torch.Tensor, dict]:
    """Apply a restrained local retouch without changing the generated background or head outline."""
    if photo.ndim != 4 or photo.shape[0] != 1 or photo.shape[-1] < 3:
        raise ValueError("Expected exactly one RGB image tensor.")
    rgb = photo[0, :, :, :3].detach().float().cpu().clamp(0.0, 1.0).numpy()
    original = rgb.copy()
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = np.asarray(face_bbox, dtype=np.float32)
    face_width = max(float(x2 - x1), 1.0)
    face_height = max(float(y2 - y1), 1.0)
    points = np.asarray(keypoints, dtype=np.float32)
    if points.shape != (5, 2):
        raise ValueError(f"Expected five facial keypoints; got {points.shape}.")

    face_center = (float((x1 + x2) * 0.5), float(y1 + face_height * 0.53))
    face_mask = _ellipse_mask(
        height,
        width,
        face_center,
        (face_width * 0.43, face_height * 0.47),
        blur_sigma=max(1.0, face_width * 0.012),
    )

    left_eye, right_eye, nose, left_mouth, right_mouth = points
    eye_masks = np.maximum(
        _ellipse_mask(
            height,
            width,
            tuple(left_eye),
            (face_width * 0.115, face_height * 0.045),
            blur_sigma=max(0.8, face_width * 0.006),
        ),
        _ellipse_mask(
            height,
            width,
            tuple(right_eye),
            (face_width * 0.115, face_height * 0.045),
            blur_sigma=max(0.8, face_width * 0.006),
        ),
    ) * face_mask
    mouth_center = tuple(((left_mouth + right_mouth) * 0.5).tolist())
    mouth_protection = _ellipse_mask(
        height,
        width,
        mouth_center,
        (face_width * 0.25, face_height * 0.075),
        blur_sigma=max(0.8, face_width * 0.005),
    ) * face_mask

    uint8 = np.clip(rgb * 255.0, 0, 255).round().astype(np.uint8)
    ycrcb = cv2.cvtColor(uint8, cv2.COLOR_RGB2YCrCb)
    skin_color = cv2.inRange(
        ycrcb,
        np.array([20, 118, 72], dtype=np.uint8),
        np.array([250, 185, 145], dtype=np.uint8),
    ).astype(np.float32) / 255.0
    skin_mask = face_mask * skin_color * (1.0 - np.clip(eye_masks + mouth_protection, 0.0, 1.0))
    skin_mask = cv2.GaussianBlur(skin_mask, (0, 0), max(0.8, face_width * 0.004))
    skin_mask[skin_mask < 0.002] = 0.0

    corner_mask = np.maximum(
        _gaussian(
            height,
            width,
            float(left_mouth[0]),
            float(left_mouth[1]),
            face_width * 0.075,
            face_height * 0.050,
        ),
        _gaussian(
            height,
            width,
            float(right_mouth[0]),
            float(right_mouth[1]),
            face_width * 0.075,
            face_height * 0.050,
        ),
    ) * face_mask
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    lift_pixels = face_height * MOUTH_CORNER_LIFT_FACE_HEIGHT
    warped = cv2.remap(
        rgb,
        xx,
        yy + lift_pixels * corner_mask,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    rgb = _blend(rgb, warped, corner_mask * 0.72)

    softened = cv2.bilateralFilter(
        np.clip(rgb * 255.0, 0, 255).round().astype(np.uint8),
        d=5,
        sigmaColor=12,
        sigmaSpace=3,
    ).astype(np.float32) / 255.0
    rgb = _blend(rgb, softened, skin_mask * SKIN_TEXTURE_BLEND)

    wrinkle_softened = cv2.GaussianBlur(rgb, (0, 0), 1.35)
    forehead_center = (
        float((left_eye[0] + right_eye[0]) * 0.5),
        float(y1 + face_height * 0.22),
    )
    forehead_mask = _ellipse_mask(
        height,
        width,
        forehead_center,
        (face_width * 0.30, face_height * 0.135),
        blur_sigma=max(1.0, face_width * 0.008),
    ) * skin_mask
    rgb = _blend(rgb, wrinkle_softened, forehead_mask * FOREHEAD_WRINKLE_BLEND)

    under_eye = np.maximum(
        _gaussian(
            height,
            width,
            float(left_eye[0]),
            float(left_eye[1] + face_height * 0.052),
            face_width * 0.105,
            face_height * 0.040,
        ),
        _gaussian(
            height,
            width,
            float(right_eye[0]),
            float(right_eye[1] + face_height * 0.052),
            face_width * 0.105,
            face_height * 0.040,
        ),
    ) * skin_mask
    rgb = _blend(rgb, wrinkle_softened, under_eye * UNDER_EYE_TEXTURE_BLEND)

    warmed = rgb.copy()
    warmed[..., 0] = np.clip(warmed[..., 0] + 0.025 * (1.0 - warmed[..., 0]), 0.0, 1.0)
    warmed[..., 1] = np.clip(warmed[..., 1] + 0.008 * (1.0 - warmed[..., 1]), 0.0, 1.0)
    warmed[..., 2] = np.clip(warmed[..., 2] * 0.982, 0.0, 1.0)
    rgb = _blend(rgb, warmed, skin_mask)

    fine_blur = cv2.GaussianBlur(rgb, (0, 0), 0.9)
    eye_detail = np.clip(rgb + (rgb - fine_blur) * EYE_DETAIL_GAIN, 0.0, 1.0)
    eye_detail = np.clip(
        eye_detail + EYE_BRIGHTEN_GAIN * (1.0 - eye_detail), 0.0, 1.0
    )
    rgb = _blend(rgb, eye_detail, eye_masks)

    stubble_center = (float(nose[0]), float(y1 + face_height * 0.73))
    stubble_mask = _ellipse_mask(
        height,
        width,
        stubble_center,
        (face_width * 0.34, face_height * 0.22),
        blur_sigma=max(1.0, face_width * 0.008),
    ) * face_mask * (1.0 - mouth_protection)
    stubble_detail = np.clip(rgb + (rgb - fine_blur) * STUBBLE_DETAIL_GAIN, 0.0, 1.0)
    rgb = _blend(rgb, stubble_detail, stubble_mask)

    cheek_jaw_mask = _ellipse_mask(
        height,
        width,
        (face_center[0], float(y1 + face_height * 0.65)),
        (face_width * 0.40, face_height * 0.28),
        blur_sigma=max(1.0, face_width * 0.010),
    ) * face_mask * (1.0 - mouth_protection)
    broad_blur = cv2.GaussianBlur(rgb, (0, 0), max(2.0, face_width * 0.018))
    shaped = np.clip(rgb + (rgb - broad_blur) * BONE_LIGHTING_GAIN, 0.0, 1.0)
    rgb = _blend(rgb, shaped, cheek_jaw_mask)

    cheek_mask = np.maximum(
        _gaussian(
            height,
            width,
            float(left_eye[0]),
            float(y1 + face_height * 0.56),
            face_width * 0.13,
            face_height * 0.10,
        ),
        _gaussian(
            height,
            width,
            float(right_eye[0]),
            float(y1 + face_height * 0.56),
            face_width * 0.13,
            face_height * 0.10,
        ),
    ) * skin_mask * (1.0 - mouth_protection)
    cheek_lifted = np.clip(
        rgb + CHEEK_HIGHLIGHT_GAIN * (1.0 - rgb), 0.0, 1.0
    )
    rgb = _blend(rgb, cheek_lifted, cheek_mask)

    jaw_mask = _ellipse_mask(
        height,
        width,
        (face_center[0], float(y1 + face_height * 0.79)),
        (face_width * 0.37, face_height * 0.13),
        blur_sigma=max(1.0, face_width * 0.010),
    ) * face_mask * (1.0 - mouth_protection)
    jaw_contoured = np.clip(rgb * (1.0 - JAW_CONTOUR_GAIN), 0.0, 1.0)
    rgb = _blend(rgb, jaw_contoured, jaw_mask)

    rgb, freckle_mask, freckle_report = _attenuate_freckles(
        rgb, np.asarray(face_bbox, dtype=np.float32), points
    )
    hair_mask = np.zeros((height, width), dtype=np.float32)
    hair_report = None
    if semantic_hair_mask is not None:
        rgb, hair_mask, hair_report = _naturalize_hair(rgb, semantic_hair_mask)

    active_mask = np.maximum.reduce(
        (
            skin_mask,
            forehead_mask,
            under_eye,
            eye_masks,
            stubble_mask,
            cheek_jaw_mask,
            cheek_mask,
            jaw_mask,
            corner_mask,
            freckle_mask,
            hair_mask,
        )
    )
    active_mask[active_mask < 0.002] = 0.0
    rgb[active_mask == 0.0] = original[active_mask == 0.0]
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)

    changed = np.any(np.abs(rgb - original) > (0.5 / 255.0), axis=2)
    outside = active_mask == 0.0
    outside_error = np.abs(rgb[outside] - original[outside]) if np.any(outside) else np.zeros(1)
    report = {
        "profile": POLISH_PROFILE,
        "deterministic": True,
        "face_bbox": [round(float(value), 4) for value in (x1, y1, x2, y2)],
        "mouth_corner_lift_pixels": round(float(lift_pixels), 3),
        "active_mask_fraction": round(float(np.mean(active_mask > 0.0)), 6),
        "changed_pixel_fraction": round(float(changed.mean()), 6),
        "protected_pixel_max_error_0_to_255": round(float(outside_error.max() * 255.0), 8),
        "background_and_head_outline_are_source_pixels": True,
        "background_hairline_and_head_outline_are_source_pixels": True,
        "freckle_attenuation": freckle_report,
        "hair_material_correction": hair_report,
        "operations": [
            "closed-mouth corner lift",
            "face-local pore-preserving fine-texture attenuation",
            "forehead line attenuation inside the existing hairline",
            "under-eye fatigue attenuation",
            "subtle skin warmth",
            "existing eye-detail contrast and restrained brightness",
            "existing stubble-detail contrast",
            "existing cheek-and-jaw detail contrast",
            "cheek highlight and jaw-contour lighting",
            "isolated dark dot and freckle removal on cheeks and nose with unselected texture and stubble protected",
            *(
                [
                    "semantic-hair-interior wide-groove attenuation with fine texture retained",
                    "subtle existing-luminance-guided hair highlights inside the protected hair interior",
                ]
                if semantic_hair_mask is not None
                else []
            ),
        ],
    }
    output = torch.from_numpy(rgb).unsqueeze(0)
    preview = torch.from_numpy(np.repeat(active_mask[..., None], 3, axis=2)).unsqueeze(0)
    return output, preview, report
