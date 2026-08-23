from __future__ import annotations


NO_REFERENCE = "No additional reference"

PHOTO_STYLES = {
    "Smartphone — natural": (
        "Casual smartphone photograph from an ordinary recent rear camera: moderate wide-angle "
        "perspective, mostly deep focus, gentle computational exposure, slight sensor noise and "
        "compression. No portrait-mode blur, fake bokeh, excessive HDR, or beauty processing."
    ),
    "Professional — natural": (
        "Natural professional photograph with soft lens transitions, restrained retouching, "
        "realistic skin texture, and subtle camera grain."
    ),
    "Prompt decides": "",
}

FRAMINGS = {
    "Prompt decides": "",
    "Head and shoulders": "Head-and-shoulders framing.",
    "Waist-up": "Natural waist-up framing.",
    "Full body": (
        "Wide full-body composition with the entire person visible head to feet, from the top of the hair through "
        "both shoes, with clear ground beneath the feet; no crop at the knees or ankles."
    ),
}

MOMENTS = {
    "Prompt decides": "",
    "Looking at camera": "Looking naturally toward the camera.",
    "Candid / looking away": (
        "Candid three-quarter profile with eyes clearly looking away from the camera; no eye contact."
    ),
    "Action": (
        "Natural in-progress action with believable body mechanics and slight motion; the candid "
        "gaze follows the activity unless the scene explicitly requests eye contact."
    ),
}

REALISM_RENDERING = (
    "Render the entire person as one coherent in-camera photograph: face, hair, neck, arms, "
    "and clothing share the same scene lighting, white balance, depth of field, edge softness, "
    "and camera grain. Use natural low-contrast skin microtexture with no local face sharpening "
    "or etched wrinkles. Do not exaggerate pores, facial lines, age, symmetry, or muscularity."
)


def selected_reference_names(primary: str, *additional: str) -> list[str]:
    names = [primary, *(name for name in additional if name and name != NO_REFERENCE)]
    return [name.strip() for name in names if name and name.strip()]


def duplicate_reference_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        folded = name.casefold()
        if folded in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(folded)
    return duplicates


def compose_scene_prompt(
    scene_prompt: str,
    photo_style: str,
    framing: str,
    moment: str,
) -> str:
    scene = " ".join(scene_prompt.strip().split())
    if not scene:
        raise ValueError("Describe the new photo you want to create.")
    if photo_style not in PHOTO_STYLES:
        raise ValueError(f"Unknown photo style: {photo_style}")
    if framing not in FRAMINGS:
        raise ValueError(f"Unknown framing: {framing}")
    if moment not in MOMENTS:
        raise ValueError(f"Unknown moment: {moment}")
    parts = [
        scene,
        PHOTO_STYLES[photo_style],
        FRAMINGS[framing],
        MOMENTS[moment],
        REALISM_RENDERING,
    ]
    return " ".join(part for part in parts if part)
