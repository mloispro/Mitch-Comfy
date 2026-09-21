"""One frozen house CPU pilot. No queue, model download or production mutation."""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps, PngImagePlugin

from experimental_upgrade_whole_face_shape import whole_face_shape
from upgrade_face_contour_diagnostic import projected_contour, relative_width_change

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent/'ComfyUI'
RUN = ROOT/'work/upgrade-source-faithful-20260903/whole-face-shape-house-pilot'
PUBLIC = COMFY/'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260904-020400-003998'
INPUTS = {
    'SOURCE': (COMFY/'input/mitch-photo2-source-aef87048.png','aef8704873c40c92ec365c091ea142998e72b3d80d22b45f55275309165ba5b4'),
    'RAW': (PUBLIC/'before-polish_00001_.png','4908d5a2399bf04a4708bcc8cba534ceaf952bf34d1b6cef6142f93082b720e2'),
    'LIVE LOW': (PUBLIC/'photo_00001_.png','796a2320f615768640b30bfd11f2d6973b23c9d3a69720bdb282216eb05a29db')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with Image.open(path) as image:
        return np.array(ImageOps.exif_transpose(image).convert('RGB'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-policy',choices=('dense','feature_cage'),default='dense')
    parser.add_argument('--common-finish',action='store_true',help='Apply existing safe common polish equally to raw control and shaped image.')
    args = parser.parse_args()
    global RUN
    if args.control_policy == 'feature_cage':
        RUN = RUN.with_name('whole-face-shape-house-feature-cage')
    if args.common_finish:
        if args.control_policy != 'feature_cage':
            raise ValueError('Only the safe feature cage is eligible for common-finish evaluation.')
        parent_geometry_path = RUN/'audit.json'
        parent_geometry = json.loads(parent_geometry_path.read_text())
        if sha(RUN/'candidate.png') != parent_geometry['output_sha256']:
            raise ValueError('Previously evaluated shape pixels changed.')
        RUN = RUN.with_name(RUN.name+'-common-finish')
    started = time.perf_counter()
    if RUN.exists():
        raise ValueError('Frozen single pilot already has artifacts; preserve them.')
    for name,(path,expected) in INPUTS.items():
        if sha(path) != expected:
            raise ValueError(f'{name} provenance mismatch.')
    parent_path = ROOT/'work/upgrade-source-faithful-20260903/v5-live-house-native/visual-and-identity-audit.json'
    parent = json.loads(parent_path.read_text())
    refs = parent['genuine_references']
    if len(refs) != 6:
        raise ValueError('Expected six held-out genuine references.')
    for record in refs:
        if sha(record['path']) != record['sha256']:
            raise ValueError('Changed genuine reference.')
    models = Path.home()/'.insightface/models/antelopev2'
    if not all((models/name).is_file() for name in ('scrfd_10g_bnkps.onnx','glintr100.onnx','1k3d68.onnx')):
        raise ValueError('Required existing local face models missing; no downloads allowed.')
    sys.path.insert(0,str(COMFY))
    sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    import flux2_klein9b_source_gaze_lock as gaze
    import flux2_klein9b_deterministic_polish as common
    from flux2_klein9b_deterministic_polish import build_semantic_hair_mask
    from upgrade_common_polish_policy import common_polish_policy
    from experimental_upgrade_smile_balance import measure_smile
    torch.set_num_threads(4)
    cv2.setNumThreads(4)
    analyzer = FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
        providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        faces = analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(faces) != 1:
            raise ValueError('Exactly one face required.')
        return faces[0]
    photos = {name:read(path) for name,(path,_) in INPUTS.items()}
    points = {name:gaze._detect_refined_landmarks(rgb)[0] for name,rgb in photos.items()}
    hair = build_semantic_hair_mask(photos['RAW'],face(photos['RAW']).bbox)
    provenance = {'inputs':{name:{'path':str(path),'sha256':expected} for name,(path,expected) in INPUTS.items()},
        'parent_live_audit':str(parent_path),'parent_live_audit_sha256':sha(parent_path),
        'module_sha256':sha(Path(__file__).with_name('experimental_upgrade_whole_face_shape.py')),
        'runner_sha256':sha(__file__),'genuine_references':refs,'diffusion_runs':0,
        'phone_camera_style':True,'turbo':False,'production_changed':False,
        'input_policy':'Previously verified public raw house; source geometry only; optional explicitly reported common cleanup; no legacy High eye warp.',
        'cpu_only':True,'strength':.8,'source_pixels_copied':False,'control_policy':args.control_policy,
        'common_finish_applied_equally_to_control_and_candidate':args.common_finish}
    RUN.mkdir(parents=True)
    (RUN/'intent.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    try:
        shaped,support,geometry = whole_face_shape(photos['RAW']/255,points['RAW'],points['SOURCE'],hair,.8,args.control_policy)
    except Exception as exc:
        (RUN/'failure.json').write_text(json.dumps({**provenance,'error':str(exc)},indent=2),encoding='utf-8')
        raise
    to_rgb = lambda array: np.rint(np.clip(array,0,1)*255).astype(np.uint8)
    photos['SHAPE ONLY'] = to_rgb(shaped)
    common_reports = {}
    common_mask = np.zeros_like(shaped)
    if args.common_finish:
        # Existing process-local safe-policy ablation, no new retouch parameters.
        # Re-detect after geometry so masks/keypoints match the edited face.
        with common_polish_policy(common) as overrides:
            for label,pixels in (('REVISED CONTROL',photos['RAW']/255),('CANDIDATE',shaped)):
                detected = face(to_rgb(pixels))
                semantic_hair = build_semantic_hair_mask(to_rgb(pixels),detected.bbox)
                polished,polish_mask,polish_report = common.apply_deterministic_face_polish(
                    torch.from_numpy(pixels.astype(np.float32)).unsqueeze(0),detected.bbox,detected.kps,semantic_hair)
                common_reports[label] = {'overrides':overrides,'report':polish_report}
                if label == 'CANDIDATE':
                    shaped = polished[0].numpy()
                    common_mask = polish_mask[0].numpy()
                else:
                    control,_,control_gaze = gaze.apply_source_gaze_lock(
                        torch.from_numpy(photos['SOURCE'].astype(np.float32)/255).unsqueeze(0),polished)
                    photos[label] = to_rgb(control[0].numpy())
                    common_reports[label]['gaze'] = control_gaze
    finished,gaze_mask,gaze_report = gaze.apply_source_gaze_lock(
        torch.from_numpy(photos['SOURCE'].astype(np.float32)/255).unsqueeze(0),
        torch.from_numpy(shaped).unsqueeze(0))
    photos['CANDIDATE'] = to_rgb(finished[0].numpy())
    union = (support>0)|(gaze_mask[0,:,:,0].numpy()>0)|(common_mask[:,:,0]>0)
    delta = np.abs(photos['CANDIDATE'].astype(np.int16)-photos['RAW'].astype(np.int16))
    exterior_error = int(delta[~union].max(initial=0))
    if exterior_error:
        raise ValueError('Exterior pixel preservation failed.')
    vectors = [face(read(record['path'])).normed_embedding for record in refs]
    centroid = np.mean(vectors,axis=0);centroid /= np.linalg.norm(centroid)
    results = {};detections = {}
    for name,rgb in photos.items():
        detections[name] = detected = face(rgb)
        points[name] = p = gaze._detect_refined_landmarks(rgb)[0]
        results[name] = {'identity_centroid':float(detected.normed_embedding@centroid),
            'individual_reference_similarity':[float(detected.normed_embedding@vector) for vector in vectors],
            'pose_pitch_yaw_roll':detected.pose.tolist(),
            'mouth_opening_ratio':float(measure_smile(p)['opening_ratio']),
            'contour':projected_contour(p),
            'eye_coordinates':[gaze._eye_measurement(p,eye)['coordinate'].tolist() for eye in gaze._EYES]}
    metadata = PngImagePlugin.PngInfo();metadata.add_text('whole_face_shape_probe',json.dumps(provenance))
    Image.fromarray(photos['CANDIDATE']).save(RUN/'candidate.png',pnginfo=metadata)
    Image.fromarray(photos['SHAPE ONLY']).save(RUN/'shape-before-gaze.png')
    if args.common_finish:
        Image.fromarray(photos['REVISED CONTROL']).save(RUN/'revised-control.png')
    Image.fromarray(to_rgb(support)).save(RUN/'support.png')
    Image.fromarray(to_rgb(hair>0)).save(RUN/'protected-hair.png')
    overlay = photos['RAW'].copy()
    overlay[support>0] = np.rint(.6*overlay[support>0]+.4*np.array([30,170,255])).astype(np.uint8)
    Image.fromarray(overlay).save(RUN/'support-overlay.png')
    for filename,crop in (('source-low-candidate-face.jpg',True),('source-low-candidate-thumbnail.jpg',False)):
        tiles = []
        box = detections['RAW'].bbox;pad = (box[2]-box[0])*.14
        box = tuple(np.rint(box+[-pad,-pad,pad,pad]).astype(int))
        labels = ('SOURCE','LIVE LOW','REVISED CONTROL','CANDIDATE') if args.common_finish else ('SOURCE','LIVE LOW','CANDIDATE')
        for name in labels:
            im = Image.fromarray(photos[name])
            if crop:
                im = im.crop(box)
                im = im.resize((round(im.width*560/im.height),560),Image.Resampling.LANCZOS)
            else:
                im.thumbnail((420,650),Image.Resampling.LANCZOS)
            tiles.append((name,im))
        sheet = Image.new('RGB',(sum(im.width for _,im in tiles),max(im.height for _,im in tiles)+36),(20,20,20))
        draw = ImageDraw.Draw(sheet);font = ImageFont.load_default(size=16);x = 0
        for name,im in tiles:
            sheet.paste(im,(x,36));draw.text((x+6,8),name,fill='white',font=font);x += im.width
        sheet.save(RUN/filename,quality=97)
    report = {**provenance,'status':'evaluated_pending_visual_review_not_promoted',
        'geometry':geometry,'gaze':gaze_report,'results':results,'common_finish':common_reports,
        'exterior_final_rgb_max_error':exterior_error,
        'source_pose_max_delta_degrees':float(np.abs(detections['CANDIDATE'].pose-detections['SOURCE'].pose).max()),
        'candidate_width_change_from_raw_percent':relative_width_change(results['RAW']['contour'],results['CANDIDATE']['contour']),
        'output_sha256':sha(RUN/'candidate.png'),'seconds':time.perf_counter()-started,
        'limitations':'One isolated CPU geometry pilot. Not public High, not trained beauty conditioning or three-photo success. Existing skin/hair cleanup is applied only when common_finish_applied_equally_to_control_and_candidate is true. Geometry can change likeness.'}
    (RUN/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'results':results,'geometry':geometry,'seconds':report['seconds'],'output':str(RUN/'candidate.png')},indent=2))


if __name__ == '__main__':
    main()
