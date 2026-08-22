#!/usr/bin/env python3
"""Submit, inspect, and publish the local FLUX.2 Klein identity LoRA job."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_nodes" / "ComfyUI-AIToolkit-Training"
sys.path.insert(0, str(INTEGRATION_DIR))

from aitk_integration import (  # noqa: E402
    AIToolkitClient,
    build_flux2_klein_job_config,
    choose_completed_lora,
    fingerprint_dataset,
    load_settings,
    publish_lora_idempotent,
    validate_dataset,
)


DEFAULT_DATASET = ROOT / "datasets" / "flux2-klein-identity-v1"
DEFAULT_TRIGGER = "m1tch_person"


def _client() -> tuple[dict, AIToolkitClient]:
    settings = load_settings(INTEGRATION_DIR / "settings.json")
    return settings, AIToolkitClient(settings, timeout=30.0)


def submit(args: argparse.Namespace) -> None:
    settings, client = _client()
    dataset = validate_dataset(str(args.dataset), args.trigger)
    fingerprint = fingerprint_dataset(dataset)
    job_ref = (
        f"flux2-klein-{args.model_size}-identity-v1:{fingerprint}:"
        f"s{args.steps}:r{args.rank}:lr{args.lr}"
    )
    existing = client.find_by_ref(job_ref)
    if existing:
        print(json.dumps(existing, indent=2))
        return
    config = build_flux2_klein_job_config(
        job_name=args.name,
        dataset=dataset,
        trigger_word=args.trigger,
        steps=args.steps,
        learning_rate=args.lr,
        rank=args.rank,
        save_every=args.save_every,
        model_size=args.model_size,
    )
    job = client.submit(args.name, "0", config, job_ref=job_ref)
    print(json.dumps(job, indent=2))


def status(args: argparse.Namespace) -> None:
    _, client = _client()
    job = client.status(args.job_id)
    job["files"] = client.files(args.job_id)
    job["log_tail"] = client.log_tail(args.job_id, max_chars=args.log_chars)
    print(json.dumps(job, indent=2))


def publish(args: argparse.Namespace) -> None:
    settings, client = _client()
    job = client.status(args.job_id)
    source = choose_completed_lora(job, client.files(args.job_id))
    destination, relative_name, copied = publish_lora_idempotent(settings, source)
    print(json.dumps({
        "source": str(source),
        "destination": str(destination),
        "comfy_lora_name": relative_name,
        "copied": copied,
    }, indent=2))


def stage(args: argparse.Namespace) -> None:
    settings, client = _client()
    job = client.status(args.job_id)
    staged = []
    for item in client.files(args.job_id):
        source = Path(str(item.get("path", "")))
        if source.suffix.casefold() != ".safetensors" or not source.is_file():
            continue
        destination, relative_name, copied = publish_lora_idempotent(settings, source)
        staged.append({
            "source": str(source),
            "destination": str(destination),
            "comfy_lora_name": relative_name,
            "copied": copied,
        })
    if not staged:
        raise RuntimeError(f"Job {args.job_id} has no complete .safetensors checkpoints yet")
    print(json.dumps({"job_status": job.get("status"), "checkpoints": staged}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    submit_parser = commands.add_parser("submit")
    submit_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    submit_parser.add_argument("--trigger", default=DEFAULT_TRIGGER)
    submit_parser.add_argument("--name", default="m1tch-flux2-klein-identity-v1")
    submit_parser.add_argument("--steps", type=int, default=1500)
    submit_parser.add_argument("--lr", type=float, default=0.00008)
    submit_parser.add_argument("--rank", type=int, default=16)
    submit_parser.add_argument("--save-every", type=int, default=250)
    submit_parser.add_argument("--model-size", choices=("4b", "9b"), default="9b")
    submit_parser.set_defaults(func=submit)

    status_parser = commands.add_parser("status")
    status_parser.add_argument("job_id")
    status_parser.add_argument("--log-chars", type=int, default=5000)
    status_parser.set_defaults(func=status)

    publish_parser = commands.add_parser("publish")
    publish_parser.add_argument("job_id")
    publish_parser.set_defaults(func=publish)

    stage_parser = commands.add_parser("stage")
    stage_parser.add_argument("job_id")
    stage_parser.set_defaults(func=stage)
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    parsed.func(parsed)
