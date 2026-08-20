from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
TERMINAL_STATUSES = {"completed", "error", "stopped"}
SAFE_JOB_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class IntegrationError(RuntimeError):
    pass


def load_settings(path: Path | None = None) -> dict[str, Any]:
    settings_path = path or Path(__file__).with_name("settings.json")
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrationError(f"Could not read {settings_path}: {exc}") from exc

    required = {
        "ai_toolkit_root",
        "ai_toolkit_python",
        "ai_toolkit_api_url",
        "z_image_model",
        "z_image_arch",
        "generated_dataset_path",
        "generated_dataset_trigger",
        "comfy_lora_path",
    }
    missing = sorted(required.difference(settings))
    if missing:
        raise IntegrationError(f"Missing settings: {', '.join(missing)}")

    toolkit_root = Path(settings["ai_toolkit_root"])
    toolkit_python = Path(settings["ai_toolkit_python"])
    comfy_lora_path = Path(settings["comfy_lora_path"])
    if not (toolkit_root / "run.py").is_file():
        raise IntegrationError(f"AI-Toolkit run.py was not found under {toolkit_root}")
    if not toolkit_python.is_file():
        raise IntegrationError(f"AI-Toolkit Python was not found: {toolkit_python}")
    if not comfy_lora_path.is_dir():
        raise IntegrationError(f"ComfyUI LoRA folder was not found: {comfy_lora_path}")
    parsed_api = urllib.parse.urlparse(str(settings["ai_toolkit_api_url"]))
    if parsed_api.scheme not in {"http", "https"} or not parsed_api.netloc:
        raise IntegrationError("ai_toolkit_api_url must be an http(s) URL")
    return settings


@dataclass(frozen=True)
class DatasetReport:
    folder: Path
    image_count: int
    caption_count: int
    captions_with_trigger: int
    trigger_word: str = ""

    def summary(self) -> str:
        return (
            f"Validated {self.image_count} image/.txt pairs in {self.folder}; "
            f"{self.captions_with_trigger} captions already contain the trigger word. "
            "Caption files were not modified; AI-Toolkit injects the job trigger when absent."
        )


def validate_dataset(dataset_path: str, trigger_word: str) -> DatasetReport:
    folder = Path(dataset_path).expanduser().resolve()
    if not folder.is_dir():
        raise IntegrationError(f"Dataset folder does not exist: {folder}")
    if not trigger_word.strip():
        raise IntegrationError("trigger_word must not be blank")

    images = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    captions = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".txt")
    if not images:
        raise IntegrationError(f"No supported images found in {folder}")

    image_stems = {p.stem.casefold() for p in images}
    caption_by_stem = {p.stem.casefold(): p for p in captions}
    missing = [p.name for p in images if p.stem.casefold() not in caption_by_stem]
    orphaned = [p.name for p in captions if p.stem.casefold() not in image_stems]
    empty = []
    with_trigger = 0
    trigger_folded = trigger_word.strip().casefold()
    for image in images:
        caption = caption_by_stem.get(image.stem.casefold())
        if caption is None:
            continue
        text = caption.read_text(encoding="utf-8-sig").strip()
        if not text:
            empty.append(caption.name)
        if trigger_folded in text.casefold():
            with_trigger += 1

    problems = []
    if missing:
        problems.append(f"missing captions: {', '.join(missing[:10])}")
    if orphaned:
        problems.append(f"orphan captions: {', '.join(orphaned[:10])}")
    if empty:
        problems.append(f"empty captions: {', '.join(empty[:10])}")
    if problems:
        raise IntegrationError("Dataset pairing validation failed (" + "; ".join(problems) + ")")

    return DatasetReport(folder, len(images), len(captions), with_trigger)


