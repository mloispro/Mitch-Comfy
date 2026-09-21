"""The sidecar proves only a recorded source/wrapper policy, not execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('registered_eval',
    Path(__file__).with_name('evaluate-upgrade-registered-blend.py'))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WrapperProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.graph={'1':{'class_type':'LoadImage','inputs':{'image':'photo.png'},'is_changed':['abc']},
            '2':{'class_type':'Flux2Klein9BPhotoRealismUpgradeV1','inputs':{
                'source_photo':['1',0],'seed':123,'phone_camera_style':True}}}

    def test_both_observed_versions_pass_without_mutation(self):
        for name in ('Flux2Klein9BPhotoRealismUpgradeV1','Flux2Klein9BPhotoRealismUpgradeV11'):
            self.graph['2']['class_type']=name
            before=copy.deepcopy(self.graph)
            module.validate_intermediate_wrapper(self.graph,'abc',123)
            self.assertEqual(before,self.graph)

    def test_wrong_source_binding_seed_phone_or_class_rejected(self):
        for field,value in (('source_photo',['1',1]),('seed',124),('phone_camera_style',False)):
            altered=copy.deepcopy(self.graph);altered['2']['inputs'][field]=value
            with self.assertRaises(ValueError): module.validate_intermediate_wrapper(altered,'abc',123)
        self.graph['2']['class_type']='UnknownUpgrade'
        with self.assertRaises(ValueError): module.validate_intermediate_wrapper(self.graph,'abc',123)

    def test_hash_extra_nodes_and_malformed_wrapper_rejected(self):
        for graph,sha in ((self.graph,'wrong'),({},'abc'),({**self.graph,'3':{}},'abc')):
            with self.assertRaises(ValueError): module.validate_intermediate_wrapper(graph,sha,123)


if __name__=='__main__': unittest.main()
