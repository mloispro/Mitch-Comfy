"""Prove two recorded native graphs differ only in one chosen text branch/save prefix."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(old,new,branch='positive'):
    if branch not in ('positive','negative'): raise ValueError('Select the one text branch under test.')
    if old['reference_mode']!='four' or new['reference_mode']!='four':
        raise ValueError('Expected the unchanged four-reference layout.')
    for field in ('identity_strength','seed','steps','cfg','turbo'):
        if old.get(field)!=new.get(field): raise ValueError(f'Experiment changed {field}.')
    # Older manifests omit the convenience phone-strength field. The submitted
    # LoRA node is authoritative and is still compared exactly below.
    for manifest in (old,new):
        if ('phone_camera_style_strength' in manifest and manifest['phone_camera_style_strength']
                !=manifest['prompt']['3']['inputs']['strength_model']):
            raise ValueError('Declared phone strength conflicts with actual graph.')
    for field in ('references','verified_models'):
        if old[field]!=new[field]: raise ValueError(f'Experiment changed {field}.')
    before,after=old['prompt'],new['prompt']
    if before.keys()!=after.keys(): raise ValueError('Graph node set changed.')
    differences=[]
    text_node='6' if branch=='positive' else '7'
    allowed={(text_node,'text'),('27','filename_prefix')}
    for node in before:
        if before[node]['class_type']!=after[node]['class_type']: raise ValueError('Node class changed.')
        a,b=before[node]['inputs'],after[node]['inputs']
        if a.keys()!=b.keys(): raise ValueError('Node inputs changed.')
        for key in a:
            if a[key]!=b[key]:
                if (node,key) not in allowed: raise ValueError(f'Unexpected graph difference: {node}.{key}')
                differences.append(f'{node}.{key}')
    if f'{text_node}.text' not in differences: raise ValueError('Selected text branch did not change.')
    return differences


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--branch',choices=('positive','negative'),default='positive')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if args.output.exists() or not args.output.resolve().is_relative_to(root):
        raise ValueError('Use a new project-local output.')
    old=json.loads(args.before.read_text(encoding='utf-8-sig'))
    new=json.loads(args.after.read_text(encoding='utf-8-sig'))
    report={'graph_differences':compare(old,new,args.branch),'text_branch':args.branch,'passed':True,
        'before_sha256':hashlib.sha256(args.before.read_bytes()).hexdigest(),
        'after_sha256':hashlib.sha256(args.after.read_bytes()).hexdigest(),
        'scope':'Submitted graph/recorded provenance comparison. Executed PNG metadata must still be checked after generation.',
        'production_changed':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
