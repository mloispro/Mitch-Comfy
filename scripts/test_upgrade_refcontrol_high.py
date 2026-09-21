import copy
import unittest

import cv2
import numpy as np

from upgrade_refcontrol_high import (
    PINS, TEMPLATE, read_json, source_edges, build_graph, validate_graph,
)


class RefControlHighTests(unittest.TestCase):
    def setUp(self):
        self.refs = [{'name':'source-canny.png [input]'}, {'name':'raw.png [output]'}]
        self.manifest = {'stage':'refcontrol_native_high_edit', 'postprocess':False, 'turbo':False,
                         'synthetic_self_reference':True, 'phone_camera_style':False,
                         'upstream_phone_camera_style':True,
                         'phone_appearance_mode':'inherited_klein_raw_no_stacked_adapter',
                         'references':self.refs, 'seed':8675416, 'output_prefix':'test/raw',
                         'verified_models':[{'model_relative_path':p,'sha256':h} for p,h in PINS.items()]}
        self.manifest['prompt'] = build_graph(self.refs,8675416,'test/raw')

    def test_minimal_author_graph_only_scene_specific_changes(self):
        validate_graph(self.manifest)
        template = read_json(TEMPLATE)['prompt']
        graph = self.manifest['prompt']
        self.assertEqual({k for k in graph if graph[k] != template[k]}, {'5','10','20','33','37'})
        self.assertEqual(graph['13']['inputs']['latent'],['12',0])
        self.assertEqual(graph['23']['inputs'],{'conditioning':['13',0],'latent':['22',0]})
        self.assertEqual(graph['24']['inputs'],{'conditioning':['14',0],'latent':['22',0]})
        self.assertEqual(graph['30']['inputs']['cfg'],5)
        self.assertEqual(graph['32']['inputs']['steps'],20)
        self.assertEqual(graph['34']['class_type'],'EmptyFlux2LatentImage')
        self.assertEqual(graph['36']['inputs']['samples'],['35',0])
        self.assertEqual(sum(n['class_type'].startswith('LoraLoader') for n in graph.values()),1)

    def test_changed_reference_order_model_or_controls_rejected(self):
        for node, field, value in [('13','latent',['22',0]), ('2','strength_model',.8),
                                   ('2','lora_name','identity.safetensors'), ('32','steps',4),
                                   ('35','latent_image',['12',0]), ('11','upscale_method','lanczos')]:
            with self.subTest(node=node,field=field):
                bad = copy.deepcopy(self.manifest)
                bad['prompt'][node]['inputs'][field] = value
                with self.assertRaises(ValueError): validate_graph(bad)

    def test_provenance_and_no_turbo_postprocess_or_active_phone_claim(self):
        for field in ('postprocess','turbo','phone_camera_style'):
            bad=copy.deepcopy(self.manifest);bad[field]=True
            with self.assertRaises(ValueError): validate_graph(bad)
        for field in ('synthetic_self_reference','upstream_phone_camera_style'):
            bad=copy.deepcopy(self.manifest);bad[field]=False
            with self.assertRaises(ValueError): validate_graph(bad)
        with self.assertRaises(ValueError): build_graph(self.refs[:1],1,'test')

    def test_sole_author_trigger_refinement_changes_only_prompt(self):
        refined=copy.deepcopy(self.manifest)
        refined['prompt_variant']='author-trigger-only'
        refined['prompt']=build_graph(self.refs,8675416,'test/raw','author-trigger-only')
        validate_graph(refined)
        self.assertEqual(refined['prompt']['5']['inputs']['text'],'refcontrol')
        self.assertEqual({k for k in refined['prompt'] if refined['prompt'][k]!=self.manifest['prompt'][k]},{'5'})
        with self.assertRaises(ValueError): build_graph(self.refs,1,'test','unbounded-new-prompt')

    def test_author_canny_resize_padding_and_binary_rgb(self):
        rng=np.random.default_rng(12)
        source=rng.integers(0,256,(1008,1680,3),dtype=np.uint8)
        actual=source_edges(source)
        self.assertEqual(actual.shape,(512,853,3))
        resized=cv2.resize(source,(853,512),interpolation=cv2.INTER_AREA)
        expected=cv2.Canny(np.pad(resized,((0,0),(0,43),(0,0)),mode='edge'),100,200)[:512,:853]
        for channel in range(3): np.testing.assert_array_equal(actual[:,:,channel],expected)
        self.assertEqual(set(np.unique(actual)),{0,255})
        np.testing.assert_array_equal(actual,source_edges(source))

    def test_small_control_upscales_and_rejects_wrong_pixel_format(self):
        rgb=np.zeros((128,192,3),dtype=np.uint8);rgb[40:90,50:130]=255
        self.assertEqual(source_edges(rgb).shape,(512,768,3))
        with self.assertRaises(ValueError): source_edges(rgb.astype(np.float32))
        with self.assertRaises(ValueError): source_edges(rgb[:,:,0])


if __name__ == '__main__': unittest.main()
