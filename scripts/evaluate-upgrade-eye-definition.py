"""Replay audited revised Low, then test eye/brow photometry without geometry."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image,ImageDraw,ImageFont,ImageOps,PngImagePlugin
from insightface.app import FaceAnalysis

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
import flux2_klein9b_source_gaze_lock as gaze
import flux2_klein9b_deterministic_polish as common
from experimental_upgrade_eye_definition import apply_eye_definition,definition_profile,feature_regions
from experimental_upgrade_smile_balance import measure_smile
from upgrade_expression_acceptance import closed_lip_check,identity_retention_check


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component-audit',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--strength',type=float,choices=(1.,.65),default=1.)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):raise ValueError('Use a new project work directory.')
    parent=json.loads(args.component_audit.read_text(encoding='utf-8-sig'))
    if not parent.get('source_lid_component_only'):raise ValueError('Expected an audited common-polish/Low replay.')
    def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def read(path):
        with Image.open(path) as image:return np.array(ImageOps.exif_transpose(image).convert('RGB'))
    def read_record(record):
        path=ROOT/record['path']
        if sha(path)!=record['sha256']:raise ValueError('Audited input changed: '+str(path))
        return read(path)
    source=read_record(parent['input_records']['SOURCE'])
    raw=read_record(parent['candidate_input_record'])
    before_path=args.component_audit.parent/'before-lid-correction.png'
    before=read(before_path)
    if hashlib.sha256(before.tobytes()).hexdigest()!=parent['source_lid_curve']['before_sha256_pixels']:
        raise ValueError('Common-polish pixel provenance changed.')
    torch.set_num_threads(4)
    tensor=lambda image:torch.from_numpy(image.astype(np.float32)/255).unsqueeze(0)
    replay,_,gaze_report=gaze.apply_source_gaze_lock(tensor(source),tensor(before))
    low=np.rint(replay[0].numpy()*255).clip(0,255).astype(np.uint8)
    low_path=args.component_audit.parent/'revised-low-source-gaze.png'
    if not np.array_equal(low,read(low_path)):raise ValueError('Revised Low cannot be reproduced exactly.')
    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),providers=['CPUExecutionProvider'],
                          allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        faces=analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(faces)!=1:raise ValueError('Exactly one face required.')
        return faces[0]
    sys.path.insert(0,str(ROOT.parent/'ComfyUI'))
    low_face=face(low);points,_=gaze._detect_refined_landmarks(low)
    hair=common.build_semantic_hair_mask(low,low_face.bbox)
    candidate,mask,detail=apply_eye_definition(low.astype(np.float32)/255,points,hair,args.strength)
    high=np.rint(candidate*255).clip(0,255).astype(np.uint8)
    refs=parent['genuine_references']
    if len(refs)<2:raise ValueError('At least two independent genuine photographs required.')
    embeddings=[face(read_record(record)).normed_embedding for record in refs]
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    faces={'SOURCE':face(source),'RAW':face(raw),'LOW':low_face,'HIGH':face(high)}
    scores={key:float(value.normed_embedding@centroid) for key,value in faces.items()}
    if abs(scores['LOW']-parent['identity_centroid']['matched_revised_low'])>1e-5:
        raise ValueError('Revised Low diagnostic does not reproduce.')
    source_points,_=gaze._detect_refined_landmarks(source);after_points,_=gaze._detect_refined_landmarks(high)
    gaze_diagnostics=[]
    for definition in gaze._EYES:
        s=gaze._eye_measurement(source_points,definition);b=gaze._eye_measurement(points,definition);a=gaze._eye_measurement(after_points,definition)
        gaze_diagnostics.append({'eye':definition['name'],'source':s['coordinate'].tolist(),
                                 'before':b['coordinate'].tolist(),'after':a['coordinate'].tolist(),
                                 'horizontal_delta_from_low':float(abs(a['coordinate'][0]-b['coordinate'][0])),
                                 'horizontal_source_error':float(abs(a['coordinate'][0]-s['coordinate'][0]))})
    region_mask=mask>0
    outside=int(np.abs(high.astype(np.int16)-low.astype(np.int16))[~region_mask].max(initial=0))
    protected=np.asarray(hair)>0
    for region in feature_regions(low.shape[:2],points):protected|=region['pupil_core']|region['sclera']
    fixed_error=int(np.abs(high.astype(np.int16)-low.astype(np.int16))[protected].max(initial=0))
    if outside or fixed_error:raise RuntimeError('Saved8-bit output changed protected pixels.')
    audit={'status':'experimental_component_not_promoted','profile':detail['profile'],'strength':args.strength,
           'parent_audit':str(args.component_audit),'parent_audit_sha256':sha(args.component_audit),
           'input_records':parent['input_records'],'candidate_input_record':parent['candidate_input_record'],
           'before_polish_stage_sha256':sha(before_path),'low_path':str(low_path),'low_sha256':sha(low_path),
           'low_replay_pixel_exact':True,'genuine_references':refs,'scores':scores,'operation':detail,
           'gaze_before_photometry':gaze_report,'final_redetected_gaze':gaze_diagnostics,
           'outside_eye_brow_mask_error_0_to_255':outside,'pupil_core_sclera_hair_error_0_to_255':fixed_error,
           'closed_lips':closed_lip_check(measure_smile(source_points)['opening_ratio'],measure_smile(after_points)['opening_ratio']),
           'identity_retention':identity_retention_check(scores['SOURCE'],scores['RAW'],scores['HIGH'],'high-edit'),
           'max_pose_delta_from_low_degrees':float(np.abs(faces['HIGH'].pose-faces['LOW'].pose).max()),
           'max_pose_delta_from_source_degrees':float(np.abs(faces['HIGH'].pose-faces['SOURCE'].pose).max()),
           'definition_before':definition_profile(low,points)[1],
           'definition_after_fixed_landmarks':definition_profile(high,points)[1],
           'definition_after_redetected':definition_profile(high,after_points)[1],
           'module_sha256':sha(Path(__file__).with_name('experimental_upgrade_eye_definition.py')),
           'production_changed':False,'diffusion_runs':0,'local_only':True,
           'limitation':'No geometry was changed, but photometric definition can affect perceived gaze. Redetection and likeness are diagnostics, not a full High or three-photo acceptance.'}
    out.mkdir(parents=True)
    metadata=PngImagePlugin.PngInfo();metadata.add_text('postprocess',json.dumps({'profile':detail['profile'],'strength':args.strength,'low_sha256':sha(low_path)}))
    Image.fromarray(high).save(out/'high.png',pnginfo=metadata);Image.fromarray(region_mask.astype(np.uint8)*255).save(out/'mask.png')
    audit['output_sha256']=sha(out/'high.png')
    for crop,filename in ((True,'source-low-high-face.jpg'),(False,'source-low-high-thumbnail.jpg')):
        tiles=[]
        for label,rgb in (('SOURCE',source),('REVISED LOW',low),('EYE DEFINITION - TEST',high)):
            tile=Image.fromarray(rgb)
            if crop:
                bbox=face(rgb).bbox;margin=(bbox[2]-bbox[0])*.12
                tile=tile.crop(tuple((bbox+[-margin,-margin,margin,margin]).astype(int)))
                tile=tile.resize((round(tile.width*420/tile.height),420),Image.Resampling.LANCZOS)
            else:tile.thumbnail((330,450),Image.Resampling.LANCZOS)
            tiles.append((label,tile))
        sheet=Image.new('RGB',(sum(tile.width for _,tile in tiles),max(tile.height for _,tile in tiles)+38),(20,20,20))
        draw=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=16);x=0
        for label,tile in tiles:
            sheet.paste(tile,(x,38));draw.text((x+7,8),label,fill='white',font=font);x+=tile.width
        sheet.save(out/filename,quality=96)
    (out/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({key:audit[key] for key in ('status','scores','closed_lips','identity_retention','final_redetected_gaze','outside_eye_brow_mask_error_0_to_255','output_sha256')},indent=2))


if __name__=='__main__':main()
