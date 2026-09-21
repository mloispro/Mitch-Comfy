import math
import unittest

from upgrade_qwen_reference_acceptance import validate_reference_layout


class QwenReferenceTests(unittest.TestCase):
    def fixture(self,identity=True):
        scene={'name':'scene.png [output]','sha256':'a'}
        anchor={'name':'genuine.jpg [input]','sha256':'b','kind':'camera_still','split':'train',
                'provenance_record_id':'train07','provenance_manifest_sha256':'c'}
        graph={'41':{'class_type':'LoadImage','inputs':{'image':scene['name']}},
               '160':{'inputs':{'image':['41',0]}},'156':{'inputs':{'pixels':['160',0]}}}
        for key in ('151','149'):
            graph[key]={'class_type':'TextEncodeQwenImageEditPlus','inputs':{'image1':['160',0]}}
            if identity: graph[key]['inputs']['image2']=['83',0]
        if identity: graph['83']={'class_type':'LoadImage','inputs':{'image':anchor['name']}}
        return {'prompt':graph,'references':[scene,anchor] if identity else [scene],
                'reference_mode':'scene_plus_genuine_identity' if identity else 'edit_target_only'}

    def test_single_and_two_image_layouts(self):
        for identity in (False,True):
            self.assertEqual(validate_reference_layout(self.fixture(identity))['reference_count'],1+identity)

    def original_fixture(self):
        value=self.fixture()
        value.update(source_role='original_source',upstream_phone_camera_style=False,phone_camera_style=False,
                     phone_camera_style_strength=0,phone_appearance_mode='experimental_native_prompt_only',
                     baseline_report_role='comparison_and_seed_only_not_upstream')
        value['references'][0].update(source_audit='audit.json',source_audit_sha256='abc')
        return value

    def test_direct_original_has_honest_phone_provenance(self):
        self.assertEqual(validate_reference_layout(self.original_fixture())['reference_count'],2)

    def test_direct_original_rejects_false_phone_claims(self):
        for field,bad in (('upstream_phone_camera_style',True),('phone_camera_style',True),
                          ('phone_camera_style_strength',.25),('baseline_report_role','upstream'),
                          ('phone_appearance_mode','inherited_from_klein'),('upstream_evaluation_audit','a.json')):
            value=self.original_fixture();value[field]=bad
            with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_direct_original_needs_source_audit(self):
        value=self.original_fixture();del value['references'][0]['source_audit']
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_missing_negative_reference_rejected(self):
        value=self.fixture();del value['prompt']['149']['inputs']['image2']
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_swapped_scene_or_latent_rejected(self):
        for key,field in (('151','image1'),('156','pixels')):
            value=self.fixture();value['prompt'][key]['inputs'][field]=['83',0]
            with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_unreviewed_third_reference_rejected(self):
        value=self.fixture();value['prompt']['151']['inputs']['image3']=['83',0]
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_validation_or_synthetic_reference_rejected(self):
        for field,bad in (('split','validation'),('kind','synthetic')):
            value=self.fixture();value['references'][1][field]=bad
            with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_wrong_loader_or_duplicate_reference_rejected(self):
        value=self.fixture();value['prompt']['83']['inputs']['image']='wrong.png'
        with self.assertRaises(ValueError): validate_reference_layout(value)
        value=self.fixture();value['references'][1]['sha256']='a'
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def three_input_fixture(self):
        value=self.fixture()
        value['reference_mode']='scene_identity_original_expression'
        value['references'].append({'name':'source.png [input]','sha256':'d',
            'kind':'original_expression_source','source_audit':'audit.json','source_audit_sha256':'e',
            'identity_influence':'unisolated_not_proven_absent'})
        value['prompt']['184']={'class_type':'LoadImage','inputs':{'image':'source.png [input]'}}
        for key in ('151','149'): value['prompt'][key]['inputs']['image3']=['184',0]
        return value

    def test_recorded_three_reference_mode(self):
        self.assertEqual(validate_reference_layout(self.three_input_fixture())['reference_count'],3)

    def test_missing_or_swapped_third_branch_is_rejected(self):
        for key in ('151','149'):
            value=self.three_input_fixture();del value['prompt'][key]['inputs']['image3']
            with self.assertRaises(ValueError): validate_reference_layout(value)
            value=self.three_input_fixture();value['prompt'][key]['inputs']['image3']=['83',0]
            with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_source_without_provenance_or_false_identity_claim_rejected(self):
        for field in ('source_audit','source_audit_sha256','identity_influence'):
            value=self.three_input_fixture();del value['references'][2][field]
            with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_expression_cannot_replace_genuine_identity_or_repeat_target(self):
        value=self.three_input_fixture();value['references'][1],value['references'][2]=value['references'][2],value['references'][1]
        with self.assertRaises(ValueError): validate_reference_layout(value)
        value=self.three_input_fixture();value['references'][2]['sha256']='a'
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_wrong_third_loader_rejected(self):
        value=self.three_input_fixture();value['prompt']['184']['inputs']['image']='wrong.png'
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_full_noise_is_not_reported_as_retaining_source_initialization(self):
        for denoise,retained in ((1.,False),(.35,True)):
            value=self.three_input_fixture();value['denoise']=denoise
            result=validate_reference_layout(value)
            self.assertTrue(result['scene_supplies_sampler_latent'])
            self.assertEqual(result['source_spatial_initialization_retained'],retained)

    def packed_fixture(self):
        value=self.three_input_fixture()
        value.update(reference_packing='author32_explicit_native_latents',framing_mode='whole_frame',reference_packing_geometry=[])
        graph=value['prompt'];positive,negative='151','149'
        for i,(source,size) in enumerate(zip(('160','83','184'),((1680,1008),(2544,3392),(1680,1008)))):
            factor=math.sqrt(1048576/(size[0]*size[1]));dims=[round(d*factor/32)*32 for d in size]
            value['reference_packing_geometry'].append({'reference_index':i+1,'source_node':source,
                'source_dimensions':list(size),'vae_dimensions':dims,'latent_dimensions':[d//8 for d in dims],
                'circular_patch_padding_required':False})
            scale,encode,p,n=map(str,range(190+4*i,194+4*i))
            graph[scale]={'class_type':'ImageScale','inputs':{'image':[source,0],'upscale_method':'area','crop':'disabled','width':dims[0],'height':dims[1]}}
            graph[encode]={'class_type':'VAEEncode','inputs':{'pixels':[scale,0],'vae':['146',0]}}
            graph[p]={'class_type':'ReferenceLatent','inputs':{'conditioning':[positive,0],'latent':[encode,0]}}
            graph[n]={'class_type':'ReferenceLatent','inputs':{'conditioning':[negative,0],'latent':[encode,0]}}
            positive,negative=p,n
        for key,previous in (('148',positive),('147',negative)):
            graph[key]={'class_type':'FluxKontextMultiReferenceLatentMethod','inputs':{'conditioning':[previous,0],'reference_latents_method':'index_timestep_zero'}}
        return value

    def test_author32_native_chain_preserves_all_reference_roles(self):
        value=self.packed_fixture()
        self.assertEqual(value['reference_packing_geometry'][0]['vae_dimensions'],[1312,800])
        self.assertEqual(value['reference_packing_geometry'][1]['vae_dimensions'],[896,1184])
        self.assertEqual(validate_reference_layout(value)['reference_count'],3)

    def test_double_latents_rejected_on_either_cfg_branch(self):
        for key in ('151','149'):
            value=self.packed_fixture();value['prompt'][key]['inputs']['vae']=['146',0]
            with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_swapped_missing_or_repeated_explicit_latents_rejected(self):
        for key,field in (('196','latent'),('197','latent'),('200','conditioning'),('201','conditioning')):
            value=self.packed_fixture();value['prompt'][key]['inputs'][field]=['191',0]
            with self.assertRaises(ValueError): validate_reference_layout(value)
        value=self.packed_fixture();del value['prompt']['199']
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_odd_latent_dimensions_or_crop_rejected(self):
        value=self.packed_fixture();value['prompt']['190']['inputs']['width']=1320
        with self.assertRaises(ValueError): validate_reference_layout(value)
        value=self.packed_fixture();value['prompt']['190']['inputs']['crop']='center'
        with self.assertRaises(ValueError): validate_reference_layout(value)
        value=self.packed_fixture();value['reference_packing_geometry'][0]['vae_dimensions']=[1320,792]
        with self.assertRaises(ValueError): validate_reference_layout(value)

    def test_bypass_packing_or_unknown_mode_rejected(self):
        value=self.packed_fixture();value['prompt']['147']['inputs']['conditioning']=['149',0]
        with self.assertRaises(ValueError): validate_reference_layout(value)
        value=self.packed_fixture();value['reference_packing']='unknown'
        with self.assertRaises(ValueError): validate_reference_layout(value)


if __name__=='__main__': unittest.main()
