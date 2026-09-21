"""Bounded, in-memory HTTP range test with an independent download resumer.

Only the explicitly pinned CPU download process can be paused. No model files
are written and no authentication headers or signed URLs are printed.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import psutil

TARGET_PID = 51236
TARGET_PARENT = 53644
TARGET_CREATED = 1788793510.559382
SCRIPT_ARG = "scripts/download-upgrade-beautygrpo.py"
REVISION = "24e9dedc4ef646698dc8eb4e18ae2cec3c9fea0d"
EXPECTED_SIZE = 23802947360
RANGE_SIZE = 16 * 1024 * 1024


def emit(value):
    print(json.dumps(value), flush=True)


def owned():
    process = psutil.Process(TARGET_PID)
    command = process.cmdline()
    if abs(process.create_time() - TARGET_CREATED) > 0.01:
        raise RuntimeError("Download creation time changed")
    if process.ppid() != TARGET_PARENT:
        raise RuntimeError("Download parent changed")
    if len(command) != 3 or command[1:] != [SCRIPT_ARG, "--download"]:
        raise RuntimeError("Download command no longer matches")
    return process


def watchdog():
    owned()
    emit({"watchdog_ready": True, "pid": os.getpid()})
    arm = json.loads(sys.stdin.readline())
    deadline = arm["resume_by"]
    emit({"watchdog_armed": True})
    time.sleep(max(0, deadline - time.monotonic()))
    process = owned()
    resumed = False
    if process.status() == psutil.STATUS_STOPPED:
        process.resume()
        resumed = True
    emit({"watchdog_finished": True, "resumed_by_watchdog": resumed,
          "target_status": process.status()})


def probe():
    import requests
    from huggingface_hub import get_hf_file_metadata, hf_hub_url

    process = owned()
    if process.status() != psutil.STATUS_RUNNING:
        raise RuntimeError("Download was not running before the probe")
    # Resolve and authenticate while the download is still running.
    metadata = get_hf_file_metadata(hf_hub_url(
        "black-forest-labs/FLUX.1-Kontext-dev", "flux1-kontext-dev.safetensors",
        revision=REVISION), token=None)
    if metadata.size != EXPECTED_SIZE or metadata.commit_hash != REVISION:
        raise RuntimeError("Pinned model metadata did not match")
    session = requests.Session()
    request = requests.Request("GET", metadata.location, headers={
        "Range": f"bytes=0-{RANGE_SIZE - 1}", "Accept-Encoding": "identity"})
    prepared = session.prepare_request(request)
    # If job breakaway is unavailable, Popen fails before any suspension.
    flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
             | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    guard = subprocess.Popen([sys.executable, "-B", __file__, "--watchdog"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, creationflags=flags)
    if json.loads(guard.stdout.readline()).get("watchdog_ready") is not True:
        raise RuntimeError("Independent watchdog was not ready")
    process = owned()
    if process.status() != psutil.STATUS_RUNNING:
        raise RuntimeError("Download changed state before suspension")
    start = time.monotonic()
    guard.stdin.write(json.dumps({"resume_by": start + 19.0}) + "\n")
    guard.stdin.flush()
    if json.loads(guard.stdout.readline()).get("watchdog_armed") is not True:
        raise RuntimeError("Independent watchdog was not armed")
    report = {"target_pid": TARGET_PID, "range_verified": False,
              "bytes_discarded": 0, "files_written": False}
    response = None
    paused = False
    request_start = None
    try:
        process = owned()
        process.suspend()
        paused = True
        if process.status() != psutil.STATUS_STOPPED:
            raise RuntimeError("Target suspension could not be verified")
        report["suspension_verified"] = True
        request_start = time.monotonic()
        # A one-read-at-a-time body loop plus a 1-second socket timeout bounds
        # body reads. The separate watchdog resumes the download at 19 seconds.
        response = session.send(prepared, stream=True, allow_redirects=False,
                                timeout=(3.0, 1.0))
        headers_at = time.monotonic()
        expected_range = f"bytes 0-{RANGE_SIZE - 1}/{EXPECTED_SIZE}"
        report.update(status=response.status_code,
            header_seconds=round(headers_at-request_start, 4),
            range_verified=(response.status_code == 206 and
                            response.headers.get("Content-Range") == expected_range))
        if not report["range_verified"]:
            raise RuntimeError("HTTP Range was not honored exactly")
        while report["bytes_discarded"] < RANGE_SIZE and time.monotonic()-start < 17:
            chunk = response.raw.read1(min(65536, RANGE_SIZE-report["bytes_discarded"]),
                                       decode_content=False)
            if not chunk:
                break
            report["bytes_discarded"] += len(chunk)
        elapsed = time.monotonic()-request_start
        report.update(total_seconds=round(elapsed, 4),
            complete=(report["bytes_discarded"] == RANGE_SIZE),
            mib_per_second=round(report["bytes_discarded"]/1024**2/max(elapsed, 1e-6), 4))
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        if request_start is not None:
            elapsed = time.monotonic()-request_start
            report.update(total_seconds=round(elapsed, 4), complete=False,
                mib_per_second=round(report["bytes_discarded"]/1024**2/max(elapsed, 1e-6), 4))
    finally:
        if paused:
            target = owned()
            report["remained_suspended_during_probe"] = target.status() == psutil.STATUS_STOPPED
            if report["remained_suspended_during_probe"]:
                target.resume()
        if response is not None:
            response.close()
        session.close()
        report["resumed_verified"] = owned().status() == psutil.STATUS_RUNNING
        report["pause_window_seconds"] = round(time.monotonic()-start, 4)
        emit(report)
        guard.stdin.close()
        for line in guard.stdout:
            emit({"watchdog": json.loads(line)})
        guard.wait(timeout=5)
        emit({"final_resume_verified": owned().status() == psutil.STATUS_RUNNING,
              "watchdog_exit": guard.returncode})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchdog", action="store_true")
    args = parser.parse_args()
    try:
        watchdog() if args.watchdog else probe()
    except Exception as exc:
        emit({"safe_error_type": type(exc).__name__})
        raise SystemExit(1)
