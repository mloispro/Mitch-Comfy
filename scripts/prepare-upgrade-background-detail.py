"""Prepare one local CPU silhouette mask; never queue, download or change production."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

from upgrade_background_detail import background_mask, build_graph, validate_graph, PROMPT

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
CONTROL=ROOT/'work/upgrade-source-faithful-20260903/house-source-native-preserve'
PINS={
    CONTROL/'experiment.json':'14435b176f1dbf355ef7133f850668fca5a4c78a35b8feb01d67442d3880887d',
    CONTROL/'evaluation/audit.json':'3e0c1a83ecd617df1ea60137b724ffb2e1f6379935406a830e0194965c77dbf3',
    COMFY/'models/rembg/u2net_human_seg.onnx':'01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c',
    COMFY/'.venv/Lib/site-packages/rembg/sessions/base.py':'2d48f2f0df33763e8133533c8881a498b4fd5eb39f9f7566561e6e1f38ff558c',
    COMFY/'.venv/Lib/site-packages/rembg/sessions/u2net_human_seg.py':'fdb781c337e275192273fc8c78735bb5188d5f1de5b643547d9bcb0c81a788d8',
}
DATASET_SHA='d56fe2d752febfa63ca0e76689dfd9d4eaac7443ca086ffa9dfef51186563003'


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            value.update(block)
    return value.hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):
        raise ValueError('Use a fresh work directory.')
    for path,expected in PINS.items():
        if digest(path)!=expected:
            raise ValueError('Pinned preparation input changed: '+str(path))
    control=read(CONTROL/'experiment.json');audit=read(CONTROL/'evaluation/audit.json')
    if not (control['reference_mode']=='source_only' and control['identity_strength']==.9
            and control['phone_camera_style_strength']==.25 and not control['turbo']
            and audit['executed_png_graph_verified'] and not audit['postprocess_applied']):
        raise ValueError('Expected audited source-only native identity/phone parent.')
    parent=audit['inputs']['CANDIDATE HIGH'];parent_path=(ROOT/parent['path']).resolve()
    if digest(parent_path)!=parent['sha256']:
        raise ValueError('Source-faithful parent bytes changed.')
    dataset=ROOT/'datasets/mitch-identity-stills-v3/manifest.json'
    if digest(dataset)!=DATASET_SHA:
        raise ValueError('Genuine dataset changed.')
    record=[r for r in read(dataset)['records'] if r['id']=='07_sweater_front_neutral'][0]
    identity=COMFY/'input/mitch-upgrade-calm-genuine-0e9f30d5.jpg'
    if record['kind']!='camera_still' or record['split']!='train':
        raise ValueError('Expected a genuine held-in portrait.')
    for path in (identity,Path(record['source']),Path(record['dataset_file']),
                 ROOT/'work/flux2-klein9b-identity-v3-r32-dop/train/dataset/07_sweater_front_neutral.jpg'):
        if digest(path)!=record['dataset_sha256']:
            raise ValueError('Genuine identity provenance mismatch.')
    with Image.open(parent_path) as image:
        source=ImageOps.exif_transpose(image).convert('RGB').resize((1280,768),Image.Resampling.LANCZOS)
    # Bypass BaseSession.__init__, which can invoke a downloader. Only an explicit
    # pre-existing, pinned local ONNX file is opened. Use the installed prediction
    # and normalization implementations verbatim, CPU only.
    from rembg.sessions.u2net_human_seg import U2netHumanSegSession
    options=ort.SessionOptions();options.intra_op_num_threads=4
    session=U2netHumanSegSession.__new__(U2netHumanSegSession)
    session.inner_session=ort.InferenceSession(str(COMFY/'models/rembg/u2net_human_seg.onnx'),
        sess_options=options,providers=['CPUExecutionProvider'])
    person=np.asarray(session.predict(source)[0]);mask,geometry=background_mask(person)
    out.mkdir(parents=True)
    source.save(out/'edit-source.png');Image.fromarray(person).save(out/'person-probability.png')
    Image.fromarray(mask).save(out/'edit-mask.png')
    rgb=np.asarray(source).astype(np.float32);alpha=mask.astype(np.float32)/255*.40
    overlay=rgb*(1-alpha[...,None])+np.array([0,210,255])*alpha[...,None]
    Image.fromarray(np.rint(overlay).astype(np.uint8)).save(out/'mask-overlay.png')
    refs=[]
    for path,role in ((out/'edit-source.png','source_faithful_synthetic_edit_target'),
                      (identity,'genuine_identity'),(out/'edit-mask.png','background_edit_mask_not_identity')):
        value=digest(path)
        name=identity.name if path==identity else 'mitch-upgrade-bg-'+path.stem+'-'+value[:12]+'.png'
        refs.append({'path':str(path),'name':name,'sha256':value,'role':role})
    refs[1].update(provenance_manifest=str(dataset),provenance_manifest_sha256=DATASET_SHA,
                   provenance_record_id=record['id'])
    # Retain the previously proven BF16 masked-sampling configuration.
    loaders=control['prompt'];loaders['1']['inputs']['weight_dtype']='default'
    prefix='upgrade-source-faithful/'+out.name
    graph=build_graph(loaders,*(r['name'] for r in refs),[1280,768],8675416,prefix)
    manifest={'status':'prepared_mask_review_required_not_submitted',
              'stage':'klein_base9b_background_detail_pilot','reference_mode':'source_first_genuine_second',
              'identity_reference_count':1,'references':refs,'verified_models':control['verified_models'],
              'control_manifest':str(CONTROL/'experiment.json'),'control_manifest_sha256':digest(CONTROL/'experiment.json'),
              'source_audit':str(CONTROL/'evaluation/audit.json'),'source_audit_sha256':digest(CONTROL/'evaluation/audit.json'),
              'source_parent':{'path':str(parent_path),'sha256':parent['sha256']},
              'source_resize':'Full frame LANCZOS to1280x768; no crop or enlargement',
              'mask_geometry':geometry,'segmentation_pins':{str(k):v for k,v in PINS.items() if 'rembg' in str(k)},
              'dimensions':[1280,768],'seed':8675416,'steps':50,'cfg':4,
              'identity_strength':.9,'phone_camera_style':True,'phone_camera_style_strength':.25,
              'turbo':False,'postprocess':False,'production_changed':False,
              'output_prefix':prefix,'effective_prompt':PROMPT,'negative_prompt':'','prompt':graph,
              'identity_mechanism':'Genuine-photo-trained Base9B V3 identity LoRA plus genuine portrait; protected source latents retain existing subject. Mask is not an identity signal.',
              'scope':'Background-detail feasibility, not a proven complete High. Uses source-faithful parent without Low/High/restoration/gaze.'}
    validate_graph(manifest)
    (out/'experiment.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'run':str(out),'mask':geometry,'references':refs},indent=2))


if __name__=='__main__':main()
