"""Frozen three-photo CPU composition evaluation; no production import or GPU queue."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
import psutil
import torch
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps

from experimental_upgrade_whole_face_shape import whole_face_shape
from upgrade_face_contour_diagnostic import FACE_OVAL

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
WORK=ROOT/'work/upgrade-source-faithful-20260903'
CASES={
    'house':('input/mitch-photo2-source-aef87048.png','aef8704873c40c92ec365c091ea142998e72b3d80d22b45f55275309165ba5b4',
        'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260904-020400-003998/before-polish_00001_.png',
        '4908d5a2399bf04a4708bcc8cba534ceaf952bf34d1b6cef6142f93082b720e2'),
    'canyon':('input/mitch-canyon-source-edit-05333f6f.png','05333f6fd60dab6629f34b616a3e1fea4771b997aa472675fcccd1f6a2535eef',
        'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-005704-305944/before-polish_00001_.png',
        'e20f79f0c8fdef060080bbe72e639dc59bb89d1ccf147e6b8b1523cf45d20a82'),
    'third':('input/mitch-upgrade-third-genuine-fef084d6.png','4c26b56e105daf8790ac108bf127f970522675ff39bd74cb9161724be34d4367',
        'output/upgrade-source-faithful/third-baseline-native/raw_00001_.png',
        '4d8d18101e2a417796a83c414bfed9368de7688b452db262b479f73831ca1b67')}
MODEL=COMFY/'models/facerestore_models/codeformer-v0.1.0.pth'
MODEL_SHA='1009e537e0c2a07d4cabce6355f53cb66767cd4b4297ec7a4a64ca4b8a5684b7'
TEMPLATE=np.array([[192.98138,239.94708],[318.90277,240.1936],[256.63416,314.01935],
                   [201.26117,371.41043],[313.08905,371.15118]],np.float32)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    with Image.open(path) as im:return np.array(ImageOps.exif_transpose(im).convert('RGB'))
def uint8(value):return np.rint(np.clip(value,0,1)*255).astype(np.uint8)
def tensor(rgb):return torch.from_numpy(rgb.astype(np.float32)/255).unsqueeze(0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=tuple(CASES),required=True)
    args=parser.parse_args();out=WORK/f'shape-restoration-policy-{args.case}'
    if out.exists():raise ValueError('Preserve this frozen case; no overwrite or parameter grid.')
    if psutil.virtual_memory().available<8*1024**3:raise ValueError('Insufficient shared RAM; no cache release.')
    source_name,source_hash,raw_name,raw_hash=CASES[args.case]
    source_path,raw_path=COMFY/source_name,COMFY/raw_name
    if sha(source_path)!=source_hash or sha(raw_path)!=raw_hash or sha(MODEL)!=MODEL_SHA:
        raise ValueError('Pinned source/raw/restoration model changed.')
    proof=WORK/'whole-face-shape-house-feature-cage/audit.json'
    if sha(proof)!='118b5ab9850c70bf1f62ae6c6c8cec93e1bcb8878d05b38e69e6d435b3303791':
        raise ValueError('Reviewed policy parent changed.')
    refs=json.loads(proof.read_text())['genuine_references']
    if args.case=='third':
        refs=[r for r in refs if r['sha256']!='fef084d60982754250ab76a7320d71228c96255b2d5244b7461f77b67ce929cf']
    for ref in refs:
        if sha(ref['path'])!=ref['sha256']:raise ValueError('Changed genuine evaluation photograph.')
    local=Path.home()/'.insightface/models/antelopev2'
    if not all((local/f).is_file() for f in ('scrfd_10g_bnkps.onnx','glintr100.onnx','1k3d68.onnx')):
        raise ValueError('Existing scoring models missing; downloads prohibited.')
    sys.path.insert(0,str(COMFY));sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0,str(COMFY/'custom_nodes/ComfyUI-ReActor'))
    import flux2_klein9b_deterministic_polish as common
    import flux2_klein9b_source_gaze_lock as gaze
    from experimental_upgrade_smile_balance import measure_smile
    from r_facelib.utils.face_restoration_helper import FaceRestoreHelper
    from scripts.r_archs.codeformer_arch import CodeFormer
    if sha(Path(common.__file__))!='3f37fd5632d4ae1236314df795aaddbf73fa55ef74cae2bab62c7359a5778676':
        raise ValueError('Low baseline implementation changed.')
    torch.set_num_threads(4);cv2.setNumThreads(4)
    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
        providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found=analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(found)!=1:raise ValueError('Exactly one detected face required.')
        return found[0]
    photos={'SOURCE':read(source_path),'RAW':read(raw_path)}
    if photos['SOURCE'].shape!=photos['RAW'].shape:raise ValueError('This fixed comparison expects same source/raw dimensions.')
    points={name:gaze._detect_refined_landmarks(rgb)[0] for name,rgb in photos.items()}
    detected=face(photos['RAW']);hair=common.build_semantic_hair_mask(photos['RAW'],detected.bbox)
    provenance={'case':args.case,'inputs':{'SOURCE':{'path':str(source_path),'sha256':source_hash},
        'RAW':{'path':str(raw_path),'sha256':raw_hash}},'genuine_references':refs,
        'third_uses_four_reference_baseline_not_source_only_parent':args.case=='third',
        'source_original_excluded_from_genuine_scoring':args.case=='third',
        'raw_provenance_scope':'Previously audited immutable native raw files; no new generation or independent expanded graph execution claimed.',
        'policy':'raw -> source geometry0.8/115-control cage -> source gaze -> CodeFormer0.7/512/ParseNet1x -> final source gaze',
        'low_policy':'same raw -> current Low v5 -> source gaze; CPU replay, not a new live-node output',
        'shape_policy_parent_sha256':sha(proof),'model_sha256':MODEL_SHA,'runner_sha256':sha(__file__),
        'shape_module_sha256':sha(Path(__file__).with_name('experimental_upgrade_whole_face_shape.py')),
        'phone_camera_style':True,'turbo':False,'new_diffusion_runs':0,'production_changed':False,
        'no_source_rgb_copied':True,'device':'cpu','beauty_or_identity_lock_claimed':False}
    out.mkdir(parents=True);(out/'intent.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    started=time.perf_counter()
    low,_,low_report=common.apply_deterministic_face_polish(tensor(photos['RAW']),detected.bbox,detected.kps,hair)
    low,_,low_gaze=gaze.apply_source_gaze_lock(tensor(photos['SOURCE']),low)
    photos['LOW (CPU)']=uint8(low[0].numpy());Image.fromarray(photos['LOW (CPU)']).save(out/'low.png')
    try:
        shaped,support,shape_report=whole_face_shape(photos['RAW']/255,points['RAW'],points['SOURCE'],hair,.8,'feature_cage')
        shaped,_,initial_gaze=gaze.apply_source_gaze_lock(tensor(photos['SOURCE']),torch.from_numpy(shaped).unsqueeze(0))
        photos['SHAPE']=uint8(shaped[0].numpy());Image.fromarray(photos['SHAPE']).save(out/'shape.png')
        found=face(photos['SHAPE'])
        affine,_=cv2.estimateAffinePartial2D(found.kps,TEMPLATE,method=cv2.LMEDS)
        if affine is None or not np.isfinite(affine).all():raise ValueError('Invalid FFHQ alignment.')
        aligned=cv2.warpAffine(photos['SHAPE'],affine,(512,512),flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,borderValue=(135,133,132))
        Image.fromarray(aligned).save(out/'aligned-input.png')
        model=CodeFormer(dim_embd=512,codebook_size=1024,n_head=8,n_layers=9,connect_list=['32','64','128','256']).cpu()
        checkpoint=torch.load(MODEL,map_location='cpu',weights_only=True)
        model.load_state_dict(checkpoint['params_ema'],strict=True);del checkpoint;model.eval()
        value=tensor(aligned).permute(0,3,1,2).sub(.5).div(.5)
        with torch.inference_mode():restored=model(value,w=.7,adain=True)[0]
        restored=uint8(restored[0].clamp(-1,1).add(1).div(2).permute(1,2,0).numpy());del model
        Image.fromarray(restored).save(out/'restored-crop.png')
        helper=FaceRestoreHelper.__new__(FaceRestoreHelper)
        helper.input_img=cv2.cvtColor(photos['SHAPE'],cv2.COLOR_RGB2BGR)
        helper.face_size=(512,512);helper.upscale_factor=1;helper.use_parse=True
        helper.device=torch.device('cpu');helper.face_parse=common._hair_parser()
        helper.affine_matrices=[affine];helper.inverse_affine_matrices=[]
        helper.restored_faces=[cv2.cvtColor(restored,cv2.COLOR_RGB2BGR)]
        helper.get_inverse_affine(None)
        photos['RESTORED']=cv2.cvtColor(helper.paste_faces_to_input_image(),cv2.COLOR_BGR2RGB)
        Image.fromarray(photos['RESTORED']).save(out/'restored-before-final-gaze.png')
        final,_,final_gaze=gaze.apply_source_gaze_lock(tensor(photos['SOURCE']),tensor(photos['RESTORED']))
        photos['CANDIDATE']=uint8(final[0].numpy());Image.fromarray(photos['CANDIDATE']).save(out/'candidate.png')
    except Exception as exc:
        (out/'failure.json').write_text(json.dumps({**provenance,'error':str(exc),'low_completed':True},indent=2),encoding='utf-8')
        raise
    vectors=[face(read(ref['path'])).normed_embedding for ref in refs]
    centroid=np.mean(vectors,axis=0);centroid/=np.linalg.norm(centroid)
    # Secondary strict diagnostic omits val05, whose hair-only crop conditions
    # native generation. Keep historical all-face-reference scores separate.
    strict_vectors=[v for ref,v in zip(refs,vectors) if 'val_05_' not in Path(ref['path']).name]
    strict_centroid=np.mean(strict_vectors,axis=0);strict_centroid/=np.linalg.norm(strict_centroid)
    results={};detections={}
    for name,rgb in photos.items():
        f=face(rgb);detections[name]=f;p=gaze._detect_refined_landmarks(rgb)[0];points[name]=p
        results[name]={'identity_centroid':float(f.normed_embedding@centroid),
            'strict_no_source_or_hair_photo_centroid':float(f.normed_embedding@strict_centroid),
            'pose_pitch_yaw_roll':f.pose.tolist(),'mouth_opening_ratio':float(measure_smile(p)['opening_ratio']),
            'eye_coordinates':[gaze._eye_measurement(p,e)['coordinate'].tolist() for e in gaze._EYES]}
    head=(hair>0).astype(np.uint8)
    for p in (points['RAW'],points['CANDIDATE']):cv2.fillPoly(head,[np.rint(p[list(FACE_OVAL)]).astype(np.int32)],1)
    exterior=cv2.distanceTransform(1-head,cv2.DIST_L2,5)>64
    delta=np.abs(photos['CANDIDATE'].astype(np.int16)-photos['RAW'].astype(np.int16))
    report={**provenance,'status':'three_case_policy_component_evaluated_not_promoted','results':results,
        'shape':shape_report,'low':low_report,'low_gaze':low_gaze,'initial_gaze':initial_gaze,'final_gaze':final_gaze,
        'affine':affine.tolist(),'strict_reference_count':len(strict_vectors),
        'exterior_head64_max_rgb_error':int(delta[exterior].max(initial=0)),
        'exterior_head64_mean_rgb_error':float(delta[exterior].mean()),
        'source_pose_delta_degrees':float(np.abs(detections['CANDIDATE'].pose-detections['SOURCE'].pose).max()),
        'candidate_sha256':sha(out/'candidate.png'),'seconds':time.perf_counter()-started,
        'limitation':'Pixel texture restoration and2D source-shape transfer, not trained beauty conditioning or identity lock. Visual review required; no public integration.'}
    if args.case=='house':
        earlier=WORK/'shape-codeformer-house-full-frame/full-frame.png'
        if sha(earlier)!='3050cafabbe0963c178685cdd9a5ded1b6da4754da6221d444c65f5fbb65e40d':
            raise ValueError('Earlier house composition bytes changed.')
        report['house_replay_before_final_gaze_max_rgb_error']=int(np.abs(photos['RESTORED'].astype(np.int16)-read(earlier).astype(np.int16)).max())
    for crop,filename in ((True,'source-low-candidate-face.jpg'),(False,'source-low-candidate-full.jpg')):
        tiles=[]
        for name in ('SOURCE','LOW (CPU)','CANDIDATE'):
            im=Image.fromarray(photos[name])
            if crop:
                box=detections[name].bbox;pad=(box[2]-box[0])*.15
                im=im.crop(tuple(np.rint(box+[-pad,-pad,pad,pad]).astype(int)))
                im=im.resize((round(im.width*460/im.height),460),Image.Resampling.LANCZOS)
            else:im.thumbnail((430,650),Image.Resampling.LANCZOS)
            tiles.append((name,im))
        sheet=Image.new('RGB',(sum(im.width for _,im in tiles),max(im.height for _,im in tiles)+36),(20,20,20))
        draw=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=16);x=0
        for name,im in tiles:sheet.paste(im,(x,36));draw.text((x+5,7),name,font=font,fill='white');x+=im.width
        sheet.save(out/filename,quality=97)
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('case','results','source_pose_delta_degrees','exterior_head64_max_rgb_error','seconds')},indent=2))


if __name__=='__main__':main()
