import copy
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('prompt_check',Path(__file__).with_name('verify-upgrade-prompt-only-change.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PromptOnlyTests(unittest.TestCase):
    def setUp(self):
        self.old={'reference_mode':'four','identity_strength':.9,'seed':10,'steps':50,'cfg':4,'turbo':False,
            'references':[{'sha256':'abc'}],'verified_models':[{'sha256':'def'}],
            'prompt':{'3':{'class_type':'LoraLoaderModelOnly','inputs':{'strength_model':.25}},
                      '6':{'class_type':'CLIPTextEncode','inputs':{'text':'old'}},
                      '7':{'class_type':'CLIPTextEncode','inputs':{'text':''}},
                      '27':{'class_type':'SaveImage','inputs':{'filename_prefix':'old'}}}}
        self.new=copy.deepcopy(self.old)
        self.new['phone_camera_style_strength']=.25
        self.new['prompt']['6']['inputs']['text']='new'
        self.new['prompt']['27']['inputs']['filename_prefix']='new'

    def test_legacy_missing_field_uses_unchanged_graph(self):
        self.assertEqual(set(module.compare(self.old,self.new)),{'6.text','27.filename_prefix'})

    def test_actual_strength_change_rejected(self):
        self.new['phone_camera_style_strength']=.2
        self.new['prompt']['3']['inputs']['strength_model']=.2
        with self.assertRaises(ValueError): module.compare(self.old,self.new)

    def test_declared_strength_mismatch_rejected(self):
        self.new['phone_camera_style_strength']=.1
        with self.assertRaises(ValueError): module.compare(self.old,self.new)

    def test_seed_or_reference_change_rejected(self):
        self.new['seed']=11
        with self.assertRaises(ValueError): module.compare(self.old,self.new)
        self.new['seed']=10
        self.new['references'][0]['sha256']='changed'
        with self.assertRaises(ValueError): module.compare(self.old,self.new)

    def test_negative_is_explicit_and_keeps_positive_fixed(self):
        self.new['prompt']['6']['inputs']['text']='old'
        self.new['prompt']['7']['inputs']['text']='visible teeth'
        self.assertEqual(set(module.compare(self.old,self.new,'negative')),{'7.text','27.filename_prefix'})
        with self.assertRaises(ValueError): module.compare(self.old,self.new)
        self.new['prompt']['6']['inputs']['text']='changed too'
        with self.assertRaises(ValueError): module.compare(self.old,self.new,'negative')


if __name__=='__main__': unittest.main()
