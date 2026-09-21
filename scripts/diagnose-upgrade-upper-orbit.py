"""Read-only upper-eye texture diagnostic; masked panels are inspection aids only."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
from flux2_klein9b_attractiveness import _UPPER_LIDS,_EYE_CONTOURS,_BROWS


def inspect_orbit(rgb,points):
    gray=cv2.cvtColor(rgb.astype(np.float32)/255,cv2.COLOR_RGB2GRAY)
    h,w=gray.shape;yy,xx=np.mgrid[:h,:w].astype(np.float32)
    mask=np.zeros((h,w),np.uint8);guard=np.zeros_like(mask);results=[]
    for ids in (*_EYE_CONTOURS,*_BROWS):
        cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
    guard=cv2.dilate(guard,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
    for ids in _UPPER_LIDS:
        lid=points[list(ids)];axis=lid[-1]-lid[0];width=float(np.linalg.norm(axis));axis/=width
        normal=np.array([-axis[1],axis[0]],np.float32)
        if normal[1]<0: normal=-normal
        u=((xx-lid[0,0])*axis[0]+(yy-lid[0,1])*axis[1])/width
        v=((xx-lid[0,0])*normal[0]+(yy-lid[0,1])*normal[1])/width
        local=(lid-lid[0])@np.stack((axis,normal),axis=1)/width
        order=np.argsort(local[:,0])
        lid_v=np.interp(u,local[order,0],local[order,1])
        above=lid_v-v
        selected=(u>=.12)&(u<=.88)&(above>=.04)&(above<=.25)&(guard==0)
        if selected.sum()<12: raise ValueError('Insufficient unoccluded upper-orbit sample.')
        fine=cv2.GaussianBlur(gray,(0,0),max(.7,width*.015))
        broad=cv2.GaussianBlur(gray,(0,0),max(2.,width*.08))
        dark=np.maximum(broad-fine,0)[selected]
        results.append({'eye_width_pixels':width,'sampled_pixels':int(selected.sum()),
                        'dark_band_mean':float(dark.mean()),'dark_band_p95':float(np.percentile(dark,95)),
                        'fraction_dark_band_above_0_02':float(np.mean(dark>.02)),
                        'median_local_luma':float(np.median(gray[selected]))})
        mask[selected]=255
    assert not np.any((mask>0)&(guard>0))
    return mask,results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component-audit',type=Path,action='append',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--mode',choices=('upper-orbit','eye-definition'),default='upper-orbit')
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'): raise ValueError('Use new project work output.')
    out.mkdir(parents=True);report={'status':'diagnostic_only','cases':{},'photo_edits':False,'gpu_jobs':0,'uploads':False}
    for audit_path in args.component_audit:
        audit=json.loads(audit_path.read_text(encoding='utf-8-sig'))
        if not audit.get('source_lid_component_only'): raise ValueError('Expected isolated source-lid audit.')
        source_record=audit['input_records']['SOURCE'];source_path=ROOT/source_record['path']
        before=audit_path.parent/'before-lid-correction.png'
        if hashlib.sha256(source_path.read_bytes()).hexdigest()!=source_record['sha256']: raise ValueError('Source changed.')
        panels=[];records={}
        for label,path in (('SOURCE',source_path),('REVISED LOW BEFORE GAZE',before)):
            with Image.open(path) as image: rgb=np.array(ImageOps.exif_transpose(image).convert('RGB'))
            if label!='SOURCE' and hashlib.sha256(rgb.tobytes()).hexdigest()!=audit['source_lid_curve']['before_sha256_pixels']:
                raise ValueError('Pre-edit pixels changed.')
            points,_=_detect_refined_landmarks(rgb)
            if args.mode=='eye-definition':
                from experimental_upgrade_eye_definition import definition_profile
                mask,stats=definition_profile(rgb,points)
            else:
                mask,stats=inspect_orbit(rgb,points)
            records[label]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'eyes':stats}
            region=points[[i for ids in (*_EYE_CONTOURS,*_BROWS) for i in ids]]
            box=(max(0,int(region[:,0].min()-12)),max(0,int(region[:,1].min()-12)),
                 min(rgb.shape[1],int(region[:,0].max()+12)),min(rgb.shape[0],int(region[:,1].max()+12)))
            overlay=rgb.copy();overlay[mask>0]=np.clip(rgb[mask>0]*.45+np.array([20,160,30])*.55,0,255).astype(np.uint8)
            for name,array in ((label,rgb),(label+' SAMPLE MASK',overlay)):
                tile=Image.fromarray(array).crop(box);tile=tile.resize((440,round(tile.height*440/tile.width)),Image.Resampling.LANCZOS)
                panels.append((name,tile))
        case=audit_path.parent.name;report['cases'][case]={'component_audit':str(audit_path),'images':records}
        sheet=Image.new('RGB',(880,max(panels[0][1].height,panels[1][1].height)+max(panels[2][1].height,panels[3][1].height)+64),(20,20,20))
        draw=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=14);y=0
        for start in (0,2):
            for x,(label,tile) in zip((0,440),panels[start:start+2]):
                draw.text((x+6,y+5),label,fill='white',font=font);sheet.paste(tile,(x,y+28))
            y+=max(panels[start][1].height,panels[start+1][1].height)+32
        sheet.save(out/(case+'.jpg'),quality=96)
    report['method']='Fixed normalized band 0.04..0.25 eye widths above the upper lid; middle76% of width; dilated eye/brow silhouettes excluded. Positive broad-minus-fine luma at sigma0.08/0.015 eye widths.'
    if args.mode=='eye-definition':
        report['method']='Fixed inferred iris annulus/limbal/sclera masks inside eroded eye boundaries, pupil core excluded; bright catchlights excluded from iris/limbal statistics; detected brow silhouette. Original hue is not a target.'
    report['mode']=args.mode
    report['limitation']='Rendered crease/shading/texture diagnostic, not physical lighting, apparent age, identity or attractiveness. Overlay panels are not candidate edits.'
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__': main()
