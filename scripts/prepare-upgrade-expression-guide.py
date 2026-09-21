"""Add sparse source expression contours to an existing guide; no face pixels copied.

Experimental native-reference conditioning, not a trained ControlNet. Identity is
still carried by the protected character LoRA and genuine portrait reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline-report', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Write experimental artifacts inside the project.')
    sys.path.insert(0, str(root / 'custom_nodes/ComfyUI-AIToolkit-Training'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
    from mediapipe.python.solutions import face_mesh_connections as connections

    baseline = json.loads(args.baseline_report.read_text(encoding='utf-8-sig'))
    guide_path = args.baseline_report.parent / 'structure-guide_00001_.png'
    source = np.array(ImageOps.exif_transpose(Image.open(args.source)).convert('RGB'))
    guide = np.array(Image.open(guide_path).convert('RGB'))
    if source.shape != guide.shape:
        raise ValueError('Source and existing guide must have identical full-frame dimensions.')
    points, version = _detect_refined_landmarks(source)
    lines = np.zeros(guide.shape[:2], np.uint8)
    thickness = max(1, round(min(guide.shape[:2]) / 512))
    groups = ('FACEMESH_LIPS', 'FACEMESH_LEFT_EYE', 'FACEMESH_RIGHT_EYE',
              'FACEMESH_LEFT_EYEBROW', 'FACEMESH_RIGHT_EYEBROW')
    for name in groups:
        for a, b in sorted(getattr(connections, name)):
            cv2.line(lines, tuple(np.rint(points[a]).astype(int)),
                     tuple(np.rint(points[b]).astype(int)), 255, thickness, cv2.LINE_AA)
    for center_id, ring_ids in ((468, (469,470,471,472)), (473, (474,475,476,477))):
        ring = points[list(ring_ids)]
        axes = np.maximum(1, np.rint(np.ptp(ring, axis=0) / 2)).astype(int)
        cv2.ellipse(lines, tuple(np.rint(points[center_id]).astype(int)), tuple(axes),
                    0, 0, 360, 255, thickness, cv2.LINE_AA)
    result = np.maximum(guide, lines[..., None])
    unchanged = lines == 0
    assert np.array_equal(result[unchanged], guide[unchanged])
    prompt = baseline['effective_prompt']
    old_options = (
        'Picture 2 is a face-interior-free edge guide made from Picture 1 and supplies geometry only.',
        'Picture 2 is a face-interior-free edge outline of Picture 1 and supplies geometry only.',
    )
    matching = [text for text in old_options if prompt.count(text) == 1]
    if len(matching) != 1:
        raise ValueError('Unsupported baseline role paragraph.')
    old = matching[0]
    new = ('Picture 2 is an edge guide made from Picture 1. Its sparse inner-face lines preserve '
           'only the source expression: the exact relaxed eyelid contours, iris focus, eyebrow '
           'angle, closed-lip curve and natural unequal smile corners. Keep these expression '
           'contours while rendering the identity of the man in Picture 3; do not substitute '
           'Picture 3\'s expression or force both smile corners upward. The guide supplies '
           'geometry, not skin texture or facial identity.')
    if prompt.count(old) != 1:
        raise ValueError('Unsupported baseline role paragraph.')
    prompt = prompt.replace(old, new)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / 'expression-guide.png'
    if target.exists():
        raise FileExistsError('Do not overwrite an earlier experiment.')
    Image.fromarray(result).save(target)
    (args.output_dir / 'prompt.txt').write_text(prompt, encoding='utf-8')
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    report = {
        'status': 'experimental_not_production', 'source': str(args.source.resolve()),
        'source_sha256': digest(args.source), 'base_guide': str(guide_path),
        'base_guide_sha256': digest(guide_path), 'expression_guide_sha256': digest(target),
        'mediapipe_version': version, 'connections': list(groups), 'iris_contours': True,
        'stroke_width': thickness, 'changed_pixels': int(np.any(result != guide, axis=2).sum()),
        'outside_expression_strokes_byte_exact': bool(np.array_equal(result[unchanged], guide[unchanged])),
        'source_face_pixels_copied': False, 'nose_jaw_shading_added': False,
        'conditioning': 'native ReferenceLatent at existing slot2 and resolution; not ControlNet',
        'identity': 'unchanged protected Base9B character LoRA0.9 and genuine portrait slot3',
    }
    (args.output_dir / 'provenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
