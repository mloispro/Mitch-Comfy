"""Acquire the authorized author BeautyGRPO adapter and compatible Kontext model.

No generation, training, photos, dependency changes or production graph edits.
Default is metadata inspection. --download retrieves only the selected files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi, get_hf_file_metadata, hf_hub_download, hf_hub_url

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'work/upgrade-high-20260907/models'
COMFY = ROOT.parent/'ComfyUI'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2), b''):h.update(block)
    return h.hexdigest()


def entry(repo, filename, target, token=False):
    info = HfApi(token=token).model_info(repo,files_metadata=True)
    item = next(s for s in info.siblings if s.rfilename == filename)
    if not item.lfs or len(item.lfs.sha256)!=64:raise ValueError('No published SHA256.')
    return {'repo':repo,'revision':info.sha,'filename':filename,'size':item.size,
            'sha256':item.lfs.sha256,'target':target,'token':token}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--download',action='store_true')
    args=p.parse_args()
    adapter=entry('Sehnsucht24/BeautyGRPO','fluxkontext/checkpoint/pytorch_lora_weights.safetensors',
                  'loras/beautygrpo/BeautyGRPO.safetensors')
    if adapter['sha256']!='23105cbd94fcd9f7b14d224dd28ce84cb5fa0f9bd5ba077cc0de27428e46c8a1':
        raise ValueError('Author adapter changed from reviewed release.')
    base_repo='black-forest-labs/FLUX.1-Kontext-dev'
    base_file='flux1-kontext-dev.safetensors'
    try:
        # Use the normal stored HF authentication if already authorized. Never
        # print credentials or agree to a new account-sharing gate here.
        get_hf_file_metadata(hf_hub_url(base_repo,base_file),token=None)
        base=entry(base_repo,base_file,'diffusion_models/flux1-kontext-dev.safetensors',token=None)
        parity='BF16 original diffusion model; text precision recorded separately'
    except Exception as exc:
        print('Original BF16 access unavailable: '+type(exc).__name__,flush=True)
        base=entry('Comfy-Org/flux1-kontext-dev_ComfyUI',
            'split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors',
            'diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors')
        parity='Official Comfy FP8-scaled diffusion export; not author BF16 parity'
    # Avoid quantized text when testing a trained retouching adapter.
    encoder=entry('comfyanonymous/flux_text_encoders','t5xxl_fp16.safetensors',
                  'text_encoders/t5xxl_fp16.safetensors')
    selected=[adapter,base,encoder]
    public=[{k:v for k,v in item.items() if k!='token'} for item in selected]
    print(json.dumps({'selected':public,'precision':parity,'download':args.download},indent=2),flush=True)
    if not args.download:return
    if shutil.disk_usage(ROOT).free<sum(i['size'] for i in selected)*3:
        raise ValueError('Insufficient disk space for verified download/install.')
    WORK.mkdir(parents=True,exist_ok=True)
    records=[]
    for item in selected:
        dest=COMFY/'models'/item['target']
        if dest.exists():
            if sha(dest)!=item['sha256']:raise ValueError('Preserve conflicting model: '+str(dest))
            print('Already verified: '+str(dest),flush=True)
        else:
            print('Downloading '+item['target'],flush=True)
            source=Path(hf_hub_download(item['repo'],filename=item['filename'],revision=item['revision'],
                token=item['token'],local_dir=WORK/item['repo'].replace('/','--')))
            if sha(source)!=item['sha256']:raise ValueError('Downloaded hash mismatch.')
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dest)
            if sha(dest)!=item['sha256']:raise ValueError('Installed hash mismatch.')
        records.append({**{k:v for k,v in item.items() if k!='token'},'installed':str(dest)})
        print('Verified '+item['target'],flush=True)
    receipt=WORK/'verified-download.json'
    if receipt.exists():raise ValueError('Preserve existing receipt.')
    receipt.write_text(json.dumps({'models':records,'precision':parity,
        'authorization':'download whatever you want; get it done',
        'photos_uploaded':False,'character_training':False,'dependencies_changed':False},indent=2),encoding='utf-8')
    print('Receipt: '+str(receipt),flush=True)


if __name__=='__main__':main()
