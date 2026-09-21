"""Prepare a bounded native face-context edit; no generation or compositing."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image,ImageOps

PROMPT=(
    'Retouch the man in this image into a distinctly more handsome best-day version of m1tch_person. '
    'He looks several years younger and well-rested, with clear even lightly tanned skin, fine natural '
    'pores, a smooth relaxed forehead, refreshed confident eyes, beautifully groomed eyebrows, lean '
    'defined cheeks and a neat jawline. His lips gently meet in a small warm asymmetric closed-mouth '
    'smile. His existing short stubble is neatly groomed. His existing hairstyle has individual natural '
    'strands with delicate sunlit highlights. Preserve his recognizable facial identity, the original '
    'head angle, forehead proportions, iris direction, camera perspective and natural lighting. '
    'The result is a realistic casual snapshot of the same man after a flattering professional retouch.'
)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','source','low','baseline-report','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new project output directory.')
    def read(path): return ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    raw=read(args.raw);rgb=np.array(raw)
    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
                         providers=['CPUExecutionProvider'],allowed_modules=['detection'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    faces=analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
    if len(faces)!=1: raise ValueError('Exactly one face required.')
    x0,y0,x1,y1=faces[0].bbox
    side=min(raw.width,raw.height,int(round(max(x1-x0,y1-y0)*1.40)))
    left=max(0,min(raw.width-side,round((x0+x1-side)/2)))
    top=max(0,min(raw.height-side,round((y0+y1-side)/2)))
    box=(left,top,left+side,top+side)
    args.output_dir.mkdir(parents=True)
    files={}
    for name,path in (('raw',args.raw),('source',args.source),('low',args.low)):
        image=read(path)
        scaled_box=tuple(round(v*(image.width/raw.width if i%2==0 else image.height/raw.height)) for i,v in enumerate(box))
        crop=image.crop(scaled_box).resize((1024,1024),Image.Resampling.BICUBIC)
        destination=args.output_dir/f'{name}-crop.png';crop.save(destination)
        files[name]={'original':str(path),'original_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'crop':str(destination),'crop_sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
    settings=json.loads(args.baseline_report.read_text(encoding='utf-8-sig'))
    settings.update(width=1024,height=1024,effective_prompt=PROMPT,
                    status='prepared_focused_edit_not_generated')
    (args.output_dir/'settings.json').write_text(json.dumps(settings,indent=2),encoding='utf-8')
    (args.output_dir/'prompt.txt').write_text(PROMPT,encoding='utf-8')
    (args.output_dir/'provenance.json').write_text(json.dumps({
        'status':'prepared_not_generated_or_composited','box_in_raw':list(map(int,box)),
        'face_bbox':faces[0].bbox.tolist(),'context_factor':1.40,'output_size':[1024,1024],
        'files':files,'identity_mechanism':'existing genuine-photo-trained Base9B LoRA; crop is only the edit target',
        'evaluation_note':'Raw/source/Low crops are diagnostic input views, not new photographs or genuine scoring references.'
    },indent=2),encoding='utf-8')
    print(json.dumps({'box':list(map(int,box)),'files':files},indent=2))

if __name__=='__main__':main()
