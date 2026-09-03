from __future__ import annotations


APPEARANCE_POLISH_LABEL_ON = "Visible flattering enhancement"
APPEARANCE_POLISH_LABEL_OFF = "Exact natural appearance"


def compose_appearance_polish(
    enabled: bool,
    *,
    expression_authority: str,
    preserve_bone_structure: bool = False,
) -> str:
    """Return the shared, identity-safe positive prompt clause for the 9B workflows."""
    if not bool(enabled):
        return ""

    bone_structure = (
        "Preserve his exact natural head and face shape from the genuine identity photograph: forehead width and "
        "height, temple width, cheekbone width, cheek fullness, jaw width and taper, chin width and length, and true "
        "face length-to-width ratio. Do not broaden, square, narrow, lengthen, shorten, idealize, or masculinize his "
        "skull, jaw, chin, or cheekbones. Keep his natural asymmetry and core feature spacing."
        if preserve_bone_structure
        else (
            "Refine his bone structure within believable same-person variation: give him a slightly stronger natural "
            "jaw and chin, modestly higher and more defined cheekbones, and subtly improved left-right facial balance. "
            "Keep his core face width, feature spacing, and distinctive eyes, nose, mouth, ears, and hairline "
            "recognizable."
        )
    )

    return " ".join(
        (
            "Give m1tch_person a clearly visible, natural-looking, more handsome best-day enhancement while keeping "
            "him unmistakably recognizable as the same adult. Present him about three to five years younger.",
            f"Use {expression_authority} as the head-direction, gaze, and expression-intent anchor. Give him an "
            "attractive, confident, approachable expression with relaxed facial tension. His mouth stays closed: the "
            "upper and lower lips meet across the full width of his mouth in one natural unbroken lip line, every tooth "
            "remains behind the lips, and only the mouth corners lift slightly. Make his eyes slightly more attractive "
            "through relaxed openness, clean natural catchlights, clear irises, and balanced eyelid presentation while "
            "keeping his natural eye size, iris color, spacing, and requested gaze. The final photograph retains the "
            "single unbroken closed lip line.",
            bone_structure,
            "Make the improvement obvious at normal viewing size: reduce fine forehead lines, crow's-feet, and "
            "under-eye creasing by about half; soften under-eye puffiness and shadow; and give his skin a noticeable "
            "light bronze sun tan with a warmer, healthier, more even complexion and natural tonal variation.",
            "Render pores finer and less prominent while still visible, and render his stubble neatly trimmed, even, "
            "and flattering with individual hairs. Keep natural lips and authentic skin texture. The result is a "
            "moderate, identity-faithful photographic improvement rather than a different person.",
        )
    )
