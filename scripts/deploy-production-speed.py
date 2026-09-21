"""Audited, idle-only activation of the local Production Speed nodes.

No model management, generation, automatic reload retry or recipe changes.
Every operational attempt has an exclusive receipt directory. Snapshot is read
only apart from its own audit files. Reload preserves the live worker argv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
PYTHON = COMFY / ".venv/Scripts/python.exe"
AUDIT = ROOT / "work/production-speed-rollout"
GPUS = {8188: "GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17",
        8189: "GPU-de12eec8-4b3d-f2ae-791c-8423a86915fd"}


def get(port, route):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/{route}", timeout=8) as response:
        return json.load(response)


def write(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)


def process(port):
    listeners = {c.pid for c in psutil.net_connections(kind="tcp")
                 if c.laddr.port == port and c.status == psutil.CONN_LISTEN}
    if len(listeners) != 1 or None in listeners:
        raise RuntimeError(f"Ambiguous or missing listener on {port}: {listeners}")
    proc = psutil.Process(listeners.pop())
    command = proc.cmdline()
    stats = get(port, "system_stats")
    argv = stats["system"]["argv"]
    if command[1:] != argv:
        raise RuntimeError(f"Process/API argv mismatch on {port}")
    if Path(argv[0]).resolve() != (COMFY / "main.py").resolve():
        raise RuntimeError("Unexpected main.py")
    if argv[argv.index("--port") + 1] != str(port):
        raise RuntimeError("Unexpected port argument")
    if argv[argv.index("--cuda-device") + 1] != GPUS[port]:
        raise RuntimeError("Unexpected GPU UUID")
    if "--disable-auto-launch" not in argv:
        raise RuntimeError("Missing normal-worker launch flag")
    return {"pid": proc.pid, "parent_pid": proc.ppid(), "created": proc.create_time(), "exe": proc.exe(),
            "argv": argv, "stats": stats}


def snapshot():
    workers = {}
    for port in GPUS:
        p = process(port)
        p["queue"] = get(port, "queue")
        workers[str(port)] = p
    gpu = subprocess.check_output([
        "nvidia-smi", "--query-gpu=uuid,name,memory.used,utilization.gpu",
        "--format=csv,noheader,nounits"], text=True)
    return {"utc": time.time(), "workers": workers, "gpu_csv": gpu,
            "available_ram": psutil.virtual_memory().available}


def require_idle(state):
    for port, worker in state["workers"].items():
        q = worker["queue"]
        if q["queue_running"] or q["queue_pending"]:
            raise RuntimeError(f"Worker {port} has work; will not reload")
    seen = []
    for row in state["gpu_csv"].splitlines():
        values = [v.strip() for v in row.split(",")]
        if len(values) != 4 or int(values[3]) > 10:
            raise RuntimeError(f"GPU busy or unexpected GPU data: {row}")
        if int(values[2]) > 4096:
            raise RuntimeError(f"GPU has substantial resident work: {row}")
        seen.append(values[0])
    if sorted(seen) != sorted(GPUS.values()):
        raise RuntimeError("GPU response does not contain exactly both expected GPU UUIDs")
    if state["available_ram"] < 16 * 1024**3:
        raise RuntimeError("Insufficient host headroom")


def inventory(base):
    result = {}
    for p in sorted(base.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            h = hashlib.sha256()
            with p.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            result[p.relative_to(ROOT).as_posix()] = {"size": p.stat().st_size,
                                                       "sha256": h.hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["snapshot", "reload", "verify-preserved"])
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--port", type=int, choices=GPUS)
    parser.add_argument("--baseline")
    args = parser.parse_args()
    if not args.receipt.replace("-", "").replace("_", "").isalnum():
        raise RuntimeError("Use a simple unique receipt name")
    output = AUDIT / args.receipt
    output.mkdir(parents=True, exist_ok=False)
    if args.action == "verify-preserved":
        if not args.baseline:
            raise RuntimeError("Baseline receipt required")
        base = (AUDIT / args.baseline / "preserved-files.json").resolve()
        if not base.is_relative_to(AUDIT.resolve()):
            raise RuntimeError("Baseline outside audit directory")
        expected = json.loads(base.read_text(encoding="utf-8"))
        actual = {**inventory(ROOT / "workflows/production"),
                  **inventory(ROOT / "workflows/experiments")}
        differences = [k for k in set(expected) | set(actual) if expected.get(k) != actual.get(k)]
        write(output / "verification.json", {"passed": not differences, "differences": differences,
                                            "files": len(actual)})
        if differences:
            raise RuntimeError(f"Preserved files changed: {differences}")
        print(json.dumps({"passed": True, "files": len(actual), "receipt": str(output)}))
        return
    before = snapshot()
    write(output / "before.json", before)
    if args.action == "snapshot":
        write(output / "preserved-files.json", {
            **inventory(ROOT / "workflows/production"),
            **inventory(ROOT / "workflows/experiments")})
        print(json.dumps({"receipt": str(output), "state": before}))
        return
    if args.port is None:
        raise RuntimeError("Explicit --port required for reload")
    require_idle(before)
    for port in GPUS:
        write(output / f"history-{port}.json", get(port, "history"))
    old = before["workers"][str(args.port)]
    confirmation = snapshot()
    require_idle(confirmation)
    for port in GPUS:
        a, b = before["workers"][str(port)], confirmation["workers"][str(port)]
        if (a["pid"], a["created"], a["argv"]) != (b["pid"], b["created"], b["argv"]):
            raise RuntimeError("Worker identity changed before activation")
    write(output / "reload-intent.json", {"target": old, "confirmed": confirmation})
    proc = psutil.Process(old["pid"])
    if proc.create_time() != old["created"] or proc.cmdline()[1:] != old["argv"]:
        raise RuntimeError("Target changed after admission")
    reload_started = time.time()
    final_queue = get(args.port, "queue")
    if final_queue["queue_running"] or final_queue["queue_pending"]:
        raise RuntimeError("New work arrived after admission; do not reload")
    proc.terminate()
    proc.wait(timeout=10)
    if any(c.laddr.port == args.port and c.status == psutil.CONN_LISTEN
           for c in psutil.net_connections(kind="tcp")):
        raise RuntimeError("Port occupied after stop; do not duplicate worker")
    with (output / "stdout.log").open("xb") as out, (output / "stderr.log").open("xb") as err:
        launcher = subprocess.Popen([str(PYTHON), *old["argv"]], cwd=COMFY,
            stdout=out, stderr=err, stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    write(output / "started.json", {"launcher_pid": launcher.pid, "argv": old["argv"]})
    # One bounded readiness wait. A timeout never launches a replacement.
    end = time.monotonic() + 50
    ready = None
    while time.monotonic() < end:
        try:
            ready = process(args.port)
            break
        except (OSError, RuntimeError, ValueError, psutil.Error):
            time.sleep(1)
    if ready is None:
        raise RuntimeError(f"Readiness not confirmed; inspect existing process/logs at {output}")
    if ready["argv"] != old["argv"]:
        raise RuntimeError("Reloaded argv changed")
    ready_process = psutil.Process(ready["pid"])
    ancestry = [ready_process.pid, *[parent.pid for parent in ready_process.parents()]]
    if launcher.pid not in ancestry or ready["created"] < reload_started:
        raise RuntimeError("Ready listener is not the newly launched worker; do not claim activation")
    other_port = 8189 if args.port == 8188 else 8188
    other = process(other_port)
    original_other = before["workers"][str(other_port)]
    if (other["pid"], other["created"]) != (original_other["pid"], original_other["created"]):
        raise RuntimeError("Other worker changed; inspect")
    write(output / "result.json", {"passed": True, "worker": ready,
                                  "other_worker_unchanged": True})
    print(json.dumps({"passed": True, "port": args.port, "pid": ready["pid"],
                      "receipt": str(output)}))


if __name__ == "__main__":
    main()
