"""Audit the completed public v5 house job against its submission and CPU controls.

No generation, image modification, runtime restart or live-state mutation.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / 'ComfyUI'
RUN = ROOT / 'work/upgrade-source-faithful-20260903/v5-live-house-native'
JOB = '52348431-764b-407b-bc74-8da6c055ca66'
CPU = ROOT / 'work/upgrade-source-faithful-20260903/parsenet-v5-production-code-replay'
RAW = COMFY / 'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-111226-463056/before-polish_00001_.png'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with Image.open(path) as im:
        return np.array(ImageOps.exif_transpose(im).convert('RGB'))


def canonical(graph):
    return {key: {k: v for k, v in node.items() if k != 'is_changed'}
            for key, node in graph.items()}


def compare(actual, control):
    a, b = read(actual), read(control)
    if a.shape != b.shape:
        raise ValueError('Unexpected image dimensions.')
    delta = np.abs(a.astype(np.int16) - b.astype(np.int16))
    return {'exact_pixels': bool(np.array_equal(a, b)),
            'max_rgb_error': int(delta.max()), 'mean_rgb_error': float(delta.mean()),
            'actual_file_sha256': sha(actual), 'control_file_sha256': sha(control),
            'actual_decoded_sha256': hashlib.sha256(a.tobytes()).hexdigest(),
            'control_decoded_sha256': hashlib.sha256(b.tobytes()).hexdigest()}


def main():
    destination = RUN / 'output-audit.json'
    if destination.exists():
        raise ValueError('Preserve the existing audit.')
    validation = json.loads((RUN / 'validation.json').read_text())
    intent = json.loads((RUN / 'submission-intent.json').read_text())
    history = json.loads((RUN / 'terminal-history.json').read_text())[JOB]
    assert history['status']['completed'] and history['status']['status_str'] == 'success'
    assert history['prompt'][2] == intent['prompt']
    image_record = history['outputs']['2']['images'][0]
    actual = COMFY / 'output' / image_record['subfolder'] / image_record['filename']
    folder = actual.parent
    report = json.loads((folder / 'report.json').read_text())
    graph = json.loads((folder / 'prompt-api.json').read_text())
    assert canonical(graph) == canonical(intent['prompt'])
    with Image.open(actual) as im:
        info = dict(im.info)
    # The public custom node embeds its report, not SaveImage's ordinary prompt key.
    assert json.loads(info['flux2_klein9b_upgrade_photo_detail_realism_v1']) == report
    assert report['appearance_profile'].startswith('deterministic_face_and_hair_local_v5+')
    hair = report['appearance_report']['hair_material_correction']
    assert hair['parser_hair_class'] == 13 and hair['active_inner_hair_pixels'] > 0
    assert report['phone_camera_style'] and not report['turbo']
    assert report['appearance_level'] == 'low'
    assert report['steps'] == 50 and report['seed'] == 8675416
    assert report['cfg'] == 4.0 and report['sampler'] == 'euler'
    assert report['width'] == 1680 and report['height'] == 1008
    assert report['gpu'] == 'NVIDIA GeForce RTX 3090'
    assert not report['restoration'] and not report['upscaling']
    assert len(report['reference_order']) == 4
    fields = {'model': 'model', 'text_encoder': 'text_encoder', 'vae': 'vae',
              'lora': 'lora', 'identity_reference': 'identity', 'hair_reference': 'hair'}
    for field, key in fields.items():
        assert report[field + '_sha256'] == validation['hashes'][key]
    assert report['additional_loras'][0]['sha256'] == validation['hashes']['smartphone_style']
    assert hair['parser_model_sha256'] == validation['hashes']['hair_parser']
    source = COMFY / 'input' / intent['prompt']['1']['inputs']['image']
    assert sha(source).upper() == validation['hashes']['smoke_source']
    assert hashlib.sha256(read(source).tobytes()).hexdigest().upper() == report['source_decoded_pixel_sha256']
    assert sha(CPU / 'audit.json') == '1ed41ab5278b5a23a7e1837002be598007593b14c26ce2189866d0c666de72d7'
    assert sha(RAW) == 'b51f6e6e0ad0105afb00542aaa7ca619032efd44819279f578da7952c19a7673'
    assert sha(CPU / 'house/v5-low.png') == '85bb0e9a0c197fefa90177477625310aa1f88d12f87657d8af8f8e91c60a9246'
    comparisons = {'raw': compare(folder / 'before-polish_00001_.png', RAW),
                   'low': compare(actual, CPU / 'house/v5-low.png')}
    result = {'status': 'provenance_verified_pixel_comparison_complete', 'prompt_id': JOB,
              'actual_output': str(actual), 'report_sha256': sha(folder / 'report.json'),
              'executed_graph_matches_intent': True, 'png_report_matches_sidecar': True,
              'appearance_level': 'low',
              'phone_on': True, 'turbo_off': True, 'parser_hair_class': 13,
              'comparisons': comparisons, 'stronger_high_validated': False,
              'identity_score_reusable_only_if_low_pixels_exact': True}
    if comparisons['low']['exact_pixels']:
        result['same_pixel_low_identity'] = json.loads((CPU / 'audit.json').read_text())['results']['house']['v5']['low_identity']
    destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
