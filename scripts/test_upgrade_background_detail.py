import copy
import json
from pathlib import Path
import unittest
import numpy as np
from upgrade_background_detail import background_mask, build_graph, validate_graph, PROMPT


class BackgroundDetailTests(unittest.TestCase):
    def test_protected_person_and_feather_direction(self):
        person=np.zeros((128,192),np.uint8);person[25:,60:130]=255
        mask,meta=background_mask(person)
        self.assertFalse(mask[person>0].any())
        self.assertEqual(mask[70,60-meta['protection_margin_px']],0)
        self.assertEqual(mask[70,59],0)
        self.assertEqual(mask[0,0],255)
        self.assertTrue(np.any((mask>0)&(mask<255)))
        self.assertTrue(np.all(np.diff(mask[70,:60].astype(int))<=0))

    def test_bad_masks_rejected(self):
        for data in (np.zeros((64,64),np.uint8),np.full((64,64),255,np.uint8),np.zeros((64,64,3),np.uint8)):
            with self.assertRaises(ValueError):background_mask(data)

    def test_graph_preserves_source_and_codec(self):
        loaders={str(i):{'class_type':'dummy','inputs':{}} for i in range(1,6)}
        loaders['1']['inputs']['weight_dtype']='default'
        loaders['2']['inputs']['strength_model']=.9
        loaders['3']['inputs']['strength_model']=.25
        graph=build_graph(loaders,'source.png','genuine.jpg','mask.png',[1280,768],8675416,'upgrade-source-faithful/test')
        self.assertEqual(graph['6']['inputs']['text'],PROMPT)
        self.assertEqual(graph['28']['inputs'],{'samples':['11',0],'mask':['24',0]})
        self.assertEqual(graph['12']['inputs']['latent'],['11',0])
        self.assertEqual(graph['13']['inputs']['latent'],['11',0])
        self.assertEqual(graph['30']['inputs']['samples'],['11',0])
        self.assertNotIn('ImageCompositeMasked',[n['class_type'] for n in graph.values()])

    def test_prepared_contract_and_corruption_rejection(self):
        path=Path(__file__).resolve().parents[1]/'work/upgrade-source-faithful-20260903/background-detail-house-pilot/experiment.json'
        manifest=json.loads(path.read_text(encoding='utf-8'))
        validate_graph(manifest)
        for field,value in (('turbo',True),('phone_camera_style',False),('postprocess',True)):
            bad=copy.deepcopy(manifest);bad[field]=value
            with self.assertRaises(ValueError):validate_graph(bad)
        bad=copy.deepcopy(manifest);bad['prompt']['28']['inputs']['mask']=['14',0]
        with self.assertRaises(ValueError):validate_graph(bad)

    def test_single_scene_reference_refinement(self):
        root=Path(__file__).resolve().parents[1]/'work/upgrade-source-faithful-20260903'
        original=json.loads((root/'background-detail-house-pilot/experiment.json').read_text())
        refined=json.loads((root/'background-detail-house-scene-reference/experiment.json').read_text())
        validate_graph(refined)
        self.assertEqual(original['references'],refined['references'][:3])
        fixed_keys=set(original['prompt'])-{'6','21','27','31'}
        for key in fixed_keys:self.assertEqual(original['prompt'][key],refined['prompt'][key])
        self.assertEqual(refined['prompt']['43']['inputs'],{'conditioning':['17',0],'latent':['42',0]})
        self.assertEqual(refined['prompt']['44']['inputs'],{'conditioning':['18',0],'latent':['42',0]})
        self.assertEqual(refined['prompt']['32']['inputs']['samples'],['11',0])
        self.assertEqual(refined['prompt']['33']['inputs']['samples'],['25',0])
        self.assertEqual(refined['prompt']['26']['inputs'],original['prompt']['26']['inputs'])
        bad=copy.deepcopy(refined);bad['references'][3]['role']='genuine_identity'
        with self.assertRaises(ValueError):validate_graph(bad)


if __name__=='__main__':unittest.main()
