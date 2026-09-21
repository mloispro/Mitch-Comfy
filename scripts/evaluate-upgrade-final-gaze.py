"""Replay the existing finish on a verified native candidate.

CPU-only; never claims that a geometric diagnostic establishes attractiveness.
Optional common polish disables the legacy forced smile and cheek highlight in
this isolated process only. It does not apply the old High geometry a second time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps, PngImagePlugin


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-audit',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--common-polish',action='store_true')
    parser.add_argument('--source-lid-curve-from-raw',action='store_true',
                        help='Isolated CPU component test: use the audited base raw for both Low and High, adding only the new source upper-lid curve to High.')
    parser.add_argument('--native-high-skip-skin-smoothing',action='store_true',
                        help='Diagnostic only: skip duplicate skin/forehead/under-eye smoothing on native High; Low is unchanged.')
    parser.add_argument('--comfy-root',type=Path)
    parser.add_argument('--comparison-label',default='STRONGER HIGH',
                        help='Presentation label for the experimental finished candidate; not an acceptance claim.')
    args=parser.parse_args()
    if args.native_high_skip_skin_smoothing and not args.common_polish:
        raise ValueError('Skipping duplicate smoothing requires common polish.')
    if args.source_lid_curve_from_raw and (not args.common_polish or args.native_high_skip_skin_smoothing):
        raise ValueError('Source-lid isolation requires identical common polish on both branches.')
    root=Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new output directory within the project.')
    native=json.loads(args.native_audit.read_text(encoding='utf-8-sig'))
    candidate_role='high-edit' if args.source_lid_curve_from_raw else native.get('candidate_role','high-edit')
    candidate_label='BASE' if candidate_role=='source-fidelity' else 'HIGH'
    if not native.get('executed_png_graph_verified') or native.get('postprocess_applied'):
        raise ValueError('Expected a verified, unretouched native-candidate audit.')
    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def read_record(record):
        path=root/record['path']
        if digest(path)!=record['sha256']:
            raise ValueError(f'Input changed since native audit: {path}')
        with Image.open(path) as opened:
            return np.array(ImageOps.exif_transpose(opened).convert('RGB'))
    source=read_record(native['inputs']['SOURCE'])
    candidate_input_key='BASE RAW' if args.source_lid_curve_from_raw else 'CANDIDATE HIGH'
    candidate=read_record(native['inputs'][candidate_input_key])
    sys.path.insert(0,str(root/'custom_nodes/ComfyUI-AIToolkit-Training'))
    import flux2_klein9b_source_gaze_lock as gaze
    def tensor(rgb): return torch.from_numpy(rgb.astype(np.float32)/255).unsqueeze(0)
    def pixels(photo): return np.round(photo[0].numpy()*255).clip(0,255).astype(np.uint8)
    torch.set_num_threads(4)
    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
                         providers=['CPUExecutionProvider'],
                         allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        faces=analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(faces)!=1: raise ValueError('Exactly one face required.')
        return faces[0]
    def polish(rgb,high_candidate=False):
        import flux2_klein9b_deterministic_polish as common
        from upgrade_common_polish_policy import common_polish_policy
        detected=face(rgb)
        hair=common.build_semantic_hair_mask(rgb,detected.bbox)
        skip_smoothing=bool(high_candidate and args.native_high_skip_skin_smoothing)
        # These are process-local overrides, restored even if the call fails.
        with common_polish_policy(common,native_high_skip_smoothing=skip_smoothing) as overrides:
            result,mask,detail=common.apply_deterministic_face_polish(
                tensor(rgb),detected.bbox,detected.kps,hair)
        detail['isolated_overrides']=overrides
        detail['operations']=[op for op in detail['operations']
                              if op not in ('closed-mouth corner lift','cheek highlight and jaw-contour lighting')]
        detail['operations'].append('jaw-contour lighting; cheek highlight disabled')
        if skip_smoothing:
            skipped={'face-local pore-preserving fine-texture attenuation',
                     'forehead line attenuation inside the existing hairline',
                     'under-eye fatigue attenuation'}
            detail['operations']=[op for op in detail['operations'] if op not in skipped]
            detail['operations'].append('native High texture retained without duplicate skin smoothing')
        detail['module_sha256']=digest(Path(common.__file__))
        return pixels(result),mask[0,:,:,0].numpy()>0,detail
    pre_gaze=candidate
    polish_selected=np.zeros(candidate.shape[:2],dtype=bool)
    polish_report=None
    matched_low=None
    low_report=None
    lid_report=None
    lid_selected=np.zeros(candidate.shape[:2],dtype=bool)
    before_lids=None
    if args.common_polish:
        sys.path.insert(0,str(args.comfy_root or root.parent/'ComfyUI'))
        pre_gaze,polish_selected,polish_report=polish(candidate,high_candidate=True)
        baseline=read_record(native['inputs']['BASE RAW'])
        low_pre_gaze,low_polish_mask,low_polish_report=polish(baseline)
        low_tensor,low_gaze_mask,low_gaze_report=gaze.apply_source_gaze_lock(tensor(source),tensor(low_pre_gaze))
        matched_low=pixels(low_tensor)
        low_selected=low_polish_mask|(low_gaze_mask[0,:,:,0].numpy()>0)
        low_report={'label':'REVISED LOW (no forced smile or cheek highlight)',
                    'common_polish':low_polish_report,'source_gaze':low_gaze_report,
                    'outside_union_mask_pixel_error':int(np.abs(matched_low.astype(np.int16)-baseline.astype(np.int16))[~low_selected].max(initial=0))}
    if args.source_lid_curve_from_raw:
        from experimental_upgrade_source_lids import apply_source_lids,upper_lid_targets
        from flux2_klein9b_attractiveness import _UPPER_LIDS
        import flux2_klein9b_deterministic_polish as common
        before_lids=pre_gaze.copy()
        lid_source_points,_=gaze._detect_refined_landmarks(source)
        lid_before_points,_=gaze._detect_refined_landmarks(before_lids)
        hair=common.build_semantic_hair_mask(before_lids,face(before_lids).bbox)
        changed,lid_mask,lid_report=apply_source_lids(before_lids.astype(np.float32)/255,
                                                     lid_before_points,lid_source_points,hair)
        pre_gaze=np.round(changed*255).clip(0,255).astype(np.uint8)
        lid_selected=lid_mask>0
        lid_report['outside_lid_mask_pixel_error']=int(np.abs(pre_gaze.astype(np.int16)-before_lids.astype(np.int16))[~lid_selected].max(initial=0))
        lid_report['module_sha256']=digest(Path(__file__).with_name('experimental_upgrade_source_lids.py'))
        lid_report['before_sha256_pixels']=hashlib.sha256(before_lids.tobytes()).hexdigest()
        lid_report['after_sha256_pixels']=hashlib.sha256(pre_gaze.tobytes()).hexdigest()
    corrected,mask,report=gaze.apply_source_gaze_lock(tensor(source),tensor(pre_gaze))
    finished=pixels(corrected)
    selected=mask[0,:,:,0].numpy()>0
    union_selected=selected|polish_selected|lid_selected
    outside_error=int(np.abs(finished.astype(np.int16)-pre_gaze.astype(np.int16))[~selected].max(initial=0))
    union_error=int(np.abs(finished.astype(np.int16)-candidate.astype(np.int16))[~union_selected].max(initial=0))
    refs=native['genuine_references']
    if len(refs)<2: raise ValueError('At least two independent genuine references required.')
    embeddings=[face(read_record(record)).normed_embedding for record in refs]
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    before_face,after_face=face(candidate),face(finished)
    scores={'before':float(before_face.normed_embedding@centroid),
            'pre_gaze':float(face(pre_gaze).normed_embedding@centroid),
            'after':float(after_face.normed_embedding@centroid)}
    if matched_low is not None:
        scores['matched_revised_low']=float(face(matched_low).normed_embedding@centroid)
    maximum=max(item['horizontal_error_after'] for item in report['eye_reports'])
    source_points,_=gaze._detect_refined_landmarks(source)
    before_points,_=gaze._detect_refined_landmarks(pre_gaze)
    after_points,_=gaze._detect_refined_landmarks(finished)
    if lid_report is not None:
        observed={}
        for label,points in (('before_lids',lid_before_points),('after_lids',before_points),('after_final_gaze',after_points)):
            errors=[]
            for ids in _UPPER_LIDS:
                target,width,_,_=upper_lid_targets(points,lid_source_points,ids)
                errors.append(float(np.linalg.norm(points[list(ids[1:-1])]-target[1:-1],axis=1).mean()/width))
            observed[label]=errors
        lid_report['redetected_normalized_source_curvature_errors']=observed
        lid_report['redetection_note']='Separate from achieved field geometry; landmark redetection is approximate and must not substitute for visual inspection.'
    two_dimensional=[]
    for definition in gaze._EYES:
        original=gaze._eye_measurement(source_points,definition)
        fixed=gaze._eye_measurement(before_points,definition)
        after=gaze._eye_measurement(after_points,definition)
        target=(fixed['image_left']+fixed['horizontal']*original['coordinate'][0]
                +fixed['vertical']*original['coordinate'][1])
        error=after['iris_center']-target
        two_dimensional.append({'name':definition['name'],
            'before_target_error_pixels':float(np.linalg.norm(fixed['iris_center']-target)),
            'after_target_error_pixels':float(np.linalg.norm(error)),
            'after_target_error_eye_width_fraction':float(np.linalg.norm(error)/fixed['eye_width']),
            'note':'Includes horizontal and vertical displacement in the pre-gaze eyelid frame; diagnostic only.'})
    from experimental_upgrade_smile_balance import measure_smile
    from upgrade_expression_acceptance import closed_lip_check,identity_retention_check
    source_face=face(source)
    final_checks={
        'closed_lips':closed_lip_check(measure_smile(source_points)['opening_ratio'],measure_smile(after_points)['opening_ratio']),
        'max_pose_delta_from_source_degrees':float(np.max(np.abs(after_face.pose-source_face.pose))),
        'identity_retention':identity_retention_check(
            float(source_face.normed_embedding@centroid),native['results']['BASE RAW']['identity_centroid'],
            scores['after'],candidate_role)}
    audit={'status':'experimental_not_promoted','native_audit':str(args.native_audit),
           'source_lid_component_only':args.source_lid_curve_from_raw,
           'candidate_input_key':candidate_input_key,'candidate_input_record':native['inputs'][candidate_input_key],
           'source_lid_curve':lid_report,
           'historical_native_candidate_failures_note':'Original audit candidate was not reused; this component starts from its hash-verified BASE RAW.' if args.source_lid_curve_from_raw else None,
           'comparison_label':args.comparison_label,
           'native_high_skip_skin_smoothing':args.native_high_skip_skin_smoothing,
           'candidate_role':candidate_role,
           'native_audit_sha256':digest(args.native_audit),'native_failures_retained':native['failures'],
           'input_records':native['inputs'],'genuine_references':refs,'source_gaze':report,
           'identity_centroid':scores,'outside_mask_pixel_error':outside_error,
           'common_polish_applied':args.common_polish,'common_polish':polish_report,
           'matched_revised_low':low_report,'final_checks':final_checks,
           'outside_polish_and_gaze_union_pixel_error':union_error,
           'maximum_horizontal_source_error':maximum,
           'two_dimensional_source_gaze_diagnostic':two_dimensional,
           'horizontal_gaze_check_passed':maximum<=.02 and outside_error==0 and union_error==0,
           'limitation':'Horizontal gaze check only; not vertical-gaze, source-pose, identity or attractiveness approval.',
           'gaze_module_sha256':digest(Path(gaze.__file__)),'diffusion_runs':0,'local_only':True}
    args.output_dir.mkdir(parents=True)
    metadata=PngImagePlugin.PngInfo()
    metadata.add_text('postprocess',json.dumps({'profile':gaze.SOURCE_GAZE_LOCK_PROFILE,
                      'common_polish_applied':args.common_polish,
                      'common_polish_overrides':polish_report['isolated_overrides'] if polish_report else None,
                      'input_sha256':native['inputs'][candidate_input_key]['sha256'],
                      'source_lid_component_only':args.source_lid_curve_from_raw,
                      'source_sha256':native['inputs']['SOURCE']['sha256']}))
    Image.fromarray(finished).save(args.output_dir/f'{candidate_label.lower()}-source-gaze.png',pnginfo=metadata)
    Image.fromarray(selected.astype(np.uint8)*255).save(args.output_dir/'gaze-mask.png')
    if before_lids is not None:
        Image.fromarray(before_lids).save(args.output_dir/'before-lid-correction.png')
        Image.fromarray(lid_selected.astype(np.uint8)*255).save(args.output_dir/'lid-correction-mask.png')
    if args.common_polish:
        Image.fromarray(pre_gaze).save(args.output_dir/'high-common-polish-before-gaze.png')
        Image.fromarray(polish_selected.astype(np.uint8)*255).save(args.output_dir/'common-polish-mask.png')
        Image.fromarray(union_selected.astype(np.uint8)*255).save(args.output_dir/'finish-union-mask.png')
        Image.fromarray(matched_low).save(args.output_dir/'revised-low-source-gaze.png')
    tiles=[]
    for rgb in (source,candidate,finished):
        bounds=face(rgb).bbox
        margin=(bounds[2]-bounds[0])*.12
        box=bounds+np.array([-margin,-margin,margin,margin])
        tile=Image.fromarray(rgb).crop(tuple(box.astype(int)))
        tiles.append(tile.resize((round(tile.width*420/tile.height),420),Image.Resampling.LANCZOS))
    canvas=Image.new('RGB',(sum(tile.width for tile in tiles),max(tile.height for tile in tiles)+40),(22,22,22))
    draw=ImageDraw.Draw(canvas);font=ImageFont.load_default(size=18);left=0
    for label,tile in zip(('SOURCE',f'NATIVE {candidate_label}',f'{candidate_label} + SOURCE GAZE'),tiles):
        canvas.paste(tile,(left,40));draw.text((left+10,10),label,font=font,fill='white');left+=tile.width
    canvas.save(args.output_dir/'source-native-gaze-face.jpg',quality=96)
    if matched_low is not None:
        for face_crop,filename in ((True,'source-low-high-face.jpg'),(False,'source-low-high-thumbnail.jpg')):
            comparison=[]
            for label,rgb in zip(('SOURCE','REVISED LOW',args.comparison_label),(source,matched_low,finished)):
                tile=Image.fromarray(rgb)
                if face_crop:
                    bounds=face(rgb).bbox;margin=(bounds[2]-bounds[0])*.12
                    box=bounds+np.array([-margin,-margin,margin,margin])
                    tile=tile.crop(tuple(box.astype(int)))
                    tile=tile.resize((round(tile.width*420/tile.height),420),Image.Resampling.LANCZOS)
                else:
                    tile.thumbnail((330,450),Image.Resampling.LANCZOS)
                comparison.append((label,tile))
            sheet=Image.new('RGB',(sum(t.width for _,t in comparison),max(t.height for _,t in comparison)+40),(22,22,22))
            draw=ImageDraw.Draw(sheet);left=0
            for label,tile in comparison:
                sheet.paste(tile,(left,40));draw.text((left+10,10),label,font=font,fill='white');left+=tile.width
            sheet.save(args.output_dir/filename,quality=96)
    (args.output_dir/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({k:audit[k] for k in ('status','identity_centroid','native_failures_retained','final_checks',
                     'outside_polish_and_gaze_union_pixel_error','maximum_horizontal_source_error')},indent=2))
    if not audit['horizontal_gaze_check_passed']: raise SystemExit(1)


if __name__=='__main__': main()
