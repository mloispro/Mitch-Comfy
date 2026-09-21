import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("speed_deploy", Path(__file__).with_name("deploy-production-speed.py"))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class AdmissionTests(unittest.TestCase):
    def state(self):
        return {"workers": {str(port): {"queue": {"queue_running": [], "queue_pending": []}}
                            for port in deploy.GPUS},
                "gpu_csv": f"{deploy.GPUS[8188]}, RTX3090, 1300, 0\n{deploy.GPUS[8189]}, RTX4070, 237, 0\n",
                "available_ram": 40 * 1024**3}

    def test_idle_admitted(self):
        deploy.require_idle(self.state())

    def test_pending_and_running_on_either_worker_refused(self):
        for port in deploy.GPUS:
            for queue in ("queue_running", "queue_pending"):
                with self.subTest(port=port, queue=queue):
                    state = self.state()
                    state["workers"][str(port)]["queue"][queue] = [[1, "user-prompt"]]
                    with self.assertRaises(RuntimeError):
                        deploy.require_idle(state)

    def test_busy_gpu_refused(self):
        state = self.state()
        state["gpu_csv"] = "uuid, RTX3090, 1300, 80\n"
        with self.assertRaises(RuntimeError):
            deploy.require_idle(state)

    def test_resident_gpu_work_refused(self):
        state = self.state()
        state["gpu_csv"] = "uuid, RTX3090, 20000, 0\n"
        with self.assertRaises(RuntimeError):
            deploy.require_idle(state)

    def test_low_ram_refused(self):
        state = self.state()
        state["available_ram"] = 8 * 1024**3
        with self.assertRaises(RuntimeError):
            deploy.require_idle(state)

    def test_missing_or_duplicate_gpu_rows_refused(self):
        for rows in ("", f"{deploy.GPUS[8188]}, RTX3090, 1300, 0\n" * 2):
            state = self.state()
            state["gpu_csv"] = rows
            with self.assertRaises(RuntimeError):
                deploy.require_idle(state)

    def test_inventory_detects_bytes_preserves_sources(self):
        original = deploy.ROOT
        with tempfile.TemporaryDirectory() as name:
            deploy.ROOT = Path(name)
            try:
                f = deploy.ROOT / "workflow.json"
                f.write_bytes(b'{"original":true}')
                before = deploy.inventory(deploy.ROOT)
                self.assertEqual(before["workflow.json"]["size"], 17)
                self.assertEqual(f.read_bytes(), b'{"original":true}')
                f.write_bytes(b'{"original":false}')
                self.assertNotEqual(before, deploy.inventory(deploy.ROOT))
            finally:
                deploy.ROOT = original


if __name__ == "__main__":
    unittest.main()
