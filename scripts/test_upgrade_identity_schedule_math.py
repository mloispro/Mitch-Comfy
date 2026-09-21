"""CPU contract test of the installed Euler/flow continuation, not an image-quality test."""
import ast
import math
from pathlib import Path
import unittest

import torch

COMFY = Path('C:/projects/AI-Tools/ComfyUI')


def definitions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name in names]
    assert {node.name for node in selected} == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)


NS = {'torch': torch, 'math': math, 'trange': lambda n, **kwargs: range(n),
      'to_d': lambda x, sigma, denoised: (x-denoised)/sigma}
definitions(COMFY/'comfy/model_sampling.py', ['reshape_sigma', 'CONST'], NS)
definitions(COMFY/'comfy_extras/nodes_flux.py',
            ['generalized_time_snr_shift', 'compute_empirical_mu', 'get_schedule'], NS)
definitions(COMFY/'comfy/k_diffusion/sampling.py', ['sample_euler'], NS)


class IdentityScheduleMathTests(unittest.TestCase):
    def setUp(self):
        self.sigmas = NS['get_schedule'](50, 1680*1008//256)
        self.flow = NS['CONST']()
        self.latent = torch.randn((1, 128, 4, 4), generator=torch.Generator().manual_seed(41))
        self.model = lambda x, sigma, **kw: .2*x + .15*torch.sin(x) + .1*sigma.reshape(-1,1,1,1)

    def test_split_covers_same_intervals_and_shared_boundary(self):
        early, late = self.sigmas[:36], self.sigmas[35:]
        self.assertEqual(len(early)-1 + len(late)-1, 50)
        self.assertTrue(torch.equal(torch.cat((early[:-1], late)), self.sigmas))
        self.assertEqual(early[-1], late[0])
        self.assertGreater(float(late[0]), 0)
        self.assertLess(float(late[0]), 1)

    def test_flow_export_and_zero_noise_import_cancel(self):
        sigma = self.sigmas[35]
        exported = self.flow.inverse_noise_scaling(sigma, self.latent)
        restored = self.flow.noise_scaling(sigma, torch.zeros_like(self.latent), exported)
        torch.testing.assert_close(restored, self.latent, atol=5e-7, rtol=1e-6)

    def test_actual_installed_euler_matches_constant_weight_split(self):
        sample = NS['sample_euler']
        direct = sample(self.model, self.latent.clone(), self.sigmas, disable=True)
        for step in (15, 35):
            with self.subTest(step=step):
                early = sample(self.model, self.latent.clone(), self.sigmas[:step+1], disable=True)
                exported = self.flow.inverse_noise_scaling(self.sigmas[step], early)
                restored = self.flow.noise_scaling(self.sigmas[step], torch.zeros_like(early), exported)
                split = sample(self.model, restored, self.sigmas[step:], disable=True)
                torch.testing.assert_close(split, direct, atol=5e-7, rtol=1e-6)

    def test_new_noise_would_not_be_a_valid_continuation(self):
        sigma = self.sigmas[35]
        exported = self.flow.inverse_noise_scaling(sigma, self.latent)
        corrupted = self.flow.noise_scaling(sigma, torch.ones_like(self.latent), exported)
        self.assertGreater(float((corrupted-self.latent).abs().mean()), .1)


if __name__ == '__main__':
    print('Actual shifted sigma at split step35:', float(NS['get_schedule'](50, 1680*1008//256)[35]))
    unittest.main()
