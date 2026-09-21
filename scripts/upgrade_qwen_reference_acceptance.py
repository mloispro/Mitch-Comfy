"""Verify the experimental Qwen reference layout without loading image models."""
from __future__ import annotations

import math


def validate_reference_layout(manifest: dict) -> dict:
    graph=manifest['prompt']
    refs=manifest['references']
    mode=manifest.get('reference_mode','edit_target_only')
    expected={'edit_target_only':1,'scene_plus_genuine_identity':2,'scene_identity_original_expression':3}.get(mode)
    if expected is None or len(refs)!=expected:
        raise ValueError('Unsupported Qwen reference count or role layout.')
    if manifest.get('source_role')=='original_source':
        if (expected!=2 or not refs[0].get('source_audit') or not refs[0].get('source_audit_sha256')
                or manifest.get('upstream_phone_camera_style') is not False
                or manifest.get('phone_camera_style') is not False
                or manifest.get('phone_camera_style_strength')!=0
                or manifest.get('phone_appearance_mode')!='experimental_native_prompt_only'
                or manifest.get('baseline_report_role')!='comparison_and_seed_only_not_upstream'
                or manifest.get('upstream_evaluation_audit')):
            raise ValueError('Original-source edit must not claim inherited or active Klein phone LoRA.')
    if graph['41']['class_type']!='LoadImage' or graph['41']['inputs']['image']!=refs[0]['name']:
        raise ValueError('Picture1 must be the recorded edit target.')
    if graph['160']['inputs']['image']!=['41',0] or graph['156']['inputs']['pixels']!=['160',0]:
        raise ValueError('The scene, not the identity portrait, must initialize the sampler latent.')
    for encoder in ('151','149'):
        node=graph[encoder]
        if node['class_type']!='TextEncodeQwenImageEditPlus' or node['inputs'].get('image1')!=['160',0]:
            raise ValueError('Both native CFG branches must receive the scene as image1.')
        if expected==3:
            if node['inputs'].get('image3')!=['184',0]:
                raise ValueError('Both native CFG branches must receive the original expression image3.')
        elif 'image3' in node['inputs']:
            raise ValueError('An unreviewed third reference is not allowed.')
        if expected>=2:
            if node['inputs'].get('image2')!=['83',0]:
                raise ValueError('Both native CFG branches must receive the same identity image2.')
        elif 'image2' in node['inputs']:
            raise ValueError('Unrecorded second image.')
    if expected>=2:
        reference=refs[1]
        if (reference.get('kind')!='camera_still' or reference.get('split')!='train'
                or not reference.get('provenance_record_id') or not reference.get('provenance_manifest_sha256')):
            raise ValueError('Expected recorded genuine training-photo provenance, not a held-out score reference.')
        if reference['sha256']==refs[0]['sha256']:
            raise ValueError('The edit target is not an independent genuine identity input.')
        if graph['83']['class_type']!='LoadImage' or graph['83']['inputs']['image']!=reference['name']:
            raise ValueError('Picture2 loader does not match its provenance record.')
    if expected==3:
        expression=refs[2]
        if (expression.get('kind')!='original_expression_source' or not expression.get('source_audit')
                or not expression.get('source_audit_sha256')
                or expression.get('identity_influence')!='unisolated_not_proven_absent'):
            raise ValueError('Original expression input needs audited source provenance and honest identity scope.')
        if len({ref['sha256'].lower() for ref in refs})!=3:
            raise ValueError('The three input roles must use distinct photographs.')
        if graph['184']['class_type']!='LoadImage' or graph['184']['inputs']['image']!=expression['name']:
            raise ValueError('Picture3 loader does not match its provenance record.')
    packing=manifest.get('reference_packing','native')
    if packing not in ('native','author32_explicit_native_latents'):
        raise ValueError('Unreviewed reference packing mode.')
    if packing=='author32_explicit_native_latents':
        if manifest.get('framing_mode')!='whole_frame':
            raise ValueError('Explicit reference packing requires unchanged whole-frame aspect.')
        geometry=manifest.get('reference_packing_geometry',[])
        if len(geometry)!=expected: raise ValueError('Missing reference packing dimensions.')
        previous_positive,previous_negative='151','149'
        for encoder in (previous_positive,previous_negative):
            if 'vae' in graph[encoder]['inputs']:
                raise ValueError('Plus VAE must be omitted to avoid double appearance references.')
        for index,source_node in enumerate(('160','83','184')[:expected]):
            item=geometry[index]
            width,height=item['source_dimensions']
            if width<=0 or height<=0: raise ValueError('Invalid source dimensions.')
            scale=math.sqrt(1048576/(width*height))
            dimensions=[round(width*scale/32)*32,round(height*scale/32)*32]
            if (item['reference_index']!=index+1 or item['source_node']!=source_node
                    or item['vae_dimensions']!=dimensions or min(dimensions)<=0
                    or item['latent_dimensions']!=[d//8 for d in dimensions]
                    or item['circular_patch_padding_required'] is not False):
                raise ValueError('Reference packing metadata differs from author32 calculation.')
            scale_id,encode_id,positive_id,negative_id=map(str,range(190+4*index,194+4*index))
            wanted={
                scale_id:{'class_type':'ImageScale','inputs':{'image':[source_node,0],
                    'upscale_method':'area','crop':'disabled','width':dimensions[0],'height':dimensions[1]}},
                encode_id:{'class_type':'VAEEncode','inputs':{'pixels':[scale_id,0],'vae':['146',0]}},
                positive_id:{'class_type':'ReferenceLatent','inputs':{'conditioning':[previous_positive,0],'latent':[encode_id,0]}},
                negative_id:{'class_type':'ReferenceLatent','inputs':{'conditioning':[previous_negative,0],'latent':[encode_id,0]}},
            }
            for key,value in wanted.items():
                if graph.get(key)!=value: raise ValueError('Explicit native appearance-reference chain changed.')
            previous_positive,previous_negative=positive_id,negative_id
        for key,previous in (('148',previous_positive),('147',previous_negative)):
            if graph[key]!={'class_type':'FluxKontextMultiReferenceLatentMethod',
                           'inputs':{'conditioning':[previous,0],'reference_latents_method':'index_timestep_zero'}}:
                raise ValueError('Final reference ordering/method changed.')
    return {'mode':mode,'reference_count':expected,'reference_packing':packing,
            'scene_supplies_sampler_latent':True,
            'source_spatial_initialization_retained':float(manifest.get('denoise',1.0))<1.0,
            'both_cfg_branches_match':True,
            'note':'Validates wiring/declared roles, not identity preservation. At denoise 1 the scene latent supplies shape, not a retained spatial prior. File provenance is checked separately.'}
