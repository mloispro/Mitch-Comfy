"""CPU evaluation of a registered generated-variant blend; no generation queued."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps, PngImagePlugin

from experimental_upgrade_registered_blend import registered_blend


def validate_intermediate_wrapper(graph, source_sha256, seed):
    """Validate the two observed public wrappers, not an embedded native graph."""
    try:
        valid=(set(graph)=={'1','2'}
            and graph['1']['class_type']=='LoadImage'
            and graph['1'].get('is_changed')==[source_sha256]
            and graph['2']['class_type'] in {
                'Flux2Klein9BPhotoRealismUpgradeV1',
                'Flux2Klein9BPhotoRealismUpgradeV11'}
            and graph['2']['inputs']['source_photo']==['1',0]
            and graph['2']['inputs']['seed']==seed
            and graph['2']['inputs']['phone_camera_style'] is True)
    except (KeyError, TypeError):
        valid=False
    if not valid:
        raise ValueError('Unsupported/unverified intermediate base provenance.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-audit',type=Path,required=True)
    parser.add_argument('--amount',type=float,default=.4)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new project-local output directory.')
    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
    audit=load(args.native_audit)
    if not audit['executed_png_graph_verified'] or audit['postprocess_applied']:
        raise ValueError('Expected a verified raw native-variant audit.')
    manifest_path=root/audit['manifest'];manifest=load(manifest_path)
    if (manifest['reference_mode']!='four' or manifest['turbo']
            or not manifest['phone_camera_style'] or manifest['phone_camera_style_strength']!=.25):
        raise ValueError('Expected the verified four-reference phone-on/non-Turbo variant.')
    baseline_path=root/manifest['baseline_report'];baseline=load(baseline_path)
    expected_models={baseline[key].lower() for key in ('model_sha256','text_encoder_sha256','vae_sha256','lora_sha256')}
    expected_models.add(baseline['additional_loras'][0]['sha256'].lower())
    if expected_models!={record['sha256'].lower() for record in manifest['verified_models']}:
        raise ValueError('Base and variant model provenance differ.')
    if not (baseline['seed']==manifest['seed'] and baseline['steps']==manifest['steps']==50
            and baseline['cfg']==manifest['cfg']==4 and baseline['lora_strength']==manifest['identity_strength']==.9
            and baseline['phone_camera_style'] and not baseline['turbo']):
        raise ValueError('Base and variant sampling/identity policy differ.')
    for reference in manifest['references']:
        if digest(Path(reference['path']))!=reference['sha256'].lower():
            raise ValueError('Native reference file changed.')
    paths={name:root/audit['inputs'][key]['path'] for name,key in (
        ('SOURCE','SOURCE'),('BASE RAW','BASE RAW'),('LOW','LOW'),('NATIVE BEAUTY','CANDIDATE HIGH'))}
    photos={}
    for (name,path),key in zip(paths.items(),('SOURCE','BASE RAW','LOW','CANDIDATE HIGH')):
        if digest(path)!=audit['inputs'][key]['sha256']: raise ValueError(f'Changed image: {name}')
        with Image.open(path) as image: photos[name]=np.array(ImageOps.exif_transpose(image).convert('RGB'))
    def graph_from_png(path):
        with Image.open(path) as image:
            if 'prompt' not in image.info: return None
            graph=json.loads(image.info['prompt'])
        for node in graph.values():
            if node['class_type']=='LoadImage': node.pop('is_changed',None)
        return graph
    if graph_from_png(paths['NATIVE BEAUTY'])!=manifest['prompt']:
        raise ValueError('Native variant PNG no longer matches the recorded graph.')
    base_graph_path=baseline_path.parent/baseline['prompt_graph']
    base_graph=load(base_graph_path)
    base_embedded_graph=graph_from_png(paths['BASE RAW'])
    if base_embedded_graph is None:
        # The public Upgrade node saves its before-polish intermediate without
        # PNG prompt metadata. Do not pretend the wrapper sidecar is embedded
        # execution evidence: require the previously audited bytes and validate
        # the recorded wrapper/source separately, with that limitation reported.
        validate_intermediate_wrapper(base_graph,audit['inputs']['SOURCE']['sha256'],manifest['seed'])
    else:
        clean_base=json.loads(json.dumps(base_graph))
        for node in clean_base.values():
            if node['class_type']=='LoadImage': node.pop('is_changed',None)
        if base_embedded_graph!=clean_base:
            raise ValueError('Base PNG does not match its recorded production graph.')
    sys.path.insert(0,str(root/'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0,str(root.parent/'ComfyUI'))
    import flux2_klein9b_source_gaze_lock as gaze
    import flux2_klein9b_deterministic_polish as common
    from experimental_upgrade_smile_balance import measure_smile
    from upgrade_expression_acceptance import closed_lip_check,identity_retention_check
    torch.set_num_threads(4)
    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
        providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found=analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(found)!=1: raise ValueError('Exactly one face is required.')
        return found[0]
    points={name:gaze._detect_refined_landmarks(rgb)[0] for name,rgb in photos.items() if name in ('BASE RAW','NATIVE BEAUTY')}
    hair=common.build_semantic_hair_mask(photos['BASE RAW'],face(photos['BASE RAW']).bbox)
    args.output_dir.mkdir(parents=True)
    provenance={'native_audit':str(args.native_audit),'native_audit_sha256':digest(args.native_audit),
        'variant_manifest_sha256':digest(manifest_path),'base_report_sha256':digest(baseline_path),
        'base_graph_sha256':digest(base_graph_path),'variant_executed_graph_verified':True,
        'base_has_embedded_graph':base_embedded_graph is not None,
        'base_provenance_scope':'Previously audited exact intermediate PNG bytes plus recorded wrapper/source/engine sidecar; no embedded graph in this public-node intermediate.' if base_embedded_graph is None else 'Embedded PNG graph matches sidecar.',
        'inputs':{name:{'path':str(path),'sha256':digest(path)} for name,path in paths.items()},
        'amount':args.amount,'diffusion_runs':0,'production_changed':False,
        'blend_module_sha256':digest(Path(__file__).with_name('experimental_upgrade_registered_blend.py'))}
    try:
        blend,mask,blend_report,aligned=registered_blend(photos['BASE RAW']/255,
            photos['NATIVE BEAUTY']/255,points['BASE RAW'],points['NATIVE BEAUTY'],hair,args.amount)
    except Exception as exc:
        (args.output_dir/'failure.json').write_text(json.dumps({**provenance,'error':str(exc)},indent=2),encoding='utf-8')
        raise
    to_rgb=lambda array:np.rint(np.clip(array,0,1)*255).astype(np.uint8)
    photos['BLEND BEFORE GAZE']=to_rgb(blend)
    finished,gaze_mask,gaze_report=gaze.apply_source_gaze_lock(
        torch.from_numpy(photos['SOURCE'].astype(np.float32)/255).unsqueeze(0),
        torch.from_numpy(blend).unsqueeze(0))
    photos['REGISTERED HIGH']=to_rgb(finished[0].numpy())
    union=(mask>0)|(gaze_mask[0,:,:,0].numpy()>0)
    outside=int(np.abs(photos['REGISTERED HIGH'].astype(np.int16)-photos['BASE RAW'].astype(np.int16))[~union].max(initial=0))
    refs=audit['genuine_references'];embeddings=[]
    if len(refs)<2: raise ValueError('At least two genuine references required.')
    for record in refs:
        path=root/record['path']
        if digest(path)!=record['sha256']: raise ValueError('Genuine scoring reference changed.')
        with Image.open(path) as image: rgb=np.array(ImageOps.exif_transpose(image).convert('RGB'))
        embeddings.append(face(rgb).normed_embedding)
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    detections={name:face(rgb) for name,rgb in photos.items()}
    scores={name:float(detection.normed_embedding@centroid) for name,detection in detections.items()}
    source_points=gaze._detect_refined_landmarks(photos['SOURCE'])[0]
    final_points=gaze._detect_refined_landmarks(photos['REGISTERED HIGH'])[0]
    checks={'likeness':identity_retention_check(scores['SOURCE'],scores['BASE RAW'],scores['REGISTERED HIGH'],'high-edit'),
        'closed_lips':closed_lip_check(measure_smile(source_points)['opening_ratio'],measure_smile(final_points)['opening_ratio']),
        'maximum_source_pose_error_degrees':float(np.max(np.abs(detections['REGISTERED HIGH'].pose-detections['SOURCE'].pose))),
        'maximum_horizontal_gaze_error':max(item['horizontal_error_after'] for item in gaze_report['eye_reports']),
        'maximum_source_eye_coordinate_error':float(max(np.abs(gaze._eye_measurement(final_points,eye)['coordinate']-
            gaze._eye_measurement(source_points,eye)['coordinate']).max() for eye in gaze._EYES)),
        'outside_blend_and_gaze_pixel_error':outside}
    failures=[]
    if not checks['likeness']['passed']: failures.append('Likeness diagnostic failed; visual tradeoff review required.')
    if not checks['closed_lips']['passed']: failures.append('Closed-lip requirement failed.')
    if checks['maximum_source_pose_error_degrees']>3: failures.append('Source pose diagnostic failed.')
    if checks['maximum_horizontal_gaze_error']>.02: failures.append('Horizontal gaze diagnostic failed.')
    if outside: failures.append('Exterior preservation failed.')
    metadata=PngImagePlugin.PngInfo();metadata.add_text('registered_variant_blend',json.dumps(provenance))
    Image.fromarray(photos['REGISTERED HIGH']).save(args.output_dir/'high.png',pnginfo=metadata)
    Image.fromarray(photos['BLEND BEFORE GAZE']).save(args.output_dir/'blend-before-gaze.png')
    Image.fromarray(to_rgb(mask)).save(args.output_dir/'blend-support.png')
    for name,rgb in aligned.items(): Image.fromarray(to_rgb(rgb)).save(args.output_dir/(name+'.png'))
    def sheet(names,filename,face_crop=False,width=360):
        tiles=[]
        for name in names:
            tile=Image.fromarray(photos[name])
            if face_crop:
                box=detections[name].bbox;margin=(box[2]-box[0])*.12
                tile=tile.crop(tuple(np.rint(box+[-margin,-margin,margin,margin]).astype(int)))
                tile=tile.resize((round(tile.width*420/tile.height),420),Image.Resampling.LANCZOS)
            else: tile.thumbnail((width,900),Image.Resampling.LANCZOS)
            tiles.append((name,tile))
        canvas=Image.new('RGB',(sum(tile.width for _,tile in tiles),max(tile.height for _,tile in tiles)+36),(22,22,22))
        draw=ImageDraw.Draw(canvas);font=ImageFont.load_default(size=16);x=0
        for name,tile in tiles:
            draw.text((x+6,8),name,font=font,fill='white');canvas.paste(tile,(x,36));x+=tile.width
        canvas.save(args.output_dir/filename,quality=97)
    sheet(['SOURCE','LOW','REGISTERED HIGH'],'source-low-high-face.jpg',True)
    sheet(['SOURCE','LOW','REGISTERED HIGH'],'source-low-high-thumbnail.jpg')
    sheet(['BASE RAW','NATIVE BEAUTY','REGISTERED HIGH'],'generated-variants-face.jpg',True)
    result={**provenance,'status':'evaluated_not_promoted','blend':blend_report,'gaze':gaze_report,
        'identity_centroid':scores,'genuine_references':refs,'checks':checks,'failures':failures,
        'output_sha256':digest(args.output_dir/'high.png'),
        'limitation':'Composited generated face region, not native output, identity lock, attractiveness score or three-photo acceptance. No common polish applied.'}
    (args.output_dir/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'scores':scores,'checks':checks,'failures':failures,'blend':blend_report},indent=2))
    if failures: raise SystemExit(1)


if __name__=='__main__': main()
