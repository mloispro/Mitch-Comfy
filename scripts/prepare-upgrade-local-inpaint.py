"""Prepare a reviewed CPU head mask and frozen source-first Klein inpaint graph."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageOps
import torch

from upgrade_local_inpaint import build_mask, build_graph, validate_graph, PROMPT

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent/'ComfyUI'
CONTROL = ROOT/'work/upgrade-source-faithful-20260903/native-high-bf16-house'
CONTROL_SHA = '36b48c7291f0dfbb64c88c6a68205a665fe51f7fb99be2323d50674db2f9884e'
DATASET_SHA = 'd56fe2d752febfa63ca0e76689dfd9d4eaac7443ca086ffa9dfef51186563003'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(); out = args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):
        raise ValueError('Use a fresh project work directory.')
    if sha(CONTROL/'experiment.json') != CONTROL_SHA:
        raise ValueError('Frozen source control changed.')
    control = read(CONTROL/'experiment.json'); audit = read(CONTROL/'evaluation/audit.json')
    if not audit['executed_png_graph_verified'] or audit['postprocess_applied']:
        raise ValueError('Expected native control audit.')
    for record in audit['inputs'].values():
        if sha(ROOT/record['path']) != record['sha256']:
            raise ValueError('Audited image changed.')
    dataset_path = ROOT/'datasets/mitch-identity-stills-v3/manifest.json'
    if sha(dataset_path) != DATASET_SHA:
        raise ValueError('Genuine-photo manifest changed.')
    record = [r for r in read(dataset_path)['records'] if r['id']=='07_sweater_front_neutral'][0]
    identity = COMFY/'input/mitch-upgrade-calm-genuine-0e9f30d5.jpg'
    if record['kind'] != 'camera_still' or record['split'] != 'train':
        raise ValueError('Expected genuine held-in identity photograph.')
    for path in (identity, Path(record['source']), Path(record['dataset_file']),
                 ROOT/'work/flux2-klein9b-identity-v3-r32-dop/train/dataset/07_sweater_front_neutral.jpg'):
        if sha(path) != record['dataset_sha256']:
            raise ValueError('Identity source/staging/training provenance mismatch.')
    source_path = ROOT/audit['inputs']['BASE RAW']['path']
    with Image.open(source_path) as im:
        # One roughly1MP pilot with exact original5:3 aspect, no face crop or upscale.
        source = ImageOps.exif_transpose(im).convert('RGB').resize((1280,768), Image.Resampling.LANCZOS)
    rgb = np.array(source); bbox = np.array(audit['results']['BASE RAW']['bbox_xyxy'])*1280/1680
    sys.path.insert(0, str(COMFY))
    sys.path.insert(0, str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
    from upgrade_parsenet_hair import corrected_parsenet_hair_mask
    import mediapipe as mp
    torch.set_num_threads(4)
    landmarks, _ = _detect_refined_landmarks(rgb)
    oval = sorted({i for edge in mp.solutions.face_mesh.FACEMESH_FACE_OVAL for i in edge})
    hull = np.zeros(rgb.shape[:2], np.uint8)
    cv2.fillConvexPoly(hull, cv2.convexHull(np.rint(landmarks[oval]).astype(np.int32)), 255)
    hair = corrected_parsenet_hair_mask(rgb, bbox)
    mask, geometry = build_mask(hull, hair, bbox[2]-bbox[0])
    out.mkdir(parents=True)
    source.save(out/'edit-source.png'); Image.fromarray(mask).save(out/'edit-mask.png')
    overlay = rgb.copy().astype(np.float32)
    alpha = mask.astype(np.float32)/255*.4
    overlay = overlay*(1-alpha[...,None])+np.array([0,210,255])*alpha[...,None]
    Image.fromarray(np.rint(overlay).astype(np.uint8)).save(out/'mask-overlay.png')
    refs = []
    for path, role in ((out/'edit-source.png','synthetic_phone_on_edit_source_not_identity'),
                       (identity,'genuine_identity'), (out/'edit-mask.png','edit_mask_not_identity')):
        digest = sha(path)
        name = identity.name if path == identity else 'mitch-upgrade-inpaint-'+path.stem+'-'+digest[:12]+'.png'
        refs.append({'path':str(path), 'name':name, 'sha256':digest, 'role':role})
    refs[1].update(provenance_manifest=str(dataset_path), provenance_manifest_sha256=DATASET_SHA,
                   provenance_record_id=record['id'])
    prefix = 'upgrade-source-faithful/'+out.name
    graph = build_graph(control['prompt'], *(r['name'] for r in refs), [1280,768],8675417,prefix)
    result = {'status':'prepared_mask_visual_review_required_not_submitted',
              'stage':'klein_base9b_masked_high_pilot','reference_mode':'source_first_genuine_second',
              'identity_reference_count':1,'references':refs,'verified_models':control['verified_models'],
              'control_manifest':str(CONTROL/'experiment.json'),'control_manifest_sha256':CONTROL_SHA,
              'source_audit':str(CONTROL/'evaluation/audit.json'),'source_audit_sha256':sha(CONTROL/'evaluation/audit.json'),
              'source_parent':audit['inputs']['BASE RAW'],'source_resize':'LANCZOS to1280x768 (no crop)',
              'baseline_report':control['baseline_report'],'baseline_report_sha256':control['baseline_report_sha256'],
              'mask_geometry':geometry,'mask_parser_hair_class':13,
              'dimensions':[1280,768],'seed':8675417,'steps':50,'cfg':4.0,
              'identity_strength':.9,'phone_camera_style':True,'phone_camera_style_strength':.25,
              'turbo':False,'postprocess':False,'production_changed':False,
              'effective_prompt':PROMPT,'negative_prompt':'','output_prefix':prefix,'prompt':graph,
              'interpretation':'Author source-first masked-sampling adaptation, not a precision-only A/B; preserves source latents outside head mask. No face swap/restoration/crop composite.'}
    validate_graph(result)
    (out/'experiment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'output_dir':str(out),'mask_geometry':geometry,'references':refs},indent=2))


if __name__=='__main__': main()
