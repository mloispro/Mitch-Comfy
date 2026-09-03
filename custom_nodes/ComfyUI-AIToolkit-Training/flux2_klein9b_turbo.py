from __future__ import annotations

import hashlib
from pathlib import Path

import folder_paths


TURBO_LORA_NAME = (
    r"flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors"
)
TURBO_LORA_SHA256 = (
    "A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600"
)
TURBO_LORA_BYTES = 1_386_477_008
TURBO_LORA_STRENGTH = 1.0
TURBO_STEPS = 8
TURBO_GUIDANCE = 1.0
TURBO_MODE_LABEL_ON = "Fast Turbo — 8 steps"
TURBO_MODE_LABEL_OFF = "Quality — 50 steps"
TURBO_SOURCE = "https://huggingface.co/kalle07/FLUX.2-klein-9B-turbo-lora-set"
TURBO_TEST_BASIS = (
    "RTX 3090 same-prompt/reference/seed A/B on 2026-09-01: 15.799 seconds versus "
    "153.855 seconds (9.738x), held-out identity centroid 0.7966 versus 0.8105, "
    "minimum similarity 0.6145 versus 0.6257, closed lips retained, and no observed "
    "skin, stubble, hair, or background-quality regression. Four steps was rejected."
)

_VERIFIED_SIGNATURES: dict[str, tuple[str, int, int]] = {}


def sampling_settings(
    enabled: bool,
    quality_steps: int = 50,
    quality_guidance: float = 4.0,
) -> tuple[int, float]:
    """Return the complete tested sampling regime for the selected mode."""
    if enabled:
        return TURBO_STEPS, TURBO_GUIDANCE
    return int(quality_steps), float(quality_guidance)


def verify_turbo_lora() -> str:
    """Resolve and hash-lock the exact BF16-standard rank-256 Turbo extraction."""
    full_path = folder_paths.get_full_path("loras", TURBO_LORA_NAME)
    if not full_path:
        raise RuntimeError(f"Missing locked Klein 9B Turbo LoRA: {TURBO_LORA_NAME}")
    path = Path(full_path)
    if int(path.stat().st_size) != TURBO_LORA_BYTES:
        raise RuntimeError(
            "Klein 9B Turbo LoRA byte-size mismatch. "
            f"Expected {TURBO_LORA_BYTES}, found {path.stat().st_size}."
        )
    signature = (str(path.resolve()), int(path.stat().st_size), int(path.stat().st_mtime_ns))
    cache_key = str(path.resolve())
    if _VERIFIED_SIGNATURES.get(cache_key) != signature:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(block)
        actual = digest.hexdigest().upper()
        if actual != TURBO_LORA_SHA256:
            raise RuntimeError(
                "Klein 9B Turbo LoRA hash mismatch. "
                f"Expected {TURBO_LORA_SHA256}, found {actual}."
            )
        _VERIFIED_SIGNATURES[cache_key] = signature
    return str(path)


def turbo_mode_report(enabled: bool, path: str | None, load_order: int | None) -> dict:
    """Return the immutable mode/provenance block saved by every 9B workflow."""
    steps, guidance = sampling_settings(enabled)
    return {
        "enabled": bool(enabled),
        "name": TURBO_LORA_NAME if enabled else None,
        "path": path if enabled else None,
        "sha256": TURBO_LORA_SHA256 if enabled else None,
        "bytes": TURBO_LORA_BYTES if enabled else None,
        "rank": 256 if enabled else None,
        "precision": "BF16 standard" if enabled else None,
        "strength": TURBO_LORA_STRENGTH if enabled else 0.0,
        "load_order": load_order if enabled else None,
        "steps": steps,
        "guidance": guidance,
        "sampler": "euler",
        "scheduler": "Flux2Scheduler",
        "quality_fallback": "50 steps / CFG 4 with no Turbo LoRA",
        "source": TURBO_SOURCE,
        "acceptance_test": TURBO_TEST_BASIS,
    }
