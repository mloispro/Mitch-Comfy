import unittest
from upgrade_seed_probe import build_probe,build_dtype_probe,changed_inputs,validate_house_report_hash,HOUSE_REPORT_SHA,precision_runtime_preflight


class SeedProbeTests(unittest.TestCase):
    def setUp(self):
        self.graph = {
            '1': {'class_type':'UNETLoader','inputs':{'unet_name':'model.safetensors','weight_dtype':'fp8_e4m3fn'}},
            '20': {'class_type':'RandomNoise','inputs':{'noise_seed':8675416}},
            '27': {'class_type':'SaveImage','inputs':{'filename_prefix':'old','images':['26',0]}},
            '6': {'class_type':'CLIPTextEncode','inputs':{'text':'unchanged','clip':['4',0]}},
        }

    def test_only_next_seed_and_prefix_change(self):
        result = build_probe(self.graph, 'upgrade-source-faithful/probe/raw')
        self.assertEqual(result['20']['inputs']['noise_seed'],8675417)
        self.assertEqual(self.graph['20']['inputs']['noise_seed'],8675416)
        self.assertEqual(changed_inputs(self.graph,result),['20.noise_seed','27.filename_prefix'])

    def test_extra_prompt_change_detected(self):
        result = build_probe(self.graph, 'upgrade-source-faithful/probe/raw')
        result['6']['inputs']['text']='changed'
        self.assertIn('6.text',changed_inputs(self.graph,result))

    def test_node_shape_change_rejected(self):
        result = build_probe(self.graph, 'upgrade-source-faithful/probe/raw')
        result['6']['inputs']['extra']=1
        with self.assertRaises(ValueError):changed_inputs(self.graph,result)

    def test_invalid_seed_or_prefix_rejected(self):
        for prefix in ('../outside','upgrade-source-faithful/../outside','C:/outside'):
            with self.assertRaises(ValueError):build_probe(self.graph,prefix)
        self.graph['20']['inputs']['noise_seed']=2**64-1
        with self.assertRaises(ValueError):build_probe(self.graph,'upgrade-source-faithful/probe/raw')

    def test_legacy_report_pin_and_contradictory_metadata(self):
        self.assertEqual(validate_house_report_hash({},HOUSE_REPORT_SHA),HOUSE_REPORT_SHA)
        with self.assertRaises(ValueError):validate_house_report_hash({},'0'*64)
        with self.assertRaises(ValueError):validate_house_report_hash({'baseline_report_sha256':'0'*64},HOUSE_REPORT_SHA)

    def test_dtype_probe_keeps_seed_and_prompt(self):
        result=build_dtype_probe(self.graph,'upgrade-source-faithful/dtype/raw')
        self.assertEqual(changed_inputs(self.graph,result),['1.weight_dtype','27.filename_prefix'])
        self.assertEqual(result['20'],self.graph['20'])
        self.assertEqual(result['6'],self.graph['6'])
        self.assertEqual(self.graph['1']['inputs']['weight_dtype'],'fp8_e4m3fn')
        with self.assertRaises(ValueError):build_dtype_probe(result,'upgrade-source-faithful/retry/raw')

    def test_precision_requires_ram_and_no_dtype_override(self):
        stats={'system':{'argv':[],'ram_free':30*1024**3},'devices':[{'name':'RTX 3090'}]}
        self.assertTrue(precision_runtime_preflight(stats)['process_dtype_override_absent'])
        stats['system']['ram_free']=7*1024**3
        with self.assertRaises(ValueError):precision_runtime_preflight(stats)
        stats['system']['ram_free']=30*1024**3
        stats['system']['argv']=['--fp8_e4m3fn-unet']
        with self.assertRaises(ValueError):precision_runtime_preflight(stats)


if __name__=='__main__':unittest.main()