def validate_generated_dataset(settings: dict[str, Any]) -> DatasetReport:
    """Validate only the configured generated dataset and infer its shared trigger."""
    folder = Path(settings["generated_dataset_path"]).expanduser().resolve()
    expected_trigger = str(settings["generated_dataset_trigger"]).strip()
    if not expected_trigger:
        raise IntegrationError("generated_dataset_trigger must not be blank")

    report = validate_dataset(str(folder), expected_trigger)
    captions = sorted(folder.glob("*.txt"), key=lambda path: path.name.casefold())
    inferred: dict[str, list[str]] = {}
    for caption in captions:
        text = caption.read_text(encoding="utf-8-sig").strip()
        leading = re.split(r"[,\s]", text, maxsplit=1)[0].strip()
        if not leading:
            raise IntegrationError(f"Could not infer a trigger from {caption.name}")
        inferred.setdefault(leading.casefold(), []).append(caption.name)

    if len(inferred) != 1:
        description = ", ".join(f"{trigger} ({len(files)})" for trigger, files in sorted(inferred.items()))
        raise IntegrationError(f"Dataset captions do not agree on one leading trigger: {description}")
    inferred_trigger = next(iter(inferred))
    if inferred_trigger != expected_trigger.casefold():
        raise IntegrationError(
            f"Dataset trigger is {inferred_trigger!r}; expected {expected_trigger!r}. Refusing to guess."
        )
    if report.captions_with_trigger != report.caption_count:
        raise IntegrationError(
            f"Expected {expected_trigger!r} in every caption, found it in "
            f"{report.captions_with_trigger} of {report.caption_count}"
        )
    return DatasetReport(
        report.folder,
        report.image_count,
        report.caption_count,
        report.captions_with_trigger,
        expected_trigger,
    )


