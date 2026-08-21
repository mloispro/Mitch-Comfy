from __future__ import annotations

import json
import re
import struct
from copy import deepcopy
from pathlib import Path
from typing import Any


MODES = ("Single", "Dating Pack", "Instagram Pack")
SCENE_PRESETS = (
    "Auto Mix",
    "Natural Candid",
    "Smart Casual",
    "Travel",
    "Hobby/Active",
    "Pet",
    "Night Out",
    "Custom",
)
CAMERA_LOOKS = ("Authentic Phone", "Professional", "35mm Lifestyle")
CAMERA_RELATIONSHIPS = ("Auto Mix", "Looking at camera", "Candid/action")
ASPECTS = ("Portrait 2:3", "Instagram 4:5", "Square", "Landscape 3:2")
IDENTITY_FINISHES = ("Auto", "Native Only", "Force ReActor")
REFERENCE_ROLES = ("Auto", "Front", "Left", "Right", "Full Body", "General", "Ignore")

DEFAULT_COUNTS = {"Single": 1, "Dating Pack": 6, "Instagram Pack": 9}
RESOLUTIONS = {
    "Portrait 2:3": (1024, 1536),
    "Instagram 4:5": (1024, 1280),
    "Square": (1024, 1024),
    "Landscape 3:2": (1536, 1024),
}
OOM_RESOLUTIONS = {
    "Portrait 2:3": (768, 1152),
    "Instagram 4:5": (768, 960),
    "Square": (768, 768),
    "Landscape 3:2": (1152, 768),
}

LOOK_PROMPTS = {
    "Authentic Phone": (
        "authentic recent smartphone photo, natural auto-exposure, mild sensor grain, realistic sharpening, "
        "ordinary dynamic range, no beauty filter"
    ),
    "Professional": (
        "professional full-frame photograph, intentional composition, controlled natural-looking light, crisp optics, "
        "restrained editorial color, realistic skin rather than commercial retouching"
    ),
    "35mm Lifestyle": (
        "35mm lifestyle photograph, subtle film grain, gentle highlight rolloff, shallow but believable depth of field, "
        "documentary color"
    ),
}

NEGATIVE_PROMPT = (
    "CGI, illustration, painting, waxy skin, plastic skin, beauty filter, excessive skin smoothing, malformed face, "
    "asymmetric eyes, bad hands, extra fingers, missing fingers, extra limbs, duplicate subject, cloned face, collage, "
    "split screen, text, watermark, logo, frame, blank border"
)


def load_registry(path: Path | None = None) -> dict[str, Any]:
    source = path or Path(__file__).with_name("social_photo_presets.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported social-photo preset schema.")
    scenes = payload.get("scenes")
    packs = payload.get("packs")
    if not isinstance(scenes, list) or not scenes or not isinstance(packs, dict):
        raise ValueError("Preset registry must contain scenes and packs.")
    required = {"key", "category", "label", "relationship", "subject_position", "prompt"}
    keys: set[str] = set()
    for scene in scenes:
        missing = required.difference(scene)
        if missing:
            raise ValueError(f"Scene is missing fields: {', '.join(sorted(missing))}")
        if scene["key"] in keys:
            raise ValueError(f"Duplicate scene key: {scene['key']}")
        keys.add(scene["key"])
    for pack_name, scene_keys in packs.items():
        unknown = set(scene_keys).difference(keys)
        if unknown:
            raise ValueError(f"{pack_name} references unknown scenes: {', '.join(sorted(unknown))}")
    return payload


def resolve_count(mode: str, count_override: int) -> int:
    if mode not in DEFAULT_COUNTS:
        raise ValueError(f"Unknown mode: {mode}")
    if count_override == 0:
        return DEFAULT_COUNTS[mode]
    if not 1 <= int(count_override) <= 9:
        raise ValueError("Photo count must be 0 for the mode default or between 1 and 9.")
    return int(count_override)


def resolve_resolution(aspect: str, fallback: bool = False) -> tuple[int, int]:
    table = OOM_RESOLUTIONS if fallback else RESOLUTIONS
    if aspect not in table:
        raise ValueError(f"Unknown aspect ratio: {aspect}")
    return table[aspect]


