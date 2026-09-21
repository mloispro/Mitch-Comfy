"""Offline, CPU-only compatibility diagnostics; never loads or downloads model weights.

Reads the local base's safetensors header and tokenizer, and tests the installed
ConditioningAverage class on tiny synthetic tensors. This is not a workflow,
an image generator, a PixelSmile loader test, or a quality acceptance test.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import struct

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import numpy as np
import torch
from transformers import Qwen2Tokenizer

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / 'ComfyUI'
TARGET_MODULES = (
    'attn.to_q', 'attn.to_k', 'attn.to_v', 'attn.add_q_proj',
    'attn.add_k_proj', 'attn.add_v_proj', 'attn.to_out.0',
    'attn.to_add_out', 'img_mlp.net.0.proj', 'img_mlp.net.2',
    'txt_mlp.net.0.proj', 'txt_mlp.net.2',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_header(path):
    with path.open('rb') as handle:
        size_bytes = handle.read(8)
        if len(size_bytes) != 8:
            raise ValueError('Truncated safetensors length.')
        length = struct.unpack('<Q', size_bytes)[0]
        if not 2 <= length <= 64 * 1024**2:
            raise ValueError('Unexpected safetensors header size.')
        header = handle.read(length)
        if len(header) != length:
            raise ValueError('Truncated safetensors header.')
    return json.loads(header), hashlib.sha256(header).hexdigest()


def conditioning_check():
    # Extract only the inspected local CPU class, avoiding nodes.py's GPU imports.
    path = COMFY / 'nodes.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ConditioningAverage')
    namespace = {'torch': torch, 'logging': logging}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), namespace)
    blend = namespace['ConditioningAverage']().addWeighted
    target = torch.arange(24, dtype=torch.float32).reshape(1, 6, 4) / 7
    neutral = torch.flip(target, dims=[1]) / 3
    ref = torch.zeros((1, 16, 2, 2))
    mask = torch.ones((1, 6), dtype=torch.int64)
    meta = {'reference_latents': [ref], 'attention_mask': mask}
    checks = []
    for score in (0.0, 0.5, 1.0):
        output, returned = blend([[target, meta]], [[neutral, meta]], score)[0][0]
        expected = neutral + score * (target - neutral)
        error = float((output - expected).abs().max())
        assert error < 1e-6
        assert returned['reference_latents'][0] is ref
        assert returned['attention_mask'] is mask
        checks.append({'score': score, 'max_formula_error': error,
                       'target_reference_and_mask_preserved': True})
    longer_neutral = torch.cat([neutral, torch.full((1, 1, 4), 19.0)], dim=1)
    mismatch = blend([[target, meta]], [[longer_neutral, meta]], 0.0)[0][0][0]
    assert mismatch.shape[1] == 6 and longer_neutral.shape[1] == 7
    return {'equal_length_checks': checks,
            'unequal_length_neutral_is_silently_truncated': True,
            'safe_scope': 'Single equal-length pair, equal masks and the same source reference; no general unequal-length approval.',
            'nodes_py_sha256': sha(path)}


def token_check():
    directory = COMFY / 'comfy/text_encoders/qwen25_tokenizer'
    tokenizer = Qwen2Tokenizer.from_pretrained(str(directory), local_files_only=True)
    prefix = 'Picture 1: <|vision_start|><|image_pad|><|vision_end|>'
    prompts = {name: f'Edit the person to show a {name} expression' for name in ('neutral', 'confident')}
    ids = {name: tokenizer.encode(prefix + prompt, add_special_tokens=False) for name, prompt in prompts.items()}
    return {'prompts': prompts, 'text_token_ids': ids,
            'lengths_equal_before_image_expansion': len(ids['neutral']) == len(ids['confident']),
            'encoded_multimodal_tensors_tested': False,
            'limitation': 'Tokenization only; the same image/template is required and actual encoder tensor/mask equality remains untested.',
            'tokenizer_file_sha256': {p.name: sha(p) for p in directory.iterdir() if p.is_file()}}


def schedule_check():
    # Values read from Qwen's published 2511 scheduler_config.json. This is an
    # analytic diagnostic, not execution of the author's diffusers scheduler.
    sigmas = np.linspace(1.0, 1.0/50, 50, dtype=np.float32)
    sequence = 1024 * 1024 // 256
    mu = .5 + (sequence - 256) * (.9 - .5) / (8192 - 256)
    shifted = math.exp(mu) / (math.exp(mu) + (1 / sigmas - 1))
    author = 1 - (1 - shifted) / ((1 - shifted[-1]) / (1 - .02))
    community = 3.1 * sigmas / (1 + (3.1 - 1) * sigmas)
    assert abs(float(author[-1]) - .02) < 1e-6
    assert bool(np.all(np.diff(author) < 0))
    return {'steps_compared': 50, 'output_size': [1024, 1024],
            'author_mu': mu, 'equivalent_pre_terminal_rational_shift': math.exp(mu),
            'author_terminal_before_final_zero': float(author[-1]),
            'shift_3_1_terminal_before_final_zero': float(community[-1]),
            'max_sigma_difference': float(np.max(np.abs(author-community))),
            'exact_scheduler_parity_claimed': False,
            'conclusion': 'Constant AuraFlow shift3.1/simple is not the published dynamic-plus-terminal-stretch schedule.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'work') or output.exists():
        raise ValueError('Use a new audit file within this workspace work directory.')
    base = COMFY / 'models/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors'
    header, header_hash = read_header(base)
    keys = [k for k in header if k != '__metadata__']
    target_matches = {suffix: [k for k in keys if k.endswith('.'+suffix+'.weight')] for suffix in TARGET_MODULES}
    report = {
        'status': 'read_only_compatibility_diagnosis_not_generation_ready',
        'base_path': str(base), 'base_size_bytes': base.stat().st_size,
        'base_header_sha256': header_hash, 'whole_base_rehashed': False,
        'base_2511_marker': [k for k in keys if '__index_timestep_zero__' in k],
        'target_name_coverage': {k: {'count': len(v), 'first_match': v[:1],
            'first_shape': header[v[0]]['shape'] if v else None} for k, v in target_matches.items()},
        'adapter_present': any('pixelsmile' in str(p).lower() for p in (COMFY/'models/loras').rglob('*.safetensors')),
        'adapter_key_rank_alpha_and_patch_loading_verified': False,
        'tokenizer': token_check(), 'conditioning_average': conditioning_check(),
        'scheduler': schedule_check(),
        'cuda_initialized': torch.cuda.is_initialized(),
        'network_requests': 0, 'weights_loaded': False, 'photos_read': False,
        'dependencies_installed': False, 'production_changed': False,
        'runner_sha256': sha(Path(__file__)),
    }
    assert not report['cuda_initialized']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
