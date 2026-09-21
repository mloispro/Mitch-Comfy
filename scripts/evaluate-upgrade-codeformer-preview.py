"""Read-only geometry-aware scoring of the saved aligned feasibility images."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.utils.face_align import norm_crop
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    with Image.open(path) as im:return np.array(ImageOps.exif_transpose(im).convert('RGB'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--report-name',default='geometry-diagnostics-exif-corrected.json')
    args=parser.parse_args();run=args.run.resolve();output=run/args.report_name
    if output.parent!=run:raise ValueError('Report must remain in the preview directory.')
    if not run.is_relative_to(ROOT/'work') or output.exists():raise ValueError('Use an existing preview without prior diagnostics.')
    audit=json.loads((run/'audit.json').read_text())
    if sha(audit['input'])!=audit['input_sha256'] or sha(run/'restored-crop.png')!=audit['restored_sha256']:
        raise ValueError('Saved preview bytes changed.')
    app=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),providers=['CPUExecutionProvider'],
                     allowed_modules=['detection','recognition','landmark_3d_68'])
    app.prepare(ctx_id=-1,det_size=(640,640))
    def faces(rgb):return app.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
    refs=[]
    for ref in audit['genuine_references']:
        if sha(ref['path'])!=ref['sha256']:raise ValueError('Genuine reference changed.')
        found=faces(read(ref['path']))
        if len(found)!=1:raise ValueError('Reference detection changed.')
        refs.append(found[0].normed_embedding)
    centroid=np.mean(refs,axis=0);centroid/=np.linalg.norm(centroid)
    original=read(audit['input']);detected=faces(original)
    if len(detected)!=1:raise ValueError('Whole-frame control changed.')
    control_score=float(detected[0].normed_embedding@centroid)
    control_key='whole_input' if audit.get('input_stage')=='raw' else 'whole_low'
    if abs(control_score-audit['results'][control_key]['identity_centroid'])>1e-5:
        raise ValueError('Whole-frame identity control does not reproduce the frozen EXIF-aware score.')
    matrix=np.array(audit['affine'])
    points=np.column_stack((detected[0].kps,np.ones(5)))@matrix.T
    recognizer=app.models['recognition']
    sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0,str(ROOT.parent/'ComfyUI'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks, _eye_measurement, _EYES
    from experimental_upgrade_smile_balance import measure_smile
    results={}
    for name in ('aligned-input','restored-crop'):
        rgb=read(run/(name+'.png'))
        aligned=norm_crop(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),landmark=points,image_size=recognizer.input_size[0])
        vector=recognizer.get_feat(aligned).flatten();vector/=np.linalg.norm(vector)
        # Padding is diagnostic only: saved candidate pixels are never altered.
        padded=cv2.copyMakeBorder(rgb,128,128,128,128,cv2.BORDER_CONSTANT,value=(127,127,127))
        found=faces(padded)
        entry={'fixed_input_geometry_similarity':float(vector@centroid),
               'padded_detection_count':len(found),'image_sha256':sha(run/(name+'.png'))}
        if len(found)==1:
            entry.update(padded_redetected_similarity=float(found[0].normed_embedding@centroid),
                         padded_redetected_pose=found[0].pose.tolist())
        try:
            landmarks,_=_detect_refined_landmarks(padded)
            entry['mouth_opening_ratio']=float(measure_smile(landmarks)['opening_ratio'])
            entry['eye_coordinates']=[_eye_measurement(landmarks,eye)['coordinate'].tolist() for eye in _EYES]
        except Exception as exc:entry['landmark_diagnostic_error']=str(exc)
        results[name]=entry
    report={'status':'read_only_aligned_crop_diagnostics_not_full_frame_acceptance',
            'image_orientation':'EXIF-transposed RGB for every input including genuine references',
            'whole_frame_control_similarity':control_score,
            'genuine_references':audit['genuine_references'],
            'parent_audit_sha256':sha(run/'audit.json'),'fixed_geometry':points.tolist(),
            'results':results,'padding_pixels':128,'padding_for_detection_only':True,
            'limitation':'Fixed-geometry and padded-redetection scores are diagnostics, not an identity lock. Full-frame integration and source gaze have not been tested.'}
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
