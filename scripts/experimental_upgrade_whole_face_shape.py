"""Offline source-guided whole-face geometry probe, never imported by production.

This moves existing generated pixels, including the lower facial silhouette.
It is not a trained beauty/identity model and copies no source-photo texture.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator

from upgrade_face_contour_diagnostic import FACE_OVAL


def eye_frame(points):
    origin = (points[33] + points[263]) / 2
    horizontal = points[263] - points[33]
    span = float(np.linalg.norm(horizontal))
    if span < 8:
        raise ValueError('Degenerate outer-eye span.')
    horizontal = horizontal / span
    vertical = np.array([-horizontal[1], horizontal[0]])
    if (points[152] - origin) @ vertical < 0:
        vertical = -vertical
    return origin, np.column_stack((horizontal, vertical)), span


def shape_targets(points, source, strength=.8):
    """Match source proportions in the candidate's eye-line frame, not its pose."""
    points = np.asarray(points, np.float64)
    source = np.asarray(source, np.float64)
    if (points.shape != (478, 2) or source.shape != (478, 2)
            or not np.isfinite(points).all() or not np.isfinite(source).all()
            or not np.isfinite(strength) or not 0 <= strength <= 1):
        raise ValueError('Expected finite 478x2 landmarks and strength0..1.')
    origin, basis, span = eye_frame(points)
    source_origin, source_basis, source_span = eye_frame(source)
    projected = ((source - source_origin) @ source_basis / source_span)
    aligned = origin + projected @ basis.T * span
    local = (points - origin) @ basis / span
    # No forehead shortening, hairline lowering or global head rotation.
    forehead_gate = np.clip((local[:, 1] + .65) / .35, 0, 1)
    displacement = (aligned - points) * float(strength) * forehead_gate[:, None]
    width = float(np.ptp(points[list(FACE_OVAL)] @ basis[:, 0]))
    lengths = np.linalg.norm(displacement, axis=1)
    displacement *= np.minimum(1., width * .10 / np.maximum(lengths, 1e-8))[:, None]
    target = points + displacement
    # Move each iris as a rigid ring; do not transplant source iris color/radius.
    for center, ring in ((468, (469, 470, 471, 472)), (473, (474, 475, 476, 477))):
        target[list(ring)] = points[list(ring)] + displacement[center]
    return target, {'strength': float(strength), 'face_width_pixels': width,
                    'maximum_control_shift_pixels': float(np.linalg.norm(target-points, axis=1).max()),
                    'source_alignment': 'outer-eye translation, uniform scale and roll only; no 3D pose correction',
                    'forehead_gate': 'fixed above -0.65 eye span; full strength below -0.30',
                    'lower_face_silhouette_fixed': False}


