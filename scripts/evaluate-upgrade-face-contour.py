"""Read-only outline diagnostic for a previously verified native/finished test."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageOps

from upgrade_face_contour_diagnostic import projected_contour, relative_width_change


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finish-audit',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.output.exists() or not args.output.resolve().is_relative_to(root):
        raise ValueError('Use a new output path within the project.')
    finish=json.loads(args.finish_audit.read_text(encoding='utf-8-sig'))
    native_path=root/finish['native_audit']
    if hashlib.sha256(native_path.read_bytes()).hexdigest()!=finish['native_audit_sha256']:
        raise ValueError('Native audit changed.')
    native=json.loads(native_path.read_text(encoding='utf-8-sig'))
    if not native['executed_png_graph_verified'] or native['postprocess_applied']:
        raise ValueError('Native provenance not verified.')
    sys.path.insert(0,str(root/'custom_nodes/ComfyUI-AIToolkit-Training'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
    records=dict(native['inputs'])
    role='base' if finish.get('candidate_role')=='source-fidelity' else 'high'
    records['FINISHED']={'path':str(args.finish_audit.parent/f'{role}-source-gaze.png')}
    if finish['common_polish_applied']:
        records['REVISED LOW']={'path':str(args.finish_audit.parent/'revised-low-source-gaze.png')}
    measurements={};hashes={}
    for label,record in records.items():
        path=root/record['path']
        hashes[label]=hashlib.sha256(path.read_bytes()).hexdigest()
        if record.get('sha256') and hashes[label]!=record['sha256']:
            raise ValueError(f'{label} changed since evaluation.')
        with Image.open(path) as image:
            rgb=np.array(ImageOps.exif_transpose(image).convert('RGB'))
        points,_=_detect_refined_landmarks(rgb)
        measurements[label]=projected_contour(points)
    result={'status':'diagnostic_only_not_acceptance','images':records,'sha256':hashes,
            'measurements':measurements,
            'finished_width_percent_change_from_source':relative_width_change(measurements['SOURCE'],measurements['FINISHED']),
            'finished_width_percent_change_from_raw':relative_width_change(measurements['BASE RAW'],measurements['FINISHED']),
            'source_pose_delta_degrees':finish['final_checks']['max_pose_delta_from_source_degrees'],
            'limitation':'No inferred cheek volume or attractiveness score. Shading can look puffy with unchanged outline; pose and eye spacing confound ratios. Visual review is required.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('images','sha256','measurements')},indent=2))


if __name__=='__main__':
    main()
