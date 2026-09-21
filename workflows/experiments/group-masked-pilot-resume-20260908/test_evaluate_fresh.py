"""CPU-only synthetic receipts. No API, GPU, actual image scoring, or file writes."""
import ast
import copy
from datetime import timedelta
import sys
import unittest
from unittest.mock import patch
import evaluate_fresh as f

ROUTING = {'watcher': {'path': str(f.HERE / 'fresh_runtime_v2.py'), 'sha256': 'A' * 64},
           'wddm_helper': {'path': str(f.HERE / 'wddm_admission_v2.py'), 'sha256': 'B' * 64},
           'runtime_supplement': {'path': str(f.HERE / 'fixture-only-not-an-approval.json'), 'sha256': 'C' * 64}}
e, obs = f.configure(ROUTING)
old_test = f.OLD / 'test_evaluate_hook_pair.py'
assert e.sha(old_test) == '715231D14473345F68FA550A5E45B2824E1ACC97097C615F930657D50F6C8254'
source = old_test.read_text(encoding='utf-8-sig')
assert source.count('import evaluate_hook_pair as e') == 1
namespace = {'__name__': 'fresh_synthetic_original_fixture', '__file__': str(old_test), 'ADAPTED': e}
exec(compile(source.replace('import evaluate_hook_pair as e', 'e = ADAPTED'), str(old_test), 'exec'), namespace)


def fixture():
    rows, graph, events, samples, ready = namespace['fixture']('pilot')
    launch, wr = rows['watch-launched.json'], rows['watch-ready.json']
    launch.update(launch_pid=301, executable=str(e.CORE / '.venv/Scripts/python.exe'))
    launch['argv'] = ['-X', 'utf8', '-B', str(f.HERE / 'fresh_runtime_v2.py'), '--watch', '--case', 'pilot']
    wr.update(parent_pid=301, process_start_utc=namespace['stamp'](6.2))
    wr['argv'] = [str(f.HERE / 'fresh_runtime_v2.py'), '--watch', '--case', 'pilot']
    native = (e.CORE / 'comfy_extras/nodes_custom_sampler.py').resolve()
    ready['native_registration_proof'] = {
        'selection': 'actual NODE_CLASS_MAPPINGS object; no dotted import',
        'registered_module_key': str(native.with_suffix('')), 'source_path': str(native),
        'source_sha256': ready['sources']['comfy_extras/nodes_custom_sampler.py'],
        'native_class_identity': True, 'execute_and_schema_code_equal_to_compiled_source': True,
        'sample_alias_unchanged': True}
    for key in ('baseline', 'startup_snapshot'):
        rows['worker-owned.json'][key].pop('group_memory')
    samples = [{'utc': namespace['stamp'](t), 'prompt_id': namespace['PROMPT'] if t >= 10 else None,
                'nodes_seen': i * 7, 'memory': namespace['mem'](t, 20, 20)}
               for i, t in enumerate((6.25, 10, 13, 16, 19, 20.5))]
    return rows, graph, events, samples, ready


def check(value):
    rows, graph, events, samples, ready = value
    return e.validate_records(rows, 'pilot', namespace['PROMPT'], namespace['PHOTO'], graph, events, samples, ready)


