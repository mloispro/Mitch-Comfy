"""Measure native masked-sampling leakage against its exact source-codec control."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from upgrade_local_inpaint import validate_graph

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','candidate','codec','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--protected-region',choices=('background','person'),default='background',
                        help='Person mode audits the separate background-detail pilot, not the historical face edit.')
    args=parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT/'work'):
        raise ValueError('Use a new project audit path.')
    manifest=json.loads((args.run/'experiment.json').read_text(encoding='utf-8-sig'))
    if args.protected_region=='person':
        from upgrade_background_detail import validate_graph as validate_background_graph
        validate_background_graph(manifest)
    else:
        validate_graph(manifest)
    refs={r['name']:r for r in manifest['references']}
    for reference in refs.values():
        if sha(reference['path'])!=reference['sha256']:raise ValueError('Reference changed.')
    photos=[]
    for path in (args.candidate,args.codec):
        with Image.open(path) as im:
            graph=json.loads(im.info['prompt']);photos.append(np.array(im.convert('RGB')))
        for node in graph.values():
            if node['class_type']=='LoadImage':
                if node.pop('is_changed',None)!=[refs[node['inputs']['image']]['sha256']]:
                    raise ValueError('Executed image bytes differ.')
        if graph!=manifest['prompt']:raise ValueError('Executed graph differs.')
    with Image.open(manifest['references'][0]['path']) as im:source=np.array(im.convert('RGB'))
    with Image.open(manifest['references'][2]['path']) as im:mask=np.array(im.convert('L'))
    candidate,codec=photos
    if source.shape!=candidate.shape or source.shape!=codec.shape or source.shape[:2]!=mask.shape:
        raise ValueError('Full-frame geometry differs.')
    distance=cv2.distanceTransform((mask==0).astype(np.uint8),cv2.DIST_L2,5)
    outside=distance>64
    minimum_fraction=.05 if args.protected_region=='person' else .4
    if np.mean(outside)<minimum_fraction:raise ValueError('Insufficient protected evaluation region.')
    def metric(a,b,where):
        error=np.abs(a.astype(np.float32)-b.astype(np.float32))[where]
        mse=float(np.mean(error**2))
        return {'mean_abs_rgb_0_255':float(error.mean()),'p99_abs_rgb_0_255':float(np.percentile(error,99)),
                'max_abs_rgb_0_255':float(error.max()),'psnr_db':float(10*np.log10(255**2/mse)) if mse else None,
                'exact_rgb_pixel_fraction':float(np.mean(np.all(error==0,axis=-1)))}
    report={'status':'measured_requires_visual_face_and_seam_review','manifest_sha256':sha(args.run/'experiment.json'),
            'candidate':str(args.candidate),'candidate_sha256':sha(args.candidate),
            'codec_control':str(args.codec),'codec_sha256':sha(args.codec),
            'native_and_codec_executed_graphs_verified':True,'postprocess_applied':False,
            'protected_region':args.protected_region,
            'outside_mask_margin_px':64,'outside_fraction':float(np.mean(outside)),
            'native_vs_codec_outside':metric(candidate,codec,outside),
            'codec_vs_source_outside':metric(codec,source,outside),
            'native_vs_source_outside':metric(candidate,source,outside),
            'native_vs_codec_inside':metric(candidate,codec,mask>127),
            'interpretation':'Outside-mask latent anchoring still passes through VAE decode; source RGB is not assumed exact. Background preservation alone is not High acceptance.'}
    if args.protected_region=='person':
        report['interpretation']='Black-mask person latents are protected; VAE decoding can still change RGB. Detail and person preservation require visual review, not just these metrics.'
        leak=report['native_vs_codec_outside']
        report['person_leakage_diagnostic_pass']=(leak['mean_abs_rgb_0_255']<=.5 and leak['p99_abs_rgb_0_255']<=3)
        if manifest['dimensions']!=[1280,768]:
            raise ValueError('Fixed house detail ROIs require the reviewed1280x768 pilot.')
        # Predeclared unoccluded house regions, not chosen after seeing output.
        rois={'wall':[.04,.06,.24,.36],'branches':[.76,.04,.97,.39]}
        detail={}
        def detail_metric(rgb):
            gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(np.float32)
            gx=cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=3)
            gy=cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=3)
            return {'mean_gradient_magnitude':float(np.sqrt(gx*gx+gy*gy).mean()),
                    'laplacian_variance':float(cv2.Laplacian(gray,cv2.CV_32F).var()),
                    'note':'Texture/noise diagnostic, not proof of genuine material detail.'}
        from PIL import ImageDraw, ImageFont
        for name,relative in rois.items():
            h,w=mask.shape;x0,y0,x1,y1=[round(v*(w if i%2==0 else h)) for i,v in enumerate(relative)]
            if np.mean(mask[y0:y1,x0:x1]==255)<.98:
                raise ValueError('Fixed detail ROI is not safely inside fully editable background.')
            detail[name]={'box_xyxy':[x0,y0,x1,y1]}
            tiles=[]
            for label,rgb in (('INPUT',source),('CODEC',codec),('BACKGROUND REPAIR',candidate)):
                crop=rgb[y0:y1,x0:x1];detail[name][label]=detail_metric(crop)
                tiles.append((label,Image.fromarray(crop)))
            canvas=Image.new('RGB',(sum(t.width for _,t in tiles),tiles[0][1].height+34),(20,20,20))
            draw=ImageDraw.Draw(canvas);font=ImageFont.load_default(size=15);x=0
            for label,tile in tiles:
                canvas.paste(tile,(x,34));draw.text((x+6,7),label,fill='white',font=font);x+=tile.width
            destination=args.output.with_name(args.output.stem+'-'+name+'.jpg')
            if destination.exists():raise ValueError('Detail comparison already exists.')
            canvas.save(destination,quality=96)
        report['background_detail_rois']=detail
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
