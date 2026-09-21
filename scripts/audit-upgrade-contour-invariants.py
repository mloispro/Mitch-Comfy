"""Independent pixel checks on the frozen no-narrowing eye experiment."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
sys.path.insert(0,str(ROOT.parent/'ComfyUI'))
from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
from flux2_klein9b_attractiveness import _BROWS,_LIPS,_IRISES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT):
        raise ValueError('Use a new project-local output.')
    work=ROOT/'work/upgrade-source-faithful-20260903'
    results={}
    for photo in ('house','canyon','third'):
        folder=work/f'high-eye-contour-no-narrowing-{photo}'
        audit=json.loads((folder/'audit.json').read_text(encoding='utf-8-sig'))
        base_audit=json.loads(Path(audit['skin_baseline_audit']).read_text(encoding='utf-8-sig'))
        before_path=Path(base_audit['output']['path']);after_path=Path(audit['output']['path'])
        for path,expected in [(before_path,base_audit['output']['sha256']),(after_path,audit['output']['sha256'])]:
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected: raise ValueError('Recorded image changed.')
        before=np.array(Image.open(before_path).convert('RGB'))
        after=np.array(Image.open(after_path).convert('RGB'))
        before_gaze=np.array(Image.open(folder/'contour-before-gaze.png').convert('RGB'))
        support=np.array(Image.open(folder/'eye-contour-mask.png'))>0
        delta=np.abs(after.astype(np.int16)-before.astype(np.int16))
        points,_=_detect_refined_landmarks(before)
        guard=np.zeros(before.shape[:2],np.uint8)
        for ids in (*_BROWS,_LIPS):
            cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
        guard=cv2.dilate(guard,np.ones((3,3),np.uint8))
        pupil=np.zeros(before.shape[:2],bool)
        yy,xx=np.mgrid[:before.shape[0],:before.shape[1]]
        for ids in _IRISES:
            center=points[ids[0]]
            radius=max(1.,float(np.linalg.norm(points[list(ids[1:])]-center,axis=1).mean())*.32)
            pupil|=((xx-center[0])**2+(yy-center[1])**2)<=radius**2
        result={'outside_eye_edit_pixel_error_0_to_255':int(delta[~support].max(initial=0)),
            'brow_and_lip_pixel_error_0_to_255':int(delta[guard>0].max(initial=0)),
            'pre_gaze_pupil_core_pixel_error_0_to_255':int(np.abs(before_gaze.astype(np.int16)-before.astype(np.int16))[pupil].max(initial=0)),
            'gaze_max_horizontal_error':max(e['horizontal_error_after'] for e in audit['brow_edit']['eye_contour']['final_source_gaze']['eye_reports']),
            'base_audit_sha256':hashlib.sha256(Path(audit['skin_baseline_audit']).read_bytes()).hexdigest(),
            'candidate_audit_sha256':hashlib.sha256((folder/'audit.json').read_bytes()).hexdigest(),
            'production_changed':False,'beauty_acceptance':'not_established',
            'note':'Only the added eye-contour step is tested. Earlier base pose/expression/skin failures remain; no claim that full pipeline or vertical gaze is perfect.'}
        assert result['outside_eye_edit_pixel_error_0_to_255']==0
        assert result['brow_and_lip_pixel_error_0_to_255']==0
        assert result['pre_gaze_pupil_core_pixel_error_0_to_255']==0
        assert result['gaze_max_horizontal_error']<=.02
        results[photo]=result
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__=='__main__': main()
