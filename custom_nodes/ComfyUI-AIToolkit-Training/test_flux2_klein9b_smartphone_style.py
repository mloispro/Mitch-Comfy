from __future__ import annotations

import hashlib
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


if "folder_paths" not in sys.modules:
    sys.modules["folder_paths"] = types.SimpleNamespace(get_full_path=lambda *_args: None)

style = importlib.import_module("flux2_klein9b_smartphone_style")


class SmartphoneStyleContractTests(unittest.TestCase):
    def test_trigger_is_prepended_exactly_once(self):
        prompt = "A realistic phone photograph."
        expected = "casual snapshot. A realistic phone photograph."
        self.assertEqual(style.apply_smartphone_style_trigger(prompt), expected)
        self.assertEqual(style.apply_smartphone_style_trigger(expected), expected)

    def test_empty_prompt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            style.apply_smartphone_style_trigger("   ")

    def test_locked_contract_matches_accepted_experiment(self):
        report = style.smartphone_style_report()
        self.assertEqual(report["strength"], 0.25)
        self.assertEqual(report["trigger"], "casual snapshot")
        self.assertEqual(report["base_model"], "flux2_klein_9b")
        self.assertEqual(report["civitai_version_id"], 2916530)
        self.assertEqual(
            report["sha256"],
            "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90",
        )

    def test_verifier_rejects_changed_file(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / "style.safetensors"
            path.write_bytes(b"not-the-accepted-model")
            original = style.folder_paths.get_full_path
            style.folder_paths.get_full_path = lambda *_args: str(path)
            try:
                with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                    style.verify_smartphone_style_lora()
            finally:
                style.folder_paths.get_full_path = original
                style._VERIFIED_SIGNATURES.clear()


if __name__ == "__main__":
    unittest.main()
