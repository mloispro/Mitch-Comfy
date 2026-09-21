"""Author-core zero-motion quality control; no expression driving or production changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD']='1'
import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from PIL import Image,ImageDraw,ImageFont,ImageOps
from skimage.metrics import structural_similarity


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(4*1024*1024),b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    started=time.perf_counter()
    root=Path(__file__).resolve().parents[1]
    if not args.output_dir.resolve().is_relative_to(root) or args.output_dir.exists():
        raise ValueError('Use a new output folder inside the workspace.')
    repo=root/'work/vendor/LivePortrait-code'
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!='9b294b3d0536135442ea73cb01e6cb3ca7029dd3':
        raise RuntimeError('Reviewed upstream commit changed.')
    manifest=json.loads((repo/'pretrained_weights/verified-human-control.json').read_text())
    for record in manifest['files']:
        if digest(record['path'])!=record['sha256']:
            raise RuntimeError('A verified checkpoint changed.')
    def api(port,path):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/{path}',timeout=4) as response:
            return json.load(response)
    workers=[]
    for port in (8188,8189):
        queue=api(port,'queue'); stats=api(port,'system_stats')
        workers.append({'port':port,'device':stats['devices'][0]['name'],
                        'running':len(queue['queue_running']),'pending':len(queue['queue_pending'])})
    if 'RTX 3090' not in workers[0]['device'] or workers[0]['running'] or workers[0]['pending']:
        raise RuntimeError('Workflow-locked3090 is busy or unavailable.')
    hardware=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu',
                                     '--format=csv,noheader,nounits'],text=True)
    card=[line.split(',') for line in hardware.splitlines() if 'RTX 3090' in line]
    if len(card)!=1 or int(card[0][2])>4096 or int(card[0][3])>10:
        raise RuntimeError('Do not interrupt occupied3090 hardware.')
    if 'RTX 3090' not in torch.cuda.get_device_name(0):
        raise RuntimeError('cuda:0 does not match the locked physical3090.')
    sys.path.insert(0,str(repo))
    from src.live_portrait_wrapper import LivePortraitWrapper
    from src.config.inference_config import InferenceConfig
    from src.utils.crop import crop_image,prepare_paste_back,paste_back

    def read(path):
        return np.array(ImageOps.exif_transpose(Image.open(path)).convert('RGB'))
    raw=read(args.raw)
    detector=FaceAnalysis(name='buffalo_l',root=str(Path.home()/'.insightface'),
                          providers=['CPUExecutionProvider'],allowed_modules=['detection','landmark_2d_106'])
    detector.prepare(ctx_id=-1,det_size=(512,512),det_thresh=.5)
    faces=detector.get(cv2.cvtColor(raw,cv2.COLOR_RGB2BGR))
    if len(faces)!=1:
        raise RuntimeError(f'Expected exactly one source face; detections: {[(f.bbox.tolist(),float(f.det_score)) for f in faces]}')
    crop=crop_image(raw,faces[0].landmark_2d_106,dsize=512,scale=2.3,
                    vx_ratio=0,vy_ratio=-.125,flag_do_rot=True)
    input_256=cv2.resize(crop['img_crop'],(256,256),interpolation=cv2.INTER_AREA)
    cfg=InferenceConfig(flag_use_half_precision=False,flag_normalize_lip=False,
                        flag_do_torch_compile=False,device_id=0,
                        lip_array=np.zeros((1,21,3),np.float32))
    if cfg.mask_crop is None: raise RuntimeError('Author pasteback mask missing.')
    for worker in workers:
        if 'RTX 3090' in worker['device']:
            queue=api(worker['port'],'queue')
            if queue['queue_running'] or queue['queue_pending']:
                raise RuntimeError('3090 became busy during preparation.')
    torch.cuda.reset_peak_memory_stats(0)
    wrapper=LivePortraitWrapper(cfg)
    prepared=wrapper.prepare_source(input_256)
    info=wrapper.get_kp_info(prepared)
    points=wrapper.transform_keypoint(info)
    features=wrapper.extract_feature_3d(prepared)
    decoded=wrapper.parse_output(wrapper.warp_decode(features,points,points)['out'])[0]
    stitched_points=wrapper.stitching(points,points)
    stitched=wrapper.parse_output(wrapper.warp_decode(features,points,stitched_points)['out'])[0]
    mask=prepare_paste_back(cfg.mask_crop,crop['M_c2o'],(raw.shape[1],raw.shape[0]))
    crop_outputs={'crop_roundtrip':crop['img_crop'],
                  'input_resolution_control':cv2.resize(input_256,(512,512)),
                  'zero_motion':decoded,'zero_motion_stitched':stitched}
    outputs={'raw':raw,**{name:paste_back(value,crop['M_c2o'],raw,mask)
                         for name,value in crop_outputs.items()}}
    args.output_dir.mkdir(parents=True)
    for name,value in outputs.items(): Image.fromarray(value).save(args.output_dir/f'{name}.png')
    Image.fromarray(input_256).save(args.output_dir/'network-input-256.png')
    for name,value in crop_outputs.items(): Image.fromarray(value).save(args.output_dir/f'{name}-crop512.png')
    peak=torch.cuda.max_memory_allocated(0)
    del wrapper,features,prepared,points,stitched_points,info
    torch.cuda.empty_cache()

    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
                          providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(image):
        matches=analyzer.get(cv2.cvtColor(image,cv2.COLOR_RGB2BGR))
        if len(matches)!=1: raise RuntimeError('Expected exactly one scoring face.')
        return matches[0]
    refs=sorted((root/'datasets/mitch-identity-stills-v3/validation').glob('val_*.jpg'))
    if len(refs)!=6: raise RuntimeError('Expected six genuine reference photographs.')
    embeddings=[face(read(path)).normed_embedding for path in refs]
    centroid=np.mean(embeddings,axis=0); centroid/=np.linalg.norm(centroid)
    results={}
    for name,value in outputs.items():
        detected=face(value)
        results[name]={'identity_centroid':float(detected.normed_embedding@centroid),
                       'per_reference':[float(detected.normed_embedding@ref) for ref in embeddings],
                       'pose':[float(v) for v in detected.pose],
                       'outside_author_mask_max_error':int(np.abs(value.astype(np.int16)-raw.astype(np.int16))[mask.max(axis=2)==0].max(initial=0))}
        if name in crop_outputs:
            results[name]['crop_ssim']=float(structural_similarity(crop['img_crop'],crop_outputs[name],channel_axis=2,data_range=255))
    x0,y0,x1,y1=face(raw).bbox
    box=(max(0,int(x0-30)),max(0,int(y0-30)),min(raw.shape[1],int(x1+30)),min(raw.shape[0],int(y1+30)))
    def sheet(names,path,crop_box=None,max_width=650):
        tiles=[]
        for name in names:
            tile=Image.fromarray(outputs[name])
            if crop_box: tile=tile.crop(crop_box)
            if tile.width>max_width: tile=tile.resize((max_width,round(tile.height*max_width/tile.width)),Image.Resampling.LANCZOS)
            tiles.append((name,tile))
        canvas=Image.new('RGB',(sum(tile.width for _,tile in tiles),max(tile.height for _,tile in tiles)+45),(22,22,22))
        draw=ImageDraw.Draw(canvas); font=ImageFont.load_default(size=18); x=0
        for name,tile in tiles:
            canvas.paste(tile,(x,45));draw.text((x+10,10),name.replace('_',' ').upper(),font=font,fill='white');x+=tile.width
        canvas.save(path,quality=96)
    sheet(['raw','zero_motion','zero_motion_stitched'],args.output_dir/'reconstruction-face.jpg',box)
    sheet(['raw','zero_motion','zero_motion_stitched'],args.output_dir/'reconstruction-full.jpg')
    sheet(['raw','crop_roundtrip','input_resolution_control'],args.output_dir/'sampling-controls-face.jpg',box)
    failures=[]
    for name in ('zero_motion','zero_motion_stitched'):
        if results[name]['identity_centroid']<.70 or results['raw']['identity_centroid']-results[name]['identity_centroid']>.03:
            failures.append(f'{name}: likeness-loss gate failed.')
    report={'status':'evaluated_not_promoted','identity_mechanism':'edit-target appearance volume and source canonical keypoints; no external driving face',
            'zero_motion_core':True,'expression_transfer':False,'input_shape':[256,256],'decoder_shape':list(decoded.shape),
            'crop':{'scale':2.3,'vy_ratio':-.125,'rotation':True,'M_c2o':crop['M_c2o'].tolist()},
            'dtype':'float32','checkpoint_loading':'forced weights_only','models':manifest,'workers':workers,'hardware':hardware,
            'raw_path':str(args.raw),'raw_sha256':digest(args.raw),'genuine_references':[{'path':str(path),'sha256':digest(path)} for path in refs],
            'results':results,'failures':failures,'visual_review_still_required':True,
            'peak_allocated_gpu_bytes':peak,'seconds':time.perf_counter()-started}
    (args.output_dir/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'results':results,'failures':failures,'seconds':report['seconds'],'peak_allocated_gpu_bytes':peak},indent=2))
    if failures: raise SystemExit(1)


if __name__=='__main__':
    main()
