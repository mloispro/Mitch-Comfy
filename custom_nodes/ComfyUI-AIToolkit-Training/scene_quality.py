from __future__ import annotations

import re
from typing import Any


_CONTEXT_PATTERNS = {
    "car_interior": (
        r"\b(car|vehicle|suv|truck|taxi|rideshare)\b.*\b(inside|interior|seat|driver|passenger|selfie|headrest|seatbelt)\b",
        r"\b(inside|interior|seat|driver|passenger|selfie|headrest|seatbelt)\b.*\b(car|vehicle|suv|truck|taxi|rideshare)\b",
    ),
    "traffic": (
        r"\b(street|road|traffic|intersection|crosswalk|sidewalk|city block|parking lot|driving|drive)\b",
    ),
    "crowd": (
        r"\b(crowd|bystanders|pedestrians|busy|lively|party|festival|audience|patrons|people behind)\b",
    ),
    "background_people": (
        r"\b(crowd|bystanders|pedestrians|busy|lively|audience|patrons|people behind|in the background)\b",
        r"\b(one|two|three|four|1|2|3|4)\s+(adult|adults|person|people|man|men|woman|women)\b.{0,80}\b(behind|background|middle distance|separate tables|secondary)\b",
        r"\b(behind|background|middle distance|separate tables|secondary)\b.{0,80}\b(one|two|three|four|1|2|3|4)\s+(adult|adults|person|people|man|men|woman|women)\b",
        r"\b(people|person|man|woman|men|women|friends|pedestrians|bystanders)\b.{0,32}\bbehind (him|her|them|me|the subject)\b",
        r"\bbehind (him|her|them|me|the subject)\b.{0,32}\b(people|person|man|woman|men|women|friends|pedestrians|bystanders)\b",
    ),
    "group_photo": (
        r"\b(group photo|group of|friends together|with friends|family photo|team photo)\b",
    ),
    "reflection": (
        r"\b(mirror|reflection|reflected|window glass|storefront glass|windshield|rear-view|rearview)\b",
    ),
    "action": (
        r"\b(action|walking|running|jogging|hiking|golf|golfing|surfing|swimming|cycling|biking|dancing|lifting|playing|cooking|working out|mid-stride|in motion)\b",
    ),
    "held_object": (
        r"\b(holding|carrying|gripping|using|swinging)\b.*\b(phone|cup|glass|drink|bottle|club|racket|ball|camera|steering wheel|utensil|tool)\b",
        r"\b(phone|cup|glass|drink|bottle|club|racket|ball|camera|steering wheel|utensil|tool)\b.*\b(in hand|held|gripped|carried)\b",
    ),
    "text_signage": (
        r"\b(sign|signage|logo|shirt text|jersey|menu|license plate|billboard|poster|storefront name)\b",
    ),
}


_GENERATION_GUARDRAILS = {
    "universal": (
        "Priority: a physically coherent casual photograph, not a polished AI scene. Every object has clear supports, "
        "scale, occlusion, and contact; no background edge emerges from the subject. Use one viewpoint, light, depth, and "
        "sensor texture. Prefer a few clear, naturally irregular background elements over dense filler."
    ),
    "background_detail": (
        "Make the environment recognizable and geometrically coherent, preserving believable large and medium structures, "
        "material transitions, supports, and perspective rather than inventing decorative micro-detail. Focus must follow "
        "distance: the subject plane is naturally crisp, the midground has slightly lower microcontrast and resolution, "
        "and the far distance is gently softer but still structurally readable. Never make every depth plane equally sharp, "
        "hide the setting in fake bokeh, smear it into filler, or use a featureless color wash unless shallow focus is requested."
    ),
    "car_interior": (
        "Make the subject's car seat, the camera seat, and the cabin layout obvious. Put the subject's headrest offset "
        "behind one shoulder, separated from the head, with its seatback and two supports readable. Keep every other seat, "
        "belt, window, pillar, roof edge, and rear shelf separate and continuous."
    ),
    "traffic": (
        "Use sparse, unambiguous traffic with pavement gaps between vehicles. Each car is fully separated and aligned with "
        "its lane or parking row; moving versus parked is visually obvious. Preserve curb, sidewalk, road, and pedestrian "
        "separation."
    ),
    "crowd": (
        "Every visible person is a distinct individual with different face, age, build, hair, outfit, pose, and spacing. "
        "Use an obvious mixed clothing palette: red or rust, mustard, tan, green, white, black, and one pattern; at most one "
        "cool blue or purple outfit besides the subject. Never repeat a face, garment, pose, or spacing interval."
    ),
    "background_people": (
        "Honor an explicitly requested small count; otherwise show only one to three secondary people. Keep each person "
        "laterally separated from the main subject with one continuous readable head-and-body silhouette, mostly in side or "
        "rear view and occupied with a different activity. Only the main subject is m1tchperson: every secondary person has "
        "a clearly different face, hair, build, age, and outfit. Never repeat the subject's identity, place a partial person "
        "directly behind the subject, or form a front-facing row."
    ),
    "group_photo": (
        "For the requested group, keep each person individually recognizable in a different outfit and pose, with uneven "
        "natural spacing, believable eye lines, and small unsynchronized interactions rather than a copied lineup."
    ),
    "reflection": (
        "Make every mirror, window, windshield, or glossy reflection agree with the visible person, camera viewpoint, light, "
        "and surrounding geometry. Do not invent an extra person or a contradictory reflected scene."
    ),
    "action": (
        "Capture an asymmetric instant mid-action: one leg leads, arms counter-swing or interact with the activity, and the "
        "torso and gaze follow the motion. Do not use a static square-on standing pose."
    ),
    "held_object": (
        "Make each hand grip its object at a plausible contact point with correct finger count, object scale, direction, and "
        "occlusion. The object must be supported rather than floating or melting into the hand."
    ),
    "text_signage": (
        "Keep unrequested text tiny, incidental, and out of focus. Any requested focal sign, logo, menu, shirt text, or plate "
        "must be structurally clean and legible rather than garbled."
    ),
}


