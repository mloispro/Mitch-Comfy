"""One explicit-scene conditioning refinement; no queue, pixels, defaults or weights changed."""
import argparse
import copy
import json
from pathlib import Path
from runpy import run_path

from upgrade_background_detail import build_graph, validate_graph

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT.parent/'ComfyUI'
CONTROL=ROOT/'work/upgrade-source-faithful-20260903/background-detail-house-pilot'
CONTROL_SHA='2204825b75ffed259fd6db0733ba11793f9fcad7795a07bb493968729cb49b94'
BACKGROUND=COMFY/'output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260904-020400-003998/before-polish_00001_.png'
BACKGROUND_SHA='4908d5a2399bf04a4708bcc8cba534ceaf952bf34d1b6cef6142f93082b720e2'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):
        raise ValueError('Use a fresh refinement directory.')
    helper=run_path(str(ROOT/'scripts/prepare-upgrade-background-detail.py'))
    digest=helper['digest'];read=helper['read']
    if digest(CONTROL/'experiment.json')!=CONTROL_SHA or digest(BACKGROUND)!=BACKGROUND_SHA:
        raise ValueError('Parent experiment or explicit background image changed.')
    original=read(CONTROL/'experiment.json');validate_graph(original)
    manifest=copy.deepcopy(original)
    for ref in manifest['references']:
        if digest(ref['path'])!=ref['sha256']:
            raise ValueError('Fixed source, identity, or person mask changed.')
    background={'path':str(BACKGROUND),'name':'mitch-upgrade-bg-scene-'+BACKGROUND_SHA[:12]+'.png',
                'sha256':BACKGROUND_SHA,'role':'synthetic_original_scene_background_not_identity',
                'megapixels':1.0,'upscale_method':'bicubic','resolution_steps':16,
                'provenance_report':str(BACKGROUND.with_name('report.json')),
                'provenance_report_sha256':digest(BACKGROUND.with_name('report.json'))}
    manifest['references'].append(background)
    prefix='upgrade-source-faithful/'+out.name
    graph=build_graph(original['prompt'],*(r['name'] for r in original['references']),
                       original['dimensions'],original['seed'],prefix,background_name=background['name'])
    # Existing sampling/source/identity/mask nodes cannot change beyond the
    # role-specific text and final conditioning chain required by Picture3.
    allowed={'6','21','27','31'}
    for key,node in original['prompt'].items():
        if key not in allowed and graph[key]!=node:
            raise ValueError('Unintended change to fixed pilot configuration.')
    if graph['21']['inputs']!={**original['prompt']['21']['inputs'],
                              'positive':['43',0],'negative':['44',0]}:
        raise ValueError('Unexpected guider change.')
    manifest.update(status='prepared_scene_reference_refinement_not_submitted',prompt=graph,
        reference_mode='source_first_genuine_second_background_third',output_prefix=prefix,
        effective_prompt=graph['6']['inputs']['text'],
        refinement_parent=str(CONTROL/'experiment.json'),refinement_parent_sha256=CONTROL_SHA,
        refinement_kind='single_explicit_original_background_reference',
        controlled_change='Add Picture3 background composition/material reference with role-specific text; source/person mask, identity, adapters, seed and sampler unchanged.',
        observation_only_additions=['source-latent SaveLatent leaf','sampled-latent SaveLatent leaf'],
        unchanged_mask_review_sha256=original['references'][2]['sha256'])
    validate_graph(manifest)
    out.mkdir(parents=True)
    (out/'experiment.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'manifest':str(out/'experiment.json'),'sha256':digest(out/'experiment.json'),
                      'added_background':background,'mask_unchanged':True},indent=2))


if __name__=='__main__':main()
