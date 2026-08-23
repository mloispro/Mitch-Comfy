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
        r"\b(crowd|group|friends|bystanders|pedestrians|busy|lively|party|festival|audience|patrons|people behind|restaurant|cafe|bar)\b",
    ),
    "background_people": (
        r"\b(crowd|bystanders|pedestrians|busy|lively|audience|patrons|people behind|behind (him|her|them)|in the background)\b",
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
        "Render a recognizable, materially detailed environment from foreground through midground and the major distance "
        "structures, including ordinary wear, seams, foliage, architecture, vehicles, and small irregular clutter where "
        "appropriate. Use realistic moderate-to-deep focus: distance may soften slightly but must retain coherent edges, "
        "texture, and structure. Never hide the setting with portrait-mode blur, fake bokeh, smeared shapes, foggy filler, "
        "or a featureless color wash unless the user explicitly requests shallow focus."
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
        "Show only four to seven separated background people at staggered depths, mostly in side or rear view and occupied "
        "with different activities. Do not form a front-facing row, procession, audience, or evenly spaced line behind the subject."
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
            r"\b(crowd|bystanders|pedestrians|audience|patrons|people behind|behind (him|her|them)|in the background)\b",
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
    return {
        "schema_version": 1,
        "user_scene": cleaned_prompt,
        "camera_style": photo_style,
        "framing": framing,
        "moment": moment,
        "contexts": contexts,
        "rules": rules,
        "generation_guardrails": [_GENERATION_GUARDRAILS[name] for name in rules],
    }


def apply_scene_guardrails(generation_prompt: str, contract: dict[str, Any]) -> str:
    guardrails = " ".join(contract.get("generation_guardrails", []))
    return f"{generation_prompt.strip()} Scene-coherence requirements: {guardrails}".strip()


def requires_complex_route(contract: dict[str, Any]) -> bool:
    contexts = set(contract.get("contexts", []))
    if contexts.intersection({"background_people", "group_photo", "reflection"}):
        return True
    return {"traffic", "crowd"}.issubset(contexts)
