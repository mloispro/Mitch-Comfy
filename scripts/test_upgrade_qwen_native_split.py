"""Exercise installed native method bodies with shape-only fakes; no GPU/model imports.

This proves field/order and preprocessing equivalence, not numerical VAE equivalence
or image quality. Native RGB image inputs make stock VAEEncode's untrimmed input
identical to the Plus encoder's first-three-channel slice.
"""
import ast
import math
from pathlib import Path
from types import SimpleNamespace as NS
import unittest


COMFY=Path(__file__).resolve().parents[2]/'ComfyUI'


class ShapeImage:
    def __init__(self,shape): self.shape=tuple(shape)
    def movedim(self,source,destination):
        shape=list(self.shape);value=shape.pop(source);shape.insert(destination%len(self.shape),value)
        return ShapeImage(shape)
    def __getitem__(self,key):
        return ShapeImage([len(range(n)[s]) for n,s in zip(self.shape,key)])


def method(path,name,environment,class_name=None):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    scope=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name).body if class_name else tree.body
    function=next(n for n in scope if isinstance(n,ast.FunctionDef) and n.name==name)
    function.decorator_list=[]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(path),'exec'),environment)
    return environment[name]


class NativeSplitTests(unittest.TestCase):
    def setUp(self):
        env={'math':math,'io':NS(NodeOutput=lambda c:(c,))}
        append=method(COMFY/'node_helpers.py','conditioning_set_values',env)
        def upscale(image,width,height,mode,crop):
            self.assertEqual((mode,crop),('area','disabled'))
            return ShapeImage((image.shape[0],image.shape[1],height,width))
        self.upscale=upscale
        env.update(node_helpers=NS(conditioning_set_values=append),comfy=NS(utils=NS(common_upscale=upscale)))
        self.plus=method(COMFY/'comfy_extras/nodes_qwen.py','execute',env,'TextEncodeQwenImageEditPlus')
        self.reference=method(COMFY/'comfy_extras/nodes_edit_model.py','execute',dict(env),'ReferenceLatent')
        self.encode=method(COMFY/'nodes.py','encode',dict(env),'VAEEncode')
        self.scale_image=method(COMFY/'nodes.py','upscale',dict(env),'ImageScale')
        self.clip=NS(tokenize=lambda prompt,images,llama_template:{'prompt':prompt,'images':[i.shape for i in images],'template':llama_template},
                     encode_from_tokens_scheduled=lambda tokens:[[tokens,{'unchanged_metadata':'sentinel'}]])
        self.vae=NS(encode=lambda rgb:{'encoded_rgb_shape':rgb.shape})
        self.images=[ShapeImage((1,816,1360,3)),ShapeImage((1,3392,2544,3)),ShapeImage((1,1008,1680,3))]

    def split(self,prompt,quantum):
        conditioning=self.plus(None,self.clip,prompt,None,*self.images)[0]
        for image in self.images:
            height,width=image.shape[1:3];scale=math.sqrt(1048576/(height*width))
            w=round(width*scale/quantum)*quantum;h=round(height*scale/quantum)*quantum
            resized=self.scale_image(None,image,'area',w,h,'disabled')[0]
            latent=self.encode(None,self.vae,resized)[0]
            conditioning=self.reference(None,conditioning,latent)[0]
        return conditioning

    def test_native8_split_equals_installed_combined_path_both_cfg_branches(self):
        for prompt in ('same positive prompt',''):
            combined=self.plus(None,self.clip,prompt,self.vae,*self.images)[0]
            self.assertEqual(combined,self.split(prompt,8))

    def test_author32_only_changes_appearance_dimensions(self):
        native=self.split('same positive prompt',8);aligned=self.split('same positive prompt',32)
        self.assertEqual(native[0][0],aligned[0][0])
        self.assertEqual(aligned[0][1]['unchanged_metadata'],'sentinel')
        shapes=[ref['encoded_rgb_shape'] for ref in aligned[0][1]['reference_latents']]
        self.assertEqual(shapes,[(1,800,1312,3),(1,1184,896,3),(1,800,1312,3)])
        self.assertTrue(all(s[1]%16==s[2]%16==0 for s in shapes))

    def test_plus_without_optional_vae_has_no_appearance_latents(self):
        result=self.plus(None,self.clip,'test',None,*self.images)[0]
        self.assertNotIn('reference_latents',result[0][1])


if __name__=='__main__': unittest.main()
