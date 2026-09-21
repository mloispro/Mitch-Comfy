"""Evaluation-only 2D expression flow; final RGB comes exclusively from the raw.

This does not use LivePortrait feature-volume grids as image coordinates.
"""
from __future__ import annotations

import cv2
import numpy as np


def estimate_inverse_flow(zero_rgb, edited_rgb):
    """Return edited -> zero displacement, and zero -> edited for cycle checks."""
    a, b = np.asarray(zero_rgb), np.asarray(edited_rgb)
    if a.shape != b.shape or a.ndim != 3 or a.shape[2] != 3 or a.dtype != np.uint8 or b.dtype != np.uint8:
        raise ValueError('Expected equally sized uint8 RGB reconstructions.')
    if min(a.shape[:2]) < 32:
        raise ValueError('Flow inputs are too small.')
    if np.array_equal(a, b):
        flow = np.zeros((*a.shape[:2], 2), np.float32)
        return flow, flow.copy()
    gray_a = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    gray_b = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY)
    inverse = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(gray_b, gray_a, None)
    forward = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(gray_a, gray_b, None)
    return inverse, forward


def cycle_diagnostics(inverse, forward, support):
    h, w = support.shape
    if inverse.shape != (h, w, 2) or forward.shape != inverse.shape:
        raise ValueError('Cycle dimensions differ.')
    if not np.isfinite(inverse).all() or not np.isfinite(forward).all():
        raise ValueError('Nonfinite flow.')
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    mx, my = xx + inverse[..., 0], yy + inverse[..., 1]
    sampled = cv2.remap(forward, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    active = support > .5
    if not active.any():
        raise ValueError('No active face region for cycle diagnostic.')
    out_of_bounds = (mx < 0) | (mx > w-1) | (my < 0) | (my > h-1)
    if out_of_bounds[active].any():
        raise ValueError('Flow leaves the reconstruction at an active face pixel.')
    errors = np.linalg.norm(inverse + sampled, axis=2)[active]
    return {'p95_pixels': float(np.percentile(errors, 95)),
            'fraction_over_3_pixels': float(np.mean(errors > 3)),
            'max_pixels': float(errors.max()),
            'passed': bool(np.percentile(errors, 95) <= 1.5 and np.mean(errors > 3) <= .03)}


def native_displacement(inverse, crop_to_original, shape):
    """Push a crop-space displacement into native coordinates using its affine."""
    matrix = np.asarray(crop_to_original, np.float32)
    if matrix.shape == (3, 3):
        if not np.allclose(matrix[2], [0, 0, 1]):
            raise ValueError('Expected an affine crop transform.')
        matrix = matrix[:2]
    if matrix.shape != (2, 3) or not np.isfinite(matrix).all():
        raise ValueError('Expected finite 2x3 affine transform.')
    if abs(np.linalg.det(matrix[:, :2])) < 1e-6:
        raise ValueError('Singular crop affine.')
    h, w = shape
    field = cv2.warpAffine(inverse.astype(np.float32), matrix, (w, h),
                           flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return field @ matrix[:, :2].T


def remap_original(raw, displacement, support, face_width):
    raw = np.asarray(raw)
    d = np.asarray(displacement, np.float32)
    support = np.asarray(support, np.float32)
    if raw.ndim != 3 or raw.shape[2] != 3 or raw.dtype != np.uint8:
        raise ValueError('Expected native uint8 RGB raw.')
    h, w = raw.shape[:2]
    if d.shape != (h, w, 2) or support.shape != (h, w):
        raise ValueError('Native map dimensions differ.')
    if not np.isfinite(d).all() or not np.isfinite(support).all() or not np.isfinite(face_width) or face_width <= 0:
        raise ValueError('Expected finite map and positive face width.')
    if support.min() < 0 or support.max() > 1:
        raise ValueError('Support must lie in [0, 1].')
    field = d * support[..., None]
    dx_y, dx_x = np.gradient(field[..., 0])
    dy_y, dy_x = np.gradient(field[..., 1])
    jac = (1 + dx_x) * (1 + dy_y) - dx_y * dy_x
    magnitude = np.linalg.norm(field, axis=2)
    report = {'min_inverse_jacobian': float(jac.min()),
              'max_native_displacement': float(magnitude.max()),
              'maximum_allowed_displacement': float(face_width * .12),
              'interpolation': 'one native-resolution cubic RGB remap; no decoded RGB'}
    if report['min_inverse_jacobian'] < .25:
        raise ValueError(f'Unsafe folded/compressed mapping: {report}')
    if report['max_native_displacement'] > face_width * .12:
        raise ValueError(f'Expression displacement is excessive: {report}')
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    mx, my = xx + field[..., 0], yy + field[..., 1]
    active = support > 0
    if ((mx[active] < 0).any() or (mx[active] > w-1).any()
            or (my[active] < 0).any() or (my[active] > h-1).any()):
        raise ValueError('Native remap leaves the source image.')
    after = cv2.remap(raw, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)
    after[~active] = raw[~active]
    report['outside_support_exact'] = bool(np.array_equal(after[~active], raw[~active]))
    report['zero_displacement_exact'] = bool(np.array_equal(after, raw)) if not field.any() else None
    return after, report
