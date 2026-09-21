"""Optional stronger retouch applied after the independently versioned Low finish.

This is not identity conditioning or an attractiveness estimator. High never
copies source pixels or moves pupils, irises, eyebrows, the hairline, or the head
outline. Source landmarks may guide a small upper-lid-only geometry refinement.
"""
from __future__ import annotations

import cv2
import numpy as np
import torch


ATTRACTIVENESS_LEVELS = ("off", "low", "high")
HIGH_PROFILE = "source_guided_upper_lid_and_brow_polish_v4"
HIGH_STRENGTH = 1.0
_OVAL = (10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
         397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
         172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109)
_BROWS = ((70, 63, 105, 66, 107, 55, 65, 52, 53, 46),
          (336, 296, 334, 293, 300, 276, 283, 282, 295, 285))
_EYES = ((33, 160, 158, 133, 153, 144), (362, 385, 387, 263, 373, 380))
_EYE_CONTOURS = (
    (33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7),
    (263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249),
)
_UPPER_LIDS = ((33, 246, 161, 160, 159, 158, 157, 173, 133),
               (263, 466, 388, 387, 386, 385, 384, 398, 362))
_IRISES = ((468, 469, 470, 471, 472), (473, 474, 475, 476, 477))
_LIPS = (61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91)


def normalize_attractiveness(value) -> str:
    # Compatibility for old saved/API workflows. Never use bool("off").
    if value is True:
        return "low"
    if value is False:
        return "off"
    if isinstance(value, str) and value.strip().lower() in ATTRACTIVENESS_LEVELS:
        return value.strip().lower()
    raise ValueError("Attractiveness must be off, low, or high (legacy booleans are accepted).")


def _polygon(shape, points, indices) -> np.ndarray:
    mask = np.zeros(shape, np.uint8)
    cv2.fillPoly(mask, [np.round(points[list(indices)]).astype(np.int32)], 255)
    return mask


def _soft(mask, sigma) -> np.ndarray:
    alpha = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), sigma)
    alpha[alpha < 0.002] = 0
    return np.clip(alpha, 0, 1)


def _source_guided_upper_lid_warp(rgb, points, source_points, iris_guard):
    """Transfer source-relative upper-lid curvature into fixed eye corners."""
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    shift_x = np.zeros((h, w), np.float32)
    shift_y = np.zeros((h, w), np.float32)
    weight_sum = np.zeros((h, w), np.float32)
    eye_reports = []
    for ids, contour in zip(_UPPER_LIDS, _EYE_CONTOURS):
        source_outer, source_inner = source_points[ids[0]], source_points[ids[-1]]
        candidate_outer, candidate_inner = points[ids[0]], points[ids[-1]]
        source_axis = source_inner - source_outer
        candidate_axis = candidate_inner - candidate_outer
        source_width = max(float(np.linalg.norm(source_axis)), 1.0)
        candidate_width = max(float(np.linalg.norm(candidate_axis)), 1.0)
        source_unit = source_axis / source_width
        candidate_unit = candidate_axis / candidate_width
        source_normal = np.array([-source_unit[1], source_unit[0]], np.float32)
        candidate_normal = np.array([-candidate_unit[1], candidate_unit[0]], np.float32)
        source_lower = source_points[list(contour[9:])].mean(axis=0)
        candidate_lower = points[list(contour[9:])].mean(axis=0)
        if np.dot(source_lower - (source_outer + source_inner) / 2, source_normal) < 0:
            source_normal *= -1
        if np.dot(candidate_lower - (candidate_outer + candidate_inner) / 2, candidate_normal) < 0:
            candidate_normal *= -1
        before_error, requested_shifts, applied_shifts = [], [], []
        for index in ids[1:-1]:
            source_v = float(np.dot(source_points[index] - source_outer, source_normal) / source_width)
            candidate_v = float(np.dot(points[index] - candidate_outer, candidate_normal) / candidate_width)
            requested = candidate_normal * ((source_v - candidate_v) * candidate_width)
            before_error.append(abs(source_v - candidate_v))
            maximum = candidate_width * 0.038
            applied = requested * 0.72
            applied_length = float(np.linalg.norm(applied))
            if applied_length > maximum:
                applied *= maximum / max(applied_length, 1e-6)
            center = points[index] + applied * 0.5
            dx, dy = xx - center[0], yy - center[1]
            along = dx * candidate_unit[0] + dy * candidate_unit[1]
            across = dx * candidate_normal[0] + dy * candidate_normal[1]
            weight = np.exp(-0.5 * ((along / max(candidate_width * 0.10, 1)) ** 2
                                    + (across / max(candidate_width * 0.047, 1)) ** 2))
            weight[weight < 0.01] = 0
            shift_x += float(applied[0]) * weight
            shift_y += float(applied[1]) * weight
            weight_sum += weight
            requested_shifts.append(round(float(np.linalg.norm(requested)), 4))
            applied_shifts.append(round(float(np.linalg.norm(applied)), 4))
        eye_reports.append({
            "mean_normalized_upper_lid_error_before": round(float(np.mean(before_error)), 6),
            "requested_shift_pixels": requested_shifts,
            "applied_shift_pixels": applied_shifts,
            "maximum_shift_eye_width_fraction": 0.038,
        })
    divisor = np.maximum(weight_sum, 1)
    shift_x /= divisor
    shift_y /= divisor
    active = np.clip(weight_sum / 2.1, 0, 1)
    active[_soft(iris_guard, 0.8) > 0.02] = 0
    warped = cv2.remap(rgb.astype(np.float32), xx - shift_x, yy - shift_y,
                       interpolation=cv2.INTER_CUBIC,
                       borderMode=cv2.BORDER_REFLECT_101)
    output = rgb + (warped - rgb) * active[..., None]
    return np.clip(output, 0, 1), active, eye_reports


