"""Read-only raw generation evaluation against actual Low and genuine references.

No beautification, restoration, gaze correction or selective sharpening is applied.
Comparison sheets are presentation artifacts; saved input pixels are not modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source','baseline','low','candidate','manifest','output-dir'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--exclude-reference', type=Path, action='append', default=[])
    parser.add_argument('--scope',choices=('full-frame','face-context-crop'),default='full-frame')
    parser.add_argument('--candidate-label', default='CANDIDATE HIGH',
                        help='Presentation label; use CANDIDATE BASE for a base-fidelity test.')
    parser.add_argument('--candidate-role',choices=('high-edit','source-fidelity'),default='high-edit',
                        help='A source-fidelity base repair must match the source, not a previously drifted raw.')
    parser.add_argument('--low-label', default='LOW')
    parser.add_argument('--expected-phone-style',choices=('active','inherited','inherited-native-edit','inherited-klein-edit','inherited-dev-edit','inherited-refcontrol-edit','experimental-native-prompt'),default='active',
                        help='Inherited variants must prove phone-on upstream provenance; not an active final-stage adapter.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new evaluation directory inside the project.')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    if args.candidate_role=='source-fidelity':
        if not (manifest.get('reference_mode')=='source_only' and len(manifest.get('references',[]))==1
                and manifest['references'][0]['sha256'].lower()==hashlib.sha256(args.source.read_bytes()).hexdigest()
                and manifest.get('postprocess') is False):
            raise ValueError('Source-fidelity role requires a single native reference matching the actual source; no postprocess.')
    with Image.open(args.candidate) as candidate:
        graph = json.loads(candidate.info.get('prompt','null'))
    reference_hashes = {ref['name']:ref['sha256'].lower() for ref in manifest['references']}
    for node in (graph or {}).values():
        if node.get('class_type')=='LoadImage' and 'is_changed' in node:
            if node['is_changed'] != [reference_hashes.get(node['inputs']['image'])]:
                raise RuntimeError('Executed reference hash does not match manifest.')
            del node['is_changed']
    if graph != manifest['prompt']:
        raise RuntimeError('Executed graph does not match manifest.')
    qwen_reference_layout=None
    if manifest.get('stage')=='qwen_native_high_edit':
        from upgrade_qwen_reference_acceptance import validate_reference_layout
        qwen_reference_layout=validate_reference_layout(manifest)
        if manifest.get('source_role')=='original_source':
            original=manifest['references'][0]
            original_bytes=Path(original['source_audit']).read_bytes()
            original_audit=json.loads(original_bytes.decode('utf-8-sig'))
            source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest()
            if (hashlib.sha256(original_bytes).hexdigest()!=original['source_audit_sha256']
                    or not original_audit.get('executed_png_graph_verified') or original_audit.get('postprocess_applied')
                    or original_audit['inputs']['SOURCE']['sha256'].lower()!=source_hash
                    or original['sha256']!=source_hash
                    or hashlib.sha256(Path(original['path']).read_bytes()).hexdigest()!=source_hash):
                raise RuntimeError('Direct-original input does not match the audited source.')
        if manifest.get('reference_packing')=='author32_explicit_native_latents':
            for reference,geometry in zip(manifest['references'],manifest['reference_packing_geometry']):
                with Image.open(reference['path']) as photo:
                    dimensions=list(ImageOps.exif_transpose(photo).size)
                if dimensions!=geometry['source_dimensions']:
                    raise RuntimeError('Explicit reference packing used incorrect source dimensions.')
        if qwen_reference_layout['reference_count']>=2:
            identity=manifest['references'][1]
            provenance_bytes=Path(identity['provenance_manifest']).read_bytes()
            if hashlib.sha256(provenance_bytes).hexdigest()!=identity['provenance_manifest_sha256'].lower():
                raise RuntimeError('Genuine identity provenance manifest changed.')
            records=json.loads(provenance_bytes.decode('utf-8-sig'))['records']
            matches=[r for r in records if r['id']==identity['provenance_record_id']
                     and r['kind']=='camera_still' and r['split']=='train'
                     and r['dataset_sha256']==identity['sha256']]
            if len(matches)!=1 or hashlib.sha256(Path(matches[0]['dataset_file']).read_bytes()).hexdigest()!=identity['sha256']:
                raise RuntimeError('Identity reference is not the recorded genuine training photograph.')
            if hashlib.sha256(Path(identity['path']).read_bytes()).hexdigest()!=identity['sha256']:
                raise RuntimeError('Staged identity photograph changed.')
        if qwen_reference_layout['reference_count']==3:
            expression=manifest['references'][2]
            expression_bytes=Path(expression['source_audit']).read_bytes()
            if hashlib.sha256(expression_bytes).hexdigest()!=expression['source_audit_sha256']:
                raise RuntimeError('Original expression source audit changed.')
            expression_audit=json.loads(expression_bytes.decode('utf-8-sig'))
            source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest()
            if (not expression_audit.get('executed_png_graph_verified') or expression_audit.get('postprocess_applied')
                    or expression_audit['inputs']['SOURCE']['sha256'].lower()!=expression['sha256']
                    or expression_audit['inputs']['BASE RAW']['sha256'].lower()!=manifest['references'][0]['sha256']
                    or source_hash!=expression['sha256']
                    or hashlib.sha256(Path(expression['path']).read_bytes()).hexdigest()!=source_hash):
                raise RuntimeError('Picture3 must match the audited original source for this exact base.')
    if manifest.get('turbo'):
        raise RuntimeError('Expected Turbo off.')
    if args.expected_phone_style=='active' and not manifest.get('phone_camera_style'):
        raise RuntimeError('Expected active phone-style adapter.')
    if args.expected_phone_style=='inherited-dev-edit':
        from upgrade_dev_high import validate_inputs
        if args.scope != 'full-frame':
            raise RuntimeError('Dev pilot must remain a native whole-image edit.')
        validate_inputs(manifest,args.source,args.baseline)
    if args.expected_phone_style=='inherited-refcontrol-edit':
        from upgrade_refcontrol_high import validate_inputs
        if args.scope != 'full-frame':
            raise RuntimeError('RefControl pilot must remain a native whole-image edit.')
        validate_inputs(manifest,args.source,args.baseline)
    if args.expected_phone_style=='inherited-klein-edit':
        baseline_report=Path(manifest['baseline_report'])
        baseline_bytes=baseline_report.read_bytes()
        upstream=json.loads(baseline_bytes.decode('utf-8-sig'))
        if not (args.scope=='full-frame' and manifest.get('reference_mode')=='four'
                and manifest.get('upstream_phone_camera_style') is True
                and manifest.get('phone_camera_style') is False
                and manifest.get('phone_camera_style_strength')==0
                and graph['3']['class_type']=='LoraLoaderModelOnly'
                and graph['3']['inputs']['strength_model']==0
                and graph['3']['inputs']['lora_name']==upstream['additional_loras'][0]['name']
                and upstream.get('phone_camera_style') is True and not upstream.get('turbo')
                and hashlib.sha256(baseline_bytes).hexdigest()==manifest['baseline_report_sha256'].lower()
                and args.baseline.resolve().parent==baseline_report.resolve().parent
                and hashlib.sha256(args.baseline.read_bytes()).hexdigest()==manifest['references'][0]['sha256'].lower()):
            raise RuntimeError('Klein secondary edit must inherit phone-on raw with a verified inactive second adapter.')
    if args.expected_phone_style=='experimental-native-prompt':
        if not (manifest.get('stage')=='qwen_native_high_edit' and args.scope=='full-frame'
                and manifest.get('source_role')=='original_source'
                and manifest.get('phone_appearance_mode')=='experimental_native_prompt_only'
                and manifest.get('lightning') is False
                and 'phone photograph' in manifest.get('effective_prompt','')
                and not any(n['class_type'].startswith('LoraLoader') for n in graph.values())):
            raise RuntimeError('Expected explicitly experimental native phone prompt, not a claimed phone LoRA.')
    if args.expected_phone_style=='inherited' and not (
            args.scope=='face-context-crop' and manifest.get('upstream_phone_camera_style') is True
            and manifest.get('phone_camera_style') is False and manifest.get('phone_camera_style_strength')==0):
        raise RuntimeError('Inherited style requires a phone-on upstream baseline and explicitly zero crop-stage adapter.')
    if args.expected_phone_style=='inherited-native-edit':
        baseline_report=Path(manifest['baseline_report'])
        baseline_bytes=baseline_report.read_bytes()
        upstream=json.loads(baseline_bytes.decode('utf-8-sig'))
        if not (manifest.get('stage')=='qwen_native_high_edit' and args.scope=='full-frame'
                and manifest.get('upstream_phone_camera_style') is True
                and manifest.get('phone_camera_style') is False
                and manifest.get('phone_camera_style_strength')==0
                and manifest.get('lightning') is False
                and upstream.get('phone_camera_style') is True and not upstream.get('turbo')
                and hashlib.sha256(baseline_bytes).hexdigest()==manifest['baseline_report_sha256'].lower()
                and not any(n['class_type'].startswith('LoraLoader') for n in graph.values())):
            raise RuntimeError('Native-edit inherited style provenance failed.')

    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def read(path):
        with Image.open(path) as image:
            return np.array(ImageOps.exif_transpose(image).convert('RGB'))
    paths = {'SOURCE':args.source,'BASE RAW':args.baseline,'LOW':args.low,'CANDIDATE HIGH':args.candidate}
    photos = {name:read(path) for name,path in paths.items()}
    analyzer = FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
                           providers=['CPUExecutionProvider'],
                           allowed_modules=['detection','recognition','landmark_3d_68'])
    detection_size=(640,640)
    analyzer.prepare(ctx_id=-1,det_size=detection_size)
    def face(rgb):
        pad=round(max(rgb.shape[:2])*.25) if args.scope=='face-context-crop' else 0
        padded=cv2.copyMakeBorder(rgb,pad,pad,pad,pad,cv2.BORDER_CONSTANT,value=(127,127,127)) if pad else rgb
        faces=analyzer.get(cv2.cvtColor(padded,cv2.COLOR_RGB2BGR))
        if len(faces)!=1: raise ValueError(f'Expected one face; found{len(faces)}')
        if pad:
            faces[0].bbox-=np.array([pad,pad,pad,pad],np.float32)
            faces[0].kps-=np.array([pad,pad],np.float32)
        return faces[0]
    refs=sorted((root/'datasets/mitch-identity-stills-v3/validation').glob('val_*.jpg'))
    if len(refs)!=6: raise RuntimeError('Expected six genuine references before exclusions.')
    excluded={digest(path) for path in [args.source,*args.exclude_reference]}
    refs=[path for path in refs if digest(path) not in excluded]
    if qwen_reference_layout and qwen_reference_layout['reference_count']>=2:
        if any(digest(path)==manifest['references'][1]['sha256'] for path in refs):
            raise RuntimeError('Conditioning identity photo must not also be a scoring reference.')
    if len(refs)<2: raise RuntimeError('At least two independent genuine photos required.')
    embeddings=[face(read(path)).normed_embedding for path in refs]
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    sys.path.insert(0,str(root/'custom_nodes/ComfyUI-AIToolkit-Training'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks,_eye_measurement,_EYES
    from experimental_upgrade_smile_balance import measure_smile
    results={};detected={};landmarks={};smiles={}
    for name,rgb in photos.items():
        try: detected[name]=face(rgb)
        except ValueError as exc: raise ValueError(f'{name}: {exc}') from exc
        landmarks[name],_= _detect_refined_landmarks(rgb)
        smiles[name]=measure_smile(landmarks[name])
        results[name]={
            'identity_centroid':float(detected[name].normed_embedding@centroid),
            'per_reference':[float(detected[name].normed_embedding@ref) for ref in embeddings],
            'pose_pitch_yaw_roll':[float(v) for v in detected[name].pose],
            'bbox_xyxy':[float(v) for v in detected[name].bbox],
            'mouth_opening_ratio':float(smiles[name]['opening_ratio']),
            'mouth_corner_coordinates':smiles[name]['corner_coordinates'].tolist(),
            'source_mouth_corner_error':float(np.linalg.norm(smiles[name]['corner_coordinates']-smiles['SOURCE']['corner_coordinates'],axis=1).mean()),
            'eye_coordinates':[_eye_measurement(landmarks[name],definition)['coordinate'].tolist() for definition in _EYES],
        }
    candidate=results['CANDIDATE HIGH'];base=results['BASE RAW'];source=results['SOURCE']
    diagnostics={
        'identity_delta_from_raw':candidate['identity_centroid']-base['identity_centroid'],
        'identity_delta_from_source':candidate['identity_centroid']-source['identity_centroid'],
        'max_pose_delta_from_raw_degrees':float(np.max(np.abs(np.array(candidate['pose_pitch_yaw_roll'])-base['pose_pitch_yaw_roll']))),
        'max_pose_delta_from_source_degrees':float(np.max(np.abs(np.array(candidate['pose_pitch_yaw_roll'])-source['pose_pitch_yaw_roll']))),
        'max_source_relative_eye_delta':float(np.max(np.abs(np.array(candidate['eye_coordinates'])-source['eye_coordinates']))),
        'caution':'Landmark redetection and face embeddings are diagnostics, not attractiveness or exact-pixel guarantees.'}
    def normalized_face_center(name):
        bbox=detected[name].bbox
        height,width=photos[name].shape[:2]
        return (bbox[:2]+bbox[2:])*.5/np.array([width,height])
    diagnostics['face_center_delta_from_source_frame_fraction']=(
        normalized_face_center('CANDIDATE HIGH')-normalized_face_center('SOURCE')).tolist()
    failures=[]
    from upgrade_expression_acceptance import identity_retention_check
    diagnostics['identity_retention_check']=identity_retention_check(
        source['identity_centroid'],base['identity_centroid'],candidate['identity_centroid'],args.candidate_role)
    if not diagnostics['identity_retention_check']['passed']:
        failures.append('Likeness gate failed.')
    if args.candidate_role=='high-edit' and diagnostics['max_pose_delta_from_raw_degrees']>3:
        failures.append('Pose drift needs rejection/review.')
    if diagnostics['max_pose_delta_from_source_degrees']>3:
        failures.append('Source head pose was not preserved, even if pose matches the generated baseline.')
    if max(abs(v) for v in diagnostics['face_center_delta_from_source_frame_fraction'])>.03:
        failures.append('Source face placement moved over 3 percent of a frame dimension; review framing.')
    from upgrade_expression_acceptance import closed_lip_check
    diagnostics['closed_lip_check']=closed_lip_check(source['mouth_opening_ratio'],candidate['mouth_opening_ratio'])
    if not diagnostics['closed_lip_check']['passed']:
        failures.append('Mouth-opening diagnostic exceeds the closed-lip requirement; inspect teeth.')
    args.output_dir.mkdir(parents=True)
    def sheet(names,path,box=None,width=650):
        tiles=[]
        for name in names:
            tile=Image.fromarray(photos[name])
            if box=='face':
                # Each face needs its own crop when testing a repaired position.
                # Reusing the failed baseline's box clipped the genuine source.
                x0,y0,x1,y1=detected[name].bbox
                margin=(x1-x0)*.12
                tile=tile.crop((max(0,int(x0-margin)),max(0,int(y0-margin)),
                                min(tile.width,int(x1+margin)),min(tile.height,int(y1+margin))))
                # Match presentation scale across different native output sizes.
                tile=tile.resize((round(tile.width*420/tile.height),420),Image.Resampling.LANCZOS)
            elif box:
                # Normalize full-frame coordinates for differing source/output sizes.
                w,h=tile.size; bw,bh=photos['BASE RAW'].shape[1],photos['BASE RAW'].shape[0]
                tile=tile.crop(tuple(round(v*(w/bw if i%2==0 else h/bh)) for i,v in enumerate(box)))
            tile.thumbnail((width,1000),Image.Resampling.LANCZOS)
            tiles.append((name,tile))
        canvas=Image.new('RGB',(sum(t.width for _,t in tiles),max(t.height for _,t in tiles)+42),(22,22,22))
        draw=ImageDraw.Draw(canvas);font=ImageFont.load_default(size=18);x=0
        for name,tile in tiles:
            label=({'CANDIDATE HIGH':args.candidate_label,'LOW':args.low_label}.get(name,name)
                   +(' (CROP)' if args.scope=='face-context-crop' else ''))
            canvas.paste(tile,(x,42));draw.text((x+10,10),label,fill='white',font=font);x+=tile.width
        canvas.save(path,quality=96)
    x0,y0,x1,y1=detected['BASE RAW'].bbox
    box=(max(0,x0-30),max(0,y0-30),min(photos['BASE RAW'].shape[1],x1+30),min(photos['BASE RAW'].shape[0],y1+30))
    names=['SOURCE','LOW','CANDIDATE HIGH']
    sheet(names,args.output_dir/'source-low-high-face.jpg','face')
    sheet(names,args.output_dir/'source-low-high-full.jpg')
    sheet(names,args.output_dir/'source-low-high-thumbnail.jpg',width=320)
    sheet(['BASE RAW','CANDIDATE HIGH'],args.output_dir/'raw-high-face.jpg','face')
    report={'status':'evaluated_not_promoted','validation_scope':args.scope,
            'candidate_role':args.candidate_role,
            'pose_acceptance_reference':'source and raw' if args.candidate_role=='high-edit' else 'source; previous raw drift is diagnostic, not the repair target',
            'presentation_labels':{'CANDIDATE HIGH':args.candidate_label,'LOW':args.low_label},
            'face_comparison_presentation':'Individual face bounds; crops resampled to common420px height. Full-frame/native files retain actual dimensions.',
            'stage_key_note':'CANDIDATE HIGH is the legacy result key; the explicit presentation label records what was actually evaluated.',
            'face_detection_size':list(detection_size),
            'face_detection_padding_ratio':.25 if args.scope=='face-context-crop' else 0,
            'expected_phone_style':args.expected_phone_style,
            'whole_frame_integration_validated':False,
            'results':results,'diagnostics':diagnostics,
            'failures':failures,'visual_review_required':True,'postprocess_applied':False,
            'manifest':str(args.manifest),'executed_png_graph_verified':True,
            'qwen_reference_layout':qwen_reference_layout,
            'inputs':{name:{'path':str(path),'sha256':digest(path)} for name,path in paths.items()},
            'genuine_references':[{'path':str(path),'sha256':digest(path)} for path in refs]}
    (args.output_dir/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'results':results,'diagnostics':diagnostics,'failures':failures},indent=2))
    if failures: raise SystemExit(1)


if __name__=='__main__': main()
