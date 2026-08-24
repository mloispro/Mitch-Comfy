from __future__ import annotations

import re


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}
_NUMBER = r"one|two|three|four|five|six|seven|eight|nine|[1-9]"
_PERSON = r"adult|adults|person|people|man|men|woman|women|friend|friends|pedestrian|pedestrians|bystander|bystanders"
_VEHICLE = r"car|cars|vehicle|vehicles|suv|suvs|truck|trucks|taxi|taxis"


def _number(value: str) -> int:
    return _NUMBER_WORDS.get(value.casefold(), int(value) if value.isdigit() else 0)


def _first_count(text: str, entity_pattern: str) -> int | None:
    match = re.search(
        rf"\b(?P<count>{_NUMBER})\s+(?:clearly\s+separated\s+|distinct\s+|secondary\s+|background\s+)?(?:parked\s+|moving\s+)?(?:{entity_pattern})\b",
        text,
        flags=re.IGNORECASE,
    )
    return _number(match.group("count")) if match else None


def _has_specific_vehicle_appearance(text: str) -> bool:
    body = r"sedan|hatchback|coupe|suv|truck|van|taxi|convertible|wagon"
    color = r"red|orange|yellow|green|blue|purple|silver|gray|grey|black|white|brown"
    vehicle = r"car|cars|vehicle|vehicles|suv|suvs|truck|trucks|taxi|taxis"
    if re.search(rf"\b(?:{body})\b", text, re.IGNORECASE):
        return True
    return bool(
        re.search(
            rf"\b(?:{color})\b(?:\W+\w+){{0,2}}\W+\b(?:{vehicle})\b|"
            rf"\b(?:{vehicle})\b(?:\W+\w+){{0,2}}\W+\b(?:{color})\b",
            text,
            re.IGNORECASE,
        )
    )


def build_hard_scene_constraints(contract: dict) -> str:
    """Translate count/camera intent into terse layout constraints models follow better."""
    text = str(contract.get("user_scene", ""))
    contexts = set(contract.get("contexts", []))
    person_count = _first_count(text, _PERSON)
    vehicle_count = _first_count(text, _VEHICLE)
    instructions: list[str] = []

    if person_count is not None:
        if "group_photo" in contexts:
            instructions.append(
                f"HARD HUMAN COUNT: exactly {person_count} visible humans total, including the main subject; no partial, "
                "reflected, distant, or cropped extra human anywhere."
            )
        elif "background_people" in contexts:
            total = person_count + 1
            instructions.append(
                f"HARD HUMAN COUNT: exactly {total} visible humans total—one main foreground subject plus exactly "
                f"{person_count} secondary people; no partial, reflected, distant, or cropped extra human anywhere."
            )

    if vehicle_count is not None:
        instructions.append(
            f"HARD VEHICLE COUNT: exactly {vehicle_count} complete passenger cars are visible in the entire photograph. "
            "They occupy the full visible road area; every remaining road patch is uninterrupted bare asphalt. Every car "
            "has a clearly different body style, paint color, wheel design, and size instead of looking duplicated."
        )

    if "background_people" in contexts or "group_photo" in contexts:
        instructions.append(
            "IDENTITY SEPARATION: every secondary person must have a visibly different sex or apparent ancestry, age, "
            "face shape, nose, hairline, hairstyle, build, clothing color, pose, gaze, and activity from the main subject "
            "and from every other person. No lookalikes, twins, repeated heads, or wardrobe duplicates."
        )
        if (
            person_count == 2
            and not re.search(r"\b(man|men|woman|women|male|female)\b", text, re.IGNORECASE)
        ):
            instructions.append(
                "SECONDARY CAST: keep the requested clothing, but make one secondary adult an older woman with short "
                "curly gray hair and a round face, and the other a younger man with straight dark hair and an angular "
                "face. Their age, sex, silhouette, hair, and facial structure must read differently at a glance."
            )

    if (
        vehicle_count == 2
        and not _has_specific_vehicle_appearance(text)
    ):
        instructions.append(
            "VEHICLE CAST: make one car a small dark-red hatchback and the other a light-silver midsize sedan. Their "
            "silhouettes, paint, wheelbase, grille, and roofline are unmistakably different."
        )

    lowered = text.casefold()
    if "selfie" not in lowered:
        instructions.append(
            "CAMERA OWNERSHIP: an unseen photographer holds the camera at ordinary portrait distance. The main subject's "
            "hands stay naturally within the described activity and neither arm extends toward the lens. This is not a selfie."
        )
    return " ".join(instructions)


def scene_object_targets(contract: dict) -> dict[str, int]:
    text = str(contract.get("user_scene", ""))
    contexts = set(contract.get("contexts", []))
    person_count = _first_count(text, _PERSON)
    vehicle_count = _first_count(text, _VEHICLE)
    targets: dict[str, int] = {}
    if person_count is not None:
        targets["person"] = person_count if "group_photo" in contexts else person_count + 1
    if vehicle_count is not None:
        targets["vehicle"] = vehicle_count
    return targets


def build_scene_topology(contract: dict) -> str:
    contexts = set(contract.get("contexts", []))
    text = str(contract.get("user_scene", "")).casefold()
    parked_direction = (
        " The requested parked cars are side-on, parallel, separated by bare pavement, and all point toward the same "
        "side of the frame."
        if "parked" in text
        else ""
    )
    if {"traffic", "background_people"}.issubset(contexts):
        return (
            "COMPOSITION MAP: aim the camera across the sidewalk, not down the road. Put the main subject alone in the "
            "foreground center; place secondary people laterally apart in the middle distance without overlap; show the "
            "curb and only a narrow side-on strip of road behind them; place requested vehicles fully separated in that "
            "strip; fill the rest of that strip with bare asphalt; use one continuous building facade as the far plane. "
            "Keep the secondary people beside rather than directly behind the main subject."
            f"{parked_direction}"
        )
    if "background_people" in contexts:
        return (
            "COMPOSITION MAP: main subject alone in the foreground center; each secondary person occupies a separate "
            "lateral middle-distance zone; environment occupies the far plane. No person overlaps or sits directly behind "
            "the main subject."
        )
    if "group_photo" in contexts:
        return (
            "COMPOSITION MAP: keep every group member on the same believable camera plane with uneven lateral spacing, "
            "complete readable bodies, and no hidden or partial extra person behind the group."
        )
    return ""