def fingerprint_dataset(dataset: DatasetReport) -> str:
    """Hash names and contents of every paired image and caption deterministically."""
    digest = hashlib.sha256()
    files = sorted(
        (
            path
            for path in dataset.folder.iterdir()
            if path.is_file() and (path.suffix.lower() in IMAGE_EXTENSIONS or path.suffix.lower() == ".txt")
        ),
        key=lambda path: path.name.casefold(),
    )
    for path in files:
        digest.update(path.name.casefold().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def seconds_per_step(speed_string: str) -> float | None:
    """Convert AI-Toolkit's human speed string into seconds per training step."""
    text = str(speed_string or "").strip().lower()
    match = re.search(r"([\d.]+)\s*(?:s|sec|secs|second|seconds)\s*/\s*(?:it|iter|step)", text)
    if match:
        value = float(match.group(1))
        return value if value > 0 else None
    match = re.search(r"([\d.]+)\s*(?:it|iter|step)s?\s*/\s*(?:s|sec|second)", text)
    if match:
        value = float(match.group(1))
        return (1.0 / value) if value > 0 else None
    return None


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return ""
    total = int(round(seconds))
    days, total = divmod(total, 86400)
    hours, total = divmod(total, 3600)
    minutes, secs = divmod(total, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def extract_download_status(log_tail: str) -> dict[str, str]:
    """Extract the latest compact model-download status from an AI-Toolkit log tail."""
    matches = re.findall(
        r"Downloading bytes:.*?\|\s*([\d.]+\s*[KMGT]?B)\s*,\s*([\d.]+\s*[KMGT]?B/s)",
        str(log_tail or ""),
        flags=re.IGNORECASE,
    )
    if not matches:
        return {}
    downloaded, speed = matches[-1]
    return {"downloaded": downloaded.replace(" ", ""), "download_speed": speed.replace(" ", "")}


class AIToolkitClient:
    def __init__(self, settings: dict[str, Any], timeout: float = 15.0):
        self.base_url = str(settings["ai_toolkit_api_url"]).rstrip("/")
        auth_env = str(settings.get("ai_toolkit_auth_env", "AI_TOOLKIT_AUTH"))
        self.token = os.environ.get(auth_env, "").strip()
        self.timeout = timeout

    def request(self, method: str, endpoint: str, payload: Any | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise IntegrationError(f"AI-Toolkit API returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise IntegrationError(
                f"AI-Toolkit UI is unavailable at {self.base_url}. "
                "Start C:\\projects\\AI-Tools\\ai-toolkit\\Start-AI-Toolkit.bat first. "
                f"Original error: {exc}"
            ) from exc

    def submit(
        self,
        name: str,
        gpu_ids: str,
        job_config: dict[str, Any],
        job_ref: str | None = None,
    ) -> dict[str, Any]:
        payload = {"name": name, "gpu_ids": gpu_ids, "job_config": job_config, "job_type": "train"}
        if job_ref:
            payload["job_ref"] = job_ref
        created = self.request(
            "POST",
            "/api/jobs",
            payload,
        )
        job_id = created.get("id") if isinstance(created, dict) else None
        if not job_id:
            raise IntegrationError(f"AI-Toolkit did not return a job id: {created!r}")
        quoted_id = urllib.parse.quote(str(job_id), safe="")
        quoted_gpu = urllib.parse.quote(gpu_ids, safe="")
        self.request("GET", f"/api/jobs/{quoted_id}/start")
        self.request("GET", f"/api/queue/{quoted_gpu}/start")
        return self.status(str(job_id))

    def status(self, job_id: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(job_id.strip(), safe="")
        job = self.request("GET", f"/api/jobs?id={encoded}")
        if not isinstance(job, dict) or not job.get("id"):
            raise IntegrationError(f"AI-Toolkit job not found: {job_id}")
        return job

    def find_by_ref(self, job_ref: str) -> dict[str, Any] | None:
        encoded = urllib.parse.quote(job_ref.strip(), safe="")
        job = self.request("GET", f"/api/jobs?job_ref={encoded}")
        if job is None:
            return None
        if not isinstance(job, dict):
            raise IntegrationError(f"AI-Toolkit returned an invalid job lookup result: {job!r}")
        return job if job.get("id") else None

    def files(self, job_id: str) -> list[dict[str, Any]]:
        encoded = urllib.parse.quote(job_id.strip(), safe="")
        response = self.request("GET", f"/api/jobs/{encoded}/files")
        files = response.get("files", []) if isinstance(response, dict) else []
        return [item for item in files if isinstance(item, dict)]

    def log_tail(self, job_id: str, max_chars: int = 4000) -> str:
        encoded = urllib.parse.quote(job_id.strip(), safe="")
        response = self.request("GET", f"/api/jobs/{encoded}/log")
        log = response.get("log", "") if isinstance(response, dict) else ""
        return str(log)[-max_chars:]


def build_zimage_job_config(
    settings: dict[str, Any],
    *,
    job_name: str,
    dataset: DatasetReport,
    trigger_word: str,
    steps: int,
    learning_rate: float,
    rank: int,
    save_every: int,
) -> dict[str, Any]:
    if not SAFE_JOB_NAME.fullmatch(job_name):
        raise IntegrationError(
            "job_name must start with a letter or number and contain only letters, numbers, '.', '_' or '-'"
        )
    if steps < 1 or save_every < 1 or rank < 1 or learning_rate <= 0:
        raise IntegrationError("steps, save_every, rank, and learning_rate must be positive")

    return {
        "job": "extension",
        "config": {
            "name": job_name,
            "process": [
                {
                    "type": "diffusion_trainer",
                    "training_folder": "output",
                    "device": "cuda:0",
                    "trigger_word": trigger_word.strip(),
                    "performance_log_every": 10,
                    "network": {"type": "lora", "linear": rank, "linear_alpha": rank},
                    "save": {
                        "dtype": "bf16",
                        "save_every": save_every,
                        "max_step_saves_to_keep": 4,
                        "save_format": "safetensors",
                        "push_to_hub": False,
                    },
                    "datasets": [
                        {
                            "folder_path": str(dataset.folder),
                            "caption_ext": "txt",
                            "caption_dropout_rate": 0.0,
                            "shuffle_tokens": False,
                            "cache_latents_to_disk": True,
                            "resolution": [512, 768, 1024],
                        }
                    ],
                    "train": {
                        "batch_size": 1,
                        "steps": steps,
                        "gradient_accumulation": 1,
                        "train_unet": True,
                        "train_text_encoder": False,
                        "gradient_checkpointing": True,
                        "noise_scheduler": "flowmatch",
                        "timestep_type": "weighted",
                        "optimizer": "adamw8bit",
                        "lr": learning_rate,
                        "unload_text_encoder": False,
                        "cache_text_embeddings": True,
                        "skip_first_sample": True,
                        "disable_sampling": True,
                        "dtype": "bf16",
                    },
                    "logging": {"log_every": 1, "use_ui_logger": True},
                    "model": {
                        "name_or_path": settings["z_image_model"],
                        "arch": settings["z_image_arch"],
                        "dtype": "bf16",
                        "quantize": True,
                        "qtype": "qfloat8",
                        "quantize_te": True,
                        "qtype_te": "qfloat8",
                        "low_vram": True,
                        "layer_offloading": False,
                    },
                }
            ],
        },
        "meta": {
            "name": "[name]",
            "version": "1.0",
            "submitted_by": "ComfyUI-AIToolkit-Training",
        },
    }


def choose_completed_lora(job: dict[str, Any], files: list[dict[str, Any]]) -> Path:
    if str(job.get("status", "")).lower() != "completed":
        raise IntegrationError(
            f"Job {job.get('id')} is {job.get('status', 'unknown')}, not completed: {job.get('info', '')}"
        )
    candidates = [Path(str(item["path"])) for item in files if str(item.get("path", "")).lower().endswith(".safetensors")]
    if not candidates:
        raise IntegrationError("Completed job has no .safetensors output")
    exact_name = f"{job.get('name', '')}.safetensors".casefold()
    exact = [path for path in candidates if path.name.casefold() == exact_name]
    if exact:
        return exact[0]
    return max(candidates, key=lambda path: path.stat().st_mtime if path.exists() else 0)


def publish_lora(
    settings: dict[str, Any], source: Path, destination_name: str = "", overwrite: bool = False
) -> tuple[Path, str]:
    if not source.is_file():
        raise IntegrationError(f"LoRA output does not exist: {source}")
    name = destination_name.strip() or source.name
    if not name.lower().endswith(".safetensors"):
        name += ".safetensors"
    if Path(name).name != name or name in {".", ".."}:
        raise IntegrationError("destination_name must be a filename, not a path")

    lora_root = Path(settings["comfy_lora_path"]).resolve()
    subdirectory = str(settings.get("publish_subdirectory", "aitk")).strip()
    destination_dir = (lora_root / subdirectory).resolve() if subdirectory else lora_root
    try:
        destination_dir.relative_to(lora_root)
    except ValueError as exc:
        raise IntegrationError("publish_subdirectory escapes the ComfyUI LoRA folder") from exc
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / name
    if destination.exists() and not overwrite:
        raise IntegrationError(f"Destination exists and overwrite is disabled: {destination}")

    fd, temp_name = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=destination_dir)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)
    relative_name = destination.relative_to(lora_root).as_posix()
    return destination, relative_name


def _files_match(first: Path, second: Path) -> bool:
    if first.stat().st_size != second.stat().st_size:
        return False
    first_hash = hashlib.sha256()
    second_hash = hashlib.sha256()
    with first.open("rb") as first_handle, second.open("rb") as second_handle:
        while True:
            first_chunk = first_handle.read(1024 * 1024)
            second_chunk = second_handle.read(1024 * 1024)
            if not first_chunk and not second_chunk:
                break
            first_hash.update(first_chunk)
            second_hash.update(second_chunk)
    return first_hash.digest() == second_hash.digest()


def publish_lora_idempotent(settings: dict[str, Any], source: Path) -> tuple[Path, str, bool]:
    """Publish once; an identical existing destination is treated as success."""
    lora_root = Path(settings["comfy_lora_path"]).resolve()
    subdirectory = str(settings.get("publish_subdirectory", "aitk")).strip()
    destination = ((lora_root / subdirectory) if subdirectory else lora_root) / source.name
    if destination.is_file():
        if not _files_match(source, destination):
            raise IntegrationError(f"Published LoRA exists with different contents: {destination}")
        return destination, destination.relative_to(lora_root).as_posix(), False
    published, relative = publish_lora(settings, source)
    return published, relative, True
