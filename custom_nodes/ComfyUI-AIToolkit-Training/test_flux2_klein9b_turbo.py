from __future__ import annotations

import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


if "folder_paths" not in sys.modules:
    sys.modules["folder_paths"] = types.SimpleNamespace(get_full_path=lambda *_args: None)

turbo = importlib.import_module("flux2_klein9b_turbo")


class TurboModeContractTests(unittest.TestCase):
    def test_enabled_mode_uses_tested_regime(self):
        self.assertEqual(turbo.sampling_settings(True), (8, 1.0))

    def test_disabled_mode_preserves_quality_regime(self):
        self.assertEqual(turbo.sampling_settings(False), (50, 4.0))
        self.assertEqual(turbo.sampling_settings(False, 42, 3.5), (42, 3.5))

    def test_report_is_explicit_and_reversible(self):
        enabled = turbo.turbo_mode_report(True, "C:/turbo.safetensors", 1)
        disabled = turbo.turbo_mode_report(False, None, None)
        self.assertTrue(enabled["enabled"])
        self.assertEqual(enabled["steps"], 8)
        self.assertEqual(enabled["guidance"], 1.0)
        self.assertEqual(enabled["load_order"], 1)
        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["steps"], 50)
        self.assertEqual(disabled["guidance"], 4.0)
        self.assertIsNone(disabled["path"])
        self.assertEqual(disabled["strength"], 0.0)

    def test_locked_file_contract_matches_verified_download(self):
        self.assertEqual(turbo.TURBO_LORA_BYTES, 1_386_477_008)
        self.assertEqual(
            turbo.TURBO_LORA_SHA256,
            "A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600",
        )
        self.assertIn("rank_256_bf16_standard", turbo.TURBO_LORA_NAME)

    def test_verifier_rejects_changed_file_before_hashing(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / "turbo.safetensors"
            path.write_bytes(b"not-the-locked-turbo-lora")
            original = turbo.folder_paths.get_full_path
            turbo.folder_paths.get_full_path = lambda *_args: str(path)
            try:
                with self.assertRaisesRegex(RuntimeError, "byte-size mismatch"):
                    turbo.verify_turbo_lora()
            finally:
                turbo.folder_paths.get_full_path = original
                turbo._VERIFIED_SIGNATURES.clear()


if __name__ == "__main__":
    unittest.main()