def resolve_scenes(settings: dict[str, Any], registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_registry()
    by_key = {scene["key"]: scene for scene in registry["scenes"]}
    count = resolve_count(settings["mode"], settings["count_override"])
    selected_preset = settings["scene_preset"]

    if selected_preset == "Auto Mix":
        if settings["mode"] == "Single":
            keys = ["natural-hero"]
        else:
            keys = registry["packs"][settings["mode"]]
    else:
        matches = [scene["key"] for scene in registry["scenes"] if scene["category"] == selected_preset]
        keys = matches or ["custom"]

    resolved: list[dict[str, Any]] = []
    for index in range(count):
        scene = deepcopy(by_key[keys[index % len(keys)]])
        scene["index"] = index
        scene["variation"] = index // len(keys)
        resolved.append(scene)
    return resolved


def seed_for(base_seed: int, image_index: int) -> int:
    return (int(base_seed) + 1009 * int(image_index)) & 0xFFFFFFFFFFFFFFFF


def build_prompt(scene: dict[str, Any], settings: dict[str, Any], body_status: str) -> str:
    relationship = settings["camera_relationship"]
    if relationship == "Auto Mix":
        relationship = scene["relationship"]
    gaze = (
        "the subject is looking naturally toward the camera"
        if relationship == "Looking at camera"
        else "the subject is absorbed in the activity and not deliberately posing for the camera"
    )
    body_instruction = {
        "reference_grounded": "match the supplied full-body reference's visible build and proportions",
        "reference_supplied_unverified": "use the supplied full-body image as soft context without claiming exact body identity",
        "not_supplied": "use plausible natural anatomy; exact body shape is not established by the references",
    }[body_status]
    trigger = settings.get("lora_trigger", "").strip()
    parts = [
        trigger,
        "Create one photorealistic image of the same consenting adult shown in the identity references.",
        "Preserve recognizable facial geometry, hairline, age, skin tone, and distinguishing features without beautifying or changing identity.",
        scene["prompt"],
        gaze + ".",
        body_instruction + ".",
        LOOK_PROMPTS[settings["camera_look"]] + ".",
        settings.get("brief", "").strip(),
        "One coherent edge-to-edge photograph, correct anatomy, distinct bystanders, no duplicate of the main subject, no text or watermark.",
    ]
    return " ".join(part.strip(" ,") for part in parts if part.strip()).strip()


def read_safetensors_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw_length = handle.read(8)
        if len(raw_length) != 8:
            raise ValueError("LoRA is not a valid safetensors file.")
        header_length = struct.unpack("<Q", raw_length)[0]
        if header_length <= 2 or header_length > 100_000_000:
            raise ValueError("LoRA safetensors header length is invalid.")
        try:
            return json.loads(handle.read(header_length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("LoRA safetensors header is invalid JSON.") from error


def validate_klein_4b_lora(path: Path) -> dict[str, Any]:
    header = read_safetensors_header(path)
    tensors = {key: value for key, value in header.items() if key != "__metadata__"}
    if not tensors:
        raise ValueError("LoRA contains no tensors.")
    shapes = [value.get("shape", []) for value in tensors.values()]
    hidden_3072 = any(3072 in shape for shape in shapes)
    single_blocks = {
        int(match.group(1))
        for key in tensors
        if (match := re.search(r"single_transformer_blocks\.(\d+)", key))
    }
    transformer_blocks = {
        int(match.group(1))
        for key in tensors
        if (match := re.search(r"(?<!single_)transformer_blocks\.(\d+)", key))
    }
    if not hidden_3072 or not set(range(20)).issubset(single_blocks) or not set(range(5)).issubset(transformer_blocks):
        raise ValueError("Selected LoRA is not compatible with the FLUX.2 Klein 4B architecture.")
    metadata = header.get("__metadata__", {})
    return {
        "tensor_count": len(tensors),
        "hidden_size": 3072,
        "single_blocks": len(single_blocks),
        "transformer_blocks": len(transformer_blocks),
        "metadata": {key: metadata[key] for key in ("format",) if key in metadata},
    }


def sanitize_report(value: Any) -> Any:
    """Remove source paths and tensors before a run report is serialized."""
    if isinstance(value, dict):
        return {
            key: sanitize_report(item)
            for key, item in value.items()
            if key not in {"references", "face_references", "source_path", "absolute_path"}
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_report(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if hasattr(value, "shape") and hasattr(value, "dtype"):
        return {"tensor": True, "shape": list(value.shape), "dtype": str(value.dtype)}
    return value
