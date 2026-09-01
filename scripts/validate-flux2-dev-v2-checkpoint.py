#!/usr/bin/env python3
"""Validate an AI-Toolkit FLUX.2 LoRA checkpoint and its resume state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import torch
from safetensors import safe_open


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--expected-step", type=int, required=True)
    parser.add_argument("--expected-modules", type=int, required=True)
    parser.add_argument("--optimizer", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    checkpoint = args.checkpoint.resolve()
    if not checkpoint.is_file():
        raise SystemExit(f"Checkpoint does not exist: {checkpoint}")

    with safe_open(checkpoint, framework="pt", device="cpu") as handle:
        metadata = handle.metadata() or {}
        keys = list(handle.keys())
        lora_keys = [key for key in keys if key.endswith((".lora_A.weight", ".lora_B.weight"))]
        modules: dict[str, set[str]] = {}
        dtypes: dict[str, int] = {}
        ranks: set[int] = set()
        nonfinite: list[str] = []
        for key in lora_keys:
            suffix = ".lora_A.weight" if key.endswith(".lora_A.weight") else ".lora_B.weight"
            modules.setdefault(key[: -len(suffix)], set()).add(suffix)
            tensor = handle.get_tensor(key)
            dtypes[str(tensor.dtype)] = dtypes.get(str(tensor.dtype), 0) + 1
            if suffix == ".lora_A.weight" and tensor.ndim == 2:
                ranks.add(int(tensor.shape[0]))
            if suffix == ".lora_B.weight" and tensor.ndim == 2:
                ranks.add(int(tensor.shape[1]))
            if not bool(torch.isfinite(tensor).all()):
                nonfinite.append(key)

    try:
        training_info = json.loads(metadata.get("training_info", "{}"))
    except json.JSONDecodeError:
        training_info = {}
        errors.append("training_info metadata is not valid JSON")

    actual_step = training_info.get("step")
    if actual_step != args.expected_step:
        errors.append(f"metadata step is {actual_step!r}, expected {args.expected_step}")
    if len(modules) != args.expected_modules:
        errors.append(f"LoRA module count is {len(modules)}, expected {args.expected_modules}")
    if len(lora_keys) != args.expected_modules * 2:
        errors.append(f"LoRA tensor count is {len(lora_keys)}, expected {args.expected_modules * 2}")
    incomplete = sorted(module for module, suffixes in modules.items() if len(suffixes) != 2)
    if incomplete:
        errors.append(f"{len(incomplete)} modules do not have both A and B tensors")
    if ranks != {16}:
        errors.append(f"LoRA rank dimensions are {sorted(ranks)}, expected [16]")
    if set(dtypes) != {"torch.bfloat16"}:
        errors.append(f"checkpoint tensor dtypes are {dtypes}, expected only torch.bfloat16")
    if nonfinite:
        errors.append(f"non-finite values found in {len(nonfinite)} tensors")
    if metadata.get("base_model") != "black-forest-labs/FLUX.2-dev":
        errors.append("base_model metadata is missing or incorrect")
    if metadata.get("architecture") != "flux2":
        errors.append("architecture metadata is missing or incorrect")

    optimizer_status: dict[str, Any] | None = None
    if args.optimizer:
        optimizer_path = args.optimizer.resolve()
        if not optimizer_path.is_file():
            errors.append(f"optimizer state does not exist: {optimizer_path}")
            optimizer_status = {"path": str(optimizer_path), "reloadable": False}
        else:
            try:
                state = torch.load(optimizer_path, map_location="cpu", weights_only=True)
                reloadable = (
                    isinstance(state, dict)
                    and isinstance(state.get("state"), dict)
                    and isinstance(state.get("param_groups"), list)
                )
                optimizer_status = {
                    "path": str(optimizer_path),
                    "size_bytes": optimizer_path.stat().st_size,
                    "reloadable": reloadable,
                    "top_level_keys": sorted(str(key) for key in state) if isinstance(state, dict) else [],
                }
                if not optimizer_status["reloadable"]:
                    errors.append("optimizer state is not a reloadable optimizer state_dict")
            except Exception as exc:  # noqa: BLE001 - validation must record the exact load failure
                optimizer_status = {"path": str(optimizer_path), "reloadable": False, "error": repr(exc)}
                errors.append(f"optimizer state could not be loaded: {exc!r}")

    report = {
        "schema_version": 1,
        "checkpoint": str(checkpoint),
        "sha256": sha256_file(checkpoint),
        "size_bytes": checkpoint.stat().st_size,
        "metadata": metadata,
        "training_step": actual_step,
        "lora_modules": len(modules),
        "lora_tensors": len(lora_keys),
        "rank_dimensions": sorted(ranks),
        "tensor_dtypes": dtypes,
        "nonfinite_tensors": nonfinite,
        "incomplete_modules": incomplete,
        "optimizer": optimizer_status,
        "valid": not errors,
        "errors": errors,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
