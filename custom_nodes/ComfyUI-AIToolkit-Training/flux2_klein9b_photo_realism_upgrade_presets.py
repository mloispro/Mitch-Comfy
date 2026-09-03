from __future__ import annotations

import math


MAX_OUTPUT_PIXELS = 1_700_000
MIN_OUTPUT_EDGE = 256
DEFAULT_DETAIL_INSTRUCTIONS = (
    "For this included example, the man remains in the exact source three-quarter view and looks past the "
    "camera toward image-right. Preserve the exact raised-collar coat silhouette, shirt opening, building-wall "
    "diagonals, roof edge, bare-tree layout, and every foreground/background boundary. Render the same real "
    "house exterior with separate horizontal siding boards, narrow straight seams, subtle matte painted "
    "texture, and minor surface variation. Render the same leafless tree with tapered limbs, bark ridges, "
    "irregular forks, progressively thinner twigs, tiny buds, and distinct overlapping depth layers. Keep the "
    "whole environment legible with natural small-sensor depth of field; distant elements soften gradually but "
    "remain structurally readable instead of becoming portrait-mode bokeh."
)
APPROVED_INCLUDED_EXAMPLE_PROMPT = (
    "Picture 1 is the exact landscape edit target and the highest-priority reference. Recreate its 5:3 "
    "photograph with the identical camera position, subject placement, head scale, body crop, shoulder line, "
    "raised-collar coat silhouette, shirt opening, hair silhouette and part, visible ear, head yaw, pitch and "
    "roll, gaze slightly toward image-right, eye-line angle, closed-lip expression, building-wall diagonals, "
    "roof edge, bare-tree layout, and every foreground/background boundary. The man remains in the same "
    "three-quarter view and looks past the camera toward image-right.\n\n"
    "Picture 2 is a face-interior-free edge outline of Picture 1 and supplies geometry only. Follow its outer "
    "head, hair, coat, siding, roof, branch, and frame-edge lines as the exact spatial scaffold. Convert those "
    "lines into real photographic materials and natural depth.\n\n"
    "Picture 3 exclusively supplies the identity and current apparent age of m1tch_person: his real eyes, nose, "
    "mouth, jaw, facial width, asymmetry, hairline, pores, and fine stubble. Render a healthy, rested, subtly "
    "flattering version of the same man while keeping Picture 1's exact head direction and off-camera gaze.\n\n"
    "Picture 4 is an isolated crop of genuine human hair and supplies hair material only. Use matte brown "
    "strands with varied thickness, soft root density, small flyaways, irregular broken clumps, and restrained "
    "highlights. Keep the hairstyle silhouette, volume, part, and combing direction from Picture 1.\n\n"
    "Render one recent iPhone main-camera photograph in standard Photo mode. The small-sensor depth of field "
    "keeps both the man and environment legible. Skin has restrained pores of varied size, fine stubble, tiny "
    "irregular color variation, natural lips, and moist eyes. The dark coat has believable woven fibers and "
    "soft folds.\n\n"
    "The background is a real house exterior and a real leafless tree rebuilt from Pictures 1 and 2. Render "
    "separate horizontal siding boards with narrow straight seams, subtle matte painted texture, minor surface "
    "variation, and a physically straight roof edge. Render tapered tree limbs with bark ridges, irregular forks, "
    "progressively thinner twigs, tiny buds, and distinct overlapping depth layers. Every visible branch has "
    "physical thickness and natural taper. Distant elements soften gradually but remain structurally readable. "
    "Use neutral color, restrained Smart HDR local tone mapping, smooth highlight rolloff, realistic fine sensor "
    "texture, and consistent native detail across skin, hair, fabric, siding, and wood. The result reads as a "
    "single casual iPhone capture with natural matte hair and a materially detailed background."
)


def compute_output_dimensions(
    width: int,
    height: int,
    max_pixels: int = MAX_OUTPUT_PIXELS,
) -> tuple[int, int]:
    """Preserve source aspect and native size when it is safe for the locked 3090 graph."""
    width = int(width)
    height = int(height)
    if width < MIN_OUTPUT_EDGE or height < MIN_OUTPUT_EDGE:
        raise ValueError(
            f"Source photo must be at least {MIN_OUTPUT_EDGE} pixels on each edge; got {width}x{height}."
        )
    scale = min(1.0, math.sqrt(float(max_pixels) / float(width * height)))
    output_width = max(MIN_OUTPUT_EDGE, round(width * scale / 16.0) * 16)
    output_height = max(MIN_OUTPUT_EDGE, round(height * scale / 16.0) * 16)
    return output_width, output_height


