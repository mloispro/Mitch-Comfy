"""One CPU-only brow-shape ablation on a recorded, pixel-preserving High."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageOps,ImageDraw,ImageFont
from insightface.app import FaceAnalysis


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('parent-audit','native-audit','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--glabella-relief',action='store_true',help='Single targeted refinement; preserve brow-only output separately.')
    parser.add_argument('--crease-band-scale',type=float,choices=(1.,2.),default=1.,help='Treatment cutoff only; texture measurement scale is fixed.')
    parser.add_argument('--low-label',choices=('ACTUAL LOW','REVISED LOW'),default='ACTUAL LOW')
    parser.add_argument('--skin-polish',choices=('none','warmth','spots','both'),default='none')
    parser.add_argument('--skin-baseline-audit','--frozen-baseline-audit',dest='skin_baseline_audit',type=Path,help='Verified frozen brow/crease output for pixel-exact isolated-stage ablation.')
    parser.add_argument('--eye-contour',action='store_true',help='Isolated stronger contour edit; existing final gaze correction follows.')
    parser.add_argument('--eye-aperture-scale',type=float,choices=(.82,1.),default=.82,help='Single refinement removes unwanted extra squint; corner lift unchanged.')
    parser.add_argument('--skin-spot-kind',choices=('dark_compact','chromatic_compact'),default='dark_compact')
    parser.add_argument('--skin-warmth-mask',choices=('shared','separate_feather'),default='shared')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if args.crease_band_scale!=1 and not args.glabella_relief: raise ValueError('Crease cutoff needs glabella relief.')
    if (args.skin_polish!='none' or args.eye_contour) and (not args.skin_baseline_audit or not args.glabella_relief or args.crease_band_scale!=2):
        raise ValueError('Isolated ablation requires verified frozen refined brow/crease baseline.')
    if args.eye_contour and args.skin_polish!='none': raise ValueError('Evaluate contour geometry separately from skin changes.')
    if not args.eye_contour and args.eye_aperture_scale!=.82: raise ValueError('Aperture refinement needs eye-contour experiment.')
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new project-local output directory.')
    def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def read(path):
        with Image.open(path) as photo: return np.array(ImageOps.exif_transpose(photo).convert('RGB'))
    parent=json.loads(args.parent_audit.read_text(encoding='utf-8-sig'))
    native=json.loads(args.native_audit.read_text(encoding='utf-8-sig'))
    if not native.get('executed_png_graph_verified') or native.get('postprocess_applied'):
        raise ValueError('Expected verified native source/base audit.')
    source_path=Path(parent['source']);raw_path=Path(parent['raw'])
    if digest(source_path)!=native['inputs']['SOURCE']['sha256']: raise ValueError('Source changed.')
    base_record=native['inputs']['BASE RAW'];base_path=Path(base_record['path'])
    if digest(base_path)!=base_record['sha256'] or not np.array_equal(read(raw_path),read(base_path)):
        raise ValueError('Parent raw is not the audited base pixels.')
    before_path=args.parent_audit.parent/'high.png'
    low_path=Path(parent['baseline_comparisons']['low']['path'])
    paths={'SOURCE':source_path,args.low_label:low_path,'PRIOR HIGH':before_path}
    photos={key:read(path) for key,path in paths.items()}
    source=photos['SOURCE'];before=photos['PRIOR HIGH']
    sys.path.insert(0,str(root/'custom_nodes/ComfyUI-AIToolkit-Training'))
    sys.path.insert(0,str(root.parent/'ComfyUI'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
    from flux2_klein9b_deterministic_polish import build_semantic_hair_mask
    from experimental_upgrade_source_brows import apply_source_brows,brow_frames
    from flux2_klein9b_attractiveness import _BROWS
    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
        providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found=analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(found)!=1: raise ValueError('Expected exactly one face.')
        return found[0]
    refs=native['genuine_references']
    if {r['sha256'] for r in refs}!={r['sha256'] for r in parent['references']}:
        raise ValueError('Parent/native scoring sets differ.')
    if len(refs)<2: raise ValueError('At least two separate genuine photographs required.')
    embeddings=[]
    for ref in refs:
        if digest(ref['path'])!=ref['sha256']: raise ValueError('Genuine reference changed.')
        embeddings.append(face(read(ref['path'])).normed_embedding)
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    before_face=face(before)
    before_score=float(before_face.normed_embedding@centroid)
    if abs(before_score-parent['candidates']['high']['centroid_similarity'])>1e-5:
        raise ValueError('Before image does not reproduce recorded parent likeness.')
    points,_=_detect_refined_landmarks(before);source_points,_=_detect_refined_landmarks(source)
    hair=build_semantic_hair_mask(before,before_face.bbox)
    edited,mask,detail=apply_source_brows(before.astype(np.float32)/255,points,source_points,hair,.8)
    after=np.rint(edited*255).clip(0,255).astype(np.uint8)
    if args.glabella_relief:
        from experimental_upgrade_source_brows import soften_glabellar_band
        brow_points,_=_detect_refined_landmarks(after)
        edited,crease_mask,crease_detail=soften_glabellar_band(edited,brow_points,hair,args.crease_band_scale)
        mask=np.maximum(mask,crease_mask)
        detail['glabellar_relief']=crease_detail
        after=np.rint(edited*255).clip(0,255).astype(np.uint8)
    if not np.array_equal(after[mask==0],before[mask==0]): raise RuntimeError('Outside pixels changed.')
    after_points,_=_detect_refined_landmarks(after)
    if args.skin_polish!='none' or args.eye_contour:
        baseline=json.loads(args.skin_baseline_audit.read_text(encoding='utf-8-sig'))
        baseline_output=baseline['output']
        if (digest(baseline_output['path'])!=baseline_output['sha256']
                or not np.array_equal(after,read(baseline_output['path']))):
            raise ValueError('Skin ablation did not reproduce exact frozen input pixels.')
        photos['EXPRESSION HIGH']=after.copy()
    if args.skin_polish!='none':
        from experimental_upgrade_skin_polish import polish_skin
        polished,skin_mask,skin_detail=polish_skin(after.astype(np.float32)/255,after_points,
            source.astype(np.float32)/255,source_points,hair,args.skin_polish,args.skin_spot_kind,args.skin_warmth_mask)
        mask=np.maximum(mask,skin_mask);after=np.rint(polished*255).clip(0,255).astype(np.uint8)
        detail['skin_polish']=skin_detail
        after_points,_=_detect_refined_landmarks(after)
        if not np.array_equal(after[mask==0],before[mask==0]): raise RuntimeError('Skin ablation changed pixels outside its selected regions.')
    if args.eye_contour:
        import torch
        torch.set_num_threads(4)
        from experimental_upgrade_eye_contour import contour_polish
        from flux2_klein9b_source_gaze_lock import apply_source_gaze_lock
        eye_edit,eye_mask,eye_detail=contour_polish(after.astype(np.float32)/255,after_points,hair,aperture_scale=args.eye_aperture_scale)
        contour_before_gaze=np.rint(eye_edit*255).clip(0,255).astype(np.uint8)
        corrected,gaze_mask,gaze_detail=apply_source_gaze_lock(
            torch.from_numpy(source.astype(np.float32)/255).unsqueeze(0),torch.from_numpy(eye_edit).unsqueeze(0))
        after=np.rint(corrected[0].numpy()*255).clip(0,255).astype(np.uint8)
        contour_mask=np.maximum(eye_mask,gaze_mask[0,:,:,0].numpy())
        mask=np.maximum(mask,contour_mask)
        eye_detail['final_source_gaze']=gaze_detail
        detail['eye_contour']=eye_detail
        if not np.array_equal(after[contour_mask==0],photos['EXPRESSION HIGH'][contour_mask==0]):
            raise RuntimeError('Eye ablation changed pixels outside its own edit region.')
        after_points,_=_detect_refined_landmarks(after)
    frames=brow_frames(points);source_frames=brow_frames(source_points)
    for ids,frame,source_frame,record in zip(_BROWS,frames,source_frames,detail['brows']):
        local=(after_points[list(ids)]-frame['center'])@frame['basis']/frame['width']
        record['redetected_source_relative_brow_error_after']=float(np.linalg.norm(local-source_frame['relative'],axis=1).mean())
        record['measurement']='Redetected brows relative to FIXED pre-edit eye frame; diagnostic only.'
    label='BROW + CREASE' if args.glabella_relief else 'BROW EDIT'
    if args.skin_polish!='none': label='SKIN HIGH - '+args.skin_polish.upper()
    if args.eye_contour: label='CONTOUR HIGH'
    photos[label]=after
    results={};faces={}
    for name,rgb in photos.items():
        detected=face(rgb);faces[name]=detected
        results[name]={'likeness':float(detected.normed_embedding@centroid),
            'pose_pitch_yaw_roll':[float(x) for x in detected.pose],
            'per_reference':[float(detected.normed_embedding@e) for e in embeddings]}
    args.output_dir.mkdir(parents=True)
    Image.fromarray(after).save(args.output_dir/'high-brow-edit.png')
    Image.fromarray((mask*255).astype(np.uint8)).save(args.output_dir/'brow-edit-mask.png')
    if args.skin_polish!='none':
        Image.fromarray(np.rint(skin_mask*255).astype(np.uint8)).save(args.output_dir/'skin-region-mask.png')
        spot_mask=detail['skin_polish'].pop('spot_mask',None)
        if spot_mask is not None: Image.fromarray(np.rint(spot_mask*255).astype(np.uint8)).save(args.output_dir/'spot-selection-mask.png')
    if args.eye_contour:
        Image.fromarray(contour_before_gaze).save(args.output_dir/'contour-before-gaze.png')
        Image.fromarray(np.rint(contour_mask*255).astype(np.uint8)).save(args.output_dir/'eye-contour-mask.png')
    def sheet(labels,filename,face_crop=False,width=420):
        tiles=[]
        for label in labels:
            tile=Image.fromarray(photos[label])
            if face_crop:
                x0,y0,x1,y1=faces[label].bbox;pad=(x1-x0)*.12
                tile=tile.crop((max(0,int(x0-pad)),max(0,int(y0-pad)),min(tile.width,int(x1+pad)),min(tile.height,int(y1+pad))))
                tile=tile.resize((round(tile.width*420/tile.height),420),Image.Resampling.LANCZOS)
            else: tile.thumbnail((width,1000),Image.Resampling.LANCZOS)
            tiles.append((label,tile))
        canvas=Image.new('RGB',(sum(t.width for _,t in tiles),max(t.height for _,t in tiles)+40),(22,22,22))
        draw=ImageDraw.Draw(canvas);font=ImageFont.load_default(size=17);x=0
        for label,tile in tiles:
            canvas.paste(tile,(x,40));draw.text((x+8,10),label,fill='white',font=font);x+=tile.width
        canvas.save(args.output_dir/filename,quality=96)
    sheet(['SOURCE',args.low_label,label],'source-low-brow-face.jpg',True)
    sheet(['SOURCE','PRIOR HIGH',label],'source-prior-brow-face.jpg',True)
    sheet(['SOURCE',args.low_label,label],'source-low-brow-thumbnail.jpg',width=320)
    if args.skin_polish!='none': sheet(['EXPRESSION HIGH',label],'skin-only-comparison-face.jpg',True)
    if args.eye_contour: sheet(['EXPRESSION HIGH',label],'contour-only-comparison-face.jpg',True)
    audit={'status':'evaluated_not_promoted','production_changed':False,'diffusion_runs':0,
        'parent_audit':str(args.parent_audit),'parent_audit_sha256':digest(args.parent_audit),
        'native_audit':str(args.native_audit),'native_audit_sha256':digest(args.native_audit),
        'inputs':{k:{'path':str(v),'sha256':digest(v)} for k,v in paths.items()},
        'output':{'path':str(args.output_dir/'high-brow-edit.png'),'sha256':digest(args.output_dir/'high-brow-edit.png')},
        'parent_raw_matches_verified_base_pixels':True,'parent_likeness_reproduced':True,
        'genuine_references':refs,'results':results,'brow_edit':detail,
        'outside_selected_edit_pixel_max_error_0_to_255':0,'glabella_relief_selected':args.glabella_relief,
        'brow_redetection_improved_each_eye':all(b['redetected_source_relative_brow_error_after']<b['source_relative_brow_error_before'] for b in detail['brows']),
        'skin_baseline_audit':str(args.skin_baseline_audit) if args.skin_baseline_audit else None,
        'skin_baseline_pixels_reproduced':args.skin_polish!='none',
        'skin_module_sha256':digest(root/'scripts/experimental_upgrade_skin_polish.py') if args.skin_polish!='none' else None,
        'eye_contour_module_sha256':digest(root/'scripts/experimental_upgrade_eye_contour.py') if args.eye_contour else None,
        'frozen_baseline_pixels_reproduced':args.skin_polish!='none' or args.eye_contour,
        'parent_failures_preserved':parent['validation_errors'],
        'module_sha256':digest(root/'scripts/experimental_upgrade_source_brows.py'),
        'visual_review_required':True,'note':'No new identity/phone conditioning. Earlier High pipeline limitations remain; unchanged eye pixels do not establish source gaze accuracy.'}
    audit['refinement_failures']=(['Glabellar texture/exposure guard failed; reject.']
        if args.glabella_relief and not detail['glabellar_relief']['texture_exposure_guard_passed'] else [])
    if args.skin_polish!='none' and detail['skin_polish'].get('spots',{}).get('selection_guard_passed') is False:
        audit['refinement_failures'].append('Spot selection coverage too broad; no spot repair applied.')
    if args.eye_contour and max(e['horizontal_error_after'] for e in detail['eye_contour']['final_source_gaze']['eye_reports'])>.02:
        audit['refinement_failures'].append('Final contour horizontal source-gaze error exceeds .02.')
    (args.output_dir/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({'results':results,'brow_edit':detail},indent=2))
    if audit['refinement_failures']: raise SystemExit(1)


if __name__=='__main__': main()
