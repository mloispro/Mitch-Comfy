"""Calibrated author semantic controls; evaluation only, no production import."""
from __future__ import annotations

import numpy as np
from scipy.optimize import lsq_linear


CONTROL_SCALES = np.array([.15, 5., 5.])
# Smile corners2, signed lip gap1, brow height/slope4, eye aperture2,
# normalized iris2x2, nasal width1, jaw width1.
TOLERANCES = np.array([.03, .03, .012, .12, .12, .12, .12,
                       .035, .035, .025, .08, .025, .08, .03, .05])
FEATURE_NAMES = ['mouth_corner_0_y', 'mouth_corner_1_y', 'lip_opening',
                 'brow_0_height', 'brow_0_slope', 'brow_1_height', 'brow_1_slope',
                 'eye_0_aperture', 'eye_1_aperture', 'iris_0_x', 'iris_0_y',
                 'iris_1_x', 'iris_1_y', 'nose_width', 'jaw_width']


def apply_controls(expression, controls):
    """Same offsets as author's smile/eyebrow/lip_variation_three methods."""
    p = np.asarray(controls, float)
    if p.shape != (3,) or not np.isfinite(p).all():
        raise ValueError('Expected three finite controls.')
    smile, eyebrow, lip = p
    if not (-.3 <= smile <= 1.3 and -30 <= eyebrow <= 30 and -90 <= lip <= 120):
        raise ValueError('Controls exceed author GUI range.')
    delta = expression.clone() if hasattr(expression, 'clone') else np.array(expression, copy=True)
    if tuple(delta.shape) != (1, 21, 3):
        raise ValueError('Expected one 21-point expression tensor.')
    delta[0, 20, 1] += smile * -.01
    delta[0, 14, 1] += smile * -.02
    delta[0, 17, 1] += smile * .0065
    delta[0, 17, 2] += smile * .003
    delta[0, 13, 1] += smile * -.00275
    delta[0, 16, 1] += smile * -.00275
    delta[0, 3, 1] += smile * -.0035
    delta[0, 7, 1] += smile * -.0035
    if eyebrow > 0:
        delta[0, 1, 1] += eyebrow * .001
        delta[0, 2, 1] += eyebrow * -.001
    else:
        delta[0, 1, 0] += eyebrow * -.001
        delta[0, 2, 0] += eyebrow * .001
        delta[0, 1, 1] += eyebrow * .0003
        delta[0, 2, 1] += eyebrow * -.0003
    delta[0, 19, 1] += lip * .001
    delta[0, 19, 2] += lip * .0001
    delta[0, 17, 1] += lip * -.0001
    return delta


def expression_features(points):
    from experimental_upgrade_smile_balance import measure_smile
    from experimental_upgrade_source_brows import brow_frames
    from flux2_klein9b_source_gaze_lock import _eye_measurement, _EYES
    p = np.asarray(points, np.float32)
    smile = measure_smile(p)
    values = list(smile['corner_coordinates'][:, 1])
    values.append(float(np.dot(p[14]-p[13], smile['normal']) / smile['width']))
    for frame in brow_frames(p):
        xy = frame['relative']; sorted_xy = xy[np.argsort(xy[:, 0])]
        # Overall height and outer-to-inner slope, not brow texture or darkness.
        values.extend([float(xy[:, 1].mean()), float(sorted_xy[-3:, 1].mean()-sorted_xy[:3, 1].mean())])
    eyes = [_eye_measurement(p, definition) for definition in _EYES]
    for eye in eyes:
        values.append(float(np.linalg.norm(eye['vertical']) / eye['eye_width']))
    for eye in eyes:
        values.extend(eye['coordinate'].tolist())
    span = smile['eye_span']
    values.extend([float(np.linalg.norm(p[98]-p[327])/span),
                   float(np.linalg.norm(p[234]-p[454])/span)])
    result = np.array(values, float)
    if result.shape != TOLERANCES.shape or not np.isfinite(result).all():
        raise ValueError('Invalid expression measurements.')
    return result


