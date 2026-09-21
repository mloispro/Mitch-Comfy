"""Verified native BeautyGRPO pilot. One source, no character LoRA or postprocess."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from runpy import run_path
import struct
import sys
from types import SimpleNamespace
import urllib.request
import uuid

from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
WORK=ROOT/'work/upgrade-high-20260907'
PROMPT="Beautify this person's face while maintaining a natural and realistic appearance"


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def header(path):
    with path.open('rb') as f:
        size=struct.unpack('<Q',f.read(8))[0]
        if size>64*1024**2:raise ValueError('Unexpected safetensors header.')
        return json.loads(f.read(size))


def api(port,route,body=None):
    req=urllib.request.Request(f'http://127.0.0.1:{port}/{route}',
        data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)


def idle(previous_run=None):
    guard_path=ROOT/'scripts/run-upgrade-no-character-control.py'
    if sha(guard_path)!='48942abd62a4ec18966b55430b723496fafb7ebec4004dcf8cdb2f78ad9b406f':
        raise ValueError('Reviewed idle/owned-cache guard changed.')
    guard=run_path(str(guard_path))
    snapshot=guard['worker_snapshot'](enforce_idle=True,previous_run=previous_run)
    stats=api(8188,'system_stats')['system']
    snapshot['ram']={key:stats[key] for key in ('ram_total','ram_free')}
    return snapshot


def adapter_compatibility(base_path,lora_path):
    # Use the installed native loader on CPU and verify every target against
    # base header shapes. No full diffusion model or CUDA context is allocated.
    # Native attention capability detection probes CUDA despite args.cpu=True.
    # Hide devices in this short-lived preflight process, never the live worker.
    if 'torch' in sys.modules:
        raise RuntimeError('Run adapter preflight in a fresh process before importing torch.')
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    sys.path.insert(0,str(COMFY))
    import comfy.cli_args
    comfy.cli_args.args.cpu=True
    import comfy.utils
    import comfy.lora
    import comfy.model_base
    import torch
    from safetensors.torch import load_file
    base=header(base_path)
    metadata=header(lora_path).get('__metadata__',{})
    adapter_config=json.loads(metadata['lora_adapter_metadata'])
    if (adapter_config.get('transformer.r')!=32 or adapter_config.get('transformer.lora_alpha')!=32
            or adapter_config.get('transformer.use_rslora') or adapter_config.get('transformer.use_dora')
            or adapter_config.get('transformer.rank_pattern') or adapter_config.get('transformer.alpha_pattern')):
        raise ValueError('Released adapter scaling does not match native rank32/alpha32 loading.')
    architecture={'depth':19,'depth_single_blocks':38,'hidden_size':3072}
    mapping=comfy.utils.flux_to_diffusers(architecture,output_prefix='diffusion_model.')
    # Exercise the real node's key-alias builder without allocating the model.
    class HeaderOnlyFlux(comfy.model_base.Flux):
        def __init__(self):
            torch.nn.Module.__init__(self)
            self.model_config=SimpleNamespace(unet_config=architecture)
        def state_dict(self):
            return {'diffusion_model.'+key:None for key in base if key!='__metadata__'}
    native_aliases=comfy.lora.model_lora_keys_unet(HeaderOnlyFlux(),{})
    tensors=load_file(str(lora_path),device='cpu')
    keys={}
    used=set()
    for name,tensor in tensors.items():
        if not name.endswith('.lora_A.weight'):continue
        stem=name[:-len('.lora_A.weight')]
        if not stem.startswith('transformer.'):raise ValueError('Unexpected adapter key.')
        target=mapping[stem[len('transformer.'):]+'.weight']
        if native_aliases.get(stem)!=target:raise ValueError('Native loader alias differs: '+stem)
        weight_name=target[0] if isinstance(target,tuple) else target
        shape=list(base[weight_name.removeprefix('diffusion_model.')]['shape'])
        if isinstance(target,tuple) and target[1] is not None:
            axis,start,length=target[1]
            if start+length>shape[axis]:raise ValueError('Bad packed attention offset.')
            shape[axis]=length
        pair=stem+'.lora_B.weight'
        if tuple(tensor.shape)!=(32,shape[1]) or tuple(tensors[pair].shape)!=(shape[0],32):
            raise ValueError('Adapter/base shape mismatch: '+name)
        used.update((name,pair));keys[stem]=target
    if len(keys)!=342 or used!=set(tensors):raise ValueError('Incomplete released adapter coverage.')
    patches=comfy.lora.load_lora(tensors,keys)
    if len(patches)!=342:raise ValueError('Native loader skipped adapter targets.')
    if any(type(p).__name__!='LoRAAdapter' for p in patches.values()):raise ValueError('Unexpected adapter kind.')
    if torch.cuda.is_available() or torch.cuda.is_initialized():
        raise RuntimeError('The isolated adapter preflight must not initialize CUDA.')
    return {'native_loader_patches':len(patches),'consumed_tensors':len(used),'rank':32,
            'alpha':32,'rslora':False,'dora':False,
            'actual_native_alias_builder_verified':True,
            'base_dimensions_match':True,'cpu_only_preflight':True,'cuda_initialized':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--inspect',action='store_true',help='Inspect downloaded metadata/adapter without submitting.')
    p.add_argument('--previous-run',type=Path,help='Own last successful experiment, required for retained3090 cache.')
    args=p.parse_args()
    receipt=json.loads((WORK/'models/verified-download.json').read_text())
    models=receipt['models']
    paths={item['target']:Path(item['installed']) for item in models}
    for item in models:
        if sha(Path(item['installed']))!=item['sha256']:raise ValueError('Model checksum changed.')
        print('Verified '+item['target'],flush=True)
    base_key=next(k for k in paths if k.startswith('diffusion_models/'))
    if base_key!='diffusion_models/flux1-kontext-dev.safetensors':raise ValueError('This pilot requires original BF16.')
    coverage=adapter_compatibility(paths[base_key],paths['loras/beautygrpo/BeautyGRPO.safetensors'])
    print(json.dumps(coverage),flush=True)
    from huggingface_hub import hf_hub_download
    config_path=Path(hf_hub_download('black-forest-labs/FLUX.1-Kontext-dev',
        'scheduler/scheduler_config.json',revision='24e9dedc4ef646698dc8eb4e18ae2cec3c9fea0d',
        local_dir=WORK/'author-config',token=None))
    config=json.loads(config_path.read_text())
    expected={'base_shift':.5,'max_shift':1.15,'base_image_seq_len':256,'max_image_seq_len':4096,'use_dynamic_shifting':True}
    for key,value in expected.items():
        if config.get(key)!=value:raise ValueError('Author scheduler mismatch: '+key)
    print('Author scheduler: '+json.dumps(config),flush=True)
    if args.inspect:return
    case='beautygrpo-mirror-author'
    destination=WORK/case
    if (destination/'submission-intent.json').exists() or (destination/'submission.json').exists():
        raise ValueError('Submission already attempted; inspect saved evidence, never resubmit blindly.')
    if destination.exists() and not args.execute:
        raise ValueError('Prepared run already exists; preserve it and use --execute after review.')
    if destination.exists() and not (destination/'experiment.json').is_file():
        raise ValueError('Existing destination has no valid prepared manifest; preserve it.')
    preflight=[idle(args.previous_run)]
    source=ROOT/'datasets/mitch-identity-stills-v3/validation/val_02_body_mirror_sleeveless.jpg'
    source_sha='4b32845393fbcbf6ea0ca80068c48af10db52bc81909dba9638370bc7ee0a622'
    if sha(source)!=source_sha:raise ValueError('Genuine source changed.')
    with Image.open(source) as im:
        source_orientation=im.getexif().get(274,1)
        oriented=ImageOps.exif_transpose(im).convert('RGB')
        if oriented.size!=(2992,2992):raise ValueError('Pilot requires whole square photograph.')
        resized=oriented.resize((1024,1024),Image.Resampling.BILINEAR)
    resized.info.clear()
    encoded=io.BytesIO();resized.save(encoded,format='PNG')
    source_data=encoded.getvalue();staged_sha=hashlib.sha256(source_data).hexdigest()
    staged=COMFY/'input/mitch-beautygrpo-mirror-pil-bilinear-4b328453.png'
    if not staged.exists():
        temporary=staged.with_name(staged.name+'.'+uuid.uuid4().hex+'.tmp')
        temporary.write_bytes(source_data)
        if staged.exists():raise ValueError('Staged source appeared concurrently; preserve both files.')
        # This project is Windows-local: rename fails if a concurrent target
        # exists, unlike replace. Never overwrite someone else's staged input.
        temporary.rename(staged)
    if sha(staged)!=staged_sha:raise ValueError('PIL-prepared source mismatch.')
    info=api(8188,'object_info')
    available=info['LoraLoaderModelOnly']['input']['required']['lora_name'][0]
    lora_name=next(n for n in available if n.replace('\\','/')=='beautygrpo/BeautyGRPO.safetensors')
    graph={
        '1':{'class_type':'UNETLoader','inputs':{'unet_name':paths[base_key].name,'weight_dtype':'default'}},
        '2':{'class_type':'LoraLoaderModelOnly','inputs':{'model':['1',0],'lora_name':lora_name,'strength_model':1.0}},
        '3':{'class_type':'DualCLIPLoader','inputs':{'clip_name1':'clip_l.safetensors','clip_name2':'t5xxl_fp16.safetensors','type':'flux','device':'default'}},
        '4':{'class_type':'VAELoader','inputs':{'vae_name':'ae.safetensors'}},
        '5':{'class_type':'LoadImage','inputs':{'image':staged.name}},
        '7':{'class_type':'VAEEncode','inputs':{'pixels':['5',0],'vae':['4',0]}},
        '8':{'class_type':'CLIPTextEncode','inputs':{'clip':['3',0],'text':PROMPT}},
        '9':{'class_type':'ReferenceLatent','inputs':{'conditioning':['8',0],'latent':['7',0]}},
        '10':{'class_type':'FluxGuidance','inputs':{'conditioning':['9',0],'guidance':2.5}},
        '11':{'class_type':'ConditioningZeroOut','inputs':{'conditioning':['8',0]}},
        '12':{'class_type':'KSampler','inputs':{'model':['2',0],'positive':['10',0],'negative':['11',0],'latent_image':['7',0],
            'seed':42,'steps':28,'cfg':1.0,'sampler_name':'euler','scheduler':'simple','denoise':1.0}},
        '13':{'class_type':'VAEDecode','inputs':{'samples':['12',0],'vae':['4',0]}},
        '14':{'class_type':'SaveImage','inputs':{'images':['13',0],'filename_prefix':'upgrade-high-20260907/'+case+'/raw'}},
    }
    for node in graph.values():
        if node['class_type'] not in info:raise ValueError('Live node unavailable: '+node['class_type'])
    for node_id,field in (('1','unet_name'),('2','lora_name'),('3','clip_name1'),('3','clip_name2'),('4','vae_name')):
        node=graph[node_id]
        if node['inputs'][field] not in info[node['class_type']]['input']['required'][field][0]:
            raise ValueError('Exact model unavailable through the live node: '+node['inputs'][field])
    extra=[]
    additional_pins={
        'text_encoders/clip_l.safetensors':'660c6f5b1abae9dc498ac2d21e1347d2abdb0cf6c0c0c8576cd796491d9a6cdd',
        'vae/ae.safetensors':'afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38'}
    for name,expected_sha in additional_pins.items():
        path=COMFY/'models'/name
        if sha(path)!=expected_sha:raise ValueError('Official encoder/VAE pin mismatch: '+name)
        extra.append({'path':str(path),'sha256':expected_sha})
    preflight.append(idle(args.previous_run))
    manifest={'status':'prepared_not_accepted','source':{'path':str(staged),'sha256':staged_sha,'genuine':True,
        'original_path':str(source),'original_sha256':source_sha,'upstream_character_lora':False,
        'preparation':{'exif_orientation':source_orientation,'normalized_orientation':True,
            'method':'PIL BILINEAR with downsampling antialiasing','original_size':[2992,2992],
            'prepared_size':[1024,1024],'crop':False,'face_edits':False}},
        'source_role':'native whole-photo edit source; trained retouching preservation; no separate identity embedding',
        'prompt':graph,'output_node':'14','models':models,'other_models':extra,'coverage':coverage,
        'scheduler_config':config,'preflight':preflight,'steps':28,'seed':42,'guidance':2.5,
        'character_lora':False,'upstream_character_lora':False,'character_training':False,'phone_adapter':False,
        'phone_appearance':'source real phone photo','turbo':False,'postprocess':False,'production_changed':False,
        'backend_differences':['Comfy tabulated simple schedule','CPU seeded noise instead of Diffusers CUDA noise',
            'CLIP/T5 FP16 vs author BF16','EXIF orientation normalized; author inference code ignores EXIF',
            'Comfy native VAE runtime dtype selection'],
        'template':'flux_kontext_dev_basic.json / 654c828f-2572-47e8-ba85-8a832c89b30c',
        'implementation_sha256':sha(Path(__file__))}
    if destination.exists():
        prepared=json.loads((destination/'experiment.json').read_text(encoding='utf-8'))
        if ({k:v for k,v in prepared.items() if k!='preflight'}
                != {k:v for k,v in manifest.items() if k!='preflight'}):
            raise ValueError('Prepared manifest differs from fresh verified evidence.')
    else:
        destination.mkdir(parents=True)
        (destination/'experiment.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        (destination/'prompt-api.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')
    if json.loads((destination/'prompt-api.json').read_text(encoding='utf-8'))!=graph:
        raise ValueError('Prepared standalone graph differs from freshly verified graph.')
    if not args.execute:print('Prepared only: '+str(destination));return
    client_id='beautygrpo-'+uuid.uuid4().hex
    # Exclusive creation prevents two concurrent executions from both submitting.
    with (destination/'submission-intent.json').open('x',encoding='utf-8') as intent:
        json.dump({'client_id':client_id,
            'status':'attempt_started_no_blind_resubmission','manifest_sha256':sha(destination/'experiment.json'),
            'fresh_preflight':preflight},intent,indent=2)
    result=api(8188,'prompt',{'prompt':graph,'client_id':client_id})
    (destination/'submission.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
    if result.get('node_errors'):raise RuntimeError('Live validation rejected graph.')


if __name__=='__main__':main()
