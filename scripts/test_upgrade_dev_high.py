import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from upgrade_dev_high import PINS, PROMPT, build_graph, validate_graph


class DevHighGraphTests(unittest.TestCase):
    def setUp(self):
        self.refs = [{'name':'raw.png [output]'}, {'name':'original.png [input]'}]
        self.manifest = {'stage':'dev_native_high_edit', 'postprocess':False, 'turbo':False,
                         'phone_camera_style':False, 'upstream_phone_camera_style':True,
                         'phone_appearance_mode':'inherited_klein_raw_not_active_dev_adapter',
                         'effective_prompt':PROMPT, 'references':self.refs, 'seed':8675416, 'identity_strength':1.1,
                         'output_prefix':'test/raw', 'verified_models':[
                             {'model_relative_path':p,'sha256':h} for p,h in PINS.items()]}
        self.manifest['prompt'] = build_graph(self.refs,8675416,'test/raw')

    def test_author_native_path_and_reference_order(self):
        validate_graph(self.manifest)
        g = self.manifest['prompt']
        self.assertEqual(g['21']['class_type'],'BasicGuider')
        self.assertEqual(g['113']['inputs'],{'conditioning':['103',0],'latent':['112',0]})
        self.assertEqual(g['24']['inputs']['width'],['40',0])
        self.assertEqual(g['40']['inputs']['image'],['101',0])
        self.assertEqual(g['26']['inputs']['samples'],['25',0])

    def test_wrong_models_noise_guidance_reference_are_rejected(self):
        for node,field,value in [('2','lora_name','klein-identity.safetensors'),
                                 ('4','clip_name','qwen_3_8b_fp8mixed.safetensors'),
                                 ('7','guidance',1),('25','latent_image',['102',0]),
                                 ('113','conditioning',['7',0]),('23','steps',8)]:
            with self.subTest(node=node,field=field):
                bad = copy.deepcopy(self.manifest)
                bad['prompt'][node]['inputs'][field] = value
                with self.assertRaises(ValueError): validate_graph(bad)

    def test_false_phone_and_turbo_claims_rejected(self):
        for field in ('phone_camera_style','turbo','postprocess'):
            bad = copy.deepcopy(self.manifest); bad[field] = True
            with self.assertRaises(ValueError): validate_graph(bad)
        bad = copy.deepcopy(self.manifest); bad['upstream_phone_camera_style'] = False
        with self.assertRaises(ValueError): validate_graph(bad)

    def test_no_unbounded_strength_or_extra_references(self):
        with self.assertRaises(ValueError): build_graph(self.refs,1,'test',.9)
        with self.assertRaises(ValueError): build_graph(self.refs[:1],1,'test')

    def test_sole_refinement_changes_only_identity_weight(self):
        refined = copy.deepcopy(self.manifest)
        refined['identity_strength'] = .8
        refined['prompt'] = build_graph(self.refs,8675416,'test/raw',.8)
        validate_graph(refined)
        self.assertEqual([k for k in refined['prompt'] if refined['prompt'][k] != self.manifest['prompt'][k]],['2'])


class DevWorkerGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('dev_high_runner',Path(__file__).with_name('run-upgrade-dev-high.py'))
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def fake_api(self, port, route):
        if route == 'system_stats':
            return {'devices':[{'name':'RTX 3090' if port == 8188 else 'RTX 4070'}]}
        if route == 'queue': return {'queue_running':[], 'queue_pending':[]}
        if route == 'history?max_items=1':
            return {'owned':{'status':{'completed':True,'status_str':'success'},'prompt':[None,None,{}]}}
        raise AssertionError('Unexpected request; tests must never submit a job.')

    def fake_read(self, path):
        return {'prompt_id':'owned'} if path.name == 'submission.json' else {'prompt':{}}

    def test_idle_owned_cache_is_read_only(self):
        with patch.object(self.runner,'api',side_effect=self.fake_api), patch.object(self.runner,'read_json',side_effect=self.fake_read), patch.object(self.runner.subprocess,'check_output',return_value='0, NVIDIA GeForce RTX 3090, 13559, 0\n1, NVIDIA GeForce RTX 4070, 8000, 40\n'):
            result = self.runner.idle_snapshot(Path('previous'))
        self.assertFalse(result['explicit_free'])
        self.assertFalse(result['worker_restart'])

    def test_busy_target_and_unowned_cache_rejected(self):
        def busy(port,route):
            if port == 8188 and route == 'queue': return {'queue_running':[['unrelated']], 'queue_pending':[]}
            return self.fake_api(port,route)
        with patch.object(self.runner,'api',side_effect=busy):
            with self.assertRaisesRegex(RuntimeError,'active3090'):
                self.runner.idle_snapshot(Path('previous'))
        def other(port,route):
            if route.startswith('history'): return {'other':{'status':{'completed':True,'status_str':'success'}}}
            return self.fake_api(port,route)
        with patch.object(self.runner,'api',side_effect=other), patch.object(self.runner,'read_json',side_effect=self.fake_read), patch.object(self.runner.subprocess,'check_output',return_value='0, NVIDIA GeForce RTX 3090, 13559, 0\n'):
            with self.assertRaisesRegex(RuntimeError,'owned terminal'):
                self.runner.idle_snapshot(Path('previous'))


if __name__ == '__main__': unittest.main()