def solve_response(zero_features, raw_features, source_features, probes, ridge=.15,
                   close_only=False):
    """One bounded local inverse solve, with explicit brow sign branches."""
    z, r, s = [np.asarray(v, float) for v in (zero_features, raw_features, source_features)]
    if any(v.shape != TOLERANCES.shape or not np.isfinite(v).all() for v in (z, r, s)):
        raise ValueError('Invalid calibration feature vector.')
    probes = np.asarray(probes, float)
    if probes.shape != (3, 2, len(z)) or not np.isfinite(probes).all():
        raise ValueError('Expected six finite probe measurements.')
    desired = s.copy()
    desired[2] = .005  # closed lips, not copying accidental source mouth gaps
    target = z.copy()
    target[:9] += desired[:9]-r[:9]
    # Iris and nose/jaw targets remain zero-control values: keep raw geometry.
    candidates = []
    for sign in (1., -1.):
        response = (probes[:, 1]-probes[:, 0]).T / 2
        response[:, 1] = probes[1, 1 if sign > 0 else 0]-z
        matrix = response/TOLERANCES[:, None]
        rhs = (target-z)/TOLERANCES
        fit = lsq_linear(np.vstack((matrix, ridge*np.eye(3))),
                         np.r_[rhs, np.zeros(3)], bounds=([-2, 0, -4], [4, 3, 0 if close_only else 4]),
                         tol=1e-10, max_iter=100)
        physical = fit.x*CONTROL_SCALES*np.array([1., sign, 1.])
        predicted = z+response@fit.x
        residual = float(np.linalg.norm((predicted-target)/TOLERANCES))
        candidates.append({'brow_sign': sign, 'controls': physical.tolist(),
                           'predicted_features': predicted.tolist(), 'predicted_residual': residual,
                           'penalized_cost': float(2*fit.cost), 'solver_success': bool(fit.success)})
    best = min(candidates, key=lambda item: item['penalized_cost'])
    if not best['solver_success']:
        raise RuntimeError('Semantic-control solve did not converge.')
    return np.array(best['controls']), {'feature_names': FEATURE_NAMES,
        'zero_features': z.tolist(), 'raw_features': r.tolist(), 'source_features': s.tolist(),
        'target_features': target.tolist(), 'tolerances': TOLERANCES.tolist(),
        'before_residual': float(np.linalg.norm((z-target)/TOLERANCES)),
        'branches': candidates, 'selected': best, 'ridge': ridge, 'close_only': close_only}


def calibrate_controls(render, zero, raw_points, source_points, detect, close_only=False):
    z = expression_features(detect(zero)[0])
    raw = expression_features(raw_points); source = expression_features(source_points)
    probes = []; images = {}
    for index, name in enumerate(('smile', 'brow', 'lip')):
        measured = []
        for sign in (-1, 1):
            p = np.zeros(3); p[index] = sign*CONTROL_SCALES[index]
            image = render(p); images[f'probe-{name}-{sign:+}'] = image
            measured.append(expression_features(detect(image)[0]))
        probes.append(measured)
    controls, report = solve_response(z, raw, source, probes, close_only=close_only)
    edited = render(controls)
    measured = expression_features(detect(edited)[0])
    target = np.array(report['target_features'])
    report.update({'mode': 'author_semantic_controls_calibrated_v1',
                   'probe_features': np.asarray(probes).tolist(), 'controls': controls.tolist(),
                   'measured_features': measured.tolist(),
                   'measured_residual': float(np.linalg.norm((measured-target)/TOLERANCES)),
                   'prediction_error': float(np.linalg.norm((measured-np.array(report['selected']['predicted_features']))/TOLERANCES)),
                   'decoder_calls_including_zero': 8,
                   'driving_image_enters_model': False})
    return edited, report, images