def face_interior_rectangle(
    bbox: tuple[float, float, float, float] | list[float],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """Match the approved face-interior clearing proportions without removing the head contour."""
    x1, y1, x2, y2 = (float(value) for value in bbox)
    face_width = max(1.0, x2 - x1)
    face_height = max(1.0, y2 - y1)
    left = round(x1 + 0.095 * face_width)
    top = round(y1 + 0.112 * face_height)
    right = round(x2 - 0.100 * face_width)
    bottom = round(y2 - 0.081 * face_height)
    left = min(max(0, left), image_width - 1)
    top = min(max(0, top), image_height - 1)
    right = min(max(left + 1, right), image_width - 1)
    bottom = min(max(top + 1, bottom), image_height - 1)
    return left, top, right, bottom


def compose_upgrade_prompt(detail_instructions: str) -> str:
    detail = " ".join(str(detail_instructions).strip().split())
    if not detail:
        raise ValueError("Describe the source-specific background or material detail to improve.")
    if detail == " ".join(DEFAULT_DETAIL_INSTRUCTIONS.split()):
        return APPROVED_INCLUDED_EXAMPLE_PROMPT

    role_contract = (
        "Picture 1 is the exact edit target and highest-priority scene reference. Recreate the same photograph "
        "with identical camera position, aspect ratio, crop, subject placement, head scale, body and shoulder pose, "
        "clothing silhouette, visible ears, forehead height, hairline position, hair silhouette and part, head yaw, "
        "pitch and roll, gaze direction, pupil position within each eyelid, "
        "eye-line angle, expression, lighting layout, depth relationships, and every foreground and background "
        "boundary. The source head pose, facial perspective, forehead, hairline, and gaze are immutable and remain "
        "more important than flattering presentation. Do not turn, recenter, straighten, enlarge, shrink, raise the "
        "hairline, add height above the forehead, or redesign the subject or scene. Picture 1 supplies scene, pose, "
        "expression, clothing, and "
        "composition, not identity."
    )
    guide_contract = (
        "Picture 2 is a face-interior-free edge guide made from Picture 1 and supplies geometry only. Follow its "
        "outer head, hair, ear, body, clothing, object, architecture, vegetation, terrain, horizon, and frame-edge "
        "lines as the spatial scaffold, then convert those lines into coherent photographic materials and depth."
    )
    identity_contract = (
        "Picture 3 is a protected genuine photograph of m1tch_person and exclusively supplies identity and current "
        "apparent age: real eyes, nose, mouth, jaw, facial width, asymmetry, hairline, pores, and fine stubble. "
        "Render the same man while keeping Picture 1's exact facial perspective, head direction, gaze, and expression."
    )
    hair_contract = (
        "Picture 4 is a protected isolated crop of genuine human hair and supplies hair material only. Render matte "
        "brown strands with varied thickness, soft root density, irregular broken clumps, restrained highlights, and "
        "a few natural flyaways while preserving Picture 1's hairstyle silhouette, volume, part, and combing "
        "direction. Keep a clean continuous transition at the forehead, temple, ear, and back of the head, with no "
        "dark band, duplicate edge, artificial shadow, halo, seam, or floating clump."
    )
    finish = (
        "Render one recent iPhone main-camera photograph in standard Photo mode, not Portrait mode. Use natural "
        "small-sensor depth of field that keeps both the person and the complete environment legible. Where present, "
        "architecture has separate physical panels, straight seams, matte surface variation, and clean perspective; "
        "vegetation has physical thickness, taper, irregular branching, and distinct overlapping depth; terrain, "
        "water, fabric, and other visible materials retain their characteristic structure and texture. Distant "
        "elements soften gradually but remain structurally readable instead of becoming creamy bokeh. Skin has "
        "restrained pores of varied "
        "size, fine stubble, tiny irregular color variation, natural lips, moist eyes, and continuous forehead "
        "texture without a repair patch. Hair, skin, fabric, and the entire environment share coherent illumination, "
        "sensor texture, edge response, and distance-dependent softness, with consistent native detail across the "
        "face and background. Use restrained saturation and Smart HDR, "
        "smooth highlight rolloff, believable local contrast, and natural fine detail without etched sharpening. "
        "The result reads as one casual real photograph, not an AI portrait or composite. Do not add, remove, or "
        "relocate scene elements."
    )
    return " ".join((role_contract, guide_contract, identity_contract, hair_contract, detail, finish))
