"""Assemble the saved restoration crop at1x and measure full-frame consequences."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import shutil
import cv2
import numpy as np
import torch
from PIL import Image,ImageDraw,ImageFont,ImageOps
from insightface.app import FaceAnalysis

ROOT=Path(__file__).resolve().parents[1];COMFY=ROOT.parent/'ComfyUI'
PREVIEW_SHA='252632907c884a6d9c942ce30673c54da5468dd85da3c0e2245d6cabfd8c26d0'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    with Image.open(path) as im:return np.array(ImageOps.exif_transpose(im).convert('RGB'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',type=Path,required=True)
    parser.add_argument('--preview-sha256',default=PREVIEW_SHA)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--rescore-from',type=Path,help='Read an existing saved pasteback; do not rerun restoration or fusion.')
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):raise ValueError('Use a fresh project work directory.')
    if sha(args.preview/'audit.json')!=args.preview_sha256.lower():raise ValueError('Unreviewed preview.')
    audit=json.loads((args.preview/'audit.json').read_text())
    preview_sha=sha(args.preview/'audit.json');weight=audit['weight'];label=f'RESTORED {weight}'
    input_label={'raw':'RAW INPUT','shape':'SHAPE INPUT','low':'LOW V5'}[audit.get('input_stage','low')]
    if sha(audit['input'])!=audit['input_sha256'] or sha(args.preview/'restored-crop.png')!=audit['restored_sha256']:
        raise ValueError('Preview bytes changed.')
    torch.set_num_threads(4)
    sys.path.insert(0,str(COMFY/'custom_nodes/ComfyUI-ReActor'))
    sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0,str(COMFY))
    from r_facelib.utils.face_restoration_helper import FaceRestoreHelper
    from flux2_klein9b_deterministic_polish import _hair_parser,build_semantic_hair_mask
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks,_eye_measurement,_EYES
    from flux2_klein9b_attractiveness import _OVAL
    from experimental_upgrade_smile_balance import measure_smile
    low=read(audit['input']);restored=read(args.preview/'restored-crop.png')
    if args.rescore_from:
        prior=json.loads((args.rescore_from/'audit.json').read_text())
        if prior['parent_preview_sha256']!=preview_sha or prior['input_sha256']!=audit['input_sha256']:
            raise ValueError('Saved full-frame provenance does not match this preview.')
        if sha(args.rescore_from/'full-frame.png')!=prior['output_sha256']:
            raise ValueError('Saved full-frame pixels changed.')
        output=read(args.rescore_from/'full-frame.png')
    else:
        helper=FaceRestoreHelper.__new__(FaceRestoreHelper)
        helper.input_img=cv2.cvtColor(low,cv2.COLOR_RGB2BGR)
        helper.face_size=(512,512);helper.upscale_factor=1;helper.use_parse=True
        helper.device=torch.device('cpu');helper.face_parse=_hair_parser()
        helper.affine_matrices=[np.array(audit['affine'])];helper.inverse_affine_matrices=[]
        helper.restored_faces=[cv2.cvtColor(restored,cv2.COLOR_RGB2BGR)]
        helper.get_inverse_affine(None)
        output=cv2.cvtColor(helper.paste_faces_to_input_image(),cv2.COLOR_BGR2RGB)
    if output.shape!=low.shape:raise ValueError('Unexpected whole-frame resize.')
    out.mkdir(parents=True)
    if args.rescore_from:shutil.copyfile(args.rescore_from/'full-frame.png',out/'full-frame.png')
    else:Image.fromarray(output).save(out/'full-frame.png')
    app=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),providers=['CPUExecutionProvider'],
                     allowed_modules=['detection','recognition','landmark_3d_68'])
    app.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found=app.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(found)!=1:raise ValueError('Expected one full-frame face.')
        return found[0]
    embeddings=[]
    for ref in audit['genuine_references']:
        if sha(ref['path'])!=ref['sha256']:raise ValueError('Genuine reference changed.')
        embeddings.append(face(read(ref['path'])).normed_embedding)
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    control_score=float(face(low).normed_embedding@centroid)
    control_key='whole_low' if audit.get('input_stage','low')=='low' else 'whole_input'
    if abs(control_score-audit['results'][control_key]['identity_centroid'])>1e-5:
        raise ValueError('Whole-frame identity control does not reproduce the frozen EXIF-aware score.')
    source_path=COMFY/'input/mitch-photo2-source-aef87048.png'
    if sha(source_path)!='aef8704873c40c92ec365c091ea142998e72b3d80d22b45f55275309165ba5b4':raise ValueError('Original source changed.')
    source=read(source_path);results={};landmarks={};detections={}
    for name,rgb in [('SOURCE',source),(input_label,low),(label,output)]:
        found=face(rgb);points,_=_detect_refined_landmarks(rgb);landmarks[name]=points;detections[name]=found
        results[name]={'identity_centroid':float(found.normed_embedding@centroid),
                       'pose_pitch_yaw_roll':found.pose.tolist(),
                       'mouth_opening_ratio':float(measure_smile(points)['opening_ratio']),
                       'eye_coordinates':[_eye_measurement(points,eye)['coordinate'].tolist() for eye in _EYES]}
    hair=build_semantic_hair_mask(low,detections[input_label].bbox)
    head=hair.copy();cv2.fillPoly(head,[np.rint(landmarks[input_label][list(_OVAL)]).astype(np.int32)],255)
    yy,xx=np.nonzero(head);cv2.fillConvexPoly(head,cv2.convexHull(np.column_stack((xx,yy)).astype(np.int32)),255)
    distance=cv2.distanceTransform((head==0).astype(np.uint8),cv2.DIST_L2,5)
    delta=np.abs(output.astype(np.int16)-low.astype(np.int16));outside=distance>64
    source_gaze=np.array(results['SOURCE']['eye_coordinates']);new_gaze=np.array(results[label]['eye_coordinates'])
    report={'status':'full_frame_feasibility_requires_visual_review','parent_preview_sha256':preview_sha,
            'image_orientation':'EXIF-transposed RGB for every input including genuine references',
            'input_stage':audit.get('input_stage','low'),
            'genuine_references':audit['genuine_references'],
            'rescore_only':bool(args.rescore_from),
            'prior_audit_sha256':sha(args.rescore_from/'audit.json') if args.rescore_from else None,
            'weight':weight,'new_neural_inference':False,'pasteback':'installed ReActor FaceRestoreHelper; ParseNet blend; scale1',
            'helper_sha256':sha(COMFY/'custom_nodes/ComfyUI-ReActor/r_facelib/utils/face_restoration_helper.py'),
            'source_sha256':sha(source_path),'input_sha256':audit['input_sha256'],'output_sha256':sha(out/'full-frame.png'),
            'results':results,'source_horizontal_eye_deltas':np.abs(source_gaze[:,0]-new_gaze[:,0]).tolist(),
            'outside_head_64px_max_rgb_error':int(delta[outside].max()),
            'outside_head_64px_mean_rgb_error':float(delta[outside].mean()),
            'outside_head_64px_changed_fraction':float(np.mean(np.any(delta[outside]>0,axis=1))),
            'full_frame_changed_fraction':float(np.mean(np.any(delta>0,axis=-1))),
            'final_gaze_correction':False,'upscaler':False,'production_changed':False}
    font=ImageFont.load_default(size=17)
    for crop,filename in [(False,'source-low-restored-full.jpg'),(True,'source-low-restored-face.jpg')]:
        tiles=[]
        for name,rgb in [('SOURCE',source),(input_label,low),(label,output)]:
            im=Image.fromarray(rgb)
            if crop:
                x1,y1,x2,y2=detections[name].bbox;pad=(x2-x1)*.12
                im=im.crop((max(0,int(x1-pad)),max(0,int(y1-pad)),min(im.width,int(x2+pad)),min(im.height,int(y2+pad))))
                im=im.resize((round(im.width*420/im.height),420),Image.Resampling.LANCZOS)
            else:im.thumbnail((600,720),Image.Resampling.LANCZOS)
            tiles.append((name,im))
        sheet=Image.new('RGB',(sum(im.width for _,im in tiles),max(im.height for _,im in tiles)+38),(20,20,20))
        draw=ImageDraw.Draw(sheet);x=0
        for name,im in tiles:sheet.paste(im,(x,38));draw.text((x+6,8),name,fill='white',font=font);x+=im.width
        sheet.save(out/filename,quality=96)
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