class Tests(unittest.TestCase):
    def test_complete_actual_namespace_new_paths_and_unchanged_native_guard(self):
        value = fixture()
        result = check(value)
        self.assertEqual(result['worker_seconds'], 10)
        self.assertEqual(result['image'].parent, f.HERE / 'runs/ready-amber-hook-pilot')
        self.assertTrue(result['source'].is_relative_to(f.HERE / 'worker/output'))
        self.assertEqual(value[4]['guard_sha256'], e.sha(f.HERE / 'fresh_runtime.py'))
        self.assertIn(str(f.HERE / 'extra-paths-v3.yaml'), e.argv(8191))

    def test_graph_owner_native_watch_memory_fail_closed(self):
        mutations = [
            lambda v: v[0]['history.json']['prompt'][2]['34']['inputs'].update(width=1248),
            lambda v: v[0]['history.json']['prompt'][2]['4']['inputs'].update(strength_model=True),
            lambda v: v[0]['history.json']['status']['messages'][1][1].update(nodes=['1']),
            lambda v: v[0]['attempt.json'].update(client_id='foreign'),
            lambda v: v[0]['worker-owned.json']['owner'].update(pid=999),
            lambda v: v[0]['watch-ready.json'].update(parent_pid=999),
            lambda v: v[0]['watch-ready.json']['argv'].remove('--watch'),
            lambda v: v[0]['watch-terminal.json'].update(status='watch_refused'),
            lambda v: v[0]['final-preflight.json'].pop('group_memory'),
            lambda v: v[0]['final-preflight.json']['group_memory'].update(host_available_bytes=41 * 2**30 - 1),
            lambda v: v[0].pop('guard-35-return.json'),
            lambda v: v[0]['guard-1-entry.json']['memory'].update(commit_headroom_bytes=40 * 2**30 - 1),
            lambda v: v[0]['guard-35-entry.json']['memory'].update(host_available_bytes=30 * 2**30 - 1),
            lambda v: v[4].update(guard_sha256='B' * 64),
            lambda v: v[4]['native_registration_proof'].update(native_class_identity=False),
            lambda v: v[2].pop(10),
            lambda v: v[3].pop(1),
            lambda v: v[3][2]['memory'].update(host_available_bytes=12 * 2**30 - 1),
            lambda v: v[3][2]['memory'].update(commit_headroom_bytes=10 * 2**30 - 1),
            lambda v: v[0]['report.json']['files'][0].update(native_source='C:/wrong/photo.png'),
        ]
        for i, change in enumerate(mutations):
            value = fixture(); change(value)
            with self.subTest(i=i), self.assertRaises((AssertionError, KeyError, RuntimeError, ValueError)):
                check(value)

    def test_fresh_approval_historical_time_binding(self):
        prepared = e.read(f.HERE / 'prepared.json')
        approval = {key: prepared[key] for key in ('payload_sha256', 'prior_stop_sha256', 'interrupted_archive_sha256', 'control_image_sha256')}
        approval.update(approved=True, scope='ONE_FRESH_OWNED_GROUP_PILOT', prepared_sha256=f.FRESH_SHA,
                        worker_root=str(f.HERE / 'worker'), worker_owned_sha256='D' * 64,
                        supplement_prepared_sha256='C' * 64,
                        issued_utc=namespace['stamp'](0), expires_utc=namespace['stamp'](30))
        call = lambda row: f.check_root_approval(row, prepared, 'D' * 64,
            e.timestamp(namespace['stamp'](1.5)), e.timestamp(namespace['stamp'](10)), e.timestamp, 'C' * 64)
        call(approval)
        for key, bad in [('approved', False), ('scope', 'OLD_RECOVERY'), ('prepared_sha256', 'E' * 64),
                         ('worker_owned_sha256', 'E' * 64), ('control_image_sha256', 'E' * 64),
                         ('supplement_prepared_sha256', 'E' * 64),
                         ('issued_utc', namespace['stamp'](2)), ('expires_utc', namespace['stamp'](9))]:
            changed = copy.deepcopy(approval); changed[key] = bad
            with self.subTest(key=key), self.assertRaises(AssertionError): call(changed)

    def test_prior_history_cannot_adopt_control_or_interrupted_worker(self):
        f.check_empty_history({'records': [], 'latest': None})
        for value in ({'records': [{}], 'latest': None}, {'records': [], 'latest': {}},
                      {'records': [], 'latest': None, 'ignored_history': True}, {}):
            with self.subTest(value=value), self.assertRaises(AssertionError): f.check_empty_history(value)

    def test_actual_watch_helper_and_supplement_must_match_reviewed_routing(self):
        saved = {'wddm_helper_path': ROUTING['wddm_helper']['path'],
                 'wddm_helper_sha256': 'B' * 64, 'supplement_prepared_sha256': 'C' * 64}
        f.check_watch_route(saved, ROUTING)
        for key, value in [('wddm_helper_path', 'C:/wrong/helper.py'),
                           ('wddm_helper_sha256', 'E' * 64), ('supplement_prepared_sha256', 'E' * 64)]:
            changed = dict(saved); changed[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): f.check_watch_route(changed, ROUTING)

    def test_exact_new_wddm_lifetimes_no_approval_or_time_bypass(self):
        helper_path = f.HERE / 'wddm_admission_v2.py'
        w = f.load(helper_path, 'fresh_eval_fixture_reviewed_wddm', e.sha(helper_path))
        base, evidence = w.data()
        stamp = max(w.instant(base['captured_utc']), w.instant(evidence['checked_utc'])) if 'checked_utc' in evidence else w.instant(base['captured_utc'])
        candidate = {'approved': False, 'scope': 'GROUP_FRESH_V2_DESKTOP_CANDIDATE',
                     'captured_utc': stamp.isoformat(), 'parent_evidence_sha256': w.EVIDENCE_SHA,
                     'prior_candidate_sha256': w.BASE_CANDIDATE_SHA, 'wddm_helper_sha256': e.sha(helper_path),
                     'processes': copy.deepcopy(base['processes']),
                     'parents': [copy.deepcopy(r) for r in evidence['processes'] if r['pid'] in w.PARENT_IDS]}
        for row in evidence['processes']:
            if row['pid'] in w.NEW_IDS:
                candidate['processes'].append(dict(copy.deepcopy(row), matches_prior_lifetime=False, review_basis='explicit_new_lifetime'))
        approval = {'approved': True, 'scope': w.SCOPE,
                    'issued_utc': (stamp + timedelta(seconds=1)).isoformat(),
                    'expires_utc': (stamp + timedelta(minutes=30)).isoformat(),
                    'parent_evidence_sha256': w.EVIDENCE_SHA, 'prior_candidate_sha256': w.BASE_CANDIDATE_SHA,
                    'wddm_helper_sha256': e.sha(helper_path), 'supplement_prepared_sha256': 'C' * 64,
                    'reviewed_processes': copy.deepcopy(candidate['processes']), 'reviewed_parents': copy.deepcopy(candidate['parents'])}
        for row in approval['reviewed_processes'] + approval['reviewed_parents']:
            if row['pid'] in w.NEW_IDS: row['new_lifetime_approved'] = True
            if row['executable_path'] is None or row['argv'] is None: row['protected_metadata_approved'] = True
        real_sha = w.g.sha
        with patch.object(w.g, 'sha', side_effect=lambda p: 'C' * 64 if str(p).endswith('prepared-v2.json') else real_sha(p)):
            approved = w.validate_approval(approval, candidate, stamp + timedelta(seconds=2))
            self.assertEqual(len(approved), 22)
            saved = {'approval': approval, 'candidate': candidate, 'first_checked_utc': (stamp + timedelta(seconds=2)).isoformat()}
            observations = [{'utc': (stamp + timedelta(seconds=3)).isoformat(), 'captured_utc': (stamp + timedelta(seconds=2)).isoformat(),
                             'accepted_desktop_pids': sorted(w.NEW_IDS), 'exact_lifetimes_verified': True}]
            obs.v3.validate_wddm_records(saved, observations, [{}, {}], e.timestamp((stamp + timedelta(seconds=4)).isoformat()), w)
            changes = [lambda a: a['reviewed_processes'][-1].update(new_lifetime_approved=False),
                       lambda a: a['reviewed_processes'][-1].update(creation_utc=(stamp - timedelta(days=1)).isoformat()),
                       lambda a: a['reviewed_processes'].pop(),
                       lambda a: a.update(expires_utc=(stamp + timedelta(seconds=1)).isoformat()),
                       lambda a: a.update(supplement_prepared_sha256='E' * 64)]
            for i, change in enumerate(changes):
                changed = copy.deepcopy(approval); change(changed)
                with self.subTest(i=i), self.assertRaises((RuntimeError, AssertionError)):
                    w.validate_approval(changed, candidate, stamp + timedelta(seconds=2))
            with self.assertRaises((RuntimeError, AssertionError)):
                w.allowed_current([999999], [], approved, candidate['processes'])

    def test_original_scoring_bytecode_six_references_and_no_overwrite(self):
        with patch.object(e, 'verify_pins', return_value={'pins': []}):
            ns = e.load_evaluator('pilot')
            old = e.load_amber().load_routed_evaluator()
            self.assertEqual(ns['evaluate'].__code__.co_code, old['evaluate'].__code__.co_code)
            self.assertEqual(ns['evaluate'].__code__.co_consts, old['evaluate'].__code__.co_consts)
            self.assertEqual(ast.dump(ns['v2'].score_ast()), ast.dump(old['v2'].score_ast()))
            receipt, _ = ns['v2'].verify(live=False)
            self.assertEqual(len(receipt['genuine_references']), 6)
            self.assertEqual(receipt['acceptance']['main_minimum'], .55)
            self.assertEqual(receipt['acceptance']['bystander_limits_exclusive'], [.42, .50, .72])
            self.assertEqual(ns['load_helpers']().TARGET, (.51, .45))
            self.assertEqual(ns['OUT'], f.HERE / 'evaluation-pilot')
            ns['OUT'] = f.HERE
            with self.assertRaisesRegex(AssertionError, 'Never overwrite'):
                ns['evaluate'](namespace['PROMPT'], namespace['PHOTO'])

    def test_cli_default_verify_and_no_neural_imports(self):
        args = ['--prompt-id', namespace['PROMPT'], '--image-sha', namespace['PHOTO']]
        self.assertFalse(f.parse_args(args).score)
        self.assertTrue(f.parse_args(args + ['--score']).score)
        for name in ('torch', 'onnxruntime', 'insightface'):
            self.assertNotIn(name, sys.modules)


if __name__ == '__main__': unittest.main()
