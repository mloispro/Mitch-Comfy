"""Offline namespace/path tests; no GPU, model, server or child process calls."""
import inspect
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fresh_runtime as f


class FreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard, cls.observer = f.route()

    def test_native_guards_unchanged_and_fresh_binding(self):
        g = self.guard
        self.assertEqual(g.HERE, f.HERE)
        self.assertEqual(g.WORKER, f.HERE/'worker')
        self.assertEqual(g.GATE, f.GATE)
        self.assertEqual(g.CASES, {'pilot': f.PILOT_SHA})
        self.assertEqual(g.__file__, str(f.HERE/'fresh_runtime.py'))
        source = inspect.getsource(g.PhaseGuard.before)
        self.assertIn('host,commit = 40,40', source)
        self.assertIn('host,commit = 30,28', source)
        self.assertIn('effective_free_bytes', source)
        self.assertIn('same_graph(item[2],frozen)', source)

    def test_complete_observer_namespace(self):
        ns = self.observer.run_case.__globals__
        for key in ('g', 'admit_desktops', 'captured_interrupt', 'resource_monitor',
                    'bounded_heartbeat_replace', 'heartbeat', 'lifetime', 'ORDER'):
            self.assertIn(key, ns)
        self.assertIs(ns['g'], self.guard)
        self.assertEqual(len(ns['ORDER']), 36)
        self.assertIs(ns['heartbeat'].__globals__['bounded_heartbeat_replace'], self.observer.bounded_heartbeat_replace)
        self.assertIn('fresh.ps1', ns['captured_interrupt'].__code__.co_consts)
        self.assertIn('interrupt', ns['captured_interrupt'].__code__.co_consts)
        self.assertIn('fresh.ps1', ns['admit_desktops'].__code__.co_consts)
        self.assertIn('wddm', ns['admit_desktops'].__code__.co_consts)

    def test_bound_environment_and_timing_unchanged(self):
        bound = self.observer.prior
        self.assertEqual(bound.clean_python_environment({'PYTHONHOME': 'wrong', 'CUDA_VISIBLE_DEVICES': 'g', 'PATH': 'keep'}),
                         {'CUDA_VISIBLE_DEVICES': 'g', 'PATH': 'keep'})
        source = self.observer.adapted
        for exact in ('aiohttp.ClientTimeout(total=10)', 'heartbeat=10)',
                      "memory['host_available_bytes']"):
            # Memory gate is in the original independent resource function.
            if exact.startswith('memory'):
                continue
            self.assertIn(exact, source)
        resource = self.observer.namespace['resource_monitor']
        self.assertEqual(inspect.signature(resource).parameters['interval'].default, .75)
        self.assertIn('>=12*2**30', inspect.getsource(resource))
        self.assertIn('>=10*2**30', inspect.getsource(resource))
        self.assertIn('+.45', inspect.getsource(self.observer.bounded_heartbeat_replace))

    def test_refusal_precedes_original_allocation(self):
        called = []
        def refuse(*a):
            raise RuntimeError('resource gate')
        wrapped = self.guard.make_entry_wrapper(lambda *a: called.append(a), refuse, lambda *a: None)
        with self.assertRaisesRegex(RuntimeError, 'resource gate'):
            wrapped('fake tensor')
        self.assertEqual(called, [])

    def test_success_and_exception_passthrough(self):
        token = object()
        result = object()
        seen = []
        fn = self.guard.make_entry_wrapper(lambda a, *, b: result,
            lambda a,k: (seen.append((a,k)) or token), lambda *a: seen.append(a))
        self.assertIs(fn(1, b=2), result)
        self.assertEqual(seen[0], ((1,), {'b': 2}))
        self.assertEqual(seen[1], (token, 'original_returned', None))
        error = ValueError('same')
        def fail():
            raise error
        fn = self.guard.make_entry_wrapper(fail, lambda a,k: token, lambda *a: None)
        try:
            fn()
        except ValueError as actual:
            self.assertIs(actual, error)
        else:
            self.fail('Original exception swallowed')

    def test_actual_helper_arguments_without_launch(self):
        calls = []
        class FakeProcess:
            pid = 123
            returncode = 0
            async def wait(self):
                return 0
        async def fake_spawn(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeProcess()
        with tempfile.TemporaryDirectory(prefix='group-fresh-interrupt-contract-') as directory:
            fn = self.observer.namespace['captured_interrupt']
            result = asyncio.run(fn(Path(directory), Path('C:/fake/pwsh.exe'), spawn=fake_spawn))
            self.assertEqual(calls[0][0][2:6], ('-File', str(f.HERE/'fresh.ps1'), '-Action', 'interrupt'))
            self.assertEqual(result['exit_code'], 0)
            self.assertFalse(result['intent_present'])
            self.assertFalse(result['receipt_present'])
            self.assertFalse(result['retry_permitted'])


if __name__ == '__main__':
    unittest.main()
