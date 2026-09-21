"""Isolated PixelSmile conditioning; never part of the production Upgrade graph."""
import json
import math

import numpy as np
import torch

TEMPLATE = "<|im_start|>system\nDescribe the key features of the input image (color, shape, size, texture, objects, background), then explain how the user's text instruction should alter or modify the image. Generate a new image that meets the user's requirements while maintaining consistency with the original input where appropriate.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"


def expression_sigmas(steps=50, width=1024, height=1024):
    if steps != 50 or (width, height) != (1024, 1024):
        raise ValueError('The initial author-layout probe is fixed at 50 steps / 1024 square.')
    raw = np.linspace(1.0, 1.0/steps, steps, dtype=np.float32)
    mu = .5 + ((width*height/256)-256) * (.9-.5)/(8192-256)
    shifted = math.exp(mu)/(math.exp(mu)+(1/raw-1))
    terminal = 1-(1-shifted)/((1-shifted[-1])/(1-.02))
    return torch.from_numpy(np.concatenate([terminal, np.zeros(1, np.float32)]))


def blend_equal(target, neutral, score):
    if not 0 <= score <= 1 or len(target) != 1 or len(neutral) != 1:
        raise ValueError('One aligned conditioning pair and score in [0,1] required.')
    tgt, meta = target[0]
    neu, neu_meta = neutral[0]
    if tgt.shape != neu.shape or tgt.dtype != neu.dtype or tgt.device != neu.device:
        raise ValueError('No implicit sequence padding or tensor conversion.')
    if not torch.isfinite(tgt).all() or not torch.isfinite(neu).all():
        raise ValueError('Nonfinite expression conditioning.')
    mask, neu_mask = meta.get('attention_mask'), neu_meta.get('attention_mask')
    if (mask is None) != (neu_mask is None) or (mask is not None and not torch.equal(mask, neu_mask)):
        raise ValueError('Neutral and expression attention masks differ.')
    if score == 0:
        value = neu.clone()
    elif score == 1:
        value = tgt.clone()
    else:
        value = neu + score * (tgt-neu)
    return [[value, meta.copy()]]


def validate_patches(model):
    patches = model.patches
    if len(patches) != 720 or type(model.model).__name__ != 'QwenImage':
        raise ValueError('Expected only the 720 PixelSmile Qwen layer patches.')
    for key, entries in patches.items():
        if not key.startswith('diffusion_model.transformer_blocks.') or len(entries) != 1:
            raise ValueError('Unexpected stacked adapter or patch target.')
        strength, adapter, base_strength, offset, fn = entries[0]
        if strength != 1.0 or base_strength != 1.0 or offset is not None or fn is not None:
            raise ValueError('Nonstandard adapter strength or mapping.')
        if type(adapter).__name__ != 'LoRAAdapter':
            raise ValueError('Expected standard LoRA matrices.')
        up, down, alpha, mid, dora, reshape = adapter.weights
        if down.shape[0] != 64 or up.shape[1] != 64 or alpha is not None or any(v is not None for v in (mid,dora,reshape)):
            raise ValueError('Released preview rank/scaling does not match.')
    return len(patches)


class AIToolkitPixelSmileProbe:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model': ('MODEL',), 'clip': ('CLIP',), 'vae': ('VAE',),
                             'image': ('IMAGE',),
                             'score': ('FLOAT', {'default': .5, 'min': 0, 'max': 1, 'step': .05})}}

    RETURN_TYPES = ('MODEL', 'CONDITIONING', 'SIGMAS')
    FUNCTION = 'encode'
    CATEGORY = 'AI Toolkit/experimental/PixelSmile-not-production'

    def encode(self, model, clip, vae, image, score):
        import comfy.utils
        if tuple(image.shape) != (1,512,512,3):
            raise ValueError('Initial probe requires one whole square source scaled to 512 RGB.')
        count = validate_patches(model)
        pairs = []
        for expression in ('confident','neutral'):
            prompt = f'Picture 1: <|vision_start|><|image_pad|><|vision_end|>Edit the person to show a {expression} expression'
            tokens = clip.tokenize(prompt, images=[image], llama_template=TEMPLATE)
            pairs.append(clip.encode_from_tokens_scheduled(tokens))
        conditioning = blend_equal(pairs[0], pairs[1], score)
        # Preserve the author's 512 vision input rather than the shipped Plus
        # node's 384-area pre-resize. Native Comfy vision interpolation remains
        # bilinear; this is an explicitly documented backend difference.
        full = comfy.utils.common_upscale(image.movedim(-1,1),1024,1024,'lanczos','disabled').movedim(1,-1)
        reference = vae.encode(full[:,:,:,:3])
        if 'reference_latents' in conditioning[0][1]:
            raise ValueError('Unexpected extra source reference.')
        conditioning[0][1]['reference_latents'] = [reference]
        report = {'profile': 'pixelsmile_author_layout_probe_v1', 'score': score,
                  'expression': 'confident', 'patched_layer_count': count,
                  'conditioning_shape': list(conditioning[0][0].shape),
                  'reference_shape': list(reference.shape), 'vision_input': [512,512],
                  'source_count': 1, 'character_lora': False, 'turbo': False,
                  'cfg': 'positive branch only', 'output_size': [1024,1024],
                  'backend_parity': 'Comfy FP8 mixed and native bilinear vision; not bit-exact author BF16'}
        print('PIXELSMILE_PROBE ' + json.dumps(report), flush=True)
        return {'ui': {'text': [json.dumps(report)]},
                'result': (model,conditioning,expression_sigmas())}


NODE_CLASS_MAPPINGS = {'AIToolkitPixelSmileProbe': AIToolkitPixelSmileProbe}
NODE_DISPLAY_NAME_MAPPINGS = {'AIToolkitPixelSmileProbe': 'PixelSmile — isolated expression probe'}
