import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from flux2_klein9b_visual_preset_support import (
    augment_visual_preset_report,
    verify_asset_sha256,
)


class Klein9BVisualPresetSupportTests(unittest.TestCase):
    def test_verify_asset_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asset.bin"
            path.write_bytes(b"locked preset asset")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(verify_asset_sha256(path, digest, "test asset"), path)
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                verify_asset_sha256(path, "0" * 64, "different cache key")

    def test_report_augmentation_preserves_engine_purpose(self):
        with tempfile.TemporaryDirectory() as directory:
            run_directory = Path(directory) / "run-1"
            run_directory.mkdir()
            engine_report = {"purpose": "frozen_engine", "seconds": 12.5}
            (run_directory / "report.json").write_text(
                json.dumps(engine_report), encoding="utf-8"
            )
            response = {
                "result": ("photo", "prompt", "run-1", json.dumps(engine_report))
            }
            updated = augment_visual_preset_report(
                response,
                output_directory=directory,
                shell_name="visual_shell",
                preset={"label": "Preset A", "key": "preset-a"},
            )
            report = json.loads(updated["result"][-1])
            self.assertEqual(report["purpose"], "frozen_engine")
            self.assertEqual(report["visual_preset_shell"]["name"], "visual_shell")
            self.assertEqual(report["visual_preset_shell"]["key"], "preset-a")
            self.assertEqual(
                json.loads((run_directory / "report.json").read_text(encoding="utf-8")),
                report,
            )


if __name__ == "__main__":
    unittest.main()
