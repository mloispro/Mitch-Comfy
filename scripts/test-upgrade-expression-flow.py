"""Local author-core expression-only motion experiment. Never imported by production."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '1'
import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps
from experimental_upgrade_expression_flow import (
    estimate_inverse_flow, cycle_diagnostics, native_displacement, remap_original,
)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def api(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/{path}', timeout=5) as response:
        return json.load(response)


def preflight(owned_cache_prompt=None):
    workers = []
    for port in (8188, 8189):
        queue = api(port, 'queue'); stats = api(port, 'system_stats')
        workers.append({'port': port, 'device': stats['devices'][0]['name'],
                        'running': len(queue['queue_running']), 'pending': len(queue['queue_pending'])})
    if 'RTX 3090' not in workers[0]['device'] or workers[0]['running'] or workers[0]['pending']:
        raise RuntimeError('The workflow-locked RTX3090 is busy or not mapped correctly.')
    hardware = subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.used,utilization.gpu,memory.free',
                                        '--format=csv,noheader,nounits'], text=True)
    cards = [line.split(',') for line in hardware.splitlines() if 'RTX 3090' in line]
    if len(cards) != 1 or int(cards[0][3]) > 10:
        raise RuntimeError('RTX3090 is active. This script never releases/intercepts other work.')
    cache_provenance = None
    if int(cards[0][2]) > 4096:
        if owned_cache_prompt != '359b70af-a7a5-4c9f-8ea9-5bd484082b59' or int(cards[0][4]) < 8192:
            raise RuntimeError('RTX3090 lacks verified idle cache provenance or 8GiB free headroom.')
        latest = api(8188, 'history?max_items=1')
        if list(latest) != [owned_cache_prompt]:
            raise RuntimeError('Latest job no longer matches the specified owned cache.')
        status = latest[owned_cache_prompt]['status']
        if not status['completed'] or status['status_str'] != 'success':
            raise RuntimeError('Owned cached job is not terminal success.')
        cache_provenance = {'prompt_id': owned_cache_prompt, 'status': status['status_str'],
                            'free_mib': int(cards[0][4]), 'models_unloaded': False}
    if 'RTX 3090' not in torch.cuda.get_device_name(0):
        raise RuntimeError('cuda:0 is not the physical RTX3090.')
    return {'workers': workers, 'hardware': hardware, 'owned_idle_cache': cache_provenance}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-audit', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--strength', type=float, choices=(1., 2.), default=1.)
    parser.add_argument('--control-mode', choices=('absolute-expression', 'semantic-fit'), default='absolute-expression')
    parser.add_argument('--semantic-close-only', action='store_true', help='Sole semantic-policy refinement: forbid positive mouth-opening control.')
    parser.add_argument('--allow-owned-cache-prompt', help='Only the recorded terminal angle-reference job, with >=8GiB free; no unload.')
    args = parser.parse_args(); started = time.perf_counter()
    if args.control_mode == 'semantic-fit' and args.strength != 1:
        raise ValueError('Semantic calibration has no global expression multiplier.')
    if args.semantic_close_only and args.control_mode != 'semantic-fit':
        raise ValueError('Close-only constraint belongs to semantic calibration.')
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('Use a new directory within the project.')
    native = json.loads(args.native_audit.read_text(encoding='utf-8-sig'))
    if not native.get('executed_png_graph_verified') or native.get('postprocess_applied'):
        raise ValueError('Need a recorded native experiment audit for input provenance.')
    records = {label: native['inputs'][label] for label in ('SOURCE', 'BASE RAW', 'LOW')}
    refs = native['genuine_references']
    for record in [*records.values(), *refs]:
        if digest(record['path']) != record['sha256'].lower():
            raise ValueError(f"Recorded input changed: {record['path']}")
    if len(refs) < 2 or records['SOURCE']['sha256'] in {r['sha256'] for r in refs}:
        raise ValueError('Scoring requires separate genuine references.')
    repo = root / 'work/vendor/LivePortrait-code'
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != '9b294b3d0536135442ea73cb01e6cb3ca7029dd3':
        raise ValueError('Reviewed upstream commit changed.')
    if subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise ValueError('Reviewed upstream tracked source changed.')
    models = json.loads((repo / 'pretrained_weights/verified-human-control.json').read_text())
    for record in models['files']:
        if digest(record['path']) != record['sha256']:
            raise ValueError('Installed LivePortrait weights changed.')
    preflight_before = preflight(args.allow_owned_cache_prompt)
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(root / 'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0, str(root.parent / 'ComfyUI'))
    from src.live_portrait_wrapper import LivePortraitWrapper
    from src.config.inference_config import InferenceConfig
    from src.utils.crop import crop_image
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks, _eye_measurement, _EYES
    from flux2_klein9b_deterministic_polish import build_semantic_hair_mask
    from experimental_upgrade_smile_balance import _FACE_OVAL, measure_smile
    from upgrade_expression_acceptance import closed_lip_check

    torch.set_num_threads(4)
    def read(path):
        with Image.open(path) as photo:
            return np.array(ImageOps.exif_transpose(photo).convert('RGB'))
    photos = {label: read(record['path']) for label, record in records.items()}
    raw = photos['BASE RAW']; source = photos['SOURCE']
    if raw.shape != source.shape or raw.shape != photos['LOW'].shape:
        raise ValueError('This full-frame experiment requires matching dimensions.')
    detector = FaceAnalysis(name='buffalo_l', root=str(Path.home() / '.insightface'),
                            providers=['CPUExecutionProvider'], allowed_modules=['detection', 'landmark_2d_106'])
    detector.prepare(ctx_id=-1, det_size=(512, 512), det_thresh=.5)
    def detected_face(image, analyzer=detector):
        faces = analyzer.get(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if len(faces) != 1:
            raise RuntimeError(f'Expected exactly one face, found {len(faces)}.')
        return faces[0]
    raw_face = detected_face(raw)
    def crop(image, face):
        return crop_image(image, face.landmark_2d_106, dsize=512, scale=2.3,
                          vx_ratio=0, vy_ratio=-.125, flag_do_rot=True)
    base_crop = crop(raw, raw_face); drive_crop = crop(source, detected_face(source))
    raw_points, _ = _detect_refined_landmarks(raw)
    hair = build_semantic_hair_mask(raw, raw_face.bbox)
    h, w = raw.shape[:2]; face_width = float(raw_face.bbox[2] - raw_face.bbox[0])
    face_mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(face_mask, [np.rint(raw_points[list(_FACE_OVAL)]).astype(np.int32)], 1)
    face_mask = cv2.erode(face_mask, np.ones((3, 3), np.uint8))
    face_mask[cv2.dilate(hair, np.ones((3, 3), np.uint8)) > 0] = 0
    distance = cv2.distanceTransform(face_mask, cv2.DIST_L2, 5)
    support = np.minimum(distance / max(4, face_width * .065), 1).astype(np.float32)
    crop_matrix = np.asarray(base_crop['M_c2o'], np.float32)[:2]
    inverse_matrix = cv2.invertAffineTransform(crop_matrix)
    crop_support = cv2.warpAffine(support, inverse_matrix, (512, 512))
    cfg = InferenceConfig(flag_use_half_precision=False, flag_normalize_lip=False,
                          flag_stitching=False, flag_relative_motion=False, animation_region='exp',
                          flag_eye_retargeting=False, flag_lip_retargeting=False,
                          flag_do_torch_compile=False, device_id=0,
                          lip_array=np.zeros((1, 21, 3), np.float32))
    preflight_after = preflight(args.allow_owned_cache_prompt)
    torch.cuda.reset_peak_memory_stats(0)
    wrapper = LivePortraitWrapper(cfg)
    base_input = wrapper.prepare_source(cv2.resize(base_crop['img_crop'], (256, 256), interpolation=cv2.INTER_AREA))
    base_info = wrapper.get_kp_info(base_input)
    base_points = wrapper.transform_keypoint(base_info)
    features = wrapper.extract_feature_3d(base_input)
    zero = wrapper.parse_output(wrapper.warp_decode(features, base_points, base_points)['out'])[0]
    edited_info = dict(base_info)
    calibration = None; probe_images = {}; driving_expression = None
    if args.control_mode == 'semantic-fit':
        from experimental_upgrade_semantic_expression import apply_controls, calibrate_controls
        source_points, _ = _detect_refined_landmarks(source)
        def render(controls):
            controlled_info = dict(base_info)
            controlled_info['exp'] = apply_controls(base_info['exp'], controls)
            controlled_points = wrapper.transform_keypoint(controlled_info)
            return wrapper.parse_output(wrapper.warp_decode(features, base_points, controlled_points)['out'])[0]
        edited, calibration, probe_images = calibrate_controls(
            render, zero, raw_points, source_points, _detect_refined_landmarks,
            close_only=args.semantic_close_only)
        edited_info['exp'] = apply_controls(base_info['exp'], calibration['controls'])
        del render
    else:
        drive_input = wrapper.prepare_source(cv2.resize(drive_crop['img_crop'], (256, 256), interpolation=cv2.INTER_AREA))
        drive_info = wrapper.get_kp_info(drive_input)
        expression = base_info['exp'].clone()
        # Exactly the author's absolute expression subset; no driving pose or canonical face.
        ids = [1, 2, 6, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        expression[:, ids, :] = drive_info['exp'][:, ids, :]
        expression[:, 3:5, 1] = drive_info['exp'][:, 3:5, 1]
        expression[:, 5, 2] = drive_info['exp'][:, 5, 2]
        expression[:, 8, 2] = drive_info['exp'][:, 8, 2]
        expression[:, 9, 1:] = drive_info['exp'][:, 9, 1:]
        edited_info['exp'] = base_info['exp'] + args.strength * (expression - base_info['exp'])
        edited_points = wrapper.transform_keypoint(edited_info)
        edited = wrapper.parse_output(wrapper.warp_decode(features, base_points, edited_points)['out'])[0]
        driving_expression = drive_info['exp'].cpu().numpy().tolist()
        del drive_input, drive_info, expression, edited_points
    peak = torch.cuda.max_memory_allocated(0)
    coeffs = {'base_expression': base_info['exp'].cpu().numpy().tolist(),
              'driving_expression': driving_expression,
              'edited_expression': edited_info['exp'].cpu().numpy().tolist()}
    del wrapper, features, base_input, base_info, base_points, edited_info
    torch.cuda.empty_cache()
    output.mkdir(parents=True)
    for name, image in [('zero-reconstruction', zero), ('expression-reconstruction', edited),
                        ('raw-crop', base_crop['img_crop']), ('driving-crop', drive_crop['img_crop'])]:
        Image.fromarray(image).save(output / f'{name}.png')
    for name, image in probe_images.items():
        Image.fromarray(image).save(output / f'{name}.png')
    Image.fromarray(np.rint(support * 255).astype(np.uint8)).save(output / 'support.png')
    inverse, forward = estimate_inverse_flow(zero, edited)
    np.savez_compressed(output / 'motion.npz', inverse=inverse, forward=forward, crop_to_original=crop_matrix)
    cycles = cycle_diagnostics(inverse, forward, crop_support)
    report = {'status': 'evaluated_not_promoted', 'strength': args.strength,
              'control_mode': args.control_mode, 'calibration': calibration,
              'native_audit': str(args.native_audit.resolve()), 'native_audit_sha256': digest(args.native_audit),
              'inputs': records, 'genuine_references': refs, 'models': models, 'source_commit': commit,
              'conditioning': ('original scene CPU landmarks only; raw appearance/canonical pose/scale/translation and calibrated author expression controls'
                               if calibration is not None else 'original scene expression-only; generated raw appearance/canonical pose/scale/translation'),
              'final_pixels': 'raw only; no decoder or driving RGB', 'coefficients': coeffs,
              'crop_to_original': crop_matrix.tolist(), 'cycle': cycles,
              'preflight': [preflight_before, preflight_after], 'peak_allocated_gpu_bytes': peak,
              'phone_style': 'inherited from existing raw', 'turbo': False,
              'production_changed': False, 'visual_review_required': True}
    (output / 'audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if calibration is not None and (calibration['measured_residual'] >= calibration['before_residual']
                                    or calibration['measured_features'][2] > .035):
        report.update({'status': 'rejected_semantic_prediction',
                       'failure': 'Actual decoded response worsens the expression target or opens the lips; no native RGB remap.',
                       'seconds': time.perf_counter()-started})
        (output / 'audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        raise RuntimeError(report['failure'])
    if not cycles['passed']:
        report.update({'status': 'rejected_flow_consistency',
                       'failure': 'Inverse/forward correspondence is unsafe; no native RGB remap performed.',
                       'seconds': time.perf_counter() - started})
        (output / 'audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        raise RuntimeError(f'Optical-flow consistency failed: {cycles}')
    displacement = native_displacement(inverse, crop_matrix, (h, w))
    try:
        high, mapping = remap_original(raw, displacement, support, face_width)
    except ValueError as exc:
        report.update({'status': 'rejected_native_mapping', 'failure': str(exc),
                       'seconds': time.perf_counter() - started})
        (output / 'audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        raise
    self_inverse, _ = estimate_inverse_flow(zero, zero.copy())
    zero_raw, zero_guard = remap_original(raw, native_displacement(self_inverse, crop_matrix, (h, w)), support, face_width)
    if not np.array_equal(zero_raw, raw) or not np.array_equal(high[hair > 0], raw[hair > 0]):
        raise RuntimeError('Zero control or hair preservation failed.')
    Image.fromarray(high).save(output / 'expression-flow.png')
    photos['FLOW TEST'] = high
    analyzer = FaceAnalysis(name='antelopev2', root=str(Path.home() / '.insightface'),
                            providers=['CPUExecutionProvider'], allowed_modules=['detection', 'recognition', 'landmark_3d_68'])
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    embeddings = [detected_face(read(r['path']), analyzer).normed_embedding for r in refs]
    centroid = np.mean(embeddings, axis=0); centroid /= np.linalg.norm(centroid)
    results = {}; face_boxes = {}
    for label, rgb in photos.items():
        face = detected_face(rgb, analyzer); face_boxes[label] = face.bbox
        points, _ = _detect_refined_landmarks(rgb); smile = measure_smile(points)
        results[label] = {'identity_centroid': float(face.normed_embedding @ centroid),
                          'per_reference': [float(face.normed_embedding @ ref) for ref in embeddings],
                          'pose': face.pose.tolist(), 'mouth_opening_ratio': float(smile['opening_ratio']),
                          'mouth_corners': smile['corner_coordinates'].tolist(),
                          'eye_coordinates': [_eye_measurement(points, eye)['coordinate'].tolist() for eye in _EYES]}
    high_result = results['FLOW TEST']; raw_result = results['BASE RAW']; src_result = results['SOURCE']
    if calibration is not None:
        from experimental_upgrade_semantic_expression import expression_features, TOLERANCES
        high_features = expression_features(_detect_refined_landmarks(high)[0])
        raw_features = np.array(calibration['raw_features'])
        desired = raw_features + np.array(calibration['target_features'])-np.array(calibration['zero_features'])
        calibration['native_measured_features'] = high_features.tolist()
        calibration['native_measured_residual'] = float(np.linalg.norm((high_features-desired)/TOLERANCES))
    report.update({'mapping': mapping, 'zero_control': zero_guard, 'hair_exact': True, 'results': results,
                   'closed_lips': closed_lip_check(src_result['mouth_opening_ratio'], high_result['mouth_opening_ratio']),
                   'identity_delta_from_raw': high_result['identity_centroid'] - raw_result['identity_centroid'],
                   'source_pose_error_degrees': float(np.max(np.abs(np.array(high_result['pose']) - src_result['pose']))),
                   'source_eye_error': float(np.max(np.abs(np.array(high_result['eye_coordinates']) - src_result['eye_coordinates']))),
                   'output_sha256': digest(output / 'expression-flow.png'), 'seconds': time.perf_counter() - started})
    # Crops use each detected face with the same proportional margin, clearly labeled.
    def sheet(labels, filename, crop_faces=False, width=460):
        tiles = []
        for label in labels:
            tile = Image.fromarray(photos[label])
            if crop_faces:
                x0, y0, x1, y1 = face_boxes[label]; margin = (x1-x0)*.12
                tile = tile.crop((max(0, round(x0-margin)), max(0, round(y0-margin)),
                                  min(w, round(x1+margin)), min(h, round(y1+margin))))
            tile = tile.resize((width, round(tile.height * width / tile.width)), Image.Resampling.LANCZOS)
            tiles.append((label, tile))
        canvas = Image.new('RGB', (sum(t.width for _, t in tiles), max(t.height for _, t in tiles)+42), '#161616')
        draw = ImageDraw.Draw(canvas); x = 0
        for label, tile in tiles:
            canvas.paste(tile, (x, 42)); draw.text((x+10, 10), label, fill='white', font=ImageFont.load_default(size=18)); x += tile.width
        canvas.save(output / filename, quality=96)
    sheet(['SOURCE', 'LOW', 'FLOW TEST'], 'source-low-flow-face.jpg', True)
    sheet(['BASE RAW', 'FLOW TEST'], 'raw-flow-face.jpg', True, 580)
    sheet(['SOURCE', 'LOW', 'FLOW TEST'], 'source-low-flow-full.jpg')
    sheet(['SOURCE', 'LOW', 'FLOW TEST'], 'source-low-flow-thumbnail.jpg', False, 240)
    (output / 'audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('cycle', 'mapping', 'results', 'closed_lips', 'identity_delta_from_raw',
                                           'source_pose_error_degrees', 'source_eye_error', 'seconds')}, indent=2))


if __name__ == '__main__':
    main()
