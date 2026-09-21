"""One native portrait-reference resolution probe, using the verified public recipe.

Does not change production, prompts, adapters, seed, or sampling. No automatic retry.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess
import urllib.request
import uuid

import psutil
from PIL import Image, ImageOps
from upgrade_seed_probe import changed_inputs

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT/'work/upgrade-source-faithful-20260903/portrait-detail-house-control-prepared/experiment.json'
CONTROL_SHA = 'b86c3906b89c83d260f9f3649fccdba87354252dd0e57c8d8fd9815915ba2328'
REPORT_SHA = '45fadf105ae96798db81df107d570a6cc798354bc8725c6d91a87977e73c8eaf'
PREVIOUS = ROOT/'work/upgrade-source-faithful-20260903/v5-live-house-native'
PREVIOUS_ID = '52348431-764b-407b-bc74-8da6c055ca66'


def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def api(port,route,body=None):
    request=urllib.request.Request(f'http://127.0.0.1:{port}/{route}',
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as response:
        return json.load(response)


def listening(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=.5):
            return True
    except OSError:
        return False


def snapshot():
    workers=[]
    for port in (8188,8189,8190):
        try:
            stats=api(port,'system_stats');queue=api(port,'queue')
        except Exception:
            if port in (8188,8189) or listening(port):
                raise RuntimeError(f'Cannot inspect worker {port}.')
            workers.append({'port':port,'online':False});continue
        row={'port':port,'online':True,'device':stats['devices'][0]['name'],
             'running':len(queue['queue_running']),'pending':len(queue['queue_pending'])}
        workers.append(row)
        if port==8188 and '3090' not in row['device']:
            raise RuntimeError('Upgrade remains locked to RTX 3090/8188.')
        if '3090' in row['device'] and (row['running'] or row['pending']):
            raise RuntimeError('Preserve active 3090 work.')
    hardware=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu',
                                      '--format=csv,noheader,nounits'],text=True)
    cards=[line.split(',') for line in hardware.splitlines() if 'RTX 3090' in line]
    if len(cards)!=1 or int(cards[0][3])>10 or int(cards[0][2])>4096:
        raise RuntimeError('3090 hardware is busy or memory ownership requires a new audit.')
    available=psutil.virtual_memory().available
    if available<32*1024**3:
        raise RuntimeError('Need 32 GiB free host RAM; do not free another task cache.')
    forge={'online':False}
    if listening(7860):
        progress=api(7860,'sdapi/v1/progress?skip_current_image=true')
        if progress.get('progress',0)>0 or progress.get('state',{}).get('job_count',0)>0:
            raise RuntimeError('Preserve active Forge work.')
        forge={'online':True,'progress':progress}
    previous=api(8188,'history?max_items=1')
    if list(previous)!=[PREVIOUS_ID]:
        raise RuntimeError('Latest primary job changed; inspect ownership before submission.')
    terminal=previous[PREVIOUS_ID]
    if not terminal['status']['completed'] or terminal['status']['status_str']!='success':
        raise RuntimeError('Previous primary job is not a terminal success.')
    if terminal['prompt'][2]!=read(PREVIOUS/'submission-intent.json')['prompt']:
        raise RuntimeError('Previous public graph no longer matches its saved intent.')
    return {'workers':workers,'hardware':hardware,'available_host_ram':available,
            'previous_prompt_id':PREVIOUS_ID,'forge':forge,'explicit_free':False,'restart':False}


def build_probe(control,prefix):
    if not prefix.startswith('upgrade-source-faithful/') or '..' in prefix or ':' in prefix:
        raise ValueError('Unsafe output prefix.')
    graph=copy.deepcopy(control)
    node=graph['121']
    if node!={'class_type':'ImageScaleToTotalPixels','inputs':{
        'image':['120',0],'upscale_method':'nearest-exact','megapixels':.5,'resolution_steps':1}}:
        raise ValueError('Expected the unchanged 0.5 MP genuine-portrait scaler.')
    if graph['122']!={'class_type':'VAEEncode','inputs':{'pixels':['121',0],'vae':['5',0]}}:
        raise ValueError('Portrait is not entering the existing Flux2 VAE.')
    if (graph['123']['inputs']!={'conditioning':['113',0],'latent':['122',0]}
        or graph['124']['inputs']!={'conditioning':['114',0],'latent':['122',0]}):
        raise ValueError('Portrait must retain its ordered role on both CFG branches.')
    graph['121']['inputs']['megapixels']=.1
    graph['27']['inputs']['filename_prefix']=prefix
    if changed_inputs(control,graph)!=['121.megapixels','27.filename_prefix']:
        raise ValueError('Unexpected change beyond portrait resolution and destination.')
    return graph


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):
        raise ValueError('Use a fresh project work directory; never retry an uncertain submission.')
    snapshots=[snapshot()]
    if sha(CONTROL)!=CONTROL_SHA:
        raise ValueError('Prepared production-equivalent graph changed.')
    control=read(CONTROL);report=read(control['baseline_report'])
    if sha(control['baseline_report'])!=REPORT_SHA:
        raise ValueError('Audited live public report changed.')
    if not (control['reference_mode']=='four' and control['identity_strength']==.9
        and control['phone_camera_style_strength']==.25 and not control['turbo']
        and control['seed']==8675416 and control['steps']==50 and control['cfg']==4
        and control['effective_prompt']==report['effective_prompt']
        and control['prompt']['7']['inputs']['text']==''):
        raise ValueError('Control differs from the exact public generation recipe.')
    for item in control['verified_models']+control['references']:
        if sha(item['path'])!=item['sha256'].lower():
            raise ValueError('Pinned file changed: '+item['path'])
        print('Verified '+Path(item['path']).name,flush=True)
    source_sizes=[]
    for item,expected in zip(control['references'],report['reference_encoded_sizes']):
        with Image.open(item['path']) as image:
            width,height=ImageOps.exif_transpose(image).size
        factor=math.sqrt(item['megapixels']*1024**2/(width*height))
        size=[round(width*factor),round(height*factor)]
        if size!=expected:
            raise ValueError('Expanded graph resize differs from the public runtime report.')
        source_sizes.append([width,height])
    graph=build_probe(control['prompt'],'upgrade-source-faithful/'+out.name+'/raw')
    info=api(8188,'object_info')
    for node in graph.values():
        kind=node['class_type']
        if kind not in info:
            raise ValueError('Live node is missing: '+kind)
        for field in ('unet_name','clip_name','vae_name','lora_name'):
            if field in node['inputs'] and node['inputs'][field] not in info[kind]['input']['required'][field][0]:
                raise ValueError('Model is not visible: '+node['inputs'][field])
    width,height=source_sizes[2];factor=math.sqrt(.1*1024**2/(width*height))
    manifest=copy.deepcopy(control)
    manifest.update(status='prepared_not_promoted',prompt=graph,
        control_manifest=str(CONTROL),control_manifest_sha256=CONTROL_SHA,
        control_scope='Expanded equivalent of audited public node; this exact expanded control has not itself been rendered.',
        probe_kind='genuine_portrait_reference_resolution',
        controlled_change='Only genuine portrait reference 0.5 MP to 0.1 MP; no LoRA or prompt change.',
        graph_changed_inputs=changed_inputs(control['prompt'],graph),
        reference_encoded_sizes_control=report['reference_encoded_sizes'],
        portrait_encoded_size_candidate=[round(width*factor),round(height*factor)],
        acceptance_scope='Source-feature retention pilot, not an accepted complete High or three-photo proof.')
    manifest['references'][2]['megapixels']=.1
    for key in ('owned_idle_cache','workers','hardware'):
        manifest.pop(key,None)
    snapshots.append(snapshot());manifest['preflight']=snapshots
    out.mkdir(parents=True)
    (out/'experiment.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    client_id='upgrade-portrait-detail-'+uuid.uuid4().hex
    body={'prompt':graph,'client_id':client_id}
    (out/'submission-intent.json').write_text(json.dumps(body,indent=2),encoding='utf-8')
    submission=api(8188,'prompt',body)
    (out/'submission.json').write_text(json.dumps(submission,indent=2),encoding='utf-8')
    print(json.dumps(submission),flush=True)
    if submission.get('node_errors'):
        raise RuntimeError('Graph rejected; inspect the saved response.')


if __name__=='__main__':
    main()
