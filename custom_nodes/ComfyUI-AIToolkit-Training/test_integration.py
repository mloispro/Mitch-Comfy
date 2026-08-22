import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aitk_integration import (
    AIToolkitClient,
    IntegrationError,
    build_flux2_klein_job_config,
    build_zimage_job_config,
    choose_completed_lora,
    fingerprint_dataset,
    extract_download_status,
    format_duration,
    publish_lora,
    publish_lora_idempotent,
    load_settings,
    validate_dataset,
    validate_generated_dataset,
    seconds_per_step,
)


class IntegrationTests(unittest.TestCase):
    def test_live_status_helpers_parse_speed_eta_and_download(self):
        self.assertEqual(seconds_per_step("2.5 sec/iter"), 2.5)
        self.assertAlmostEqual(seconds_per_step("4 iter/sec"), 0.25)
        self.assertEqual(format_duration(3665), "1h 1m")
        self.assertEqual(
            extract_download_status("Downloading bytes: ####4 | 5.45GB, 16.6MB/s"),
            {"downloaded": "5.45GB", "download_speed": "16.6MB/s"},
        )

    def test_local_settings_point_to_installed_components(self):
        settings = load_settings(Path(__file__).with_name("settings.json"))
        self.assertTrue((Path(settings["ai_toolkit_root"]) / "run.py").is_file())
        self.assertTrue(Path(settings["ai_toolkit_python"]).is_file())

    def test_dataset_pairs_are_preserved_and_trigger_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one.png").write_bytes(b"not-decoded-by-validator")
            (folder / "one.txt").write_text("portrait of token", encoding="utf-8")
            report = validate_dataset(str(folder), "token")
            self.assertEqual(report.image_count, 1)
            self.assertEqual(report.captions_with_trigger, 1)
            self.assertEqual((folder / "one.txt").read_text(encoding="utf-8"), "portrait of token")

    def test_dataset_rejects_missing_caption(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one.jpg").write_bytes(b"x")
            with self.assertRaisesRegex(IntegrationError, "missing captions"):
                validate_dataset(str(folder), "token")

    def test_generated_dataset_infers_locked_trigger_and_fingerprint_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one.png").write_bytes(b"image")
            caption = folder / "one.txt"
            caption.write_text("zimg_person, portrait", encoding="utf-8")
            settings = {"generated_dataset_path": str(folder), "generated_dataset_trigger": "zimg_person"}
            report = validate_generated_dataset(settings)
            first = fingerprint_dataset(report)
            self.assertEqual(report.trigger_word, "zimg_person")
            caption.write_text("zimg_person, smiling portrait", encoding="utf-8")
            second = fingerprint_dataset(validate_generated_dataset(settings))
            self.assertNotEqual(first, second)

    def test_generated_dataset_rejects_inconsistent_trigger(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for stem, trigger in (("one", "zimg_person"), ("two", "other_person")):
                (folder / f"{stem}.png").write_bytes(b"image")
                (folder / f"{stem}.txt").write_text(f"{trigger}, portrait", encoding="utf-8")
            settings = {"generated_dataset_path": str(folder), "generated_dataset_trigger": "zimg_person"}
            with self.assertRaisesRegex(IntegrationError, "do not agree"):
                validate_generated_dataset(settings)

    def test_base_config_matches_current_ai_toolkit_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one.webp").write_bytes(b"x")
            (folder / "one.txt").write_text("caption", encoding="utf-8")
            report = validate_dataset(str(folder), "token")
            config = build_zimage_job_config(
                {
                    "z_image_model": "Tongyi-MAI/Z-Image-Turbo",
                    "z_image_arch": "zimage",
                    "z_image_assistant_lora": (
                        "ostris/zimage_turbo_training_adapter/"
                        "zimage_turbo_training_adapter_v2.safetensors"
                    ),
                },
                job_name="unit-test", dataset=report, trigger_word="token", steps=10,
                learning_rate=0.0001, rank=16, save_every=5,
            )
            process = config["config"]["process"][0]
            self.assertEqual(process["type"], "diffusion_trainer")
            self.assertEqual(process["model"]["arch"], "zimage")
            self.assertEqual(
                process["model"]["assistant_lora_path"],
                "ostris/zimage_turbo_training_adapter/zimage_turbo_training_adapter_v2.safetensors",
            )
            self.assertEqual(process["datasets"][0]["caption_ext"], "txt")

    def test_flux2_klein_config_is_small_local_and_checkpointed(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one.jpg").write_bytes(b"x")
            (folder / "one.txt").write_text("[trigger], portrait", encoding="utf-8")
            report = validate_dataset(str(folder), "m1tch_person")
            config = build_flux2_klein_job_config(
                job_name="m1tch-klein-v1",
                dataset=report,
                trigger_word="m1tch_person",
                steps=1500,
                learning_rate=0.00008,
                rank=16,
                save_every=250,
                model_size="9b",
            )
            process = config["config"]["process"][0]
            self.assertEqual(process["model"]["arch"], "flux2_klein_9b")
            self.assertEqual(
                process["model"]["name_or_path"],
                "black-forest-labs/FLUX.2-klein-base-9B",
            )
            self.assertEqual(process["network"]["linear"], 16)
            self.assertEqual(process["save"]["max_step_saves_to_keep"], 6)
            self.assertTrue(process["train"]["disable_sampling"])
            self.assertFalse(process["datasets"][0]["flip_x"])

    def test_flux2_klein_config_supports_public_4b_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one.jpg").write_bytes(b"x")
            (folder / "one.txt").write_text("[trigger], portrait", encoding="utf-8")
            report = validate_dataset(str(folder), "m1tch_person")
            config = build_flux2_klein_job_config(
                job_name="m1tch-klein-4b-v1",
                dataset=report,
                trigger_word="m1tch_person",
                steps=10,
                learning_rate=0.00008,
                rank=16,
                save_every=5,
                model_size="4b",
            )
            process = config["config"]["process"][0]
            self.assertEqual(process["model"]["arch"], "flux2_klein_4b")
            self.assertEqual(
                process["model"]["name_or_path"],
                "black-forest-labs/FLUX.2-klein-base-4B",
            )

    def test_submit_uses_job_and_queue_api(self):
        settings = {"ai_toolkit_api_url": "http://127.0.0.1:8675"}
        client = AIToolkitClient(settings)
        calls = []

        def fake_request(method, endpoint, payload=None):
            calls.append((method, endpoint, payload))
            if method == "POST":
                return {"id": "abc"}
            if endpoint.startswith("/api/jobs?id="):
                return {"id": "abc", "status": "queued"}
            return {}

        with patch.object(client, "request", side_effect=fake_request):
            job = client.submit("unit-test", "0", {"job": "extension"}, job_ref="dataset:123")
        self.assertEqual(job["id"], "abc")
        self.assertEqual(calls[0][2]["job_ref"], "dataset:123")
        self.assertEqual([call[:2] for call in calls], [
            ("POST", "/api/jobs"),
            ("GET", "/api/jobs/abc/start"),
            ("GET", "/api/queue/0/start"),
            ("GET", "/api/jobs?id=abc"),
        ])

    def test_publish_is_atomic_and_returns_comfy_name(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.safetensors"
            source.write_bytes(b"weights")
            lora_root = root / "loras"
            destination, relative = publish_lora(
                {"comfy_lora_path": str(lora_root), "publish_subdirectory": "aitk"}, source
            )
            self.assertEqual(destination.read_bytes(), b"weights")
            self.assertEqual(relative, "aitk/source.safetensors")

    def test_idempotent_publish_accepts_identical_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.safetensors"
            source.write_bytes(b"weights")
            settings = {"comfy_lora_path": str(root / "loras"), "publish_subdirectory": "aitk"}
            _, relative, first_copy = publish_lora_idempotent(settings, source)
            _, second_relative, second_copy = publish_lora_idempotent(settings, source)
            self.assertTrue(first_copy)
            self.assertFalse(second_copy)
            self.assertEqual(relative, second_relative)


if __name__ == "__main__":
    unittest.main()
