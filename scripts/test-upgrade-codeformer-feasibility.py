"""One CPU-only installed-CodeFormer aligned preview; no full-frame composite."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import psutil
import torch
from insightface.app import FaceAnalysis

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
MODEL=COMFY/'models/facerestore_models/codeformer-v0.1.0.pth'
MODEL_SHA='1009e537e0c2a07d4cabce6355f53cb66767cd4b4297ec7a4a64ca4b8a5684b7'
AUDIT=ROOT/'work/upgrade-source-faithful-20260903/parsenet-v5-production-code-replay/audit.json'
AUDIT_SHA='1ed41ab5278b5a23a7e1837002be598007593b14c26ce2189866d0c666de72d7'
TEMPLATE=np.array([[192.98138,239.94708],[318.90277,240.1936],[256.63416,314.01935],
                   [201.26117,371.41043],[313.08905,371.15118]],np.float32)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    with Image.open(path) as im:return np.array(ImageOps.exif_transpose(im).convert('RGB'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--fidelity',type=float,choices=(.7,.4),default=.7,
                        help='0.7 baseline or the sole 0.4 quality-biased refinement; not a weight sweep.')
    parser.add_argument('--input-stage',choices=('low','raw','shape'),default='low',
                        help='Raw freezes Low alignment; shape tests the saved safe whole-face geometry. Both freeze fidelity0.7.')
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):raise ValueError('Use a fresh project work directory.')
    if psutil.virtual_memory().available<8*1024**3:raise RuntimeError('Preserve shared host memory.')
    if digest(MODEL)!=MODEL_SHA or digest(AUDIT)!=AUDIT_SHA:raise ValueError('Model or Low provenance changed.')
    audit=json.loads(AUDIT.read_text());input_path=AUDIT.parent/'house/v5-low.png'
    if digest(input_path)!=audit['results']['house']['v5']['low_sha256']:raise ValueError('Verified Low pixels changed.')
    alignment_control=None
    shape_audit_path=None
    if args.input_stage=='raw':
        if args.fidelity!=.7:raise ValueError('Input-stage ablation freezes fidelity at 0.7.')
        control_path=AUDIT.parent.parent/'codeformer-house-aligned-feasibility/audit.json'
        if digest(control_path)!='252632907c884a6d9c942ce30673c54da5468dd85da3c0e2245d6cabfd8c26d0':
            raise ValueError('Baseline alignment changed.')
        alignment_control=json.loads(control_path.read_text())
        input_path=COMFY/'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-111226-463056/before-polish_00001_.png'
        if digest(input_path)!='b51f6e6e0ad0105afb00542aaa7ca619032efd44819279f578da7952c19a7673':
            raise ValueError('Native raw pixels changed.')
    if args.input_stage=='shape':
        if args.fidelity!=.7:raise ValueError('Composition test freezes fidelity at0.7; no new weight sweep.')
        shape_audit_path=ROOT/'work/upgrade-source-faithful-20260903/whole-face-shape-house-feature-cage/audit.json'
        if digest(shape_audit_path)!='118b5ab9850c70bf1f62ae6c6c8cec93e1bcb8878d05b38e69e6d435b3303791':
            raise ValueError('Reviewed shape provenance changed.')
        shape_audit=json.loads(shape_audit_path.read_text())
        input_path=shape_audit_path.parent/'candidate.png'
        if digest(input_path)!=shape_audit['output_sha256'] or shape_audit['geometry']['minimum_inverse_jacobian']<.20:
            raise ValueError('Expected the reviewed safe shape output.')
        if shape_audit.get('common_finish_applied_equally_to_control_and_candidate'):
            raise ValueError('Do not stack previous common cleanup into this shape/restoration test.')
    genuine_audit=json.loads((ROOT/'work/upgrade-source-faithful-20260903/parsenet-label-exact-repair-audit/audit.json').read_text())
    refs=genuine_audit['genuine_refs']
    for ref in refs:
        if digest(ref['path'])!=ref['sha256']:raise ValueError('Genuine scoring reference changed.')
    local_models=Path.home()/'.insightface/models/antelopev2'
    if not all((local_models/name).is_file() for name in ('scrfd_10g_bnkps.onnx','glintr100.onnx','1k3d68.onnx')):
        raise ValueError('Required local scoring models missing; no downloads authorized.')
    torch.set_num_threads(4)
    app=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),providers=['CPUExecutionProvider'],
                     allowed_modules=['detection','recognition','landmark_3d_68'])
    app.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found=app.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(found)!=1:raise ValueError('Expected exactly one face.')
        return found[0]
    rgb=read(input_path);detected=face(rgb)
    if alignment_control:
        transform=np.array(alignment_control['affine'])
    else:
        transform,_=cv2.estimateAffinePartial2D(detected.kps,TEMPLATE,method=cv2.LMEDS)
    if transform is None or not np.isfinite(transform).all():raise ValueError('Invalid FFHQ alignment.')
    aligned=cv2.warpAffine(rgb,transform,(512,512),flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT,borderValue=(135,133,132))
    reactor=COMFY/'custom_nodes/ComfyUI-ReActor'
    sys.path.insert(0,str(reactor))
    from scripts.r_archs.codeformer_arch import CodeFormer
    model=CodeFormer(dim_embd=512,codebook_size=1024,n_head=8,n_layers=9,
                     connect_list=['32','64','128','256']).cpu()
    checkpoint=torch.load(MODEL,map_location='cpu',weights_only=True)
    model.load_state_dict(checkpoint['params_ema'],strict=True);del checkpoint
    model.eval()
    value=torch.from_numpy(aligned.transpose(2,0,1).copy()).float().div(255).sub(.5).div(.5).unsqueeze(0)
    started=time.perf_counter()
    with torch.inference_mode():output=model(value,w=args.fidelity,adain=True)[0]
    restored=np.rint(output.squeeze(0).clamp(-1,1).add(1).div(2).permute(1,2,0).numpy()*255).astype(np.uint8)
    elapsed=time.perf_counter()-started
    del model
    embeddings=[face(read(ref['path'])).normed_embedding for ref in refs]
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0,str(COMFY))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
    from experimental_upgrade_smile_balance import measure_smile
    # Preserve every inference result before diagnostics: a detector failure is
    # evidence to inspect, not a reason to lose the preview or change parameters.
    out.mkdir(parents=True)
    Image.fromarray(aligned).save(out/'aligned-input.png')
    Image.fromarray(restored).save(out/'restored-crop.png')
    results={}
    whole_label='whole_low' if args.input_stage=='low' else 'whole_input'
    for label,image in [(whole_label,rgb),('aligned_input',aligned),('restored_crop',restored)]:
        found=app.get(cv2.cvtColor(image,cv2.COLOR_RGB2BGR))
        if len(found)!=1:
            results[label]={'face_detection_count':len(found),'diagnostic_status':'not_scorable_as_single_face'}
            continue
        detected=found[0];points,_=_detect_refined_landmarks(image)
        smile=measure_smile(points)
        results[label]={'identity_centroid':float(detected.normed_embedding@centroid),
                        'pose_pitch_yaw_roll':detected.pose.tolist(),
                        'mouth_opening_ratio':float(smile['opening_ratio'])}
    sheet=Image.new('RGB',(1024,550),(20,20,20));draw=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=18)
    for x,title,image in [(0,f'ALIGNED {args.input_stage.upper()}',aligned),(512,f'CODEFORMER {args.fidelity} - PREVIEW',restored)]:
        sheet.paste(Image.fromarray(image),(x,38));draw.text((x+8,8),title,fill='white',font=font)
    sheet.save(out/'comparison.jpg',quality=97)
    thumb=sheet.copy();thumb.thumbnail((600,350),Image.Resampling.LANCZOS);thumb.save(out/'thumbnail.jpg',quality=95)
    report={'status':'aligned_feasibility_only_requires_visual_review','weight':args.fidelity,'adain':True,
            'input_stage':args.input_stage,
            'frozen_alignment_control_sha256':'252632907c884a6d9c942ce30673c54da5468dd85da3c0e2245d6cabfd8c26d0' if alignment_control else None,
            'refinement':('fixed0.7 composition with previously reviewed full-face shape; no new strength settings' if shape_audit_path else
                          ('input-stage ablation; no weight change' if alignment_control else ('sole lower-fidelity test' if args.fidelity==.4 else 'initial baseline'))),
            'device':'cpu','model_path':str(MODEL),'model_sha256':MODEL_SHA,'input':str(input_path),
            'input_sha256':digest(input_path),'parent_audit_sha256':AUDIT_SHA,
            'shape_parent_audit':str(shape_audit_path) if shape_audit_path else None,
            'shape_parent_audit_sha256':digest(shape_audit_path) if shape_audit_path else None,
            'architecture_sha256':digest(reactor/'scripts/r_archs/codeformer_arch.py'),
            'vqgan_architecture_sha256':digest(reactor/'scripts/r_archs/vqgan_arch.py'),
            'alignment':'frozen Low-baseline FFHQ512 affine for input-stage isolation' if alignment_control else 'author FFHQ512 five-point template; local SCRFD detector substitution',
            'affine':transform.tolist(),'template':TEMPLATE.tolist(),'genuine_references':refs,
            'results':results,'inference_seconds':elapsed,'full_frame_composite':False,
            'upscaler':False,'background_evaluated':False,'production_changed':False,
            'restored_sha256':digest(out/'restored-crop.png')}
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'results':results,'inference_seconds':elapsed,'output':str(out)},indent=2))


if __name__=='__main__':main()
