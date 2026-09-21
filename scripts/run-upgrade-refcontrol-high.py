"""One local author-derived RefControl pilot, using reviewed source contours."""
from __future__ import annotations

import argparse
import importlib.util
import json
import uuid
from pathlib import Path

from upgrade_refcontrol_high import (
    ROOT, COMFY, PINS, PROMPTS, build_graph, digest, image_name, read_json, validate_inputs,
)

# Reuse the tested read-only queue, hardware and exact owned-cache checks.
spec = importlib.util.spec_from_file_location('upgrade_dev_runtime', Path(__file__).with_name('run-upgrade-dev-high.py'))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation', type=Path, required=True)
    parser.add_argument('--baseline-report', type=Path, required=True)
    parser.add_argument('--previous-run', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--contours-visually-reviewed', action='store_true', required=True)
    parser.add_argument('--prompt-variant', choices=tuple(PROMPTS), default='high')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    destination, previous = args.output_dir.resolve(), args.previous_run.resolve()
    if destination.exists() or not destination.is_relative_to(ROOT / 'work') or not previous.is_relative_to(ROOT / 'work'):
        raise ValueError('Use a fresh project work directory and an existing owned experiment.')
    snapshots = [runtime.idle_snapshot(previous)]
    preparation = read_json(args.preparation)
    audit_path = Path(preparation['source_audit'])
    if digest(audit_path) != preparation['source_audit_sha256']:
        raise ValueError('Prepared original source audit changed.')
    audit, report = read_json(audit_path), read_json(args.baseline_report)
    source = Path(preparation['source']['path']).resolve(strict=True)
    baseline = (ROOT / audit['inputs']['BASE RAW']['path']).resolve(strict=True)
    refs = [preparation['control'],
            {'path':str(baseline), 'name':image_name(baseline), 'sha256':digest(baseline),
             'role':'generated same-photo PhoneON raw: synthetic identity/style self-reference, not genuine evaluation evidence'}]
    prefix = 'upgrade-source-faithful/' + destination.name + '/raw'
    graph = build_graph(refs, report['seed'], prefix, args.prompt_variant)
    if args.prompt_variant == 'author-trigger-only':
        pilot = read_json(previous / 'experiment.json')
        if not (pilot.get('stage') == 'refcontrol_native_high_edit'
                and pilot.get('prompt_variant','high') == 'high'
                and pilot['references'] == refs and pilot['seed'] == report['seed']):
            raise ValueError('The sole trigger-only refinement must follow its exact paired High pilot.')
        changes = {key for key in graph if graph[key] != pilot['prompt'][key]}
        if changes != {'5','37'}:
            raise ValueError('Refinement changed more than prompt text and output destination.')
    info = runtime.api(8188, 'object_info')
    fields = {'UNETLoader':'unet_name','CLIPLoader':'clip_name','VAELoader':'vae_name','LoraLoaderModelOnly':'lora_name'}
    for node in graph.values():
        kind = node['class_type']
        if kind not in info:
            raise ValueError('Missing live node: ' + kind)
        if kind in fields:
            field = fields[kind]
            if node['inputs'][field] not in info[kind]['input']['required'][field][0]:
                raise ValueError('Model not visible: ' + node['inputs'][field])
    verified = []
    for relative, expected in PINS.items():
        path = COMFY / 'models' / relative
        actual = digest(path)
        if actual != expected:
            raise ValueError('Protected model changed: ' + relative)
        verified.append({'model_relative_path':relative,'path':str(path),'sha256':actual})
        print('Hash verified: ' + relative, flush=True)
    manifest = {
        'status':'prepared_not_promoted', 'stage':'refcontrol_native_high_edit',
        'source_audit':str(audit_path), 'source_audit_sha256':digest(audit_path),
        'baseline_report':str(args.baseline_report.resolve()), 'baseline_report_sha256':digest(args.baseline_report),
        'preparation':str(args.preparation.resolve()), 'preparation_sha256':digest(args.preparation),
        'contours_visually_reviewed':True, 'synthetic_self_reference':True,
        'references':refs, 'verified_models':verified, 'seed':report['seed'], 'steps':20, 'cfg':5,
        'adapter_strength':1.0, 'output_prefix':prefix, 'effective_prompt':PROMPTS[args.prompt_variant],
        'prompt_variant':args.prompt_variant,
        'phone_camera_style':False, 'upstream_phone_camera_style':True,
        'phone_appearance_mode':'inherited_klein_raw_no_stacked_adapter',
        'pose_target':'original source; raw drift remains diagnostic',
        'turbo':False, 'postprocess':False, 'production_changed':False,
        'prompt':graph, 'preflight':snapshots,
    }
    validate_inputs(manifest, source, baseline)
    snapshots.append(runtime.idle_snapshot(previous))
    destination.mkdir(parents=True)
    (destination / 'experiment.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if args.prepare_only:
        print('Prepared, not submitted: ' + str(destination), flush=True)
        return
    # One POST only: never automatically retry an uncertain submission.
    submission = runtime.api(8188,'prompt',{'prompt':graph,'client_id':'upgrade-refcontrol-high-' + uuid.uuid4().hex})
    (destination / 'submission.json').write_text(json.dumps(submission,indent=2),encoding='utf-8')
    print(json.dumps(submission),flush=True)
    if submission.get('node_errors'):
        raise RuntimeError('Live graph validation rejected this experiment.')


if __name__ == '__main__': main()
