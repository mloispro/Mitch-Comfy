"""Verify the actual v5 parser/Low/High finish against frozen three-photo evidence.

CPU only. This is a production-code replay, not live end-to-end generation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, ImageOps
from insightface.app import FaceAnalysis

ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/'work/upgrade-source-faithful-20260903/parsenet-label-exact-repair-audit'
CONTROL_SHA='6fcd30e15c1aab4f9e4aa384d5c2975c659397cb7abf9f7deb9c050c61870806'
V4_SHA='d970934ce4cf0b640a4bd24abd7da3bfa16a67f23842cbc81b14b4323793977b'
V5_SHA='3f37fd5632d4ae1236314df795aaddbf73fa55ef74cae2bab62c7359a5778676'
sys.path.insert(0,str(ROOT.parent/'ComfyUI'))
sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
import flux2_klein9b_deterministic_polish as polish
from flux2_klein9b_source_gaze_lock import apply_source_gaze_lock, _detect_refined_landmarks
from flux2_klein9b_attractiveness import apply_high_attractiveness


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    with Image.open(path) as im:return np.array(ImageOps.exif_transpose(im).convert('RGB'))
def tensor(rgb):return torch.from_numpy(rgb.astype(np.float32)/255).unsqueeze(0)
def pixels(photo):return np.rint(np.clip(photo[0].numpy(),0,1)*255).astype(np.uint8)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):
        raise ValueError('Use a fresh project work directory.')
    if digest(CONTROL/'audit.json')!=CONTROL_SHA or digest(CONTROL/'legacy_v4.py')!=V4_SHA:
        raise ValueError('Frozen three-photo evidence changed.')
    if digest(polish.__file__)!=V5_SHA:
        raise ValueError('Unreviewed v5 code.')
    spec=importlib.util.spec_from_file_location('legacy_polish_v4',CONTROL/'legacy_v4.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    control=json.loads((CONTROL/'audit.json').read_text())
    torch.set_num_threads(4)
    app=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),providers=['CPUExecutionProvider'],
                     allowed_modules=['detection','recognition','landmark_3d_68'])
    app.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found=app.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(found)!=1:raise ValueError('Expected exactly one face.')
        return found[0]
    vectors={}
    for ref in control['genuine_refs']:
        if digest(ref['path'])!=ref['sha256']:raise ValueError('Genuine held-out changed.')
        vectors[ref['path']]=face(read(ref['path'])).normed_embedding
    out.mkdir(parents=True);results={};font=ImageFont.load_default(size=16)
    for name,case in control['results'].items():
        for key in ('raw','source'):
            if digest(case[key+'_path'])!=case[key+'_sha256']:
                raise ValueError('Frozen source/raw changed.')
        raw=read(case['raw_path']);source=read(case['source_path']);found=face(raw)
        actual_mask=polish.build_semantic_hair_mask(raw,found.bbox)
        expected_mask=read(CONTROL/name/'corrected-mask.png')[:,:,0]
        np.testing.assert_array_equal(actual_mask,expected_mask)
        old_mask=old.build_semantic_hair_mask(raw,found.bbox)
        np.testing.assert_array_equal(old_mask,read(CONTROL/name/'legacy-mask.png')[:,:,0])
        available=[v for p,v in vectors.items() if not(name=='third' and 'val_03_' in p)]
        centroid=np.mean(available,axis=0);centroid/=np.linalg.norm(centroid)
        folder=out/name;folder.mkdir();entry={};tiles=[('SOURCE',Image.fromarray(source))]
        for label,module,mask,control_label in (('v4',old,old_mask,'legacy'),('v5',polish,actual_mask,'corrected')):
            low,_,low_report=module.apply_deterministic_face_polish(tensor(raw),found.bbox,found.kps,mask)
            low,_,gaze=apply_source_gaze_lock(tensor(source),low)
            rgb=pixels(low)
            if digest(CONTROL/name/(control_label+'-low.png'))!=case['results'][control_label]['output_sha256']:
                raise ValueError('Frozen Low output changed.')
            np.testing.assert_array_equal(rgb,read(CONTROL/name/(control_label+'-low.png')))
            points,_=_detect_refined_landmarks(rgb);source_points,_=_detect_refined_landmarks(source)
            high,high_mask,high_report=apply_high_attractiveness(low,points,mask,source_points)
            high_rgb=pixels(high)
            np.testing.assert_array_equal(high_rgb[high_mask[0].numpy().max(axis=-1)==0],
                                          rgb[high_mask[0].numpy().max(axis=-1)==0])
            Image.fromarray(rgb).save(folder/(label+'-low.png'))
            Image.fromarray(high_rgb).save(folder/(label+'-high.png'))
            if label=='v5':
                assert low_report['profile']=='deterministic_face_and_hair_local_v5'
                assert low_report['hair_material_correction']['parser_hair_class']==13
            entry[label]={'low_matches_frozen_pixels':True,'mask_matches_frozen_pixels':True,
                          'low_identity':float(face(rgb).normed_embedding@centroid),
                          'high_identity':float(face(high_rgb).normed_embedding@centroid),
                          'low_sha256':digest(folder/(label+'-low.png')),
                          'high_sha256':digest(folder/(label+'-high.png')),
                          'low_report':low_report,'gaze_report':gaze,'high_report':high_report}
            tiles.append((label.upper()+' HIGH',Image.fromarray(high_rgb)))
        sizes=[]
        for title,im in tiles:
            im=im.copy();im.thumbnail((540,720),Image.Resampling.LANCZOS);sizes.append((title,im))
        sheet=Image.new('RGB',(sum(im.width for _,im in sizes),max(im.height for _,im in sizes)+38),(20,20,20))
        draw=ImageDraw.Draw(sheet);x=0
        for title,im in sizes:sheet.paste(im,(x,38));draw.text((x+6,8),title,fill='white',font=font);x+=im.width
        sheet.save(folder/'source-v4-v5-high.jpg',quality=96)
        results[name]=entry
        print(json.dumps({'case':name,'actual_parser_and_low_exact_match':True,
                          'v4_high_identity':entry['v4']['high_identity'],
                          'v5_high_identity':entry['v5']['high_identity']}),flush=True)
    report={'status':'actual_v5_cpu_replay_verified_not_live_end_to_end',
            'control_sha256':CONTROL_SHA,'v4_sha256':V4_SHA,'v5_sha256':V5_SHA,
            'low_order':'actual semantic parser -> deterministic polish -> source gaze',
            'high_order':'Low including source gaze -> existing High',
            'genuine_reference_count':6,'third_excludes_own_original':True,
            'third_raw_policy_differs_not_a_universal_native_proof':True,
            'stronger_high_requirement_satisfied':False,'results':results}
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
