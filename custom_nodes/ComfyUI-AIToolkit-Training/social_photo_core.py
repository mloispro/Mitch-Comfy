from __future__ import annotations

import json
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
REFERENCE_ROLES = ("Auto", "Front", "Left", "Right", "Full Body", "General", "Ignore")
KNOWN_SYNTHETIC_IDENTITY_FIXTURES = {
    "mitch-qwen-id-front.png",
    "mitch-qwen-id-left.png",
    "mitch-qwen-id-right.png",
    "mitch-workbench-qwen-id-front.png",
    "mitch-workbench-qwen-id-left.png",
    "mitch-workbench-qwen-id-right.png",
}

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
        "ordinary handheld photo from a recent smartphone main camera, natural 26mm-equivalent perspective, deep "
        "small-sensor all-purpose focus with the subject and environment both legible, a recognizably detailed background, "
        "casual slightly imperfect framing, ambient practical "
        "light, phone auto-exposure and white balance, restrained computational sharpening, normal JPEG detail, "
        "authentic skin texture, and standard camera mode"
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


def is_known_synthetic_identity_fixture(filename: str) -> bool:
    return Path(str(filename)).name.casefold() in KNOWN_SYNTHETIC_IDENTITY_FIXTURES


def load_registry(path: Path | None = None) -> dict[str, Any]:
    source = path or Path(__file__).with_name("social_photo_presets.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported social-photo preset schema.")
    scenes = payload.get("scenes")
    packs = payload.get("packs")
    if not isinstance(scenes, list) or not scenes or not isinstance(packs, dict):
        raise ValueError("Preset registry must contain scenes and packs.")
    required = {
        "key",
        "category",
        "label",
        "relationship",
        "subject_position",
        "body_reference",
        "prompt",
    }
    keys: set[str] = set()
    for scene in scenes:
        missing = required.difference(scene)
        if missing:
            raise ValueError(f"Scene is missing fields: {', '.join(sorted(missing))}")
        if scene["key"] in keys:
            raise ValueError(f"Duplicate scene key: {scene['key']}")
        if not isinstance(scene["body_reference"], bool):
            raise ValueError(f"Scene body_reference must be boolean: {scene['key']}")
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


def identity_route(
    final_identities: list[float | None],
    face_reference_count: int,
) -> dict[str, Any]:
    scores = [float(value) for value in final_identities if value is not None]
    mean_identity = sum(scores) / len(scores) if scores else None
    minimum_identity = min(scores) if scores else None
    if not scores:
        status = "identity_not_scored"
        recommendation = "Use a clearer current face reference and compare the result visually."
    elif mean_identity >= 0.60 and minimum_identity >= 0.50:
        status = "similarity_target_met_unverified"
        recommendation = (
            "Automated facial similarity met its diagnostic target, but it cannot approve identity; "
            "compare the result visually with genuine camera originals."
        )
    elif mean_identity >= 0.55 and minimum_identity >= 0.50:
        status = "similarity_near_target_visual_review"
        recommendation = (
            "Automated facial similarity is near its conservative target; judge the likeness visually "
            "against genuine camera originals before changing the workflow."
        )
    elif face_reference_count < 3:
        status = "add_reference_angles"
        recommendation = "Add genuine current front and side-angle references, then compare visually."
    else:
        status = "dedicated_identity_adapter_needed"
        recommendation = (
            "Native identity stayed below target across supplied angles. Do not reuse the rejected Klein LoRA; "
            "visually test a model-compatible identity adapter only as a last resort."
        )
    return {
        "status": status,
        "mean_final_identity": mean_identity,
        "minimum_final_identity": minimum_identity,
        "face_reference_count": int(face_reference_count),
        "visual_approval_required": True,
        "score_scope": "InsightFace cosine similarity diagnostic; not proof of identity or likeness.",
        "recommendation": recommendation,
    }


def build_prompt(scene: dict[str, Any], settings: dict[str, Any], body_status: str) -> str:
    relationship = settings["camera_relationship"]
    if relationship == "Auto Mix":
        relationship = scene["relationship"]
    gaze = (
        "the subject is looking naturally toward the camera"
        if relationship == "Looking at camera"
        else (
            "the subject is clearly not looking at the camera: keep the face readable in three-quarter view, "
            "but aim both eyes toward the activity outside the lens; use no posed smile or camera-aware stance"
        )
    )
    body_instruction = {
        "reference_grounded": "match the supplied full-body reference's visible build and proportions",
        "reference_supplied_unverified": "use the supplied full-body image as soft context without claiming exact body identity",
        "not_supplied": "use plausible natural anatomy; exact body shape is not established by the references",
    }[body_status]
    face_reference_count = max(1, int(settings.get("face_reference_count", 1)))
    body_picture_number = settings.get("body_reference_picture")
    if face_reference_count == 1:
        reference_intro = "Picture 1 is a genuine facial identity reference for the same consenting adult."
        identity_picture_label = "Picture 1"
    else:
        reference_intro = (
            f"Pictures 1 through {face_reference_count} are genuine facial identity references of the same "
            "consenting adult across different angles."
        )
        identity_picture_label = f"Pictures 1 through {face_reference_count}"
    body_reference_intro = ""
    if body_picture_number is not None and body_status != "not_supplied":
        body_reference_intro = (
            f"Picture {int(body_picture_number)} establishes only that same person's visible build and proportions; "
            "do not copy its pose, clothing, objects, or background."
        )
    parts = [
        reference_intro,
        body_reference_intro,
        "Create one new photorealistic image of exactly that same person.",
        f"Use {identity_picture_label} only to identify the main subject; do not copy their backgrounds, poses, clothing, camera angles, crops, or lighting.",
        f"Match the facial geometry, hairline, skin tone, eye area, nose, mouth, ears, jaw, and distinctive features shown in {identity_picture_label} exactly.",
        "Preserve the subject's apparent age and face proportions exactly; do not age, de-age, widen, narrow, beautify, or masculinize the face.",
        scene["prompt"],
        gaze + ".",
        body_instruction + ".",
        LOOK_PROMPTS[settings["camera_look"]] + ".",
        settings.get("brief", "").strip(),
        "One coherent edge-to-edge photograph, not a collage, exactly one copy of the main subject, correct anatomy, distinct bystanders, no visible brand logo, no text or watermark.",
    ]
    return " ".join(part.strip(" ,") for part in parts if part.strip()).strip()


def sanitize_report(value: Any) -> Any:
    """Remove source paths and tensors before a run report is serialized."""
    if isinstance(value, dict):
        return {
            key: sanitize_report(item)
            for key, item in value.items()
            if key not in {
                "references",
                "face_references",
                "generation_reference",
                "body_generation_reference",
                "face_reference_items",
                "body_reference_items",
                "source_path",
                "absolute_path",
            }
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_report(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if hasattr(value, "shape") and hasattr(value, "dtype"):
        return {"tensor": True, "shape": list(value.shape), "dtype": str(value.dtype)}
    return value
