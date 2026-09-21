"""One final four-connection range diagnostic, using the owned-download watchdog.

Transfers four disjoint 16 MiB ranges into discarded memory. This script does
not install models or change the selected download transport.
"""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import psutil
import requests
from huggingface_hub import get_hf_file_metadata, hf_hub_url

WATCHDOG_SCRIPT = Path(__file__).with_name("probe-beautygrpo-solo-http.py")
spec = importlib.util.spec_from_file_location("owned_download_probe", WATCHDOG_SCRIPT)
guarded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guarded)


def main():
    target = guarded.owned()
    if target.status() != psutil.STATUS_RUNNING:
        raise RuntimeError("Owned download is not running")
    metadata = get_hf_file_metadata(hf_hub_url(
        "black-forest-labs/FLUX.1-Kontext-dev", "flux1-kontext-dev.safetensors",
        revision=guarded.REVISION), token=None)
    if metadata.size != guarded.EXPECTED_SIZE or metadata.commit_hash != guarded.REVISION:
        raise RuntimeError("Pinned metadata mismatch")
    ranges = []
    for index in range(4):
        first = index * guarded.RANGE_SIZE
        last = first + guarded.RANGE_SIZE - 1
        ranges.append({"index": index, "first": first, "last": last,
                       "bytes_discarded": 0, "range_verified": False})
    stop = threading.Event()
    lock = threading.Lock()
    guard = subprocess.Popen([sys.executable, "-B", str(WATCHDOG_SCRIPT), "--watchdog"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, creationflags=(subprocess.CREATE_NO_WINDOW |
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB))
    if json.loads(guard.stdout.readline()).get("watchdog_ready") is not True:
        raise RuntimeError("Independent watchdog not ready")
    target = guarded.owned()
    if target.status() != psutil.STATUS_RUNNING:
        raise RuntimeError("Owned download changed state")
    start = time.monotonic()
    guard.stdin.write(json.dumps({"resume_by": start + 19}) + "\n")
    guard.stdin.flush()
    if json.loads(guard.stdout.readline()).get("watchdog_armed") is not True:
        raise RuntimeError("Independent watchdog not armed")
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def receive(index):
        item = ranges[index]
        response = None
        session = requests.Session()
        began = time.monotonic()
        try:
            response = session.get(metadata.location, stream=True,
                allow_redirects=False, timeout=(3.0, 1.0), headers={
                    "Range": f"bytes={item['first']}-{item['last']}",
                    "Accept-Encoding": "identity"})
            expected = f"bytes {item['first']}-{item['last']}/{guarded.EXPECTED_SIZE}"
            with lock:
                item["status"] = response.status_code
                item["header_seconds"] = round(time.monotonic()-began, 4)
                item["range_verified"] = (response.status_code == 206 and
                    response.headers.get("Content-Range") == expected)
            if not item["range_verified"]:
                raise RuntimeError("Range response mismatch")
            while (not stop.is_set() and time.monotonic()-start < 16.0 and
                   item["bytes_discarded"] < guarded.RANGE_SIZE):
                chunk = response.raw.read1(min(65536,
                    guarded.RANGE_SIZE-item["bytes_discarded"]), decode_content=False)
                if not chunk or stop.is_set():
                    break
                with lock:
                    item["bytes_discarded"] += len(chunk)
            with lock:
                item["complete"] = item["bytes_discarded"] == guarded.RANGE_SIZE
                item["seconds"] = round(time.monotonic()-began, 4)
        except Exception as exc:
            with lock:
                item["error_type"] = type(exc).__name__
        finally:
            if response is not None:
                response.close()
            session.close()

    paused = False
    report = {"connections": 4, "model_files_written": False}
    try:
        target = guarded.owned()
        target.suspend()
        paused = True
        if target.status() != psutil.STATUS_STOPPED:
            raise RuntimeError("Suspension not verified")
        report["suspension_verified"] = True
        probe_start = time.monotonic()
        futures = [pool.submit(receive, index) for index in range(4)]
        concurrent.futures.wait(futures, timeout=max(0, 17.0-(time.monotonic()-start)))
        elapsed = time.monotonic()-probe_start
        stop.set()
        with lock:
            captured = [dict(item) for item in ranges]
        total = sum(item["bytes_discarded"] for item in captured)
        report.update(ranges=captured, aggregate_bytes_discarded=total,
            all_ranges_verified=all(item["range_verified"] for item in captured),
            all_complete=all(item.get("complete", False) for item in captured),
            seconds=round(elapsed, 4),
            aggregate_mib_per_second=round(total/1024**2/max(elapsed, 1e-6), 4))
    except Exception as exc:
        report["error_type"] = type(exc).__name__
    finally:
        stop.set()
        if paused:
            target = guarded.owned()
            report["remained_suspended_during_probe"] = target.status() == psutil.STATUS_STOPPED
            if report["remained_suspended_during_probe"]:
                target.resume()
        report["resumed_verified"] = guarded.owned().status() == psutil.STATUS_RUNNING
        report["pause_window_seconds"] = round(time.monotonic()-start, 4)
        guarded.emit(report)
        pool.shutdown(wait=False, cancel_futures=True)
        guard.stdin.close()
        for line in guard.stdout:
            guarded.emit({"watchdog": json.loads(line)})
        guard.wait(timeout=5)
        guarded.emit({"final_resume_verified": guarded.owned().status() == psutil.STATUS_RUNNING,
                      "watchdog_exit": guard.returncode})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        guarded.emit({"safe_error_type": type(exc).__name__})
        raise SystemExit(1)
