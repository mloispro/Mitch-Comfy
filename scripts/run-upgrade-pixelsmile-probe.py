"""One author-layout PixelSmile pilot on a genuine square photo, without a character LoRA."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import urllib.request
import uuid

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent/'ComfyUI'
PINS = {
    'diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors': 'c9fdc158e46d3b61ef75f21ae866ca2fe808bf4a53643120d1c1e87c19280a4e',
    'text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors': 'cb5636d852a0ea6a9075ab1bef496c0db7aef13c02350571e388aea959c5c0b4',
    'vae/qwen_image_vae.safetensors': 'a70580f0213e67967ee9c95f05bb400e8fb08307e017a924bf3441223e023d1f',
    'loras/pixelsmile/PixelSmile-preview.safetensors': '9bb2f7981e8cd59a5d6e31c2ca08cc0961ac46c267b81af9bce7f8d542ca319a',
}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(8*1024**2),b''):digest.update(block)
    return digest.hexdigest()


def header(path):
    with path.open('rb') as handle:
        length = struct.unpack('<Q',handle.read(8))[0]
        if length > 64*1024**2:raise ValueError('Unexpected header length.')
        return json.loads(handle.read(length))


def api(port, route, body=None):
    request = urllib.request.Request(f'http://127.0.0.1:{port}/{route}',
        data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)


def idle():
    snapshot = []
    for port in (8188,8189):
        queue, stats = api(port,'queue'),api(port,'system_stats')
        snapshot.append({'port':port,'running':len(queue['queue_running']),
            'pending':len(queue['queue_pending']),'device':stats['devices'][0]['name']})
        if port == 8188 and ('3090' not in snapshot[-1]['device'] or snapshot[-1]['running'] or snapshot[-1]['pending']):
            raise RuntimeError('Preserve active work; Upgrade locked to3090.')
    gpu = subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True)
    rows = [line.split(',') for line in gpu.splitlines() if 'RTX 3090' in line]
    if len(rows)!=1 or int(rows[0][-1].strip())>10:raise RuntimeError('3090 busy outside the queue.')
    return {'workers':snapshot,'gpu':gpu}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--neutral-control',action='store_true',
        help='The sole controlled follow-up: score 0, with every sampling/source setting fixed.')
    args = parser.parse_args()
    case = 'pixelsmile-genuine-mirror-s00' if args.neutral_control else 'pixelsmile-genuine-mirror-s05'
    score = 0.0 if args.neutral_control else .5
    destination = ROOT/'work/upgrade-source-faithful-20260903'/case
    if destination.exists():raise ValueError('Preserve previous attempt; never resubmit blindly.')
    preflight = [idle()]
    verified = []
    for relative,expected in PINS.items():
        path = COMFY/'models'/relative
        actual = sha(path)
        if actual!=expected:raise ValueError('Model hash mismatch: '+relative)
        verified.append({'path':str(path),'sha256':actual})
        print('Hash verified: '+relative,flush=True)
    base = header(COMFY/'models'/next(iter(PINS)))
    lora = header(COMFY/'models/loras/pixelsmile/PixelSmile-preview.safetensors')
    pairs = []
    # The released file mixes PEFT A/B names with diffusers down/up names.
    # Both are explicitly supported by the inspected Comfy LoRAAdapter loader.
    for key in lora:
        for down_suffix,up_suffix in (('.lora_A.weight','.lora_B.weight'),('.lora.down.weight','.lora.up.weight')):
            if key.endswith(down_suffix):
                stem = key[:-len(down_suffix)]
                if not stem.startswith('transformer.'):raise ValueError('Unexpected adapter prefix.')
                pairs.append((key,stem+up_suffix,stem[len('transformer.'):]+'.weight'))
    if len(pairs)!=720 or len(lora)-('__metadata__' in lora)!=1440:raise ValueError('Unexpected adapter coverage.')
    used = set()
    for key,other,target in pairs:
        used.update((key,other))
        out_dim,in_dim = base[target]['shape']
        if lora[key]['shape']!=[64,in_dim] or lora[other]['shape']!=[out_dim,64]:raise ValueError('Adapter shape mismatch: '+key)
    if used != set(lora)-{'__metadata__'}:raise ValueError('Unmatched adapter tensor.')
    source = ROOT/'datasets/mitch-identity-stills-v3/validation/val_02_body_mirror_sleeveless.jpg'
    expected_source = '4b32845393fbcbf6ea0ca80068c48af10db52bc81909dba9638370bc7ee0a622'
    if sha(source)!=expected_source:raise ValueError('Genuine source changed.')
    with Image.open(source) as image:
        if ImageOps.exif_transpose(image).size!=(2992,2992):raise ValueError('Source no longer whole square.')
    staged = COMFY/'input/mitch-pixelsmile-genuine-mirror-4b328453.jpg'
    if staged.exists():
        if sha(staged)!=expected_source:raise ValueError('Preserve conflicting staged source.')
    else:shutil.copy2(source,staged)
    graph = {
        '1': {'class_type':'UNETLoader','inputs':{'unet_name':'qwen_image_edit_2511_fp8mixed.safetensors','weight_dtype':'default'}},
        '2': {'class_type':'LoraLoaderModelOnly','inputs':{'model':['1',0],'lora_name':'pixelsmile/PixelSmile-preview.safetensors','strength_model':1.0}},
        '3': {'class_type':'CLIPLoader','inputs':{'clip_name':'qwen_2.5_vl_7b_fp8_scaled.safetensors','type':'qwen_image','device':'default'}},
        '4': {'class_type':'VAELoader','inputs':{'vae_name':'qwen_image_vae.safetensors'}},
        '5': {'class_type':'LoadImage','inputs':{'image':staged.name}},
        '6': {'class_type':'ImageScale','inputs':{'image':['5',0],'upscale_method':'lanczos','width':512,'height':512,'crop':'disabled'}},
        '7': {'class_type':'AIToolkitPixelSmileProbe','inputs':{'model':['2',0],'clip':['3',0],'vae':['4',0],'image':['6',0],'score':.5}},
        '8': {'class_type':'BasicGuider','inputs':{'model':['7',0],'conditioning':['7',1]}},
        '9': {'class_type':'RandomNoise','inputs':{'noise_seed':42}},
        '10': {'class_type':'KSamplerSelect','inputs':{'sampler_name':'euler'}},
        '11': {'class_type':'EmptySD3LatentImage','inputs':{'width':1024,'height':1024,'batch_size':1}},
        '12': {'class_type':'SamplerCustomAdvanced','inputs':{'noise':['9',0],'guider':['8',0],'sampler':['10',0],'sigmas':['7',2],'latent_image':['11',0]}},
        '13': {'class_type':'VAEDecode','inputs':{'samples':['12',0],'vae':['4',0]}},
        '14': {'class_type':'SaveImage','inputs':{'images':['13',0],'filename_prefix':'upgrade-source-faithful/pixelsmile-genuine-mirror-s05/raw'}},
    }
    info = api(8188,'object_info')
    for node in graph.values():
        if node['class_type'] not in info:raise RuntimeError('Required live node absent: '+node['class_type'])
    names = info['LoraLoaderModelOnly']['input']['required']['lora_name'][0]
    actual_name = next((name for name in names if name.replace('\\','/')=='pixelsmile/PixelSmile-preview.safetensors'),None)
    if actual_name is None:raise RuntimeError('Adapter not visible through live API.')
    graph['2']['inputs']['lora_name'] = actual_name
    control = None
    if args.neutral_control:
        baseline_dir = ROOT/'work/upgrade-source-faithful-20260903/pixelsmile-genuine-mirror-s05'
        baseline_path = baseline_dir/'experiment.json'
        if sha(baseline_path) != '0ba46ef53c45e5d7bad7ab70f0a16cf6fc9cf571a8570a409537030a1ad2745f':
            raise ValueError('Baseline manifest changed; do not invent a comparison.')
        baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
        audit = json.loads((baseline_dir/'evaluation/audit.json').read_text(encoding='utf-8'))
        if graph != baseline['prompt'] or sha(Path(audit['output']['path'])) != audit['output']['sha256']:
            raise ValueError('The controlled follow-up no longer matches the verified original run.')
        control = {'baseline_manifest':str(baseline_path),'baseline_prompt_id':audit['prompt_id'],
            'changed_parameter':'expression_score','from':.5,'to':0.0,
            'purpose':'Separate neutral reconstruction drift from the confident expression direction; not an Off implementation.'}
        graph['7']['inputs']['score'] = score
        graph['14']['inputs']['filename_prefix'] = 'upgrade-source-faithful/'+case+'/raw'
    preflight.append(idle())
    destination.mkdir(parents=True)
    manifest = {'status':'prepared_not_promoted','source':{'path':str(source),'sha256':expected_source,'genuine':True},
        'staged_source':str(staged),'source_role':'whole-photo edit target; trained expression adapter identity preservation, no separate identity image',
        'source_original_excluded_from_scoring':True,'character_lora':False,'upstream_character_lora':False,
        'character_training':False,'turbo':False,'phone_adapter':False,'phone_appearance':'inherited genuine phone photograph, not an active style adapter',
        'steps':50,'seed':42,'expression':'neutral' if args.neutral_control else 'confident','expression_score':score,'adapter_strength':1,
        'controlled_follow_up':control,
        'matched_adapter_pairs':len(pairs),'verified_models':verified,'preflight':preflight,'prompt':graph,
        'node_sha256':sha(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training/pixelsmile_experiment.py'),
        'known_backend_differences':['Comfy FP8 mixed rather than author BF16','Native Comfy bilinear vision interpolation rather than processor bicubic'],
        'production_workflow_changed':False,'postprocess':False,'photos_uploaded':False}
    (destination/'experiment.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if not args.execute:
        print('Prepared, not submitted: '+str(destination));return
    submission = api(8188,'prompt',{'prompt':graph,'client_id':'pixelsmile-probe-'+uuid.uuid4().hex})
    (destination/'submission.json').write_text(json.dumps(submission,indent=2),encoding='utf-8')
    print(json.dumps(submission),flush=True)
    if submission.get('node_errors'):raise RuntimeError('Live node validation rejected the graph.')


if __name__=='__main__':main()
