"""Verify the constant-strength split control before any identity-schedule trial."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_references(references):
    normalized = copy.deepcopy(references)
    for reference in normalized:
        path = Path(reference['path']).resolve(strict=True)
        if sha(path) != reference['sha256'].lower():
            raise ValueError('Recorded reference bytes changed.')
        reference['path'] = str(path).casefold()
    return normalized


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-audit', type=Path, required=True)
    parser.add_argument('--control-audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output.exists() or not args.output.resolve().is_relative_to(root):
        raise ValueError('Use a new project-local report.')
    audits = [json.loads(p.read_text(encoding='utf-8-sig'))
              for p in (args.original_audit, args.control_audit)]
    for audit in audits:
        if not audit['executed_png_graph_verified'] or audit['postprocess_applied']:
            raise ValueError('Only executed, unprocessed native images can verify the split.')
    manifests = [json.loads(Path(a['manifest']).read_text(encoding='utf-8-sig')) for a in audits]
    original, control = manifests
    schedule = control['identity_schedule']
    if not (schedule['constant_strength_control'] is True
            and schedule['early_identity_strength'] == schedule['late_identity_strength'] == .9
            and schedule['total_steps'] == 50 and schedule['split_step'] == 35
            and canonical_references(original['references']) == canonical_references(control['references'])
            and original['verified_models'] == control['verified_models']):
        raise ValueError('Control identity, references or models changed.')
    graph = copy.deepcopy(control['prompt'])
    expected_late_identity = copy.deepcopy(original['prompt']['2'])
    expected_late_identity['inputs']['strength_model'] = .9
    expected_late_phone = copy.deepcopy(original['prompt']['3'])
    expected_late_phone['inputs']['model'] = ['31', 0]
    expected_late_guider = copy.deepcopy(original['prompt']['21'])
    expected_late_guider['inputs']['model'] = ['32', 0]
    if not (graph['35']['inputs']['latent_image'] == ['25', 0]
            and graph['35']['class_type'] == 'SamplerCustomAdvanced'
            and graph['35']['inputs']['sampler'] == ['22', 0]
            and graph['35']['inputs']['guider'] == ['33', 0]
            and graph['31'] == expected_late_identity
            and graph['32'] == expected_late_phone
            and graph['33'] == expected_late_guider
            and graph['35']['inputs']['noise'] == ['34', 0]
            and graph['34']['class_type'] == 'DisableNoise'
            and graph['35']['inputs']['sigmas'] == ['30', 1]
            and graph['30']['inputs'] == {'sigmas': ['23', 0], 'step': 35}
            and graph['25']['inputs']['sigmas'] == ['30', 0]
            and graph['26']['inputs']['samples'] == ['35', 0]):
        raise ValueError('Split continuation topology changed.')
    graph['25']['inputs']['sigmas'] = ['23', 0]
    graph['26']['inputs']['samples'] = ['25', 0]
    graph['27']['inputs']['filename_prefix'] = original['prompt']['27']['inputs']['filename_prefix']
    for key in ('30', '31', '32', '33', '34', '35'):
        del graph[key]
    if graph != original['prompt']:
        raise ValueError('Non-schedule graph parameters changed.')
    paths = [Path(a['inputs']['CANDIDATE HIGH']['path']) for a in audits]
    arrays = []
    for path, audit in zip(paths, audits):
        if sha(path) != audit['inputs']['CANDIDATE HIGH']['sha256']:
            raise ValueError('Audited image changed.')
        with Image.open(path) as image:
            arrays.append(np.asarray(image.convert('RGB')))
    if arrays[0].shape != arrays[1].shape:
        raise ValueError('Control dimensions changed.')
    difference = arrays[0].astype(np.float64)-arrays[1].astype(np.float64)
    mae, mse = float(np.abs(difference).mean()), float(np.square(difference).mean())
    ssim = float(structural_similarity(*arrays, channel_axis=2, data_range=255))
    bounds = audits[0]['results']['CANDIDATE HIGH']['bbox_xyxy']
    x0, y0, x1, y1 = [int(round(value)) for value in bounds]
    face_arrays = [a[max(0,y0):min(a.shape[0],y1), max(0,x0):min(a.shape[1],x1)] for a in arrays]
    if min(face_arrays[0].shape[:2]) < 7:
        raise ValueError('Control face crop is invalid.')
    face_mae = float(np.abs(face_arrays[0].astype(np.float64)-face_arrays[1]).mean())
    face_ssim = float(structural_similarity(*face_arrays, channel_axis=2, data_range=255))
    passed = mae <= .25 and ssim >= .999 and face_mae <= .25 and face_ssim >= .999
    report = {'status': 'mechanics_pass_visual_review_required' if passed else 'rejected_split_control',
              'passed': passed, 'rgb_mae_0_to_255': mae, 'rgb_max_absolute_error': float(np.abs(difference).max()),
              'psnr_db': 10*np.log10(255**2/mse) if mse else None, 'ssim': ssim,
              'face_mae_0_to_255': face_mae, 'face_ssim': face_ssim, 'face_box': [x0,y0,x1,y1],
              'limits': {'maximum_mae': .25, 'minimum_ssim': .999},
              'images': [{'path': str(p), 'sha256': sha(p)} for p in paths],
              'audits': [{'path': str(p), 'sha256': sha(p)} for p in (args.original_audit, args.control_audit)],
              'meaning': 'Implementation-equivalence control only, not beauty/identity/production acceptance.'}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
