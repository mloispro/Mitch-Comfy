from __future__ import annotations

import argparse
from pathlib import Path

from safetensors import safe_open
from safetensors.torch import save_file


SOURCE_PREFIX = "base_model.model."
COMFY_PREFIX = "diffusion_model."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert FAL Krea2 PEFT LoRA keys to ComfyUI native Krea2 keys."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    if not source.is_file():
        raise RuntimeError(f"Source LoRA does not exist: {source}")
    if source == destination:
        raise RuntimeError("Use a separate destination; the published source must remain unchanged.")

    converted = {}
    with safe_open(source, framework="pt", device="cpu") as handle:
        metadata = dict(handle.metadata() or {})
        keys = list(handle.keys())
        unexpected = [key for key in keys if not key.startswith(SOURCE_PREFIX)]
        if unexpected:
            raise RuntimeError(
                f"Expected every tensor to begin with {SOURCE_PREFIX!r}; "
                f"found {unexpected[0]!r}."
            )
        for key in keys:
            converted_key = COMFY_PREFIX + key[len(SOURCE_PREFIX) :]
            if converted_key in converted:
                raise RuntimeError(f"Duplicate converted key: {converted_key}")
            converted[converted_key] = handle.get_tensor(key)

    metadata["comfy_key_prefix_conversion"] = (
        f"{SOURCE_PREFIX}->{COMFY_PREFIX}; tensor values unchanged"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    save_file(converted, destination, metadata=metadata)
    print(f"Converted {len(converted)} tensors: {destination}")


if __name__ == "__main__":
    main()
