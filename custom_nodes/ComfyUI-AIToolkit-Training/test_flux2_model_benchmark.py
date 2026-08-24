from __future__ import annotations

import ast
import unittest
from pathlib import Path


class Flux2ModelBenchmarkTests(unittest.TestCase):
    def test_benchmark_is_locked_to_comparable_native_settings(self):
        source = Path(__file__).with_name("flux2_model_benchmark.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass

        self.assertEqual(
            values["PROMPT"],
            "Create a new candid smartphone photo of the same adult man shown in Pictures 1 through 4 "
            "walking down a busy city street. Use the pictures only to preserve his identity; do not copy "
            "their poses, clothing, framing, or backgrounds.",
        )
        self.assertEqual((values["WIDTH"], values["HEIGHT"]), (896, 1344))
        self.assertEqual(values["SEED"], 8675311)
        self.assertEqual(values["REFERENCE_PIXELS"], 640 * 640)
        self.assertEqual(values["KLEIN_9B_STEPS"], 4)
        self.assertEqual(values["DEV_STEPS"], 20)
        self.assertEqual(values["DEV_GUIDANCE"], 4.0)

    def test_benchmark_excludes_identity_lora_and_post_processing(self):
        source = Path(__file__).with_name("flux2_model_benchmark.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("LoraLoader", source)
        self.assertIn('"identity_lora": None', source)
        self.assertIn('"refiner"', source)
        self.assertIn('"background post-processing"', source)


if __name__ == "__main__":
    unittest.main()
