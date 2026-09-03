from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESET_MANIFEST_PATH = (
    Path(__file__).resolve().parent
    / "web"
    / "assets"
    / "scene-presets"
    / "manifest.json"
)


def _load_manifest() -> dict:
    try:
        manifest = json.loads(PRESET_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not load Klein 9B scene presets: {exc}") from exc
    if manifest.get("schema_version") != 1:
        raise RuntimeError("Unsupported Klein 9B scene-preset manifest schema.")
    profiles = manifest.get("reference_profiles")
    required_profiles = {"group", "solo_left", "solo_right", "full_body"}
    if not isinstance(profiles, dict) or set(profiles) != required_profiles:
        raise RuntimeError("Scene-preset manifest has an invalid reference-profile registry.")
    valid_profiles = set(profiles.values())
    for collection_name in ("identity", "group"):
        records = manifest.get(collection_name)
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"Scene-preset manifest has no {collection_name} records.")
        labels = [record.get("label") for record in records]
        keys = [record.get("key") for record in records]
        if any(not value for value in labels + keys):
            raise RuntimeError(f"Every {collection_name} preset needs a key and label.")
        if len(labels) != len(set(labels)) or len(keys) != len(set(keys)):
            raise RuntimeError(f"Duplicate {collection_name} preset key or label.")
        for record in records:
            if not record.get("thumbnail") or "prompt" not in record:
                raise RuntimeError(
                    f"Every {collection_name} preset needs a thumbnail and prompt."
                )
            if collection_name == "identity" and record.get("profile") not in valid_profiles:
                raise RuntimeError(f"Identity preset {record['key']} has an invalid profile.")
            if collection_name == "group" and not all(
                field in record for field in ("target_x", "target_y", "head_scale")
            ):
                raise RuntimeError(f"Group preset {record['key']} has incomplete target geometry.")
    return manifest


def _records_by_label(records: list[dict]) -> dict[str, dict]:
    return {
        record["label"]: {key: value for key, value in record.items() if key != "label"}
        for record in records
    }


PRESET_MANIFEST = _load_manifest()
PRESET_MANIFEST_SHA256 = hashlib.sha256(PRESET_MANIFEST_PATH.read_bytes()).hexdigest().upper()
REFERENCE_PROFILES = PRESET_MANIFEST["reference_profiles"]
GROUP_PROFILE = REFERENCE_PROFILES["group"]
SOLO_LEFT_PROFILE = REFERENCE_PROFILES["solo_left"]
SOLO_RIGHT_PROFILE = REFERENCE_PROFILES["solo_right"]
FULL_BODY_PROFILE = REFERENCE_PROFILES["full_body"]

IDENTITY_SCENE_PRESETS = _records_by_label(PRESET_MANIFEST["identity"])
GROUP_SCENE_PRESETS = _records_by_label(PRESET_MANIFEST["group"])
CUSTOM_IDENTITY_PRESET = next(
    label for label, record in IDENTITY_SCENE_PRESETS.items() if record["key"] == "custom"
)
CUSTOM_GROUP_PRESET = next(
    label for label, record in GROUP_SCENE_PRESETS.items() if record["key"] == "custom-group"
)


def _clean(value: str) -> str:
    return " ".join((value or "").strip().split())


def resolve_identity_scene(scene_preset: str, custom_scene_prompt: str) -> tuple[str, dict]:
    if scene_preset not in IDENTITY_SCENE_PRESETS:
        raise ValueError(f"Unknown Identity Studio scene preset: {scene_preset}")
    record = IDENTITY_SCENE_PRESETS[scene_preset]
    custom = _clean(custom_scene_prompt)
    if scene_preset == CUSTOM_IDENTITY_PRESET:
        if not custom:
            raise ValueError("Write a custom scene or choose a visual preset.")
        return custom, record
    prompt = record["prompt"]
    if custom:
        prompt = f"{prompt} Additional scene direction: {custom}"
    return prompt, record


def resolve_identity_profile(scene_preset: str, requested_profile: str) -> str:
    """Use a preset's tested profile; custom scenes keep the user's selection."""
    if scene_preset not in IDENTITY_SCENE_PRESETS:
        raise ValueError(f"Unknown Identity Studio scene preset: {scene_preset}")
    if scene_preset == CUSTOM_IDENTITY_PRESET:
        return requested_profile
    return IDENTITY_SCENE_PRESETS[scene_preset]["profile"]


def resolve_group_scene(scene_preset: str, custom_scene_prompt: str) -> tuple[str, dict]:
    if scene_preset not in GROUP_SCENE_PRESETS:
        raise ValueError(f"Unknown Group Scene Studio preset: {scene_preset}")
    record = GROUP_SCENE_PRESETS[scene_preset]
    custom = _clean(custom_scene_prompt)
    if scene_preset == CUSTOM_GROUP_PRESET:
        if not custom:
            raise ValueError("Describe the uploaded group photograph or choose a visual preset.")
        return custom, record
    prompt = record["prompt"]
    if custom:
        prompt = f"{prompt} Additional scene direction: {custom}"
    return prompt, record


def preset_asset_path(record: dict) -> Path | None:
    relative = record.get("source_asset")
    return None if not relative else PROJECT_ROOT / relative
