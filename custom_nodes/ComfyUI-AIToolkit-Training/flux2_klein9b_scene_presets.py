from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

try:
    from .flux2_klein9b_mitch_identity_studio_presets import (
        FULL_BODY_PROFILE as ENGINE_FULL_BODY_PROFILE,
        GROUP_PROFILE as ENGINE_GROUP_PROFILE,
        SOLO_LEFT_PROFILE as ENGINE_SOLO_LEFT_PROFILE,
        SOLO_RIGHT_PROFILE as ENGINE_SOLO_RIGHT_PROFILE,
    )
except ImportError:  # Direct import used by the lightweight unit tests.
    from flux2_klein9b_mitch_identity_studio_presets import (
        FULL_BODY_PROFILE as ENGINE_FULL_BODY_PROFILE,
        GROUP_PROFILE as ENGINE_GROUP_PROFILE,
        SOLO_LEFT_PROFILE as ENGINE_SOLO_LEFT_PROFILE,
        SOLO_RIGHT_PROFILE as ENGINE_SOLO_RIGHT_PROFILE,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESET_MANIFEST_PATH = (
    Path(__file__).resolve().parent
    / "web"
    / "assets"
    / "scene-presets"
    / "manifest.json"
)
_REQUIRED_REFERENCE_PROFILES = {"group", "solo_left", "solo_right", "full_body"}
_EXPECTED_REFERENCE_PROFILES = {
    "group": ENGINE_GROUP_PROFILE,
    "solo_left": ENGINE_SOLO_LEFT_PROFILE,
    "solo_right": ENGINE_SOLO_RIGHT_PROFILE,
    "full_body": ENGINE_FULL_BODY_PROFILE,
}
_SAFE_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9A-Fa-f]{64}$")
_THUMBNAIL_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{label} must be a non-empty string.")
    if value != value.strip():
        raise RuntimeError(f"{label} must not have surrounding whitespace.")
    return value


def _contained_path(root: Path, relative: object, label: str) -> Path:
    value = _required_text(relative, label)
    candidate_relative = Path(value)
    if candidate_relative.is_absolute():
        raise RuntimeError(f"{label} must be relative to {root}.")
    resolved_root = Path(root).resolve()
    resolved = (resolved_root / candidate_relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"{label} escapes its allowed root: {value}") from exc
    return resolved


