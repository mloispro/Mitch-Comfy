"""Inspect actual installed Klein tokenization; never load model weights or generate."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
sys.path.insert(0,str(COMFY))
from comfy.cli_args import args as comfy_args
comfy_args.cpu=True
from comfy.text_encoders.flux import KleinTokenizer8B


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT):
        raise ValueError('Use a new project-local audit path.')
    work=ROOT/'work/upgrade-source-faithful-20260903'
    paths={
        'production_canyon':COMFY/'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-005704-305944/report.json',
        'production_house':COMFY/'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-111226-463056/report.json',
        'previous_native_high':work/'native-high-canyon/experiment.json',
        'compact_native_high':work/'compact-native-high-prompt.txt',
    }
    tokenizer=KleinTokenizer8B();records={}
    for name,path in paths.items():
        data=path.read_text(encoding='utf-8-sig')
        prompt=json.loads(data)['effective_prompt'] if path.suffix=='.json' else data
        chunks=tokenizer.tokenize_with_weights(prompt)['qwen3_8b']
        ids=[int(item[0]) for chunk in chunks for item in chunk]
        nonpad=[i for i in ids if i!=151643]
        records[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'tokens_including_padding':len(ids),'nonpad_tokens_including_chat_template':len(nonpad),
            'chunks':len(chunks),'all_four_roles_present':all(f'Picture {i}' in prompt for i in range(1,5)),
            'identity_trigger_present':'m1tch_person' in prompt,'phone_trigger_present':'casual snapshot' in prompt,
            'decoder_tail':tokenizer.decode(nonpad[-28:]),'prompt':prompt}
    compact=records['compact_native_high']
    assert compact['nonpad_tokens_including_chat_template']<=512
    assert compact['all_four_roles_present'] and compact['identity_trigger_present'] and compact['phone_trigger_present']
    report={'records':records,'production_changed':False,'models_loaded':False,'diffusion_runs':0,
        'installed_flux_encoder_sha256':hashlib.sha256((COMFY/'comfy/text_encoders/flux.py').read_bytes()).hexdigest(),
        'finding':'Installed Comfy tokenizer does not truncate to512; BFL reference Qwen3Embedder caps at512. A longer prompt is an implementation difference, not established cause of image defects.',
        'experiment_limit':'Compact prompt also rewrites wording; a visual change cannot be attributed solely to token length.',
        'author_source':'https://github.com/black-forest-labs/flux2/blob/main/src/flux2/text_encoder.py'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:{k:v for k,v in value.items() if k not in ('prompt','decoder_tail')} for key,value in records.items()},indent=2))


if __name__=='__main__': main()