def _apply_high_with_landmarks(rgb, points, semantic_hair_mask, source_points=None):
    rgb = np.asarray(rgb, dtype=np.float32)
    points = np.asarray(points, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or points.shape != (478, 2):
        raise ValueError("High requires an RGB image and 478 refined landmarks.")
    if not np.isfinite(points).all() or not np.isfinite(rgb).all():
        raise ValueError("Image and landmarks must be finite.")
    if source_points is not None:
        source_points = np.asarray(source_points, dtype=np.float32)
        if source_points.shape != (478, 2) or not np.isfinite(source_points).all():
            raise ValueError("High source guidance requires 478 finite landmarks.")
    h, w = rgb.shape[:2]
    if np.asarray(semantic_hair_mask).shape != (h, w):
        raise ValueError("High requires an image-sized semantic hair mask.")
    original = np.clip(rgb, 0, 1).copy()
    eye_centers = np.array([points[list(ids)].mean(axis=0) for ids in _EYES])
    tangent = eye_centers[1] - eye_centers[0]
    eye_distance = max(float(np.linalg.norm(tangent)), 1.0)
    tangent /= eye_distance
    normal = np.array([-tangent[1], tangent[0]], np.float32)
    if normal[1] < 0:
        normal *= -1
    scale = eye_distance / 160.0
    oval = _polygon((h, w), points, _OVAL)
    interior = cv2.erode(oval, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    interior[np.asarray(semantic_hair_mask) > 0] = 0
    face_alpha = _soft(interior, max(1.0, 2.2 * scale))
    face_alpha[interior == 0] = 0

    eyes = np.maximum.reduce([_polygon((h, w), points, ids) for ids in _EYE_CONTOURS])
    irises = np.maximum.reduce([_polygon((h, w), points, ids[1:]) for ids in _IRISES])
    iris_guard_size = max(3, int(round(3.4 * scale)) | 1)
    iris_guard = cv2.dilate(irises, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (iris_guard_size, iris_guard_size)))
    lips = _polygon((h, w), points, _LIPS)
    guard_size = max(3, int(round(7 * scale)) | 1)
    eye_guard = cv2.dilate(eyes, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (guard_size, guard_size)))
    lip_guard = cv2.dilate(lips, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (guard_size, guard_size)))
    brows = np.maximum.reduce([_polygon((h, w), points, ids) for ids in _BROWS])
    brow_guard = cv2.dilate(brows, np.ones((5, 5), np.uint8))
    uint8 = np.round(original * 255).astype(np.uint8)
    ycrcb = cv2.cvtColor(uint8, cv2.COLOR_RGB2YCrCb)
    skin = cv2.inRange(ycrcb, np.array([20, 118, 72], np.uint8), np.array([250, 185, 145], np.uint8)) / 255.0
    skin_alpha = face_alpha * skin * (1 - _soft(np.maximum.reduce([eye_guard, lip_guard, brow_guard]), 1.1))

    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    def gaussian(center, sx, sy):
        dx, dy = xx - center[0], yy - center[1]
        u = dx * tangent[0] + dy * tangent[1]
        v = dx * normal[0] + dy * normal[1]
        a = np.exp(-0.5 * ((u / max(sx, 1)) ** 2 + (v / max(sy, 1)) ** 2))
        a[a < 0.002] = 0
        return a

    forehead_center = eye_centers.mean(axis=0) - normal * eye_distance * 0.56
    forehead = gaussian(forehead_center, eye_distance * 0.72, eye_distance * 0.38) * skin_alpha
    under_eye = np.zeros((h, w), np.float32)
    for ids in _EYES:
        p = points[list(ids)]
        width = float(np.linalg.norm(p[3] - p[0]))
        center = p[4:6].mean(axis=0) + normal * width * 0.16
        under_eye = np.maximum(under_eye, gaussian(center, width * 0.42, width * 0.13))
    under_eye *= skin_alpha

    if source_points is not None:
        working, eye_shape_alpha, eye_shape_report = _source_guided_upper_lid_warp(
            original, points, source_points, iris_guard)
    else:
        working = original.copy()
        eye_shape_alpha = np.zeros((h, w), np.float32)
        eye_shape_report = []

    # Reduce middle-band crease contrast symmetrically, preserving broad lighting
    # and fine pores. Dark-trough filling was rejected: it made forehead patches.
    luma = cv2.cvtColor(working, cv2.COLOR_RGB2GRAY)
    fine_base = cv2.GaussianBlur(working, (0, 0), max(0.7, scale * 0.8))
    broad_base = cv2.GaussianBlur(working, (0, 0), max(2.2, scale * 4.0))
    mid_band = fine_base - broad_base
    attenuation = np.clip(0.64 * forehead + 0.42 * under_eye, 0, 0.7)
    result = working - mid_band * attenuation[..., None]
    under_eye_reference = cv2.GaussianBlur(
        luma, (0, 0), max(2.5, scale * 8.0))
    under_eye_shadow = np.clip(under_eye_reference - luma, 0, 0.055) * under_eye
    result += under_eye_shadow[..., None] * 0.34

    # A small extra warmth, not source-color transfer or full-face relighting.
    warmth = skin_alpha * 0.8
    result[..., 0] += warmth * 0.012 * (1 - result[..., 0])
    result[..., 1] += warmth * 0.003 * (1 - result[..., 1])
    result[..., 2] -= warmth * 0.008 * result[..., 2]

    # Strengthen existing brow fibers inside their detected silhouette. No
    # dilation, eyebrow relocation, arch drawing, or new hairs are synthesized.
    brow_alpha = _soft(brows, max(0.8, scale)) * face_alpha
    brow_alpha[brows == 0] = 0
    neighborhood = cv2.GaussianBlur(luma, (0, 0), max(2, 6 * scale))
    fiber_weight = np.clip((neighborhood - luma + 0.006) / 0.05, 0, 1)
    brow_darkening = brow_alpha * fiber_weight * 0.14
    result *= (1 - brow_darkening[..., None])

    # Improve the apparent eye shape tonally, without moving anatomy or gaze.
    # A narrow line follows the existing upper-lid/lash contour; the outer half
    # receives slightly more definition. Eye whites get only a restrained,
    # neutral clarity lift. The pupil core is hard protected below; later iris
    # definition is symmetric, so the location inherited from gaze lock is fixed.
    lid_line = np.zeros((h, w), np.uint8)
    outer_lid_line = np.zeros((h, w), np.uint8)
    lid_thickness = max(1, int(round(1.4 * scale)))
    for ids in _UPPER_LIDS:
        lid_points = np.round(points[list(ids)]).astype(np.int32)
        cv2.polylines(lid_line, [lid_points], False, 255, lid_thickness, cv2.LINE_AA)
        cv2.polylines(outer_lid_line, [lid_points[:5]], False, 255, lid_thickness, cv2.LINE_AA)
    lid_alpha = _soft(lid_line, max(0.45, 0.55 * scale)) * face_alpha
    outer_lid_alpha = _soft(outer_lid_line, max(0.55, 0.7 * scale)) * face_alpha
    lid_local = cv2.GaussianBlur(luma, (0, 0), max(1.0, 2.2 * scale))
    existing_lid_detail = np.clip((lid_local - luma + 0.004) / 0.045, 0, 1)
    lid_darkening = lid_alpha * (0.035 + 0.052 * existing_lid_detail) + outer_lid_alpha * 0.020
    result *= (1 - lid_darkening[..., None])

    sclera = (eyes.astype(np.float32) / 255.0) * (1 - _soft(iris_guard, max(0.5, scale * 0.6)))
    sclera[eyes == 0] = 0
    sclera_lift = sclera * 0.014
    result += (1 - result) * sclera_lift[..., None]
    # Counter the red/yellow cast rather than bleaching the eye white.
    result[..., 0] -= sclera * 0.0025 * result[..., 0]
    result[..., 2] += sclera * 0.0015 * (1 - result[..., 2])

    # Define the existing iris rather than changing its size or position. A
    # symmetric limbal-ring/texture enhancement cannot steer gaze; the central
    # pupil region remains byte-exact through the final hard guard.
    iris_detail_alpha = np.zeros((h, w), np.float32)
    limbal_alpha = np.zeros((h, w), np.float32)
    pupil_guard = np.zeros((h, w), np.uint8)
    for ids in _IRISES:
        center = points[ids[0]]
        ring_points = points[list(ids[1:])]
        radius_x = max(float((ring_points[:, 0].max() - ring_points[:, 0].min()) / 2), 1.0)
        radius_y = max(float((ring_points[:, 1].max() - ring_points[:, 1].min()) / 2), 1.0)
        radial = np.sqrt(((xx - center[0]) / radius_x) ** 2
                         + ((yy - center[1]) / radius_y) ** 2)
        iris_disk = np.clip((1.08 - radial) / 0.14, 0, 1) * (eyes > 0)
        limbal = np.exp(-0.5 * ((radial - 0.89) / 0.12) ** 2) * iris_disk
        inner = np.clip((0.88 - radial) / 0.30, 0, 1) * iris_disk
        iris_detail_alpha = np.maximum(iris_detail_alpha, inner.astype(np.float32))
        limbal_alpha = np.maximum(limbal_alpha, limbal.astype(np.float32))
        pupil_guard[radial <= 0.38] = 255
    pupil_guard = cv2.dilate(pupil_guard, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (3, 3)))
    result *= (1 - limbal_alpha[..., None] * 0.030)
    iris_base = cv2.GaussianBlur(result, (0, 0), max(0.65, scale * 0.65))
    result += (result - iris_base) * iris_detail_alpha[..., None] * 0.18
    iris_gray = result.mean(axis=2, keepdims=True)
    result += (result - iris_gray) * iris_detail_alpha[..., None] * 0.075

    active = np.maximum.reduce([skin_alpha, forehead, under_eye, brow_alpha,
                                lid_alpha, outer_lid_alpha, sclera,
                                eye_shape_alpha, iris_detail_alpha,
                                limbal_alpha]).astype(np.float32)
    # Hard guards are applied last. The usual iris lock has already run as a
    # separately reported source-fidelity operation; High cannot alter it.
    protected = (pupil_guard > 0) | (lip_guard > 0) | (interior == 0)
    active[protected] = 0
    active[active < 0.002] = 0
    result = np.clip(original + (result - original) * HIGH_STRENGTH, 0, 1)
    result[active == 0] = original[active == 0]
    selected_brow = (brow_alpha > 0.5) & ~protected
    selected_forehead = (forehead > 0.4) & ~protected
    selected_lid = (lid_alpha > 0.35) & ~protected
    selected_sclera = (sclera > 0.35) & ~protected
    report = {
        "profile": HIGH_PROFILE,
        "strength": HIGH_STRENGTH,
        "geometric_warp": bool(source_points is not None),
        "geometric_warp_scope": "upper-lid neighborhood only; eye corners and iris region fixed" if source_points is not None else None,
        "source_pixels_copied": False,
        "pupil_core_lip_pixels_exact": bool(np.array_equal(result[np.maximum(pupil_guard, lip_guard) > 0], original[np.maximum(pupil_guard, lip_guard) > 0])),
        "iris_geometry_changed": False,
        "protected_pixel_max_error_0_to_255": float(np.max(np.abs(result[active == 0] - original[active == 0]), initial=0) * 255),
        "mean_brow_darkening_0_to_255": round(float((original - result)[selected_brow].mean() * 255), 4) if selected_brow.any() else 0.0,
        "mean_upper_lid_darkening_0_to_255": round(float((original - result)[selected_lid].mean() * 255), 4) if selected_lid.any() else 0.0,
        "mean_sclera_lift_0_to_255": round(float((result - original)[selected_sclera].mean() * 255), 4) if selected_sclera.any() else 0.0,
        "mean_limbal_darkening_0_to_255": round(float((original - result)[limbal_alpha > 0.5].mean() * 255), 4) if np.any(limbal_alpha > 0.5) else 0.0,
        "mean_under_eye_shadow_lift_0_to_255": round(float(under_eye_shadow[under_eye > 0.4].mean() * 0.34 * 255), 4) if np.any(under_eye > 0.4) else 0.0,
        "source_guided_upper_lid": eye_shape_report,
        "forehead_mid_band_std_before": round(float(mid_band[selected_forehead].std() * 255), 4) if selected_forehead.any() else 0.0,
        "forehead_mid_band_std_after_target": round(float((mid_band * (1 - attenuation[..., None]))[selected_forehead].std() * 255), 4) if selected_forehead.any() else 0.0,
        "active_mask_fraction": round(float((active > 0).mean()), 6),
        "operations": ["source-guided upper-lid curvature transfer with fixed eye corners and protected iris region" if source_points is not None else "no source-guided upper-lid curvature transfer", "landmark-aligned symmetric forehead mid-frequency attenuation with lighting and microtexture retained", "under-eye mid-frequency attenuation and targeted dark-circle lift", "restrained additional skin warmth", "existing eyebrow-fiber definition within unchanged brow silhouette", "existing upper-lid and outer-corner tonal definition", "restrained sclera clarity", "symmetric iris texture and limbal definition with pupil core protected"],
    }
    return result.astype(np.float32), active, report


def apply_high_attractiveness(photo, landmarks, semantic_hair_mask, source_landmarks=None):
    if photo.ndim != 4 or photo.shape[0] != 1 or photo.shape[-1] != 3:
        raise ValueError("High requires exactly one RGB tensor.")
    rgb = photo[0].detach().float().cpu().numpy()
    output, mask, report = _apply_high_with_landmarks(
        rgb, landmarks, semantic_hair_mask, source_landmarks)
    return (torch.from_numpy(output).unsqueeze(0),
            torch.from_numpy(np.repeat(mask[..., None], 3, axis=2)).unsqueeze(0), report)
