"""Score and compare the saved live v5 house output without altering it."""
import json
import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from insightface.app import FaceAnalysis

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / 'ComfyUI'
RUN = ROOT / 'work/upgrade-source-faithful-20260903/v5-live-house-native'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with Image.open(path) as im:
        return np.array(ImageOps.exif_transpose(im).convert('RGB'))


def main():
    output = RUN / 'visual-and-identity-audit.json'
    if output.exists():
        raise ValueError('Preserve prior audit.')
    proof = json.loads((RUN / 'output-audit.json').read_text())
    live = Path(proof['actual_output'])
    assert sha(live) == proof['comparisons']['low']['actual_file_sha256']
    preview = ROOT / 'work/upgrade-source-faithful-20260903/codeformer-house-aligned-feasibility/audit.json'
    assert sha(preview) == '252632907c884a6d9c942ce30673c54da5468dd85da3c0e2245d6cabfd8c26d0'
    parent = json.loads(preview.read_text())
    refs = parent['genuine_references']
    app = FaceAnalysis(name='antelopev2', root=str(Path.home()/'.insightface'),
                       providers=['CPUExecutionProvider'],
                       allowed_modules=['detection','recognition','landmark_3d_68'])
    app.prepare(ctx_id=-1, det_size=(640,640))
    def face(rgb):
        faces = app.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if len(faces) != 1:
            raise ValueError('Expected a single face.')
        return faces[0]
    vectors = []
    for ref in refs:
        assert sha(ref['path']) == ref['sha256']
        vectors.append(face(read(ref['path'])).normed_embedding)
    centroid = np.mean(vectors, axis=0)
    centroid /= np.linalg.norm(centroid)
    sys.path.insert(0, str(COMFY))
    sys.path.insert(0, str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks, _eye_measurement, _EYES
    from experimental_upgrade_smile_balance import measure_smile
    paths = {'SOURCE': COMFY/'input/mitch-photo2-source-aef87048.png',
             'CPU LOW V5': Path(parent['input']), 'LIVE LOW V5': live}
    rgbs = {name: read(path) for name, path in paths.items()}
    results, points, faces = {}, {}, {}
    for name, rgb in rgbs.items():
        found = face(rgb)
        faces[name] = found
        landmarks, _ = _detect_refined_landmarks(rgb)
        points[name] = landmarks
        results[name] = {'path': str(paths[name]), 'sha256': sha(paths[name]),
                         'identity_centroid': float(found.normed_embedding@centroid),
                         'pose_pitch_yaw_roll': found.pose.tolist(),
                         'mouth_opening_ratio': float(measure_smile(landmarks)['opening_ratio']),
                         'eye_coordinates': [_eye_measurement(landmarks,e)['coordinate'].tolist() for e in _EYES]}
    assert abs(results['CPU LOW V5']['identity_centroid']-0.7379376888275146)<1e-5
    delta = np.abs(rgbs['CPU LOW V5'].astype(np.int16)-rgbs['LIVE LOW V5'].astype(np.int16))
    eye_region = np.zeros(delta.shape[:2], np.uint8)
    for eye in _EYES:
        contour = np.rint(points['CPU LOW V5'][list(eye['contour'])]).astype(np.int32)
        cv2.fillConvexPoly(eye_region, cv2.convexHull(contour), 1)
    eye_region = cv2.dilate(eye_region, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(31,31)))>0
    outside = delta[~eye_region]
    report = {'status': 'live_v5_identity_measured_pending_visual_review',
              'parent_provenance_audit_sha256': sha(RUN/'output-audit.json'),
              'image_orientation': 'EXIF-transposed RGB', 'genuine_references': refs,
              'results': results,
              'outside_eye_region_max_rgb_delta': int(outside.max()),
              'outside_eye_region_mean_rgb_delta': float(outside.mean()),
              'outside_eye_region_pixels_delta_gt_1': int(np.sum(np.any(outside>1,axis=-1))),
              'live_pixels_not_cpu_identical': True, 'stronger_high_validated': False}
    for crop, filename in [(False,'source-cpu-live-full.jpg'),(True,'source-cpu-live-face.jpg')]:
        tiles=[]
        for name,rgb in rgbs.items():
            im=Image.fromarray(rgb)
            if crop:
                x1,y1,x2,y2=faces['LIVE LOW V5'].bbox
                pad=(x2-x1)*.18
                im=im.crop((int(x1-pad),int(y1-pad),int(x2+pad),int(y2+pad)))
                im=im.resize((round(im.width*460/im.height),460),Image.Resampling.LANCZOS)
            else:
                im.thumbnail((600,720),Image.Resampling.LANCZOS)
            tiles.append((name,im))
        sheet=Image.new('RGB',(sum(im.width for _,im in tiles),max(im.height for _,im in tiles)+38),(20,20,20))
        draw=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=17);x=0
        for name,im in tiles:
            sheet.paste(im,(x,38));draw.text((x+6,8),name,fill='white',font=font);x+=im.width
        sheet.save(RUN/filename,quality=96)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
