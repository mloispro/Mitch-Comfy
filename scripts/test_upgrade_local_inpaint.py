import unittest
import numpy as np
from upgrade_local_inpaint import build_mask, build_graph, validate_graph, PROMPT, SOURCE_GEOMETRY_PROMPT
from upgrade_parsenet_hair import select_hair


class InpaintTests(unittest.TestCase):
    def setUp(self):
        self.loaders={str(i):{'class_type':'placeholder','inputs':{}} for i in range(1,6)}
        self.loaders['1']['inputs']['weight_dtype']='default'
        self.loaders['2']['inputs']['strength_model']=.9
        self.loaders['3']['inputs']['strength_model']=.25

    def test_mask_compact_inward_feather_and_binary_extremes(self):
        face=np.zeros((160,240),np.uint8); face[40:115,90:145]=255
        hair=np.zeros_like(face); hair[25:50,85:150]=255
        mask, info=build_mask(face,hair,55)
        self.assertEqual(mask[0,0],0);self.assertEqual(mask[65,110],255)
        self.assertTrue(np.any((mask>0)&(mask<255)))
        self.assertLess(info['nonzero_fraction'],.35)
        self.assertFalse(np.any(mask[:,160:]))

    def test_broad_or_empty_mask_rejected(self):
        for value in (0,255):
            image=np.full((100,100),value,np.uint8)
            with self.assertRaises(ValueError):build_mask(image,image,50)

    def test_face_hair_gap_does_not_leave_a_forehead_strip(self):
        face=np.zeros((160,240),np.uint8); face[60:125,90:145]=255
        hair=np.zeros_like(face); hair[20:40,85:150]=255
        mask,_=build_mask(face,hair,55)
        self.assertEqual(mask[50,115],255)

    def test_source_is_both_first_reference_and_masked_initial_latent(self):
        graph=build_graph(self.loaders,'src','id','mask',[1280,768],8675417,'upgrade-source-faithful/pilot')
        self.assertEqual(graph['12']['inputs']['latent'],['11',0])
        self.assertEqual(graph['13']['inputs']['latent'],['11',0])
        self.assertEqual(graph['28']['inputs']['samples'],['11',0])
        self.assertEqual(graph['25']['inputs']['latent_image'],['28',0])
        self.assertEqual(graph['17']['inputs']['conditioning'],['12',0])
        self.assertEqual(graph['18']['inputs']['conditioning'],['13',0])
        self.assertEqual(graph['7']['inputs']['text'],'')
        self.assertEqual(graph['30']['inputs']['samples'],['11',0])
        self.assertNotIn('mask',PROMPT.lower())

    def test_wrong_geometry_prefix_or_phone_strength_rejected(self):
        with self.assertRaises(ValueError):build_graph(self.loaders,'a','b','c',[1281,768],1,'upgrade-source-faithful/test')
        with self.assertRaises(ValueError):build_graph(self.loaders,'a','b','c',[1280,768],1,'../test')
        self.loaders['3']['inputs']['strength_model']=0
        with self.assertRaises(ValueError):build_graph(self.loaders,'a','b','c',[1280,768],1,'upgrade-source-faithful/test')

    def test_parsenet_hair_is_13_and_neck_17_is_excluded(self):
        labels=np.zeros((100,100),np.uint8)
        labels[5:30,20:80]=13
        labels[55:99,10:90]=17
        hair=select_hair(labels)
        self.assertTrue(np.all(hair[5:30,20:80]==255))
        self.assertFalse(np.any(hair[55:99,10:90]))
        with self.assertRaises(ValueError):select_hair(np.full((20,20),17,np.uint8))

    def test_original_geometry_is_third_on_both_branches_not_initial_latent(self):
        graph=build_graph(self.loaders,'raw','id','mask',[1280,768],8675417,
                          'upgrade-source-faithful/geometry','original')
        self.assertEqual(graph['40']['inputs']['image'],'original')
        self.assertEqual(graph['43']['inputs'],{'conditioning':['17',0],'latent':['42',0]})
        self.assertEqual(graph['44']['inputs'],{'conditioning':['18',0],'latent':['42',0]})
        self.assertEqual(graph['21']['inputs']['positive'],['43',0])
        self.assertEqual(graph['21']['inputs']['negative'],['44',0])
        self.assertEqual(graph['28']['inputs']['samples'],['11',0])
        self.assertEqual(graph['7']['inputs']['text'],'')
        self.assertEqual(graph['6']['inputs']['text'],SOURCE_GEOMETRY_PROMPT)
        self.assertNotIn("Keep Picture 1's head direction",SOURCE_GEOMETRY_PROMPT)
        self.assertIn("Use Picture 3's",SOURCE_GEOMETRY_PROMPT)

    def test_frozen_old_and_new_manifest_roles_and_graphs(self):
        import copy
        from pathlib import Path
        import json
        root=Path(__file__).resolve().parents[1]
        old=json.loads((root/'work/upgrade-source-faithful-20260903/native-masked-high-house-ready/experiment.json').read_text())
        validate_graph(old)
        new=copy.deepcopy(old)
        new['references'].append({'name':'original','role':'original_source_geometry_expression_not_identity'})
        new['reference_mode']='raw_first_genuine_second_original_geometry_third'
        new['effective_prompt']=SOURCE_GEOMETRY_PROMPT
        refs=new['references']
        new['prompt']=build_graph(new['prompt'],refs[0]['name'],refs[1]['name'],refs[2]['name'],
                                  new['dimensions'],new['seed'],new['output_prefix'],'original')
        validate_graph(new)
        new['references'][3]['role']='genuine_identity'
        with self.assertRaises(ValueError):validate_graph(new)
        new['references'][3]['role']='original_source_geometry_expression_not_identity'
        new['prompt']['21']['inputs']['negative']=['18',0]
        with self.assertRaises(ValueError):validate_graph(new)


if __name__=='__main__':unittest.main()
