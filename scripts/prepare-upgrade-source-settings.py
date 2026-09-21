"""Prepare existing four-reference recipe for a new genuine validation photograph.

This creates settings and a structural guide, not a generation result/report.
The live runner independently verifies model hashes, API nodes and GPU state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--template-report', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--detail', required=True)
    parser.add_argument('--seed', type=int, default=8675412)
    parser.add_argument('--comfy-root', type=Path, default=Path(r'C:\projects\AI-Tools\ComfyUI'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Prepared artifacts must stay in the workspace.')
    if args.output_dir.exists():
        raise FileExistsError('Do not overwrite earlier preparation.')
    sys.path.insert(0, str(root / 'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0, str(args.comfy_root))
    from flux2_klein9b_photo_realism_upgrade_presets import (
        compose_upgrade_prompt, compute_output_dimensions, face_interior_rectangle,
    )
    from flux2_klein9b_smartphone_style import apply_smartphone_style_trigger
    from experimental_upgrade_high_prompt import make_high_prompt
    baseline = json.loads(args.template_report.read_text(encoding='utf-8-sig'))
    source = np.array(ImageOps.exif_transpose(Image.open(args.source)).convert('RGB'))
    height, width = source.shape[:2]
    out_width, out_height = compute_output_dimensions(width, height)
    if (width, height) != (out_width, out_height):
        raise ValueError('Prepare a full-frame source at supported dimensions first.')
    analyzer = FaceAnalysis(name='antelopev2', root=str(Path.home() / '.insightface'),
                            providers=['CPUExecutionProvider'], allowed_modules=['detection'])
    analyzer.prepare(ctx_id=-1, det_size=(640,640))
    faces = analyzer.get(cv2.cvtColor(source, cv2.COLOR_RGB2BGR))
    if len(faces) != 1:
        raise ValueError('Exactly one genuine subject is required for validation.')
    gray = cv2.GaussianBlur(cv2.cvtColor(source, cv2.COLOR_RGB2GRAY), (5,5), 1.0)
    edges = cv2.Canny(gray, round(0.20*255), round(0.60*255))
    interior = face_interior_rectangle(faces[0].bbox, width, height)
    cv2.rectangle(edges, interior[:2], interior[2:], 0, thickness=-1)
    keys = ('model', 'model_path', 'model_sha256', 'text_encoder', 'text_encoder_path',
            'text_encoder_sha256', 'vae', 'vae_path', 'vae_sha256', 'lora', 'lora_path',
            'lora_sha256', 'phone_camera_style_path', 'additional_loras', 'identity_reference',
            'identity_reference_path', 'hair_reference', 'hair_reference_path')
    settings = {key: baseline[key] for key in keys}
    prompt = apply_smartphone_style_trigger(compose_upgrade_prompt(args.detail))
    settings.update({
        'status': 'prepared_settings_not_generated', 'template_report': str(args.template_report),
        'source_path': str(args.source.resolve()),
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'width': width, 'height': height, 'seed': args.seed, 'steps': 50, 'cfg': 4,
        'turbo': False, 'phone_camera_style': True, 'effective_prompt': prompt,
        'detail_instructions': args.detail, 'guide': {
            'source_size': [width,height], 'detected_face_count': 1,
            'selected_face_bbox': [float(v) for v in faces[0].bbox],
            'cleared_face_interior_rectangle': list(interior), 'canny_low': .2, 'canny_high': .6,
            'role': 'geometry only; face interior removed',
        },
    })
    args.output_dir.mkdir(parents=True)
    Image.fromarray(cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)).save(
        args.output_dir / 'structure-guide_00001_.png')
    (args.output_dir / 'settings.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    (args.output_dir / 'high-prompt.txt').write_text(make_high_prompt(prompt), encoding='utf-8')
    print(json.dumps({'status': settings['status'], 'width': width, 'height': height,
                      'source_sha256': settings['source_sha256'], 'output': str(args.output_dir)}, indent=2))


if __name__ == '__main__':
    main()
