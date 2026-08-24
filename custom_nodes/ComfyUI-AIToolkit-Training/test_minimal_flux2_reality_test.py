from __future__ import annotations

import ast
import unittest
from pathlib import Path


class MinimalFlux2RealityTestTests(unittest.TestCase):
    def test_locked_experiment_settings(self):
        source = Path(__file__).with_name("minimal_flux2_reality_test.py").read_text(
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
            "A candid smartphone photo of m1tch_person walking down a busy city street.",
        )
        self.assertEqual(values["LORA_STRENGTH"], 0.50)
        self.assertEqual(values["STEPS"], 20)
        self.assertEqual((values["WIDTH"], values["HEIGHT"]), (896, 1344))


if __name__ == "__main__":
    unittest.main()
