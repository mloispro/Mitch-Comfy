"""One frozen source-geometry correction to the completed masked house pilot."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from upgrade_local_inpaint import build_graph, validate_graph, SOURCE_GEOMETRY_PROMPT

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT/'work/upgrade-source-faithful-20260903/native-masked-high-house-ready'
CONTROL_SHA = 'a79d8c16d7d690c88675059040985dde31d6170c8870baab2c81a5c3fbad55f1'
SOURCE = ROOT.parent/'ComfyUI/input/mitch-photo2-source-aef87048.png'
SOURCE_SHA = 'aef8704873c40c92ec365c091ea142998e72b3d80d22b45f55275309165ba5b4'


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(); out = args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):
        raise ValueError('Use a fresh project work folder.')
    if digest(CONTROL/'experiment.json') != CONTROL_SHA or digest(SOURCE) != SOURCE_SHA:
        raise ValueError('Pinned control or original source changed.')
    previous = json.loads((CONTROL/'experiment.json').read_text(encoding='utf-8-sig'))
    validate_graph(previous)
    for ref in previous['references']:
        if digest(ref['path']) != ref['sha256']:
            raise ValueError('Existing masked-pilot input changed.')
    result = copy.deepcopy(previous)
    result['references'].append({'path': str(SOURCE), 'name': SOURCE.name,
                                 'sha256': SOURCE_SHA,
                                 'role': 'original_source_geometry_expression_not_identity'})
    result.update(status='prepared_not_submitted', stage='klein_base9b_masked_high_original_geometry',
                  reference_mode='raw_first_genuine_second_original_geometry_third',
                  refinement_parent=str(CONTROL/'experiment.json'), refinement_parent_sha256=CONTROL_SHA,
                  effective_prompt=SOURCE_GEOMETRY_PROMPT,
                  output_prefix='upgrade-source-faithful/'+out.name,
                  interpretation='One conditioning-layout correction: append original geometry/expression reference and corresponding role wording. All models, strengths, seed, source latent, mask, sampler and negative text stay fixed. No postprocessing.')
    refs = result['references']
    result['prompt'] = build_graph(previous['prompt'], refs[0]['name'], refs[1]['name'],
                                  refs[2]['name'], result['dimensions'], result['seed'],
                                  result['output_prefix'], refs[3]['name'])
    validate_graph(result)
    old, new = previous['prompt'], result['prompt']
    if set(new)-set(old) != {'40','41','42','43','44'} or set(old)-set(new):
        raise ValueError('Unexpected node-layout changes.')
    changes = [f'{key}.{field}' for key in old for field in old[key]['inputs']
               if old[key]['inputs'][field] != new[key]['inputs'][field]]
    if sorted(changes) != ['21.negative','21.positive','27.filename_prefix','31.filename_prefix','6.text']:
        raise ValueError('Unplanned old-node change: '+repr(changes))
    result['controlled_changes'] = {'added_nodes': sorted(set(new)-set(old)),
                                    'changed_existing_inputs': sorted(changes)}
    out.mkdir(parents=True)
    path = out/'experiment.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'manifest':str(path),'sha256':digest(path),'changes':result['controlled_changes']},indent=2))


if __name__ == '__main__': main()
