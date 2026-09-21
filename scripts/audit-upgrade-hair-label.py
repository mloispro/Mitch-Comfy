"""CPU three-photo proof of ParseNet hair/neck label mismatch and isolated repair."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, ImageOps
from insightface.app import FaceAnalysis

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
sys.path.insert(0,str(COMFY));sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
from flux2_klein9b_deterministic_polish import build_semantic_hair_mask, apply_deterministic_face_polish
from flux2_klein9b_source_gaze_lock import apply_source_gaze_lock
from upgrade_parsenet_hair import parsed_labels,select_hair

CASES={
    'house':('input/mitch-photo2-source-aef87048.png',
             'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-111226-463056/before-polish_00001_.png',
             'b51f6e6e0ad0105afb00542aaa7ca619032efd44819279f578da7952c19a7673',
             ROOT/'work/flux2-klein9b-attractiveness-20260903/house-eye-final/low.png'),
    'canyon':('input/mitch-canyon-source-edit-05333f6f.png',
              'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-005704-305944/before-polish_00001_.png',
              'e20f79f0c8fdef060080bbe72e639dc59bb89d1ccf147e6b8b1523cf45d20a82',
              ROOT/'work/flux2-klein9b-attractiveness-20260903/canyon-eye-final/low.png'),
    'third':('input/mitch-upgrade-third-genuine-fef084d6.png',
             'output/upgrade-source-faithful/third-source-native-preserve/raw_00001_.png',
             '3f0cc682a9cb440f54e40fb750e87e105498a7a4c90d4c35020427381fdcc54a',None),
}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    with Image.open(path) as im:return np.array(ImageOps.exif_transpose(im).convert('RGB'))
def tensor(rgb):return torch.from_numpy(rgb.astype(np.float32)/255).unsqueeze(0)
def pixels(photo):return np.rint(np.clip(photo[0].numpy(),0,1)*255).astype(np.uint8)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):raise ValueError('Use a fresh project directory.')
    module=ROOT/'custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_deterministic_polish.py'
    if sha(module)!='d970934ce4cf0b640a4bd24abd7da3bfa16a67f23842cbc81b14b4323793977b':
        raise ValueError('Legacy production control changed.')
    torch.set_num_threads(4)
    app=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),providers=['CPUExecutionProvider'],
                     allowed_modules=['detection','recognition','landmark_3d_68'])
    app.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found=app.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(found)!=1:raise ValueError('Expected one face.')
        return found[0]
    refs=sorted((ROOT/'datasets/mitch-identity-stills-v3/validation').glob('val_*.jpg'))
    vectors={str(p):face(read(p)).normed_embedding for p in refs}
    out.mkdir(parents=True);results={}
    font=ImageFont.load_default(size=16)
    for name,(source_rel,raw_rel,expected,baseline) in CASES.items():
        raw_path=COMFY/raw_rel;source_path=COMFY/source_rel
        if sha(raw_path)!=expected:raise ValueError('Frozen raw changed: '+name)
        raw=read(raw_path);source=read(source_path);detected=face(raw)
        labels=parsed_labels(raw,detected.bbox)
        legacy=build_semantic_hair_mask(raw,detected.bbox);corrected=select_hair(labels)
        # Labels17 and13 should have zero original class intersection. Legacy
        # closing can cross a couple of boundary pixels; report instead of hiding it.
        case=out/name;case.mkdir();entry={'raw_path':str(raw_path),'raw_sha256':expected,
             'source_path':str(source_path),'source_sha256':sha(source_path),
             'raw_bbox':detected.bbox.tolist(),'corrected_hair_class':13,'legacy_selected_class':17,
             'legacy_hair_pixel_count':int(np.count_nonzero(legacy)),
             'corrected_hair_pixel_count':int(np.count_nonzero(corrected)),
             'legacy_fraction_in_actual_neck':float(np.mean(labels[legacy>0]==17)),
             'legacy_fraction_in_actual_hair':float(np.mean(labels[legacy>0]==13)),
             'corrected_fraction_in_neck':float(np.mean(labels[corrected>0]==17))}
        available=[value for p,value in vectors.items() if not(name=='third' and 'val_03_' in p)]
        centroid=np.mean(available,axis=0);centroid/=np.linalg.norm(centroid)
        masks=[];outputs=[];reports={}
        for title,mask in (('LEGACY CLASS17 (NECK)',legacy),('CORRECTED CLASS13 (HAIR)',corrected)):
            slug='legacy' if title.startswith('LEGACY') else 'corrected'
            Image.fromarray(mask).save(case/(slug+'-mask.png'))
            overlay=raw.astype(np.float32);alpha=(mask>0).astype(np.float32)*.42
            overlay=overlay*(1-alpha[...,None])+np.array([0,210,255])*alpha[...,None]
            masks.append((title,Image.fromarray(np.rint(overlay).astype(np.uint8))))
            polished,_,detail=apply_deterministic_face_polish(tensor(raw),detected.bbox,detected.kps,mask)
            finished,gaze_mask,gaze_report=apply_source_gaze_lock(tensor(source),polished)
            rgb=pixels(finished);Image.fromarray(rgb).save(case/(slug+'-low.png'))
            outputs.append((title,Image.fromarray(rgb)))
            reports[slug]={'identity_centroid':float(face(rgb).normed_embedding@centroid),
                           'output_sha256':sha(case/(slug+'-low.png')),
                           'hair_report':detail['hair_material'] if 'hair_material' in detail else detail,
                           'actual_injected_parsenet_class':17 if slug=='legacy' else 13,
                           'inherited_report_label_is_legacy_metadata':slug=='corrected',
                           'gaze':gaze_report,'gaze_mask':(gaze_mask[0].numpy().max(axis=-1)>0)}
        old=np.array(outputs[0][1]);new=np.array(outputs[1][1])
        allowed=(legacy>0)|(corrected>0)|reports['legacy'].pop('gaze_mask')|reports['corrected'].pop('gaze_mask')
        delta=np.max(np.abs(new.astype(np.int16)-old.astype(np.int16)),axis=-1)
        entry['outside_hair_neck_and_gaze_max_rgb_error']=int(delta[~allowed].max())
        if entry['outside_hair_neck_and_gaze_max_rgb_error']!=0:raise ValueError('Unexplained changes outside isolated repair.')
        entry['legacy_replays_actual_low_pixels']=bool(np.array_equal(old,read(baseline))) if baseline else None
        entry['results']=reports
        for kind,tiles in (('masks',masks),('low-comparison',outputs)):
            small=[]
            for title,im in tiles:
                im=im.copy();im.thumbnail((600,760),Image.Resampling.LANCZOS);small.append((title,im))
            sheet=Image.new('RGB',(sum(im.width for _,im in small),max(im.height for _,im in small)+38),(20,20,20))
            draw=ImageDraw.Draw(sheet);x=0
            for title,im in small:sheet.paste(im,(x,38));draw.text((x+6,8),title,fill='white',font=font);x+=im.width
            sheet.save(case/(kind+'.jpg'),quality=96)
        results[name]=entry
    report={'status':'CPU_label_repair_evaluated_not_production','production_changed':False,
            'scope':'Low replay only; not a complete stronger-High fix or end-to-end generation',
            'legacy_module_sha256':sha(module),'results':results,
            'corrected_helper_sha256':sha(ROOT/'scripts/upgrade_parsenet_hair.py'),
            'same_5x5_closing_and_largest_component_as_legacy':True,
            'genuine_refs':[{'path':str(p),'sha256':sha(p)} for p in refs],
            'third_excludes_own_original_genuine_reference':True,'visual_review_required':True}
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({n:{k:v for k,v in r.items() if k not in ('results','raw_bbox')} for n,r in results.items()},indent=2))


if __name__=='__main__':main()
