"""Rejected small-change experiment, retained for offline reproduction only.

Not imported by production nodes. This is cosmetic geometry, not identity
conditioning. The mouth column moves as one unit (upper lip, seam and lower lip
together), without synthesizing teeth. Eye/brow pixels are outside its compact
support. The visible benefit was insufficient despite improved landmark error.
"""
from __future__ import annotations

import cv2
import numpy as np


SMILE_BALANCE_PROFILE = "source_relative_closed_mouth_balance_v1"
SMILE_BALANCE_STRENGTH = 0.50
MAX_CORNER_SHIFT_MOUTH_WIDTH = 0.045
_FACE_OVAL = (10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,
              400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109)


def measure_smile(points):
    points = np.asarray(points, dtype=np.float32)
    if points.shape != (478, 2) or not np.isfinite(points).all():
        raise ValueError("Smile balance requires 478 finite landmarks.")
    eye_left = points[[33,133]].mean(axis=0)
    eye_right = points[[362,263]].mean(axis=0)
    axis = eye_right - eye_left
    eye_span = max(float(np.linalg.norm(axis)), 1.0)
    tangent = axis / eye_span
    normal = np.array([-tangent[1], tangent[0]], np.float32)
    if np.dot(points[152] - points[1], normal) < 0:
        normal *= -1
    center = points[[13,14]].mean(axis=0)
    corners = points[[61,291]]
    width = max(float(np.linalg.norm(corners[1] - corners[0])), 1.0)
    offsets = corners - center
    local = np.column_stack((offsets @ tangent, offsets @ normal)) / width
    opening = abs(float(np.dot(points[14] - points[13], normal))) / width
    return {"center": center, "corners": corners, "width": width,
            "tangent": tangent, "normal": normal, "eye_span": eye_span,
            "corner_coordinates": local, "opening_ratio": opening,
            "smile_lift": -float(local[:,1].mean())}


def apply_smile_balance(rgb, points, source_points, semantic_hair_mask,
                        strength=SMILE_BALANCE_STRENGTH):
    rgb = np.asarray(rgb, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or not np.isfinite(rgb).all():
        raise ValueError("Smile balance requires a finite RGB image.")
    if not 0 <= float(strength) <= 1:
        raise ValueError("Smile balance strength must be between zero and one.")
    h, w = rgb.shape[:2]
    if np.asarray(semantic_hair_mask).shape != (h,w):
        raise ValueError("Smile balance requires an image-sized hair mask.")
    original = rgb.copy()
    candidate = measure_smile(points)
    source = measure_smile(source_points)
    empty = np.zeros((h,w), np.float32)
    report = {"profile": SMILE_BALANCE_PROFILE, "strength": float(strength),
              "source_pixels_copied": False, "teeth_synthesized": False,
              "mouth_opening_scaled": False,
              "source_smile_lift": round(source["smile_lift"],6),
              "candidate_smile_lift": round(candidate["smile_lift"],6),
              "source_opening_ratio": round(source["opening_ratio"],6),
              "candidate_opening_ratio": round(candidate["opening_ratio"],6)}
    # Do not turn a neutral/open-mouth scene into an arbitrary beauty smile.
    # The source expression must be a detectable closed-mouth smile.
    if source["smile_lift"] < 0.012 or source["opening_ratio"] > 0.10 or candidate["opening_ratio"] > 0.10 or strength == 0:
        report.update(status="skipped_not_closed_mouth_source_smile", active_pixel_count=0)
        return original, empty, report

    width = candidate["width"]
    source_width_ratio = source["width"] / source["eye_span"]
    candidate_width_ratio = width / candidate["eye_span"]
    width_ratio = float(np.clip(source_width_ratio / candidate_width_ratio, 0.94, 1.06))
    desired = source["corner_coordinates"].copy() * width
    desired[:,0] *= width_ratio
    current = candidate["corner_coordinates"] * width
    requested = (desired - current) * float(strength)
    lengths = np.linalg.norm(requested, axis=1)
    maximum = width * MAX_CORNER_SHIFT_MOUTH_WIDTH
    shifts = requested * np.minimum(1, maximum / np.maximum(lengths, 1e-8))[:,None]
    if float(np.max(np.linalg.norm(shifts,axis=1))) < 0.12:
        report.update(status="skipped_already_close", active_pixel_count=0)
        return original, empty, report

    yy, xx = np.mgrid[:h,:w].astype(np.float32)
    tangent, normal = candidate["tangent"], candidate["normal"]
    dx,dy = xx-candidate["center"][0], yy-candidate["center"][1]
    u = dx*tangent[0] + dy*tangent[1]
    v = dx*normal[0] + dy*normal[1]
    # Smooth compact horizontal supports, flat vertically throughout the lips.
    # This keeps the entire lip column together instead of opening a gap.
    shift_u,shift_v = empty.copy(),empty.copy()
    for corner, shift in zip(current, shifts):
        d = np.abs(u-corner[0]) / max(width*0.46,1)
        weight = np.where(d<1, (1-d*d)**2, 0).astype(np.float32)
        shift_u += shift[0]*weight
        shift_v += shift[1]*weight
    order = np.argsort(current[:,0])
    baseline = np.interp(u, [current[order[0],0],0,current[order[1],0]],
                         [current[order[0],1],0,current[order[1],1]]).astype(np.float32)
    distance = np.maximum(np.abs(v-baseline)/width-0.115,0)/0.19
    gate = np.where(distance<1, (1-distance*distance)**2, 0).astype(np.float32)
    support = (np.abs(shift_u)+np.abs(shift_v)>1e-5).astype(np.float32)*gate
    face = np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.round(np.asarray(points)[list(_FACE_OVAL)]).astype(np.int32)],255)
    face = cv2.erode(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(11,11)))
    support[(face==0)|(np.asarray(semantic_hair_mask)>0)] = 0
    shift_u *= support
    shift_v *= support
    map_x = xx-(shift_u*tangent[0]+shift_v*normal[0])
    map_y = yy-(shift_u*tangent[1]+shift_v*normal[1])
    # Linear interpolation avoids ringing on the dark closed lip seam.
    output = cv2.remap(original,map_x,map_y,cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT_101)
    active = support>0
    output[~active] = original[~active]
    report.update(status="applied", source_width_ratio=round(source_width_ratio,6),
                  candidate_width_ratio=round(candidate_width_ratio,6),
                  source_width_ratio_capped=round(width_ratio,6),
                  applied_corner_shifts_local_pixels=shifts.round(4).tolist(),
                  maximum_allowed_shift_pixels=round(maximum,4),
                  maximum_field_shift_pixels=round(float(np.hypot(shift_u,shift_v).max()),4),
                  active_pixel_count=int(active.sum()),
                  protected_pixel_max_error_0_to_255=float(np.max(np.abs(output[~active]-original[~active]),initial=0)*255),
                  upper_and_lower_lips_share_same_displacement=True)
    return output.astype(np.float32),support,report
