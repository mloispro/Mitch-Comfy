"""One reviewed local masked High submission; no retry, restart or cache mutation."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import uuid

from runpy import run_path
from upgrade_local_inpaint import validate_graph
from upgrade_seed_probe import precision_runtime_preflight

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
READY_SHA='a79d8c16d7d690c88675059040985dde31d6170c8870baab2c81a5c3fbad55f1'
SOURCE_GEOMETRY_SHA='e15287686a84c8ade7a6d795248d23d21d25fcf6173f43731c8624d26536f80f'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--previous-run',type=Path,required=True)
    parser.add_argument('--reviewed-mask-sha256',required=True)
    args=parser.parse_args();out=args.run.resolve()
    if not out.is_relative_to(ROOT/'work') or (out/'submission-intent.json').exists():
        raise ValueError('Use the prepared project run once; inspect any existing intent instead of retrying.')
    scope=run_path(str(ROOT/'scripts/run-upgrade-seed-probe.py'))
    digest=scope['digest'];read=scope['read']
    spec=importlib.util.spec_from_file_location('guard',ROOT/'scripts/run-upgrade-dev-high.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    path=out/'experiment.json'
    manifest_sha=digest(path)
    if manifest_sha not in (READY_SHA,SOURCE_GEOMETRY_SHA):
        raise ValueError('Not a reviewed frozen house pilot or its one source-reference correction.')
    manifest=read(path);validate_graph(manifest)
    if manifest_sha==SOURCE_GEOMETRY_SHA:
        if digest(manifest['refinement_parent'])!=READY_SHA or manifest['refinement_parent_sha256']!=READY_SHA:
            raise ValueError('Masked refinement control changed.')
    if manifest.get('mask_parser_hair_class')!=13 or manifest['references'][2]['sha256']!=args.reviewed_mask_sha256:
        raise ValueError('Incorrect or unreviewed hair/edit mask.')
    snapshots=[guard.idle_snapshot(args.previous_run)]
    memory=[precision_runtime_preflight(guard.api(8188,'system_stats'),minimum_ram_gib=32)]
    for item in manifest['references']+manifest['verified_models']:
        if digest(item['path'])!=item['sha256'].lower():raise ValueError('Protected asset changed: '+item['path'])
        print('Verified '+Path(item['path']).name,flush=True)
    for field in ('control_manifest','source_audit','baseline_report'):
        if digest(manifest[field])!=manifest[field+'_sha256'].lower():raise ValueError('Provenance changed: '+field)
    if digest(manifest['source_parent']['path'])!=manifest['source_parent']['sha256']:
        raise ValueError('Detailed raw parent changed.')
    identity=manifest['references'][1]
    if digest(identity['provenance_manifest'])!=identity['provenance_manifest_sha256']:
        raise ValueError('Genuine identity provenance changed.')
    identity_record=[r for r in read(identity['provenance_manifest'])['records'] if r['id']==identity['provenance_record_id']][0]
    if (identity_record['kind']!='camera_still' or identity_record['split']!='train'
        or identity_record['dataset_sha256']!=identity['sha256']
        or digest(identity_record['dataset_file'])!=identity['sha256']):
        raise ValueError('Identity reference is not the genuine held-in photo.')
    for item in manifest['references']:
        target=COMFY/'input'/item['name']
        if target.exists():
            if digest(target)!=item['sha256']:raise ValueError('Input staging collision.')
        else:shutil.copyfile(item['path'],target)
        if digest(target)!=item['sha256']:raise ValueError('Staged bytes changed.')
    info=guard.api(8188,'object_info')
    for node in manifest['prompt'].values():
        kind=node['class_type']
        if kind not in info:raise ValueError('Missing live node: '+kind)
        for field in ('unet_name','clip_name','vae_name','lora_name'):
            if field in node['inputs'] and node['inputs'][field] not in info[kind]['input']['required'][field][0]:
                raise ValueError('Missing live model: '+node['inputs'][field])
    snapshots.append(guard.idle_snapshot(args.previous_run))
    memory.append(precision_runtime_preflight(guard.api(8188,'system_stats'),minimum_ram_gib=32))
    log=ROOT/'local/dual-comfy/rtx-3090-primary-20260903-131844.stderr.log'
    record={'preflight':snapshots,'memory_checks':memory,'manifest_sha256':digest(path),
            'log_path':str(log),'log_start_byte':log.stat().st_size,'automatic_retry':False,
            'reviewed_mask_sha256':args.reviewed_mask_sha256,'client_id':'upgrade-masked-high-'+uuid.uuid4().hex}
    (out/'submission-intent.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    submission=guard.api(8188,'prompt',{'prompt':manifest['prompt'],'client_id':record['client_id']})
    (out/'submission.json').write_text(json.dumps(submission,indent=2),encoding='utf-8')
    print(json.dumps(submission),flush=True)
    if submission.get('node_errors'):raise RuntimeError('Comfy graph validation rejected this submission.')


if __name__=='__main__':main()
