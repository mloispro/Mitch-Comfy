"""Read-only broad facial appearance measurements; not an illumination/beauty estimator."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps


def appearance_profile(rgb,mask,face_width):
    image=rgb.astype(np.float32)/255
    broad=cv2.GaussianBlur(image,(0,0),max(1,float(face_width)*.025))
    luma=broad@np.array([.2126,.7152,.0722],np.float32)
    values=luma[mask]
    if len(values)<100: raise ValueError('Insufficient interior face pixels.')
    p10,median,p90=np.percentile(values,[10,50,90])
    lab=cv2.cvtColor(broad,cv2.COLOR_RGB2LAB)[mask]
    return {'broad_srgb_luminance_p10_median_p90':[float(v) for v in (p10,median,p90)],
            'broad_contrast_span_over_median':float((p90-p10)/max(median,1e-6)),
            'median_Lab_a_b':[float(v) for v in np.median(lab[:,1:],axis=0)],
            'interior_pixels':int(mask.sum()),'gaussian_sigma_pixels':max(1,float(face_width)*.025)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new project output directory.')
    audit=json.loads(args.audit.read_text(encoding='utf-8-sig'))
    if not audit['executed_png_graph_verified'] or audit['postprocess_applied']:
        raise ValueError('Expected verified native-generation audit.')
    sys.path.insert(0,str(root/'custom_nodes/ComfyUI-AIToolkit-Training'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
    from flux2_klein9b_attractiveness import _OVAL,_EYE_CONTOURS,_BROWS,_LIPS
    panels=[];results={};inputs={}
    for label in ('SOURCE','BASE RAW','CANDIDATE HIGH'):
        record=audit['inputs'][label];path=root/record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Image changed since native audit.')
        with Image.open(path) as opened: rgb=np.array(ImageOps.exif_transpose(opened).convert('RGB'))
        points,_=_detect_refined_landmarks(rgb)
        mask=np.zeros(rgb.shape[:2],np.uint8)
        cv2.fillPoly(mask,[np.rint(points[list(_OVAL)]).astype(np.int32)],255)
        face_width=float(np.ptp(points[list(_OVAL),0]))
        radius=max(1,round(face_width*.025))
        mask=cv2.erode(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1)))
        guard=np.zeros_like(mask)
        for indices in (*_EYE_CONTOURS,*_BROWS,_LIPS):
            cv2.fillPoly(guard,[np.rint(points[list(indices)]).astype(np.int32)],255)
        guard=cv2.dilate(guard,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1)))
        selected=(mask>0)&(guard==0)
        results[label]=appearance_profile(rgb,selected,face_width);inputs[label]=record
        bounds=np.array(audit['results'][label]['bbox_xyxy']);margin=(bounds[2]-bounds[0])*.12
        overlay=rgb.copy();overlay[selected]=np.clip(overlay[selected]*.60+[0,90,0],0,255).astype(np.uint8)
        for variant,array in (('appearance',rgb),('measured region',overlay)):
            tile=Image.fromarray(array).crop(tuple((bounds+[-margin,-margin,margin,margin]).astype(int)))
            tile=tile.resize((round(tile.width*360/tile.height),360),Image.Resampling.LANCZOS)
            panels.append((label+' '+variant,tile))
    args.output_dir.mkdir(parents=True)
    report={'status':'diagnostic_only','native_audit':str(args.audit),'inputs':inputs,'results':results,
            'limitation':'Broad rendered facial appearance includes lighting, albedo, exposure, face shape and texture. These measurements do not isolate physical illumination, skin tone, actual age or attractiveness. No pixels edited for a candidate.'}
    (args.output_dir/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    font=ImageFont.load_default(size=14)
    widths=[max(panels[i][1].width,panels[i+1][1].width) for i in (0,2,4)]
    sheet=Image.new('RGB',(sum(widths),800),(22,22,22));draw=ImageDraw.Draw(sheet);x=0
    for column,index in enumerate((0,2,4)):
        for row in (0,1):
            label,tile=panels[index+row];y=row*400
            draw.text((x+6,y+8),label,font=font,fill='white');sheet.paste(tile,(x,y+32))
        x+=widths[column]
    sheet.save(args.output_dir/'appearance-and-regions.jpg',quality=96)
    print(json.dumps(report['results'],indent=2))


if __name__=='__main__': main()