_CAMERA_GUARDRAILS = {
    "Smartphone — natural": (
        "Camera model: one ordinary recent smartphone 1x rear main camera, roughly 24–28mm equivalent, standard Photo mode, "
        "with genuinely deep optical focus and no portrait segmentation. The subject and midground remain clearly resolved; "
        "distant architecture and vehicles are only gently softer and retain readable shapes and material structure. Do not "
        "simulate a large-aperture portrait lens or dissolve the environment into bokeh."
    ),
    "Professional — natural": (
        "Camera model: one environmental-portrait camera using a plausible 35–50mm lens around f/5.6–f/8, with the eyes at "
        "the focus plane and a gradual physical falloff through the setting. Do not combine a telephoto-looking subject with "
        "a wide-angle background or use creamy portrait bokeh to conceal scene errors."
    ),
    "Prompt decides": (
        "Use the single physically plausible lens, subject distance, aperture, and focus behavior requested by the user; if "
        "none is specified, use a natural environmental-photo lens with gradual distance-dependent focus falloff."
    ),
}


_SINGLE_CAPTURE_RULE = (
    "The whole frame comes from one physical exposure: one projection and vanishing geometry, focus distance, aperture, "
    "motion behavior, exposure, white balance, sharpening response, sensor grain, and compression. Subject and environment "
    "must share those optics. Hair, shoulders, and clothing meet the scene with ordinary in-camera occlusion and matching "
    "edge softness—no halo, pasted cutout, depth-mask boundary, or separately sharpened layer. Keep natural skin variation "
    "subtle and sparse; do not cover the face or arms with repeated dark spots, sores, scratches, or high-contrast marks. "
    "Unless the user explicitly requests a selfie, the camera is held by someone else and the subject never extends an arm "
    "toward the lens or appears to hold the camera."
)


def _normalized_text(*parts: str) -> str:
    return " ".join(" ".join(str(part).strip().lower().split()) for part in parts if part)


def infer_scene_contexts(scene_prompt: str, moment: str = "") -> list[str]:
    text = _normalized_text(scene_prompt, moment)
    contexts: list[str] = []
    for context, patterns in _CONTEXT_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            contexts.append(context)
    if "action" not in contexts and moment.strip().casefold() == "action":
        contexts.append("action")
    if "group_photo" in contexts and "background_people" in contexts:
        explicit_background = re.search(
            r"\b(crowd|bystanders|pedestrians|audience|patrons|people behind|in the background)\b",
            text,
        )
        if not explicit_background:
            contexts.remove("background_people")
    return contexts


def build_scene_contract(
    scene_prompt: str,
    photo_style: str,
    framing: str,
    moment: str,
) -> dict[str, Any]:
    cleaned_prompt = " ".join(scene_prompt.strip().split())
    if not cleaned_prompt:
        raise ValueError("Describe the new photo you want to create.")
    contexts = infer_scene_contexts(cleaned_prompt, moment)
    rules = ["universal", "background_detail", *contexts]
    camera_guardrail = _CAMERA_GUARDRAILS.get(
        photo_style, _CAMERA_GUARDRAILS["Prompt decides"]
    )
    return {
        "schema_version": 1,
        "user_scene": cleaned_prompt,
        "camera_style": photo_style,
        "framing": framing,
        "moment": moment,
        "contexts": contexts,
        "rules": rules,
        "camera_model": camera_guardrail,
        "single_capture_rule": _SINGLE_CAPTURE_RULE,
        "generation_guardrails": [
            _GENERATION_GUARDRAILS[name] for name in rules
        ] + [camera_guardrail, _SINGLE_CAPTURE_RULE],
    }


def apply_scene_guardrails(generation_prompt: str, contract: dict[str, Any]) -> str:
    guardrails = " ".join(contract.get("generation_guardrails", []))
    return f"{generation_prompt.strip()} Scene-coherence requirements: {guardrails}".strip()


def requires_complex_route(contract: dict[str, Any]) -> bool:
    contexts = set(contract.get("contexts", []))
    if contexts.intersection({"background_people", "group_photo", "reflection"}):
        return True
    return "crowd" in contexts and bool(
        contexts.intersection({"background_people", "traffic"})
    )
