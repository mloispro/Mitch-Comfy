"""Submit one guarded local Dev experiment; no production edits or model downloads."""
from __future__ import annotations

import argparse
import copy
import json
import socket
import subprocess
import urllib.request
import uuid
from pathlib import Path

from upgrade_dev_high import COMFY, ROOT, PINS, MODEL, CLIP, VAE, LORA, PROMPT, build_graph, digest, image_name, read_json, validate_inputs


def api(port, route, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f'http://127.0.0.1:{port}/{route}', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def idle_snapshot(previous):
    workers = []
    for port in (8188, 8189, 8190):
        try:
            stats, queue = api(port, 'system_stats'), api(port, 'queue')
        except Exception:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.5):
                    pass
            except OSError:
                if port in (8188, 8189):
                    raise RuntimeError(f'Required worker{port} cannot be inspected.')
                workers.append({'port': port, 'online': False})
                continue
            raise RuntimeError(f'Listening worker{port} cannot be inspected.')
        row = {'port': port, 'online': True, 'device': stats['devices'][0]['name'],
               'running': len(queue['queue_running']), 'pending': len(queue['queue_pending'])}
        workers.append(row)
        if '3090' in row['device'] and (row['running'] or row['pending']):
            raise RuntimeError('Preserve active3090 work.')
        if port == 8188 and '3090' not in row['device']:
            raise RuntimeError('Upgrade is locked to RTX3090/8188.')
    hardware = subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], text=True)
    rows = [line.split(',') for line in hardware.splitlines() if 'RTX 3090' in line]
    if len(rows) != 1 or int(rows[0][3].strip()) > 10:
        raise RuntimeError('3090 is busy or ambiguous.')
    expected_id = read_json(previous / 'submission.json')['prompt_id']
    latest = api(8188, 'history?max_items=1')
    if list(latest) != [expected_id] or not latest[expected_id]['status']['completed'] or latest[expected_id]['status']['status_str'] != 'success':
        raise RuntimeError('Latest job is not the saved owned terminal success; preserve cache.')
    expected = read_json(previous / 'experiment.json')['prompt']
    actual = copy.deepcopy(latest[expected_id]['prompt'][2])
    for node in actual.values():
        node.pop('is_changed', None)
    if actual != expected:
        raise RuntimeError('Owned cached graph does not match saved experiment.')
    return {'workers': workers, 'hardware': hardware, 'owned_cache_prompt_id': expected_id,
            'explicit_free': False, 'worker_restart': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-audit', type=Path, required=True)
    parser.add_argument('--baseline-report', type=Path, required=True)
    parser.add_argument('--previous-run', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--identity-strength', type=float, choices=(1.1,0.8), default=1.1)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    destination, previous = args.output_dir.resolve(), args.previous_run.resolve()
    if destination.exists() or not destination.is_relative_to(ROOT / 'work') or not previous.is_relative_to(ROOT / 'work'):
        raise ValueError('Use a fresh project work directory and an existing owned experiment.')
    snapshots = [idle_snapshot(previous)]
    audit, report = read_json(args.source_audit), read_json(args.baseline_report)
    refs = []
    for key, role in (('BASE RAW', 'detailed PhoneON edit target; not genuine identity evidence'),
                      ('SOURCE', 'original pose/pupil/expression reference; not a verified identity anchor')):
        path = (ROOT / audit['inputs'][key]['path']).resolve(strict=True)
        refs.append({'path': str(path), 'name': image_name(path), 'sha256': digest(path), 'role': role})
    info = api(8188, 'object_info')
    for kind, field, name in (('UNETLoader','unet_name',MODEL), ('CLIPLoader','clip_name',CLIP), ('VAELoader','vae_name',VAE), ('LoraLoaderModelOnly','lora_name',LORA)):
        if name not in info[kind]['input']['required'][field][0]:
            raise RuntimeError(f'Model not visible: {name}')
    verified = []
    for relative, expected_hash in PINS.items():
        path = COMFY / 'models' / relative
        actual_hash = digest(path)
        if actual_hash != expected_hash:
            raise ValueError(f'Protected model changed: {relative}')
        verified.append({'model_relative_path': relative, 'path': str(path), 'sha256': actual_hash})
        print(f'Hash verified: {relative}', flush=True)
    prefix = 'upgrade-source-faithful/' + destination.name + '/raw'
    graph = build_graph(refs, report['seed'], prefix, args.identity_strength)
    for node in graph.values():
        if node['class_type'] not in info:
            raise ValueError('Missing live node: ' + node['class_type'])
    manifest = {'status': 'prepared_not_promoted', 'stage': 'dev_native_high_edit',
                'source_audit': str(args.source_audit.resolve()), 'source_audit_sha256': digest(args.source_audit),
                'baseline_report': str(args.baseline_report.resolve()), 'baseline_report_sha256': digest(args.baseline_report),
                'references': refs, 'verified_models': verified, 'seed': report['seed'], 'steps': 28,
                'guidance': 4, 'identity_strength': args.identity_strength, 'output_prefix': prefix, 'effective_prompt': PROMPT,
                'phone_camera_style': False, 'upstream_phone_camera_style': True,
                'phone_appearance_mode': 'inherited_klein_raw_not_active_dev_adapter',
                'turbo': False, 'postprocess': False, 'production_changed': False,
                'prompt': graph, 'preflight': snapshots}
    validate_inputs(manifest, refs[1]['path'], refs[0]['path'])
    snapshots.append(idle_snapshot(previous))
    destination.mkdir(parents=True)
    (destination / 'experiment.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if args.prepare_only:
        print('Prepared, not submitted: ' + str(destination), flush=True)
        return
    # Single submission only. Never auto-retry an uncertain POST.
    submission = api(8188, 'prompt', {'prompt': graph, 'client_id': 'upgrade-dev-high-' + uuid.uuid4().hex})
    (destination / 'submission.json').write_text(json.dumps(submission, indent=2), encoding='utf-8')
    print(json.dumps(submission), flush=True)
    if submission.get('node_errors'):
        raise RuntimeError('Live graph validation rejected this experiment.')


if __name__ == '__main__':
    main()
