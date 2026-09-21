"""Experimental native Dev High graph; never imported by production nodes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / 'ComfyUI'
MODEL = 'flux2_dev_fp8mixed.safetensors'
CLIP = 'mistral_3_small_flux2_fp4_mixed.safetensors'
VAE = 'flux2-vae.safetensors'
LORA = r'flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors'
PINS = {
    'diffusion_models/' + MODEL: '863a82e4ff950a42a6b0e80bea824828f129eb1a8fbbdbd9e8cb29859127b486',
    'text_encoders/' + CLIP: '1ee1ff334d78228d73049ef0ee4fcd21c1700536b5a45c06547af057f92463a7',
    'vae/' + VAE: 'd64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5',
    'loras/' + LORA: '7c0c4f1726189c51e19c8392c12fe3e03a26bd084fffb8d84b907c966a77cc3e',
}
DATASET_SHA = 'd56fe2d752febfa63ca0e76689dfd9d4eaac7443ca086ffa9dfef51186563003'
PROMPT = '''Retouch Picture 1 into a visibly more handsome, natural photograph of m1tch_person, the same adult man. Keep Picture 1's complete scene, clothing, body, framing, lighting and detailed background.

Picture 2 is the original expression and pose reference. Preserve its head direction, head size, forehead proportions and hairline, and the exact direction in which his pupils look. Bring back its appealing eye shape, clean naturally defined eyebrows, relaxed brow and confident asymmetric closed-lip smile. The lips touch continuously, covering every tooth. Keep recognizable m1tch_person facial identity, his distinctive nose, eye color and chin, with lean cheeks and a clean natural cheekbone-to-jaw transition.

Make the face noticeably more rested and attractive: clear evenly toned lightly tanned skin, greatly softened forehead and frown creases, no freckles or dark speckles, fine irregular natural pores and tidy realistic stubble. His cheeks remain lean, never inflated. Give the existing hairstyle natural separate strands, softly varied clumps and subtle sunlit highlights, keeping the original hairline and forehead size.

One coherent realistic smartphone main-camera photograph. Keep the background's readable material detail and natural depth, gentle highlights, subtle sensor texture and consistent photographic sharpness across the whole frame. Avoid waxy skin, painted hair, sharpened pore dots, artificial facial lighting, a beauty-filter look, a different head angle or a toothy smile.'''


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def image_name(path):
    path = Path(path).resolve(strict=True)
    for kind in ('input', 'output'):
        parent = (COMFY / kind).resolve()
        if path.is_relative_to(parent):
            return str(path.relative_to(parent)) + f' [{kind}]'
    raise ValueError('Reference must already exist in local Comfy input/output.')


def build_graph(references, seed, prefix, strength=1.1):
    if len(references) != 2 or strength not in (1.1, 0.8):
        raise ValueError('This bounded pilot requires two ordered references and identity1.1 or its sole0.8 refinement.')
    def node(kind, **inputs):
        return {'class_type': kind, 'inputs': inputs}
    graph = {
        '1': node('UNETLoader', unet_name=MODEL, weight_dtype='default'),
        '2': node('LoraLoaderModelOnly', model=['1', 0], lora_name=LORA, strength_model=strength),
        '4': node('CLIPLoader', clip_name=CLIP, type='flux2', device='default'),
        '5': node('VAELoader', vae_name=VAE),
        '6': node('CLIPTextEncode', clip=['4', 0], text=PROMPT),
        '7': node('FluxGuidance', conditioning=['6', 0], guidance=4.0),
    }
    previous = '7'
    for index, ref in enumerate(references):
        load, scale, encode, condition = (str(100 + index * 10 + k) for k in range(4))
        graph[load] = node('LoadImage', image=ref['name'])
        graph[scale] = node('ImageScaleToTotalPixels', image=[load, 0], upscale_method='bicubic', megapixels=1.0, resolution_steps=16)
        graph[encode] = node('VAEEncode', pixels=[scale, 0], vae=['5', 0])
        graph[condition] = node('ReferenceLatent', conditioning=[previous, 0], latent=[encode, 0])
        previous = condition
    graph.update({
        '40': node('GetImageSize', image=['101', 0]),
        '20': node('RandomNoise', noise_seed=seed),
        '21': node('BasicGuider', model=['2', 0], conditioning=[previous, 0]),
        '22': node('KSamplerSelect', sampler_name='euler'),
        '23': node('Flux2Scheduler', steps=28, width=['40', 0], height=['40', 1]),
        '24': node('EmptyFlux2LatentImage', width=['40', 0], height=['40', 1], batch_size=1),
        '25': node('SamplerCustomAdvanced', noise=['20', 0], guider=['21', 0], sampler=['22', 0], sigmas=['23', 0], latent_image=['24', 0]),
        '26': node('VAEDecode', samples=['25', 0], vae=['5', 0]),
        '27': node('SaveImage', images=['26', 0], filename_prefix=prefix),
    })
    return graph


def validate_graph(manifest):
    if not (manifest['stage'] == 'dev_native_high_edit' and manifest['postprocess'] is False
            and manifest['turbo'] is False and manifest['phone_camera_style'] is False
            and manifest['upstream_phone_camera_style'] is True
            and manifest['phone_appearance_mode'] == 'inherited_klein_raw_not_active_dev_adapter'
            and manifest['effective_prompt'] == PROMPT):
        raise ValueError('Unsupported Dev experiment or misleading phone/Turbo provenance.')
    expected = build_graph(manifest['references'], manifest['seed'], manifest['output_prefix'], manifest['identity_strength'])
    if manifest['prompt'] != expected:
        raise ValueError('Dev graph differs from the bounded author-derived pilot.')
    actual = {x['model_relative_path']: x['sha256'].lower() for x in manifest['verified_models']}
    if actual != PINS:
        raise ValueError('Dev model set differs from the protected compatible weights.')


def validate_inputs(manifest, original, baseline):
    validate_graph(manifest)
    for ref in manifest['references']:
        if digest(ref['path']) != ref['sha256'] or image_name(ref['path']) != ref['name']:
            raise ValueError('Native reference changed.')
    first, second = manifest['references']
    if digest(baseline) != first['sha256'] or digest(original) != second['sha256']:
        raise ValueError('Expected exact audited raw target followed by original expression reference.')
    audit_path = Path(manifest['source_audit'])
    if digest(audit_path) != manifest['source_audit_sha256']:
        raise ValueError('Source audit changed.')
    audit = read_json(audit_path)
    if not (audit['executed_png_graph_verified'] and not audit['postprocess_applied']
            and audit['inputs']['BASE RAW']['sha256'] == first['sha256']
            and audit['inputs']['SOURCE']['sha256'] == second['sha256']):
        raise ValueError('Source and baseline do not belong to the same recorded evaluation.')
    report_path = Path(manifest['baseline_report'])
    report = read_json(report_path)
    if not (digest(report_path) == manifest['baseline_report_sha256']
            and Path(baseline).resolve().parent == report_path.resolve().parent
            and report['phone_camera_style'] is True and report['turbo'] is False):
        raise ValueError('No verified PhoneON/TurboOFF upstream target.')
    dataset_path = ROOT / 'datasets/mitch-identity-stills-v3/manifest.json'
    if digest(dataset_path) != DATASET_SHA:
        raise ValueError('Genuine training provenance changed.')
    records = read_json(dataset_path)['records']
    if sum(r['split'] == 'train' for r in records) != 13:
        raise ValueError('Expected the genuine thirteen-photo training dataset.')
    for record in records:
        if record['kind'] != 'camera_still' or digest(record['dataset_file']) != record['dataset_sha256']:
            raise ValueError('Genuine identity dataset changed.')
