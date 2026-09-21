"""Strength1.1 Group attribution only; unchanged frozen CPU scoring is explicit opt-in.

No API, worker action, model loading or scoring occurs on import/verification.
The separately reviewed routing pins must exist before any actual verification.
"""
import argparse
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = Path('C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/group-identity-hook-gate/runtime-3090')
PAIR_ROOT = OLD.parent
PREPARATION = HERE / 'EVALUATOR-PREPARED.json'
FRESH_SHA = '6B3A687FB02F8D015D4CA7B1F165FDE48389335D70634AB1003C01E743D94FDE'
OBSERVATION_SHA = '89887BABB81CA100769F1E084B6CAC57B5737682C265B3DFF0B7158770507F38'


def load(path, name, expected):
    import hashlib
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == expected, 'Reviewed source drift: ' + str(path)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(routing=None):
    """Fresh paths and receipt bindings; no execution or score body changes."""
    obs = load(OLD / 'evaluate_pilot_observation.py', 'fresh_frozen_complete_observer_eval', OBSERVATION_SHA)
    e, v3 = obs.e, obs.v3
    assert e.sha(HERE / 'prepared.json') == FRESH_SHA
    fresh = load(HERE / 'recipe_runtime.py', 'fresh_eval_preparation_only',
                 'B27DBC0F37BD5CC9DBA51352348EAE51381607809308E3D1E1DA6B066A7899D6')
    fresh.verify()
    routing = e.read(PREPARATION)['routing'] if routing is None else routing
    e.HERE, e.WORKER, e.NATIVE = HERE, HERE / 'worker', HERE / 'worker/output'
    # Keep every historical mask/schedule/reference/score path on the old gate.
    assert e.GATE == PAIR_ROOT
    e.GRAPH_ROOT = HERE
    e.RECIPE_SCOPE_TEXT = 'One fixed masked character-hook strength1.1 refinement; not the original mask-treatment pair, controlled speed evidence, or production promotion.'
    e.PREPARATION = PREPARATION
    e.CASES = {'pilot': fresh.PILOT_SHA}
    e.GUARD_SHA = 'B27DBC0F37BD5CC9DBA51352348EAE51381607809308E3D1E1DA6B066A7899D6'

    def verify_pins():
        fresh.verify()
        package = e.read(PREPARATION)
        assert package['status'] == 'PREPARED_CPU_ONLY_NO_SCORING_OR_QUEUE'
        assert package['routing'] == routing and package['fresh_prepared_sha256'] == FRESH_SHA
        pins = list(package['pins'])
        # Historical evaluator prerequisites remain mandatory, not just runtime pins.
        for name in ('HOOK-EVALUATOR-PREPARED.json', 'HOOK-EVALUATOR-V3-PREPARED.json'):
            pins += e.read(OLD / name)['pins']
        for pin in pins:
            assert e.sha(pin['path']) == pin['sha256'], 'Evaluator prerequisite drift: ' + pin['path']
        for key in ('watcher', 'wddm_helper', 'runtime_supplement'):
            pin = routing[key]
            assert e.sha(pin['path']) == pin['sha256'], 'Reviewed runtime routing drift: ' + key
        supplement = e.read(routing['runtime_supplement']['path'])
        for pin in supplement['pins']:
            assert e.sha(pin['path']) == pin['sha256']
        for key in ('watcher', 'wddm_helper'):
            assert any(Path(p['path']).resolve() == Path(routing[key]['path']).resolve()
                       and p['sha256'] == routing[key]['sha256'] for p in supplement['pins'])
        return {'status': package['status'], 'pins': pins}

    e.verify_pins = verify_pins

    def primitives():
        # Definitions only: never call install(), capture(), or live admission.
        g = e.load_source(OLD / 'guard_runtime_v3.py', v3.GUARD_V3_SHA, 'fresh_eval_native_definitions')
        g.HERE, g.GATE, g.WORKER = HERE, HERE, e.WORKER
        g.CASES, g.__file__ = e.CASES, str(HERE / 'recipe_runtime.py')
        assert e.sha(OLD / 'native_sampler_registration.py') == v3.REGISTRATION_SHA
        assert e.sha(OLD / 'watch_case.py') == e.WATCH_SHA
        assert e.sha(e.GATE / 'PAIR-SCHEDULE-RESULTS.json') == e.SCHEDULE_SHA
        order = [row['node'] for row in e.read(e.GATE / 'PAIR-SCHEDULE-RESULTS.json')['execution_order']]
        assert len(order) == len(set(order)) == 36
        tree = ast.parse((OLD / 'watch_case.py').read_text(encoding='utf-8-sig'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'accept_event')
        namespace = {'g': g, 'ORDER': order}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<unchanged-36-node-event-check>', 'exec'), namespace)
        return g, order, namespace['accept_event']

    e.primitives = primitives
    # Exactly two graph-path expressions, not a blanket historical-GATE move.
    # The entire original function declarations are retained; scoring is external.
    base_source = v3.OLD.read_text(encoding='utf-8-sig')
    assert e.sha(v3.OLD) == v3.OLD_SHA
    graph_deltas = []
    for name, before, after in (
        ('validate_actual', "payload = GATE / ('amber-hook-' + case + '-payload.json')",
         "payload = GRAPH_ROOT / ('amber-hook-' + case + '-payload.json')"),
        ('load_evaluator', "a.p.pin(GATE / ('amber-hook-' + case + '-payload.json'))",
         "a.p.pin(GRAPH_ROOT / ('amber-hook-' + case + '-payload.json'))")):
        node = next(n for n in ast.parse(base_source).body if isinstance(n, ast.FunctionDef) and n.name == name)
        original = ast.get_source_segment(base_source, node)
        assert original.count(before) == 1 and after not in original
        adapted = original.replace(before, after)
        scope_before = "'One ' + case + ' of the frozen native hook mask-treatment pair; not an old Amber resolution/runtime comparison or production promotion.'"
        if name == 'load_evaluator':
            assert adapted.count(scope_before) == 1
            adapted = adapted.replace(scope_before, 'RECIPE_SCOPE_TEXT')
        restored = adapted.replace('RECIPE_SCOPE_TEXT', scope_before) if name == 'load_evaluator' else adapted
        assert restored.replace(after, before) == original
        exec(compile(adapted, '<recipe-actual-graph-path-only:' + name + '>', 'exec'), e.__dict__)
        graph_deltas.append((original, adapted, before, after))
    v3.original_validate_actual = e.validate_actual
    e.RECIPE_GRAPH_DELTAS = graph_deltas
    e.RECIPE_METADATA_DELTA = (scope_before, 'RECIPE_SCOPE_TEXT')
    watcher = Path(routing['watcher']['path'])
    assert watcher.parent.resolve() == HERE and watcher.name == 'recipe_runtime.py'
    old = "str(HERE / 'watch_pilot_observation.py'), '--case', case"
    new = "str(HERE / 'recipe_runtime.py'), '--watch', '--case', case"
    assert obs.watch_source.count(old) == 2
    source = obs.watch_source.replace(old, new)
    assert source.replace(new, old) == obs.watch_source
    namespace = dict(e.__dict__, check_watcher_lifetime=obs.check_watcher_lifetime)
    exec(compile(source, '<fresh-watcher-argv-only>', 'exec'), namespace)
    v3.original_guard_watch = namespace['check_guard_watch']
    # v3.check_guard_watch still checks the complete native registration proof.
    e.check_guard_watch = v3.check_guard_watch

    def validate_actual(case, prompt, image_sha, receipt, helper):
        assert case == 'pilot'
        verify_pins()
        result = v3.original_validate_actual(case, prompt, image_sha, receipt, helper)
        run = HERE / 'runs/ready-amber-hook-pilot'
        paths = [run / name for name in ('prior-terminal-cases.json', 'prior-terminal-cases-final.json')]
        for path in paths:
            check_empty_history(e.read(path))
        owned_path, approval_path = HERE / 'worker/owned.json', HERE / 'root-approval.json'
        owned, approval = e.read(owned_path), e.read(approval_path)
        assert e.sha(owned_path) == e.sha(run / 'worker-owned.json'), 'Copied worker ownership differs'
        history = e.read(run / 'history.json')
        start = next(data['timestamp'] for kind, data in history['status']['messages'] if kind == 'execution_start')
        check_root_approval(approval, e.read(HERE / 'prepared.json'), e.sha(owned_path),
                            e.timestamp(owned['created_utc']), start, e.timestamp,
                            routing['runtime_supplement']['sha256'])
        helper_pin = routing['wddm_helper']
        sys.path.insert(0, str(OLD))
        wddm = e.load_source(Path(helper_pin['path']), helper_pin['sha256'], 'fresh_reviewed_wddm_definitions')
        saved_path, observations_path = run / 'wddm-approval.json', run / 'wddm-observations.jsonl'
        saved = e.read(saved_path)
        check_watch_route(saved, routing)
        candidate_path, desktop_approval_path = HERE / 'wddm-candidate-v2.json', HERE / 'wddm-root-approval-v2.json'
        assert e.sha(candidate_path) == saved['candidate_sha256']
        assert e.sha(desktop_approval_path) == saved['approval_sha256']
        assert e.read(candidate_path) == saved['candidate'] and e.read(desktop_approval_path) == saved['approval']
        assert saved['approval']['candidate_sha256'] == saved['candidate_sha256']
        observations = [json.loads(line) for line in observations_path.read_text(encoding='utf-8-sig').splitlines()]
        samples = [json.loads(line) for line in (run / 'watch-samples.jsonl').read_text(encoding='utf-8-sig').splitlines()]
        terminal = e.timestamp(e.read(run / 'watch-terminal.json')['utc'])
        v3.validate_wddm_records(saved, observations, samples, terminal, wddm)
        masks = v3.staged_mask_pins()
        assert v3.staged_mask_pins() == masks
        paths += [owned_path, approval_path, saved_path, observations_path, candidate_path, desktop_approval_path,
                  Path(__file__).resolve(), PREPARATION, Path(routing['runtime_supplement']['path'])]
        result['run_pins'] += masks + [{'path': str(path), 'sha256': e.sha(path)} for path in paths]
        result.update(fresh_worker_first_prompt=True, pilot_observation_complete=True,
                      independent_resource_monitor=True, maximum_resource_sample_gap_seconds=5,
                      reviewed_runtime_routing=copy.deepcopy(routing),
                      baseline_memory_receipt_available='group_memory' in owned['baseline'],
                      startup_memory_receipt_available='group_memory' in owned['startup_snapshot'])
        result.update(recipe_sha256=approval['recipe_sha256'],
                      parent_prepared_sha256=approval['parent_prepared_sha256'],
                      parent_image_sha256=approval['parent_image_sha256'],
                      recipe_scope=e.RECIPE_SCOPE_TEXT)
        return result

    e.validate_actual = validate_actual
    return e, obs


def check_empty_history(value):
    assert value == {'records': [], 'latest': None}, 'Fresh worker has nonempty/unknown prior history'


def check_watch_route(saved, routing):
    assert Path(saved['wddm_helper_path']).resolve() == Path(routing['wddm_helper']['path']).resolve()
    assert saved['wddm_helper_sha256'] == routing['wddm_helper']['sha256']
    assert saved['supplement_prepared_sha256'] == routing['runtime_supplement']['sha256']


def check_root_approval(approval, prepared, owned_sha, created, start, timestamp, supplement_sha):
    assert approval['approved'] is True and approval['scope'] == 'ONE_FRESH_OWNED_GROUP_PILOT'
    assert approval['prepared_sha256'] == FRESH_SHA
    assert approval['supplement_prepared_sha256'] == supplement_sha
    assert Path(approval['worker_root']).resolve() == (HERE / 'worker').resolve()
    assert approval['worker_owned_sha256'] == owned_sha
    # This recipe keeps these declared values in its runtime-pinned template,
    # not duplicated as top-level fields of the runtime manifest.
    expected = json.loads((HERE / 'ROOT-APPROVAL-TEMPLATE.json').read_text(encoding='utf-8-sig'))
    assert expected['approved'] is False
    assert expected['payload_sha256'] == prepared['payload_sha256']
    assert expected['parent_prepared_sha256'] == prepared['parent_prepared_sha256']
    for field in ('payload_sha256', 'prior_stop_sha256', 'interrupted_archive_sha256', 'control_image_sha256',
                  'recipe_sha256', 'parent_prepared_sha256', 'parent_image_sha256'):
        assert approval[field] == expected[field]
    assert timestamp(approval['issued_utc']) <= created <= start <= timestamp(approval['expires_utc'])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-id', required=True)
    parser.add_argument('--image-sha', required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify', action='store_true')
    mode.add_argument('--score', action='store_true')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    e, _ = configure()
    if args.score:
        e.load_evaluator('pilot')['evaluate'](args.prompt_id, args.image_sha)
    else:
        print(json.dumps({'status': 'RECIPE_ATTRIBUTION_AND_COMPLETE_WATCH_VERIFIED_NO_SCORING_OR_WRITES',
                          **e.verify_actual_only('pilot', args.prompt_id, args.image_sha)}, indent=2))


if __name__ == '__main__':
    main()
