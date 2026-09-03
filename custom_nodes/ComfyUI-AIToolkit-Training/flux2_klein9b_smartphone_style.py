from __future__ import annotations

import hashlib
from pathlib import Path

import folder_paths


SMARTPHONE_STYLE_LORA_NAME = (
    r"smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors"
)
SMARTPHONE_STYLE_LORA_SHA256 = (
    "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90"
)
SMARTPHONE_STYLE_LORA_STRENGTH = 0.25
SMARTPHONE_STYLE_TRIGGER = "casual snapshot"
SMARTPHONE_STYLE_BASE_MODEL = "flux2_klein_9b"
SMARTPHONE_STYLE_CIVITAI_MODEL_ID = 2381927
SMARTPHONE_STYLE_CIVITAI_VERSION_ID = 2916530
SMARTPHONE_STYLE_CIVITAI_FILE_ID = 2794778
SMARTPHONE_STYLE_TRAINING_STEP = 2520
SMARTPHONE_STYLE_TRAINING_EPOCH = 84
SMARTPHONE_STYLE_LORA_RANK = 8
SMARTPHONE_STYLE_TEST_BASIS = (
    "RTX 4070 one-variable A/B on 2026-09-01: identity centroid 0.7891 to 0.8100, "
    "mean 0.7110 to 0.7298, minimum 0.6711 to 0.7029; visual review found subtle "
    "whole-frame realism improvement without identity, hair, or sharpening regression."
)

_VERIFIED_SIGNATURES: dict[str, tuple[str, int, int]] = {}


def apply_smartphone_style_trigger(prompt: str) -> str:
    """Prepend the author-trained trigger exactly once to a normalized prompt."""
    normalized = " ".join(str(prompt).strip().split())
    if not normalized:
        raise ValueError("The effective prompt cannot be empty.")
    trigger_prefix = f"{SMARTPHONE_STYLE_TRIGGER}."
    if normalized.casefold().startswith(trigger_prefix.casefold()):
        return normalized
    return f"{trigger_prefix} {normalized}"


def verify_smartphone_style_lora() -> str:
    """Resolve and hash-lock the accepted Smartphone Snapshot v13 LoRA."""
    full_path = folder_paths.get_full_path("loras", SMARTPHONE_STYLE_LORA_NAME)
    if not full_path:
        raise RuntimeError(
            f"Missing locked Smartphone Snapshot v13 LoRA: {SMARTPHONE_STYLE_LORA_NAME}"
        )
    path = Path(full_path)
    signature = (str(path.resolve()), int(path.stat().st_size), int(path.stat().st_mtime_ns))
    cache_key = str(path.resolve())
    if _VERIFIED_SIGNATURES.get(cache_key) != signature:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(block)
        actual = digest.hexdigest().upper()
        if actual != SMARTPHONE_STYLE_LORA_SHA256:
            raise RuntimeError(
                "Smartphone Snapshot v13 LoRA hash mismatch. "
                f"Expected {SMARTPHONE_STYLE_LORA_SHA256}, found {actual}."
            )
        _VERIFIED_SIGNATURES[cache_key] = signature
    return str(path)


def smartphone_style_report() -> dict:
    """Return the immutable provenance/settings block stored in every production report."""
    return {
        "name": SMARTPHONE_STYLE_LORA_NAME,
        "sha256": SMARTPHONE_STYLE_LORA_SHA256,
        "strength": SMARTPHONE_STYLE_LORA_STRENGTH,
        "trigger": SMARTPHONE_STYLE_TRIGGER,
        "base_model": SMARTPHONE_STYLE_BASE_MODEL,
        "civitai_model_id": SMARTPHONE_STYLE_CIVITAI_MODEL_ID,
        "civitai_version_id": SMARTPHONE_STYLE_CIVITAI_VERSION_ID,
        "civitai_file_id": SMARTPHONE_STYLE_CIVITAI_FILE_ID,
        "training_step": SMARTPHONE_STYLE_TRAINING_STEP,
        "training_epoch": SMARTPHONE_STYLE_TRAINING_EPOCH,
        "rank": SMARTPHONE_STYLE_LORA_RANK,
        "acceptance_test": SMARTPHONE_STYLE_TEST_BASIS,
    }
