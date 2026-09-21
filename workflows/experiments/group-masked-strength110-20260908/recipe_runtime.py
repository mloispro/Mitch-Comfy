"""One recipe/lifetime routing boundary; frozen native guards and observer unchanged."""
import argparse
import asyncio
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PARENT = Path('C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/group-masked-pilot-resume-20260908')
OLD = Path('C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/group-identity-hook-gate/runtime-3090')
PROVENANCE_GATE = OLD.parent
GATE = HERE
PILOT_SHA = 'DFE5EDBF8205188C6DA053FE74C747A234D050DA0889D44017A610ACE8657CD1'
PARENT_PREPARED = '5A9166BD335BEDB19F16FDFA5501AB8CC471DD76ADE9A9025479FA9755B4CEF4'
PARENT_SUPPLEMENT = 'F0223AC4A24DE150C0B3BC168FF45A394796289128EDBDA1576F544B778A6E46'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_recipe(recipe):
    require(recipe['scope'] == 'ONE_GROUP_MASKED_STRENGTH_REFINEMENT', 'Wrong recipe scope')
    require(recipe['parent_prepared_sha256'] == PARENT_PREPARED, 'Wrong parent recipe')
    source = Path(recipe['parent_payload_path'])
    require(source == PROVENANCE_GATE/'amber-hook-pilot-payload.json', 'Wrong source graph')
    require(sha(source) == recipe['parent_payload_sha256'] == 'EB6AEF903DB72BE0E8CED5389EFB1C01E08E586B76C611CF3665796C05EFA76A', 'Parent graph drift')
    require(sha(HERE/'amber-hook-pilot-payload.json') == recipe['payload_sha256'] == PILOT_SHA, 'Recipe graph drift')
    changes = recipe['changes']
    require(changes == [
        {'path':['prompt','50','inputs','strength_model'], 'before':.9, 'after':1.1},
        {'path':['prompt','37','inputs','filename_prefix'], 'before':'9b-readiness-resume-20260907/group-amber-hook-pilot-seed8675412', 'after':'group-masked-strength110-20260908/group-amber-hook-s110-seed8675412'}], 'Only declared strength and save prefix may change')
    expected = copy.deepcopy(read(source))
    for change in changes:
        target = expected
        for key in change['path'][:-1]:
            target = target[key]
        key = change['path'][-1]
        require(target[key] == change['before'] and type(target[key]) is type(change['before']), 'Wrong original value')
        target[key] = change['after']
    # JSON equality alone treats true==1; canonical serialization preserves that distinction.
    actual = read(HERE/'amber-hook-pilot-payload.json')
    require(json.dumps(expected, sort_keys=True) == json.dumps(actual, sort_keys=True), 'Undeclared graph delta')
    require(recipe['internal_case'] == 'pilot' and recipe['run_name'] == 'ready-amber-hook-pilot', 'Case routing changed')
    require(Path(recipe['worker_root']) == HERE/'worker', 'Worker root changed')
    require(Path(recipe['execution_order_path']) == PROVENANCE_GATE/'PAIR-SCHEDULE-RESULTS.json', 'Schedule source changed')
    require(sha(recipe['execution_order_path']) == recipe['execution_order_sha256'] == 'DC3280FDD3DB0EACE1E8D6816ED9F0313F8C4FAD2D3F3E6CCD3B12618A731DE9', 'Schedule drift')
    require(len(actual['prompt']) == 36 and recipe['no_automatic_retry'] is True, 'Topology/retry changed')
    return recipe


def verify():
    """Only file/source/model-metadata checks; no live probes or neural imports."""
    for name, expected in (('prepared.json', PARENT_PREPARED), ('prepared-v2.json', PARENT_SUPPLEMENT)):
        require(sha(PARENT/name) == expected, 'Parent manifest drift')
        for pin in read(PARENT/name)['pins']:
            require(sha(pin['path']) == pin['sha256'], 'Parent pin drift: '+pin['path'])
    # Reuse only the exact completed parent's read-only verifier, not its routing layers.
    parent = load(PARENT/'fresh_runtime.py', 'recipe_parent_verifier')
    historical = parent.verify()
    prepared = read(HERE/'prepared.json')
    for pin in prepared['pins']:
        require(sha(pin['path']) == pin['sha256'], 'Recipe pin drift: '+pin['path'])
    recipe = verify_recipe(read(HERE/'recipe.json'))
    require(prepared['scope'] == 'ONE_FRESH_OWNED_GROUP_PILOT' and prepared['payload_sha256'] == recipe['payload_sha256'], 'Preparation mismatch')
    return {'status':'PASS', 'historical_pin_checks':historical['historical_pin_checks'],
            'parent_fresh_pins':historical['fresh_pins'], 'parent_supplement_pins':len(read(PARENT/'prepared-v2.json')['pins']),
            'recipe_pins':len(prepared['pins']), 'payload_sha256':recipe['payload_sha256'],
            'gpu_initialized':False, 'live_probes':False}


def route():
    verify()
    recipe = read(HERE/'recipe.json')
    sys.path.insert(0, str(OLD))
    heartbeat = importlib.import_module('watch_pilot_heartbeat')
    guard = importlib.import_module('guard_runtime_v3')
    guard.HERE, guard.GATE, guard.WORKER = HERE, HERE, HERE/'worker'
    guard.CASES = {'pilot':recipe['payload_sha256']}
    guard.__file__ = str(HERE/'recipe_runtime.py')
    # ORDER is import-time state in the frozen observer: bind the pinned, unchanged
    # topology explicitly; the actual full graph is checked separately at every phase.
    heartbeat.namespace['ORDER'] = [item['node'] for item in read(recipe['execution_order_path'])['execution_order']]
    bound = heartbeat.prior
    source = inspect.getsource(bound.original.captured_interrupt)
    for before, after in (
        ("str(g.HERE/'interrupt-owned-v3.ps1'),", "str(g.HERE/'run_recipe.ps1'),'-Action','interrupt',"),
        ('spawn=asyncio.create_subprocess_exec', 'spawn=clean_spawn'),
    ):
        require(source.count(before) == 1, 'Interrupt route anchor differs')
        source = source.replace(before, after)
    namespace = dict(vars(bound.original), clean_spawn=bound.clean_spawn)
    exec(compile(source, str(HERE/'recipe_runtime.py'), 'exec'), namespace)
    heartbeat.namespace['captured_interrupt'] = namespace['captured_interrupt']
    desktop = load(HERE/'wddm_admission.py', 'recipe_desktop_admission')
    heartbeat.namespace['admit_desktops'] = desktop.make_admit(bound)
    return guard, heartbeat


def install():
    guard, _ = route()
    guard.install()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--verify', action='store_true')
    actions.add_argument('--memory', action='store_true')
    actions.add_argument('--watch', action='store_true')
    parser.add_argument('--case', choices=('pilot',), default='pilot')
    args = parser.parse_args()
    if args.memory:
        sys.path.insert(0, str(OLD))
        from guard_runtime_v3 import memory_snapshot
        print(json.dumps(memory_snapshot()))
    elif args.watch:
        _, observer = route()
        asyncio.run(observer.run_case(args.case))
    else:
        print(json.dumps(verify()))
