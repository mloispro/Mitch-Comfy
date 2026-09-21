"""Submit one bounded seed or weight-dtype probe from a pinned evaluated graph."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid

from PIL import Image
from upgrade_seed_probe import build_probe,build_dtype_probe,changed_inputs,validate_house_report_hash,precision_runtime_preflight

ROOT=Path(__file__).resolve().parents[1]
CONTROL_SHA='d90422510e24cc94178fe894ad4d9d069ea1ddf091a857cf1251c1627ed1ffa4'
DTYPE_CONTROL_SHA='454cafa1bfe433b975b101d7838371ad4f7494f1a76dc3788de4ba41e3a1f8f7'


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):result.update(block)
    return result.hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-run',type=Path,required=True)
    parser.add_argument('--previous-run',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--probe-kind',choices=('seed','weight-dtype'),default='seed')
    args=parser.parse_args()
    out=args.output_dir.resolve();control=args.control_run.resolve();previous=args.previous_run.resolve()
    if out.exists() or any(not p.is_relative_to(ROOT/'work') for p in (out,control,previous)):
        raise ValueError('Use a fresh work directory and existing project control/previous run.')
    helper_spec=importlib.util.spec_from_file_location('dev_runner',ROOT/'scripts/run-upgrade-dev-high.py')
    helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
    snapshots=[helper.idle_snapshot(previous)]
    precision_checks=[]
    if args.probe_kind=='weight-dtype':
        precision_checks.append(precision_runtime_preflight(helper.api(8188,'system_stats')))
    control_path=control/'experiment.json'
    control_hash=CONTROL_SHA if args.probe_kind=='seed' else DTYPE_CONTROL_SHA
    control_seed=8675416 if args.probe_kind=='seed' else 8675417
    if digest(control_path)!=control_hash:raise ValueError('Frozen control changed.')
    manifest=read(control_path);parent_audit=control/'evaluation/audit.json';audit=read(parent_audit)
    if not audit['executed_png_graph_verified'] or audit['postprocess_applied']:
        raise ValueError('Expected reviewed native control.')
    if not (manifest['reference_mode']=='four' and manifest['seed']==control_seed and manifest['steps']==50
            and manifest['cfg']==4 and manifest['phone_camera_style'] and not manifest['turbo']):
        raise ValueError('Unexpected control configuration.')
    for record in audit['inputs'].values():
        if digest(ROOT/record['path'])!=record['sha256'].lower():raise ValueError('Audited image changed.')
    with Image.open(ROOT/audit['inputs']['CANDIDATE HIGH']['path']) as image:executed=json.loads(image.info['prompt'])
    reference_hashes={r['name']:r['sha256'].lower() for r in manifest['references']}
    for node in executed.values():
        if node['class_type']=='LoadImage' and 'is_changed' in node:
            if node.pop('is_changed')!=[reference_hashes[node['inputs']['image']]]:
                raise ValueError('Executed reference mismatch.')
    if executed!=manifest['prompt']:raise ValueError('Executed control graph mismatch.')
    baseline_hash=validate_house_report_hash(manifest,digest(manifest['baseline_report']))
    for record in manifest['references']+manifest['verified_models']:
        if digest(record['path'])!=record['sha256'].lower():raise ValueError('Protected file changed: '+record['path'])
        print('Hash verified: '+str(Path(record['path']).name),flush=True)
    builder=build_probe if args.probe_kind=='seed' else build_dtype_probe
    graph=builder(manifest['prompt'],'upgrade-source-faithful/'+out.name+'/raw')
    info=helper.api(8188,'object_info')
    for node in graph.values():
        kind=node['class_type']
        if kind not in info:raise ValueError('Node missing: '+kind)
        for field in ('unet_name','clip_name','vae_name','lora_name'):
            if field in node['inputs'] and node['inputs'][field] not in info[kind]['input']['required'][field][0]:
                raise ValueError('Model not visible: '+node['inputs'][field])
    result=copy.deepcopy(manifest)
    change=('Only RandomNoise seed 8675416 to 8675417; no seed search.' if args.probe_kind=='seed'
            else 'Only diffusion-model weight_dtype fp8_e4m3fn to default; unchanged text encoder, seed and both prompts.')
    result.update(status='prepared_not_promoted',seed=graph['20']['inputs']['noise_seed'],prompt=graph,preflight=snapshots,
                  baseline_report_sha256=baseline_hash,
                  probe_kind=args.probe_kind,controlled_change=change,
                  control_manifest=str(control_path),control_manifest_sha256=control_hash,
                  control_audit=str(parent_audit),control_audit_sha256=digest(parent_audit),
                  graph_changed_inputs=changed_inputs(manifest['prompt'],graph))
    result.pop('owned_idle_cache',None);result.pop('workers',None);result.pop('hardware',None)
    snapshots.append(helper.idle_snapshot(previous))
    if args.probe_kind=='weight-dtype':
        precision_checks.append(precision_runtime_preflight(helper.api(8188,'system_stats')))
        result['precision_preflight']=precision_checks
        log=ROOT/'local/dual-comfy/rtx-3090-primary-20260903-131844.stderr.log'
        result['runtime_dtype_evidence']={'log_path':str(log),'start_byte':log.stat().st_size,
                                          'verification_status':'pending actual loading log'}
    out.mkdir(parents=True)
    (out/'experiment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    # Exactly one POST. An uncertain response must be investigated, never retried.
    client_id='upgrade-seed-probe-'+uuid.uuid4().hex
    (out/'submission-intent.json').write_text(json.dumps({'client_id':client_id,'automatic_retry':False}),encoding='utf-8')
    submission=helper.api(8188,'prompt',{'prompt':graph,'client_id':client_id})
    (out/'submission.json').write_text(json.dumps(submission,indent=2),encoding='utf-8')
    print(json.dumps(submission),flush=True)
    if submission.get('node_errors'):raise RuntimeError('Live graph validation rejected submission.')


if __name__=='__main__':main()
