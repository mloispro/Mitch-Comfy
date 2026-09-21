import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('portrait_probe',Path(__file__).with_name('run-upgrade-portrait-detail-probe.py'))
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


class PortraitDetailTests(unittest.TestCase):
    def setUp(self):
        self.graph=probe.read(probe.CONTROL)['prompt']

    def test_only_portrait_resolution_and_destination_change(self):
        original=copy.deepcopy(self.graph)
        result=probe.build_probe(self.graph,'upgrade-source-faithful/test/raw')
        self.assertEqual(probe.changed_inputs(original,result),['121.megapixels','27.filename_prefix'])
        self.assertEqual(self.graph,original)
        self.assertEqual(result['121']['inputs']['megapixels'],.1)
        self.assertEqual(result['2']['inputs']['strength_model'],.9)
        self.assertEqual(result['3']['inputs']['strength_model'],.25)

    def test_wrong_reference_chain_is_rejected(self):
        self.graph['124']['inputs']['latent']=['112',0]
        with self.assertRaises(ValueError):
            probe.build_probe(self.graph,'upgrade-source-faithful/test/raw')

    def test_wrong_scale_or_unsafe_destination_is_rejected(self):
        for prefix in ('../escape','upgrade-source-faithful/../escape','C:/escape'):
            with self.assertRaises(ValueError):probe.build_probe(self.graph,prefix)
        self.graph['121']['inputs']['megapixels']=.2
        with self.assertRaises(ValueError):probe.build_probe(self.graph,'upgrade-source-faithful/test/raw')


if __name__=='__main__':unittest.main()
