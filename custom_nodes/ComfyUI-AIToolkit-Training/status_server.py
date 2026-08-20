from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from aiohttp import web
from server import PromptServer

from .aitk_integration import (
    AIToolkitClient,
    IntegrationError,
    choose_completed_lora,
    extract_download_status,
    format_duration,
    load_settings,
    publish_lora_idempotent,
    seconds_per_step,
)


JOB_REF_PREFIX = "comfy-generated-dataset:"
DEFAULT_STEPS = 3000


def _latest_generated_job(client: AIToolkitClient) -> dict[str, Any] | None:
    response = client.request("GET", "/api/jobs")
    jobs = response.get("jobs", []) if isinstance(response, dict) else []
    return next(
        (
            job
            for job in jobs
            if isinstance(job, dict) and str(job.get("job_ref", "")).startswith(JOB_REF_PREFIX)
        ),
        None,
    )


def _configured_steps(job: dict[str, Any]) -> int:
    if job.get("total_steps"):
        return int(job["total_steps"])
    try:
        config = json.loads(str(job.get("job_config") or "{}"))
        return int(config["config"]["process"][0]["train"]["steps"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return DEFAULT_STEPS


def _read_log_tail(settings: dict[str, Any], job_name: str, max_bytes: int = 65536) -> str:
    log_path = Path(settings["ai_toolkit_root"]) / "output" / job_name / "log.txt"
    if not log_path.is_file():
        return ""
    with log_path.open("rb") as handle:
        handle.seek(0, 2)
        handle.seek(max(0, handle.tell() - max_bytes))
        return handle.read().decode("utf-8", errors="replace")


def _build_status() -> dict[str, Any]:
    settings = load_settings()
    client = AIToolkitClient(settings, timeout=5.0)
    job = _latest_generated_job(client)
    if job is None:
        return {"found": False, "message": "No generated-dataset training job has been submitted yet."}

    status = str(job.get("status") or "unknown").lower()
    step = int(job.get("step") or 0)
    total_steps = _configured_steps(job)
    speed = str(job.get("speed_string") or "").strip()
    per_step = seconds_per_step(speed)
    eta_seconds = per_step * max(0, total_steps - step) if per_step else None
    info = str(job.get("info") or "").strip()
    download = extract_download_status(_read_log_tail(settings, str(job.get("name") or "")))
    lora_name = ""
    publish_note = ""

    # The live monitor completes the original one-click promise: once the durable
    # job finishes, its fixed-folder LoRA is safely and idempotently published.
    if status == "completed":
        source = choose_completed_lora(job, client.files(str(job["id"])))
        _, lora_name, copied = publish_lora_idempotent(settings, source)
        publish_note = "LoRA copied into ComfyUI." if copied else "LoRA is ready in ComfyUI."

    phase = "training" if step > 0 else ("preparing" if status in {"running", "queued"} else status)
    if download:
        phase = "downloading_model"
        info = f"Downloading Z-Image Base: {download['downloaded']} at {download['download_speed']}"

    return {
        "found": True,
        "job_id": str(job.get("id") or ""),
        "name": str(job.get("name") or ""),
        "status": status,
        "phase": phase,
        "step": step,
        "total_steps": total_steps,
        "progress_percent": round((step / total_steps) * 100, 2) if total_steps else 0,
        "info": info,
        "speed": speed,
        "eta_seconds": round(eta_seconds) if eta_seconds is not None else None,
        "eta": format_duration(eta_seconds),
        "download": download,
        "lora_name": lora_name,
        "publish_note": publish_note,
        "updated_at": str(job.get("updated_at") or ""),
    }


@PromptServer.instance.routes.post("/aitk/generated-dataset/status")
async def generated_dataset_status(_request: web.Request) -> web.Response:
    try:
        payload = await asyncio.to_thread(_build_status)
        return web.json_response(payload)
    except IntegrationError as exc:
        return web.json_response({"found": False, "error": str(exc)}, status=503)
    except Exception as exc:
        return web.json_response({"found": False, "error": f"Status monitor failed: {exc}"}, status=500)
