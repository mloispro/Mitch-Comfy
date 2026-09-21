"""Read-only geometry diagnostic: can protected iris regions suppress eyelid edits?"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'custom_nodes/ComfyUI-AIToolkit-Training'))
sys.path.insert(0, str(ROOT.parent / 'ComfyUI'))
from flux2_klein9b_attractiveness import _EYE_CONTOURS, _IRISES
from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
from experimental_upgrade_smile_balance import measure_smile


def read(path):
    with Image.open(path) as image:
        return np.array(ImageOps.exif_transpose(image).convert('RGB'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT):
        raise ValueError('Use a new project-local diagnostic output.')
    work = ROOT / 'work/upgrade-source-faithful-20260903'
    reports = {}
    for photo, folder in [('canyon', 'source-contour-final-gaze-canyon'),
                          ('house', 'source-contour-final-gaze-house'),
                          ('third', 'source-contour-corrected-third')]:
        parent = json.loads((work / folder / 'audit.json').read_text(encoding='utf-8-sig'))
        paths = {'source': Path(parent['source']),
                 'before': work / folder / 'previous_high.png',
                 'after': work / folder / 'high.png'}
        images = {key: read(path) for key, path in paths.items()}
        landmarks = {key: _detect_refined_landmarks(image)[0] for key, image in images.items()}
        p, s = landmarks['before'], landmarks['source']
        before_frame, source_frame = measure_smile(p), measure_smile(s)
        basis = np.stack((before_frame['tangent'], before_frame['normal']), axis=1)
        source_basis = np.stack((source_frame['tangent'], source_frame['normal']), axis=1)
        h, w = images['before'].shape[:2]
        eyes = []
        for contour, iris in zip(_EYE_CONTOURS, _IRISES):
            eye, source_eye = p[list(contour)], s[list(contour)]
            width = float(np.linalg.norm(eye[8] - eye[0]))
            source_width = float(np.linalg.norm(source_eye[8] - source_eye[0]))
            center, source_center = p[iris[0]], s[iris[0]]
            desired = center + (((source_eye-source_center) @ source_basis / source_width) * width) @ basis.T
            requested = (desired-eye)*.85
            length = np.linalg.norm(requested, axis=1)
            shifts = requested*np.minimum(1., width*.085/np.maximum(length, 1e-8))[:, None]
            guard = np.zeros((h,w), np.uint8)
            cv2.fillPoly(guard, [np.rint(p[list(iris[1:])]).astype(np.int32)], 255)
            protection = np.clip(cv2.distanceTransform((guard == 0).astype(np.uint8), cv2.DIST_L2, 5)/3., 0, 1)
            targets = eye+shifts
            coords = np.rint(targets).astype(int)
            factors = protection[np.clip(coords[:,1],0,h-1), np.clip(coords[:,0],0,w-1)]
            after = landmarks['after'][list(contour)]
            errors = {
                'before_mean_source_target_error_pixels': float(np.linalg.norm(eye-desired,axis=1).mean()),
                'after_mean_source_target_error_pixels_fixed_before_frame': float(np.linalg.norm(after-desired,axis=1).mean()),
            }
            eyes.append({'eye_width': width,
                'upper_lid_control_ids': list(contour[1:8]),
                'upper_lid_requested_displacement_pixels': np.linalg.norm(shifts[1:8],axis=1).tolist(),
                'iris_only_guard_retention_at_requested_upper_lid_targets': factors[1:8].tolist(),
                'upper_lid_targets_fully_blocked_by_iris_guard': int(np.count_nonzero(factors[1:8] == 0)),
                'upper_lid_targets_partially_blocked_by_iris_guard': int(np.count_nonzero((factors[1:8] > 0)&(factors[1:8] < 1))),
                **errors})
        reports[photo] = {'inputs': {key: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for key,path in paths.items()},
            'eyes': eyes, 'diffusion_runs': 0,
            'note': 'Iris guard is a subset of full protection. These are geometric target constraints, not measured achieved deformation or an attractiveness score. Final gaze only edits eroded eye interiors, not eyelid boundaries.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(reports,indent=2),encoding='utf-8')
    print(json.dumps(reports,indent=2))


if __name__ == '__main__':
    main()
