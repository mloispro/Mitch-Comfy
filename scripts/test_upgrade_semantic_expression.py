import ast
from pathlib import Path
import unittest
import numpy as np
from experimental_upgrade_semantic_expression import apply_controls, solve_response, TOLERANCES


class SemanticExpressionTests(unittest.TestCase):
    def test_author_formula_exact_and_input_immutable(self):
        path = Path(__file__).resolve().parents[1]/'work/vendor/LivePortrait-code/src/gradio_pipeline.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'GradioPipeline')
        functions = []
        for name in ('smile', 'eyebrow', 'lip_variation_three'):
            method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'update_delta_new_'+name)
            method.decorator_list = []; functions.append(method)
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
        original = np.random.default_rng(35).normal(size=(1, 21, 3)).astype(np.float32)
        for controls in ((.35, 10., -9.), (-.2, -8., 12.), (0., 0., 0.)):
            reference = original.copy()
            for name, value in zip(('smile', 'eyebrow', 'lip_variation_three'), controls):
                reference = namespace['update_delta_new_'+name](None, value, reference)
            before = original.copy()
            np.testing.assert_array_equal(apply_controls(original, controls), reference)
            np.testing.assert_array_equal(original, before)

    def test_zero_exact(self):
        original = np.arange(63, dtype=np.float32).reshape(1, 21, 3)
        np.testing.assert_array_equal(original, apply_controls(original, [0, 0, 0]))

    def test_range_and_shape_rejected(self):
        with self.assertRaises(ValueError): apply_controls(np.zeros((1, 21, 3)), [2, 0, 0])
        with self.assertRaises(ValueError): apply_controls(np.zeros((1, 20, 3)), [0, 0, 0])
        with self.assertRaises(ValueError): apply_controls(np.zeros((1, 21, 3)), [0, float('nan'), 0])

    def test_response_solves_known_linear_target(self):
        zero = np.zeros(len(TOLERANCES)); zero[2] = .005
        source = zero.copy(); source[[0, 3, 2]] += [.03, .12, 0]
        response = np.zeros((len(zero), 3)); response[0, 0] = .03; response[3, 1] = .12; response[2, 2] = .012
        probes = np.stack([np.stack([zero-response[:, i], zero+response[:, i]]) for i in range(3)])
        controls, report = solve_response(zero, zero, source, probes, ridge=.001)
        np.testing.assert_allclose(controls, [.15, 5, 0], atol=.001)
        self.assertLess(report['selected']['predicted_residual'], .001)

    def test_zero_request_has_no_motion(self):
        z = np.zeros(len(TOLERANCES)); z[2] = .005
        probes = np.broadcast_to(z, (3, 2, len(z))).copy()
        controls, report = solve_response(z, z, z, probes)
        np.testing.assert_allclose(controls, 0, atol=1e-6)
        self.assertEqual(report['before_residual'], 0)

    def test_close_only_cannot_select_positive_lip_control(self):
        z = np.zeros(len(TOLERANCES)); z[2] = .03
        source = z.copy()
        response = np.zeros((len(z), 3)); response[2, 2] = -.01
        probes = np.stack([np.stack([z-response[:, i], z+response[:, i]]) for i in range(3)])
        free, _ = solve_response(z, z, source, probes)
        constrained, report = solve_response(z, z, source, probes, close_only=True)
        self.assertGreater(free[2], 0)
        self.assertLessEqual(constrained[2], 0)
        self.assertTrue(report['close_only'])


if __name__ == '__main__':
    unittest.main()