def whole_face_shape(rgb, points, source_points, hair, strength=.8, control_policy='dense'):
    rgb = np.asarray(rgb, np.float32)
    hair = np.asarray(hair)
    if (rgb.ndim != 3 or rgb.shape[2] != 3 or hair.shape != rgb.shape[:2]
            or not np.isfinite(rgb).all() or not np.isfinite(hair).all()
            or rgb.min() < 0 or rgb.max() > 1):
        raise ValueError('Expected RGB0..1 and finite matched hair mask.')
    target, report = shape_targets(points, source_points, strength)
    points = np.asarray(points, np.float64)
    height, width = rgb.shape[:2]
    empty = np.zeros((height, width), np.float32)
    if np.max(np.abs(target-points)) < 1e-5:
        return rgb.copy(), empty, {**report, 'status': 'no_op'}
    scale = report['face_width_pixels']
    face = np.zeros((height, width), np.uint8)
    # Union allows an actual cheek/jaw silhouette adjustment instead of silently
    # pinning the outline, as the earlier tiny eye-only prototypes did.
    for polygon in (points, target):
        cv2.fillPoly(face, [np.rint(polygon[list(FACE_OVAL)]).astype(np.int32)], 1)
    radius = max(3, round(scale * .14))
    exterior_distance = cv2.distanceTransform(1-face, cv2.DIST_L2, 5)
    support = np.clip((radius-exterior_distance)/max(1., radius*.72), 0, 1)
    protected_hair = cv2.dilate((hair > 0).astype(np.uint8), np.ones((5,5),np.uint8))
    distance_hair = cv2.distanceTransform(1-protected_hair, cv2.DIST_L2, 5)
    support *= np.clip(distance_hair/max(4.,scale*.065),0,1)
    origin, basis, span = eye_frame(points)
    yy, xx = np.mgrid[:height,:width].astype(np.float32)
    local_y = ((xx-origin[0])*basis[0,1]+(yy-origin[1])*basis[1,1])/span
    support *= np.clip((local_y+.65)/.35,0,1)
    support[support < .001] = 0
    active = support > 0
    # Fixed exterior controls ensure a gradual return to the untouched frame.
    contours, _ = cv2.findContours(active.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    boundary = max(contours,key=len).reshape(-1,2)[::max(1,max(map(len,contours))//64)]
    if control_policy == 'dense':
        selected = list(range(478))
    elif control_policy == 'feature_cage':
        # The dense pilot folded at the oblique far-cheek/nose surface: dense
        # screen-projected interior vertices are not safe 2D correspondences.
        # Keep semantic boundaries, allowing the surface between them to deform
        # smoothly. Iris pixels follow the eye map, then existing gaze correction;
        # no rigid iris-ring guarantee is claimed for this cage variant.
        from flux2_klein9b_attractiveness import _EYE_CONTOURS, _BROWS
        outer_lips = (61,146,91,181,84,17,314,405,321,375,291,409,270,269,267,0,37,39,40,185)
        selected = sorted(set(FACE_OVAL+outer_lips+(1,4,6,168,2,98,327)
                              +tuple(i for group in _EYE_CONTOURS+_BROWS for i in group)))
    else:
        raise ValueError('Unknown control policy.')
    controls = np.concatenate((boundary,target[selected]))
    samples = np.concatenate((boundary,points[selected]))
    kept = []
    for index, coordinate in enumerate(controls):
        if not kept or np.linalg.norm(controls[kept]-coordinate,axis=1).min() > .6:
            kept.append(index)
    mapper = RBFInterpolator((controls[kept]-origin)/scale,
        (samples[kept]-controls[kept])/scale, kernel='thin_plate_spline',degree=1,smoothing=1e-5)
    coordinates = np.column_stack((xx[active],yy[active]))
    field = np.zeros((height,width,2),np.float32)
    values = np.empty_like(coordinates)
    for start in range(0,len(coordinates),2048):
        values[start:start+2048] = mapper((coordinates[start:start+2048]-origin)/scale)*scale
    field[active] = values*support[active,None]
    dx_y,dx_x = np.gradient(field[:,:,0]); dy_y,dy_x = np.gradient(field[:,:,1])
    jacobian = (1+dx_x)*(1+dy_y)-dx_y*dy_x
    minimum = float(jacobian[active].min(initial=1.))
    maximum = float(np.linalg.norm(field,axis=2).max(initial=0.))
    if not np.isfinite(field).all() or minimum < .20 or maximum > scale*.16:
        position = np.unravel_index(np.argmin(np.where(active,jacobian,np.inf)),jacobian.shape)
        xy = np.array(position[::-1])
        nearest = np.argsort(np.linalg.norm(target-xy,axis=1))[:8].tolist()
        raise ValueError(f'Unsafe full-face warp: Jacobian {minimum:.4f}, max shift {maximum:.4f}px, '
                         f'minimum at xy={xy.tolist()}, nearest target landmarks={nearest}. No automatic strength reduction.')
    result = np.clip(cv2.remap(rgb,xx+field[:,:,0],yy+field[:,:,1],
        cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101),0,1)
    result[~active] = rgb[~active]
    return result, support, {**report, 'status':'experimental_not_promoted',
        'profile':'source_guided_whole_face_shape_v1', 'minimum_inverse_jacobian':minimum,
        'control_policy':control_policy,'semantic_control_count':len(selected),
        'iris_ring_has_explicit_rigid_controls':control_policy=='dense',
        'maximum_displacement_pixels':maximum, 'exterior_support_radius_pixels':radius,
        'exterior_pixel_max_error':float(np.abs(result-rgb)[~active].max(initial=0)),
        'protected_hair_pixel_max_error':float(np.abs(result-rgb)[protected_hair>0].max(initial=0)),
        'source_pixels_copied':False,'identity_conditioning':False,
        'limitation':'2D geometry only. Local background/collar pixels within the lower-face transition may deform. No skin/hair restoration. Recognition, pose, gaze and realism require independent review.'}
