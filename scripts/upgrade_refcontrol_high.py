"""Experimental author-trained Canny/self-reference High; no production imports."""
from __future__ import annotations

import copy
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from upgrade_dev_high import ROOT, COMFY, digest, read_json, image_name, DATASET_SHA

TEMPLATE = ROOT / 'work/9b-readiness-20260903/group-research/refcontrol-pilot-payload.json'
TEMPLATE_SHA = '12fc9e73b2e18ced988c5da37339ac5463f58d8525a3f928c90d36071436bf26'
AUTHOR = ROOT / 'work/9b-readiness-20260903/group-research/author-refcontrol-workflow.json'
AUTHOR_SHA = 'c71149905458fb3ce936317c6bd1d49b90104c9ff56238ebf47e192f2e26ed17'
ADAPTER = r'readiness-experiments\flux2_klein_9b_refcontrol_canny.safetensors'
PINS = {
    'diffusion_models/flux-2-klein-base-9b-bf16.safetensors': '4a54fad7f5f741b99eee217198daac20b8d8e515e2a1f5b064fd51cf074f95bd',
    'text_encoders/qwen_3_8b_fp8mixed.safetensors': 'abad16806e0cbabc54e0325d6565847443fe396d5f0be38bb3cd3fe75a1201d6',
    'vae/flux2-vae.safetensors': 'd64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5',
    'loras/' + ADAPTER: 'c816dcf61ee26c55a1abfb655ce424cf5db95afae995d6692b1090d37a979870',
}
PROMPT = '''refcontrol. Picture 1 supplies the original photograph's exact composition and facial contours: keep its head direction, forehead size, hairline, lean face outline, appealing eyelid and eyebrow shapes, pupil focus and relaxed asymmetric closed-lip smile. Picture 2 supplies the same man's recognizable identity, nose, eye color, clothing, body, lighting, scene colors and detailed photographic materials.

Create one visibly more handsome but realistic photograph of the same man from Picture 2, following Picture 1's contours closely. His lips touch continuously with every tooth covered. Keep his cheeks lean, with a natural defined cheekbone-to-jaw transition. Make his skin rested, evenly toned and lightly tanned: soften forehead and frown creases, remove freckles and dark dots while retaining fine irregular real pores and neat realistic stubble. Keep the existing hairstyle and hairline, with matte separate strands, soft natural clumps and subtle highlights.

Preserve the entire scene, body, clothing and framing. Retain the readable background material detail from Picture 2 with natural depth and coherent smartphone main-camera sharpness, gentle highlights and subtle sensor texture. One continuous real photograph; no waxy skin, painted hair, inflated cheeks, new teeth, changed head direction, artificial facial lighting or cutout edges.'''
PROMPTS = {'high':PROMPT, 'author-trigger-only':'refcontrol'}


def source_edges(rgb):
    """Same CPU operations/settings as author-used CannyDetector; no model/node import."""
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError('Expected uint8 RGB source.')
    h, w = rgb.shape[:2]
    factor = 512 / min(h, w)
    width, height = round(w * factor), round(h * factor)
    resized = cv2.resize(rgb, (width, height), interpolation=cv2.INTER_CUBIC if factor > 1 else cv2.INTER_AREA)
    padded = np.pad(resized, ((0, -height % 64), (0, -width % 64), (0, 0)), mode='edge')
    edges = cv2.Canny(padded, 100, 200)[:height, :width]
    return np.repeat(edges[:, :, None], 3, axis=2).copy()


def read_rgb(path):
    with Image.open(path) as image:
        return np.array(ImageOps.exif_transpose(image).convert('RGB'))


def build_graph(references, seed, prefix, prompt_variant='high'):
    if prompt_variant not in PROMPTS:
        raise ValueError('Only the frozen High pilot and its sole author-trigger diagnostic are allowed.')
    if len(references) != 2 or digest(TEMPLATE) != TEMPLATE_SHA or digest(AUTHOR) != AUTHOR_SHA:
        raise ValueError('Require exact author-derived template and two ordered references.')
    graph = copy.deepcopy(read_json(TEMPLATE)['prompt'])
    graph['5']['inputs']['text'] = PROMPTS[prompt_variant]
    graph['10']['inputs']['image'] = references[0]['name']
    graph['20']['inputs']['image'] = references[1]['name']
    graph['33']['inputs']['noise_seed'] = seed
    graph['37']['inputs']['filename_prefix'] = prefix
    return graph


def validate_graph(manifest):
    if not (manifest['stage'] == 'refcontrol_native_high_edit'
            and manifest['synthetic_self_reference'] is True
            and manifest['phone_camera_style'] is False and manifest['upstream_phone_camera_style'] is True
            and manifest['phone_appearance_mode'] == 'inherited_klein_raw_no_stacked_adapter'
            and manifest['turbo'] is False and manifest['postprocess'] is False):
        raise ValueError('Incorrect RefControl or phone/identity provenance.')
    if manifest['prompt'] != build_graph(manifest['references'], manifest['seed'], manifest['output_prefix'], manifest.get('prompt_variant','high')):
        raise ValueError('Graph differs from bounded author-derived self-reference pilot.')
    if {r['model_relative_path']:r['sha256'] for r in manifest['verified_models']} != PINS:
        raise ValueError('Wrong model/adapter stack.')


def validate_inputs(manifest, source, baseline):
    validate_graph(manifest)
    for record in manifest['references']:
        if digest(record['path']) != record['sha256'] or image_name(record['path']) != record['name']:
            raise ValueError('Reference changed.')
    if not np.array_equal(source_edges(read_rgb(source)), read_rgb(manifest['references'][0]['path'])):
        raise ValueError('Control is not the original source full Canny with frozen settings.')
    if digest(baseline) != manifest['references'][1]['sha256']:
        raise ValueError('Synthetic self-reference must be the exact upstream raw.')
    audit_path = Path(manifest['source_audit'])
    audit = read_json(audit_path)
    if not (digest(audit_path) == manifest['source_audit_sha256']
            and audit['executed_png_graph_verified'] and not audit['postprocess_applied']
            and audit['inputs']['SOURCE']['sha256'] == digest(source)
            and audit['inputs']['BASE RAW']['sha256'] == digest(baseline)):
        raise ValueError('Original and raw are not the audited pair.')
    report_path = Path(manifest['baseline_report'])
    report = read_json(report_path)
    if not (digest(report_path) == manifest['baseline_report_sha256']
            and Path(baseline).resolve().parent == report_path.resolve().parent
            and report['phone_camera_style'] is True and report['turbo'] is False
            and report['lora_sha256'].lower() == 'd24907a84b8644a70c07611016a9d2ff8fad2d2c761a8f97b213ae1d36088eec'):
        raise ValueError('Upstream genuine-trained identity / PhoneON provenance is incomplete.')
    dataset_path = ROOT / 'datasets/mitch-identity-stills-v3/manifest.json'
    if digest(dataset_path) != DATASET_SHA:
        raise ValueError('Genuine evaluation dataset provenance changed.')
    for record in read_json(dataset_path)['records']:
        if record['kind'] != 'camera_still' or digest(record['dataset_file']) != record['dataset_sha256']:
            raise ValueError('Genuine dataset image changed.')
