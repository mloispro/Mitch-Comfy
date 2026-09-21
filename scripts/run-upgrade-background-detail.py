"""Submit the reviewed background-only pilot once, without cache mutations."""
import argparse
import importlib.util
import json
from pathlib import Path
from runpy import run_path
import shutil
import socket
import uuid

from upgrade_background_detail import validate_graph
from upgrade_seed_probe import precision_runtime_preflight

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
MANIFEST_SHA='2204825b75ffed259fd6db0733ba11793f9fcad7795a07bb493968729cb49b94'
REFINEMENT_SHA='fc6ae95058cb48a67981ee6f5f2a3c427628d149c19571afe7a6e6e4dd2dc699'
MASK_SHA='6d86ac3a277adeb245b1282212ae32665efb1aadaafc1015e9d093946df655c9'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--previous-run',type=Path,required=True)
    args=parser.parse_args();out=args.run.resolve();previous=args.previous_run.resolve()
    if not out.is_relative_to(ROOT/'work') or not previous.is_relative_to(ROOT/'work'):
        raise ValueError('Run and previous ownership record must be project-local.')
    if (out/'submission-intent.json').exists() or (out/'submission.json').exists():
        raise ValueError('An attempt already exists; inspect it, never retry automatically.')
    helper=run_path(str(ROOT/'scripts/prepare-upgrade-background-detail.py'))
    digest=helper['digest'];read=helper['read']
    spec=importlib.util.spec_from_file_location('bg_guard',ROOT/'scripts/run-upgrade-dev-high.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    path=out/'experiment.json'
    selected_sha=digest(path)
    if selected_sha not in (MANIFEST_SHA,REFINEMENT_SHA):
        raise ValueError('Only the frozen, visually reviewed pilot is authorized here.')
    manifest=read(path);validate_graph(manifest)
    if selected_sha==REFINEMENT_SHA:
        if (manifest['refinement_parent_sha256']!=MANIFEST_SHA
                or digest(manifest['refinement_parent'])!=MANIFEST_SHA):
            raise ValueError('Original background pilot changed.')
        background=manifest['references'][3]
        if digest(background['provenance_report'])!=background['provenance_report_sha256']:
            raise ValueError('Audited background provenance changed.')
    if manifest['references'][2]['sha256']!=MASK_SHA:
        raise ValueError('Unreviewed background mask.')
    def snapshot():
        state=guard.idle_snapshot(previous)
        state['memory']=precision_runtime_preflight(guard.api(8188,'system_stats'),minimum_ram_gib=32)
        try:
            with socket.create_connection(('127.0.0.1',7860),timeout=.5):pass
        except OSError:
            state['forge']={'online':False}
        else:
            progress=guard.api(7860,'sdapi/v1/progress?skip_current_image=true')
            if progress.get('progress',0)>0 or progress.get('state',{}).get('job_count',0)>0:
                raise RuntimeError('Preserve active Forge work.')
            state['forge']={'online':True,'progress':progress}
        return state
    snapshots=[snapshot()]
    for item in manifest['references']+manifest['verified_models']:
        if digest(item['path'])!=item['sha256'].lower():
            raise ValueError('Protected asset changed: '+item['path'])
        print('Verified '+Path(item['path']).name,flush=True)
    for key in ('control_manifest','source_audit'):
        if digest(manifest[key])!=manifest[key+'_sha256'].lower():
            raise ValueError('Provenance changed: '+key)
    if digest(manifest['source_parent']['path'])!=manifest['source_parent']['sha256']:
        raise ValueError('Source-faithful parent changed.')
    for name,expected in manifest['segmentation_pins'].items():
        if digest(name)!=expected:raise ValueError('Segmentation dependency changed.')
    identity=manifest['references'][1]
    if digest(identity['provenance_manifest'])!=identity['provenance_manifest_sha256']:
        raise ValueError('Identity provenance changed.')
    record=[r for r in read(identity['provenance_manifest'])['records'] if r['id']==identity['provenance_record_id']][0]
    if not (record['kind']=='camera_still' and record['split']=='train'
            and record['dataset_sha256']==identity['sha256']
            and digest(record['dataset_file'])==identity['sha256']):
        raise ValueError('Reference is not the recorded genuine training photograph.')
    info=guard.api(8188,'object_info')
    for node in manifest['prompt'].values():
        kind=node['class_type']
        if kind not in info:raise ValueError('Missing live node: '+kind)
        for field in ('unet_name','lora_name','clip_name','vae_name'):
            if field in node['inputs'] and node['inputs'][field] not in info[kind]['input']['required'][field][0]:
                raise ValueError('Model is not visible: '+node['inputs'][field])
    for item in manifest['references']:
        target=COMFY/'input'/item['name']
        if target.exists():
            if digest(target)!=item['sha256']:raise ValueError('Input staging collision.')
        else:shutil.copyfile(item['path'],target)
        if digest(target)!=item['sha256']:raise ValueError('Staged bytes changed.')
    snapshots.append(snapshot())
    log=ROOT/'work/upgrade-source-faithful-20260903/v5-live-reload-20260904-015316/primary.stderr.log'
    client='upgrade-background-detail-'+uuid.uuid4().hex
    intent={'prompt':manifest['prompt'],'client_id':client,'preflight':snapshots,
            'manifest_sha256':digest(path),'reviewed_mask_sha256':MASK_SHA,
            'log_path':str(log),'log_start_byte':log.stat().st_size,'automatic_retry':False}
    (out/'submission-intent.json').write_text(json.dumps(intent,indent=2),encoding='utf-8')
    response=guard.api(8188,'prompt',{'prompt':manifest['prompt'],'client_id':client})
    (out/'submission.json').write_text(json.dumps(response,indent=2),encoding='utf-8')
    print(json.dumps(response),flush=True)
    if response.get('node_errors'):raise RuntimeError('Graph rejected; inspect saved response.')


if __name__=='__main__':main()
