"""Fresh paths only: frozen native guards and fully constructed heartbeat observer."""
import argparse
import asyncio
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = Path('C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/group-identity-hook-gate/runtime-3090')
GATE = OLD.parent
PILOT_SHA = 'EB6AEF903DB72BE0E8CED5389EFB1C01E08E586B76C611CF3665796C05EFA76A'
OLD_MANIFESTS = (
    ('RUNTIME-PREPARED.json', '9A8F7E80AF8AD5D92F9FF9069D62DEEC1DB2D5114F747B3BFA718EB7931DE4BA'),
    ('RUNTIME-V2-PREPARED.json', 'A7647D023A1F6EABC1AC7A8932C2CD47EDE581E0B4E9C3835C12A7949A00B540'),
    ('RUNTIME-V3-PREPARED.json', '6FA31727CB5F9BB1BB7249392BEC8BCE08EE96F952F40B63A26098706A43942F'),
    ('PILOT-OBSERVATION-PREPARED.json', '8B05369AB2B3C5582EFE6564C4947C869AA9957FC09E7C647B7B6F21E37D0CB4'),
    ('PILOT-BOUND-PREPARED.json', '51D903DE2AC1F2A40215C681508F0228DD1E2C75D25971FC7DFBF6278848DC11'),
    ('PILOT-RECOVERY-PREPARED.json', '825D00CA45056DFBE06EE8BE3FE2C851D7BF490DA6A17F838A8D82E5B16A3793'),
)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def verify():
    """Read-only, no neural imports, live probes, or large model hashing."""
    count = 0
    for name, expected in OLD_MANIFESTS:
        require(sha(OLD/name) == expected, 'Historical manifest drift: '+name)
        for pin in read(OLD/name)['pins']:
            require(sha(pin['path']) == pin['sha256'], 'Historical source drift: '+pin['path'])
            count += 1
    for name in ('FROZEN-PAIR.json', 'PAIR-PREPARATION.json'):
        receipt = read(GATE/name)
        for pin in receipt['pins']:
            require(sha(pin['path']) == pin['sha256'], 'Pair pin drift: '+pin['path'])
            count += 1
        for model in receipt.get('model_metadata_only', []):
            stat = Path(model['path']).stat()
            require(stat.st_size == model['bytes'] and str(stat.st_mtime_ns) == model['mtime_ns'], 'Model metadata drift')
    prepared = read(HERE/'prepared.json')
    require(prepared['scope'] == 'ONE_FRESH_OWNED_GROUP_PILOT' and prepared['payload_sha256'] == PILOT_SHA, 'Wrong fresh preparation')
    for pin in prepared['pins']:
        require(sha(pin['path']) == pin['sha256'], 'Fresh pin drift: '+pin['path'])
    archive = read(OLD/'INTERRUPTED-PILOT-ARCHIVE.json')
    require(archive['no_image'] and archive['prompt_id'] == '0fcde1cd-8123-490d-8a5c-1cd8dd9dae93', 'Wrong historical interruption')
    for pin in archive['files']:
        path = Path(archive['archive_path'])/pin['name']
        require(sha(path) == pin['sha256'] and path.stat().st_size == pin['bytes'], 'Interrupted evidence drift')
    require(sha(GATE/'amber-hook-pilot-payload.json') == PILOT_SHA, 'Pilot graph drift')
    return {'status': 'PASS', 'historical_pin_checks': count, 'fresh_pins': len(prepared['pins']),
            'worker_root': str(HERE/'worker'), 'gpu_initialized': False, 'live_probes': False}


def route():
    """Load the final frozen implementation first, then bind one new lifetime."""
    verify()
    sys.path.insert(0, str(OLD))
    heartbeat = importlib.import_module('watch_pilot_heartbeat')
    guard = importlib.import_module('guard_runtime_v3')
    # Every imported function refers to this same guard module. Native methods,
    # thresholds, full graph checks, observer state machine and heartbeat stay intact.
    guard.HERE, guard.GATE, guard.WORKER = HERE, GATE, HERE/'worker'
    guard.CASES = {'pilot': PILOT_SHA}
    guard.__file__ = str(HERE/'fresh_runtime.py')  # ready receipt binds this routing source

    # Two helper calls use the same one PowerShell facade; Python-only env cleanup
    # is exactly the already reviewed bound observer's implementation.
    bound = heartbeat.prior
    interrupt_source = inspect.getsource(bound.original.captured_interrupt)
    replacements = (
        ("str(g.HERE/'interrupt-owned-v3.ps1'),", "str(g.HERE/'fresh.ps1'),'-Action','interrupt',"),
        ('spawn=asyncio.create_subprocess_exec', 'spawn=clean_spawn'),
    )
    for before, after in replacements:
        require(interrupt_source.count(before) == 1, 'Interrupt route anchor differs')
        interrupt_source = interrupt_source.replace(before, after)
    interrupt_namespace = dict(vars(bound.original), clean_spawn=bound.clean_spawn)
    exec(compile(interrupt_source, str(HERE/'fresh_runtime.py'), 'exec'), interrupt_namespace)
    admit_source = bound.admit_adapted
    before = "str(g.HERE/'wddm-lifetimes-v3.ps1'),"
    after = "str(g.HERE/'fresh.ps1'),'-Action','wddm',"
    require(admit_source.count(before) == 1, 'Desktop helper route anchor differs')
    admit_source = admit_source.replace(before, after)
    admit_namespace = dict(bound.admit_namespace)
    exec(compile(admit_source, str(HERE/'fresh_runtime.py'), 'exec'), admit_namespace)
    heartbeat.namespace['captured_interrupt'] = interrupt_namespace['captured_interrupt']
    heartbeat.namespace['admit_desktops'] = admit_namespace['admit_desktops']
    return guard, heartbeat


def install():
    # Invoked solely by this package's private custom-node registration entry.
    guard, _ = route()
    guard.install()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--verify', action='store_true')
    action.add_argument('--memory', action='store_true')
    action.add_argument('--watch', action='store_true')
    parser.add_argument('--case', choices=('pilot',), default='pilot')
    args = parser.parse_args()
    if args.memory:
        # This import defines native-counter functions only; it does not install.
        sys.path.insert(0, str(OLD))
        from guard_runtime_v3 import memory_snapshot
        print(json.dumps(memory_snapshot()))
    elif args.watch:
        _, observer = route()
        asyncio.run(observer.run_case(args.case))
    else:
        print(json.dumps(verify()))
