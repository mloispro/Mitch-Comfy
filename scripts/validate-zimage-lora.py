from __future__ import annotations

import argparse
import json
from pathlib import Path

from safetensors import safe_open


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AI-Toolkit LoRA without loading the base model.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-modules", type=int, default=240)
    parser.add_argument("--expected-rank", type=int)
    parser.add_argument("--require-nonzero", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    path = args.path.resolve()
    if not path.is_file():
        raise SystemExit(f"LoRA does not exist: {path}")

    tensor_count = 0
    modules: set[str] = set()
    dtypes: set[str] = set()
    shapes: dict[str, list[int]] = {}
    module_tensors: dict[str, dict[str, list[int]]] = {}
    nonfinite: list[str] = []
    zero_tensors: list[str] = []
    tensor_absmax: dict[str, float] = {}
    with safe_open(path, framework="pt", device="cpu") as handle:
        metadata = handle.metadata() or {}
        for key in handle.keys():
            tensor = handle.get_tensor(key)
            tensor_count += 1
            dtypes.add(str(tensor.dtype))
            shapes[key] = list(tensor.shape)
            if not tensor.is_floating_point() or not bool(tensor.isfinite().all()):
                nonfinite.append(key)
            absmax = float(tensor.float().abs().max().item())
            tensor_absmax[key] = absmax
            if absmax == 0.0:
                zero_tensors.append(key)
            for suffix, role in (
                (".lora_A.weight", "down"),
                (".lora_B.weight", "up"),
                (".lora_down.weight", "down"),
                (".lora_up.weight", "up"),
            ):
                if key.endswith(suffix):
                    module = key[: -len(suffix)]
                    modules.add(module)
                    module_tensors.setdefault(module, {})[role] = list(tensor.shape)
                    break

    rank_counts: dict[int, int] = {}
    rank_mismatch_modules: list[dict] = []
    for module in sorted(modules):
        pair = module_tensors.get(module, {})
        down = pair.get("down")
        up = pair.get("up")
        down_rank = down[0] if down and len(down) >= 2 else None
        up_rank = up[-1] if up and len(up) >= 2 else None
        if down_rank is not None and down_rank == up_rank:
            rank_counts[down_rank] = rank_counts.get(down_rank, 0) + 1
        if (
            down_rank is None
            or up_rank is None
            or down_rank != up_rank
            or (args.expected_rank is not None and down_rank != args.expected_rank)
        ):
            rank_mismatch_modules.append(
                {"module": module, "down_shape": down, "up_shape": up}
            )

    report = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "tensor_count": tensor_count,
        "module_count": len(modules),
        "expected_modules": args.expected_modules,
        "expected_rank": args.expected_rank,
        "rank_counts": {str(key): value for key, value in sorted(rank_counts.items())},
        "rank_mismatch_modules": rank_mismatch_modules,
        "dtypes": sorted(dtypes),
        "nonfinite_tensors": nonfinite,
        "zero_tensors": zero_tensors,
        "minimum_tensor_absmax": min(tensor_absmax.values(), default=0.0),
        "maximum_tensor_absmax": max(tensor_absmax.values(), default=0.0),
        "metadata": metadata,
        "valid": (
            tensor_count == args.expected_modules * 2
            and len(modules) == args.expected_modules
            and not nonfinite
            and (args.expected_rank is None or not rank_mismatch_modules)
            and (not args.require_nonzero or not zero_tensors)
        ),
    }
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