def _bounded_number(
    value: object,
    label: str,
    minimum: float,
    maximum: float,
    *,
    error_type: type[Exception] = RuntimeError,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise error_type(f"{label} must be a finite number.")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise error_type(f"{label} must be a finite number.")
    if not minimum <= numeric <= maximum:
        raise error_type(f"{label} must be between {minimum} and {maximum}.")
    return numeric


def _validate_manifest(
    manifest: object,
    *,
    manifest_path: Path = PRESET_MANIFEST_PATH,
    project_root: Path = PROJECT_ROOT,
    require_files: bool = False,
) -> dict:
    if not isinstance(manifest, dict):
        raise RuntimeError("Klein 9B scene-preset manifest must be a JSON object.")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("Unsupported Klein 9B scene-preset manifest schema.")

    profiles = manifest.get("reference_profiles")
    if not isinstance(profiles, dict) or set(profiles) != _REQUIRED_REFERENCE_PROFILES:
        raise RuntimeError("Scene-preset manifest has an invalid reference-profile registry.")
    if profiles != _EXPECTED_REFERENCE_PROFILES:
        raise RuntimeError(
            "Scene-preset manifest reference profiles do not match the frozen Identity engine."
        )
    profile_values = list(profiles.values())
    if any(not isinstance(value, str) or not value.strip() for value in profile_values):
        raise RuntimeError("Every reference-profile label must be a non-empty string.")
    if len(profile_values) != len(set(profile_values)):
        raise RuntimeError("Reference-profile labels must be unique.")
    valid_profiles = set(profile_values)

    all_thumbnails: set[str] = set()
    for collection_name, custom_key in (("identity", "custom"), ("group", "custom-group")):
        records = manifest.get(collection_name)
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"Scene-preset manifest has no {collection_name} records.")
        if any(not isinstance(record, dict) for record in records):
            raise RuntimeError(f"Every {collection_name} preset must be a JSON object.")

        labels: list[str] = []
        keys: list[str] = []
        for record in records:
            key = _required_text(record.get("key"), f"{collection_name} preset key")
            label = _required_text(record.get("label"), f"{collection_name} preset {key} label")
            if not _SAFE_KEY.fullmatch(key):
                raise RuntimeError(f"{collection_name} preset key is not a safe slug: {key}")
            labels.append(label)
            keys.append(key)

            thumbnail = _required_text(
                record.get("thumbnail"), f"{collection_name} preset {key} thumbnail"
            )
            thumbnail_path = _contained_path(
                Path(manifest_path).parent, thumbnail, f"{collection_name} preset {key} thumbnail"
            )
            if thumbnail_path.suffix.lower() not in _THUMBNAIL_SUFFIXES:
                raise RuntimeError(f"{collection_name} preset {key} has an unsupported thumbnail type.")
            if require_files and not thumbnail_path.is_file():
                raise RuntimeError(f"Missing {collection_name} preset {key} thumbnail: {thumbnail_path}")
            if thumbnail in all_thumbnails:
                raise RuntimeError(f"Duplicate scene-preset thumbnail: {thumbnail}")
            all_thumbnails.add(thumbnail)

            prompt = record.get("prompt")
            if not isinstance(prompt, str):
                raise RuntimeError(f"{collection_name} preset {key} prompt must be a string.")
            if key != custom_key and not prompt.strip():
                raise RuntimeError(f"{collection_name} preset {key} needs a non-empty prompt.")

            if collection_name == "identity":
                if record.get("profile") not in valid_profiles:
                    raise RuntimeError(f"Identity preset {key} has an invalid profile.")
                continue

            _bounded_number(record.get("target_x"), f"Group preset {key} target_x", 0.0, 1.0)
            _bounded_number(record.get("target_y"), f"Group preset {key} target_y", 0.0, 1.0)
            _bounded_number(record.get("head_scale"), f"Group preset {key} head_scale", 0.75, 1.0)
            if key == custom_key:
                if record.get("source_asset") is not None or record.get("source_sha256") is not None:
                    raise RuntimeError("The custom Group preset must not lock a source asset.")
                continue
            source_path = _contained_path(
                project_root,
                record.get("source_asset"),
                f"Group preset {key} source_asset",
            )
            if require_files and not source_path.is_file():
                raise RuntimeError(f"Missing Group preset {key} source asset: {source_path}")
            source_hash = record.get("source_sha256")
            if not isinstance(source_hash, str) or not _SHA256.fullmatch(source_hash):
                raise RuntimeError(f"Group preset {key} source_sha256 must be 64 hexadecimal characters.")

        if len(labels) != len(set(labels)) or len(keys) != len(set(keys)):
            raise RuntimeError(f"Duplicate {collection_name} preset key or label.")
        if keys.count(custom_key) != 1:
            raise RuntimeError(f"The {collection_name} preset collection needs exactly one {custom_key} record.")
    return manifest


def _load_manifest(
    *,
    manifest_path: Path = PRESET_MANIFEST_PATH,
    project_root: Path = PROJECT_ROOT,
) -> tuple[dict, str]:
    try:
        raw_manifest = Path(manifest_path).read_bytes()
        manifest = json.loads(raw_manifest)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not load Klein 9B scene presets: {exc}") from exc
    validated = _validate_manifest(
        manifest,
        manifest_path=manifest_path,
        project_root=project_root,
    )
    return validated, hashlib.sha256(raw_manifest).hexdigest().upper()


def _records_by_label(records: list[dict]) -> dict[str, dict]:
    return {
        record["label"]: {key: value for key, value in record.items() if key != "label"}
        for record in records
    }


PRESET_MANIFEST, PRESET_MANIFEST_SHA256 = _load_manifest()
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


def resolve_group_geometry(
    scene_preset: str,
    target_x: float,
    target_y: float,
    head_scale: float,
) -> tuple[float, float, float]:
    """Resolve and validate the same geometry for validation and execution."""
    if scene_preset not in GROUP_SCENE_PRESETS:
        raise ValueError(f"Unknown Group Scene Studio preset: {scene_preset}")
    record = GROUP_SCENE_PRESETS[scene_preset]
    values = (target_x, target_y, head_scale)
    if scene_preset != CUSTOM_GROUP_PRESET:
        values = (record["target_x"], record["target_y"], record["head_scale"])
    return (
        _bounded_number(values[0], "Group target_x", 0.0, 1.0, error_type=ValueError),
        _bounded_number(values[1], "Group target_y", 0.0, 1.0, error_type=ValueError),
        _bounded_number(values[2], "Group head_scale", 0.75, 1.0, error_type=ValueError),
    )


def preset_asset_path(record: dict) -> Path | None:
    relative = record.get("source_asset")
    return None if not relative else _contained_path(PROJECT_ROOT, relative, "Group preset source_asset")
