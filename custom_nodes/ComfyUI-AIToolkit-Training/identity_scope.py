from __future__ import annotations


def build_multi_person_identity_prompt(
    guarded_scene: str,
    identity_token: str,
    priority_constraints: str = "",
) -> str:
    token = identity_token.strip()
    if not token:
        raise ValueError("A trained identity token is required for multi-person generation.")
    constraints = priority_constraints.strip()
    prefix = (
        f"NONNEGOTIABLE FRAME CONSTRAINTS: {constraints} "
        if constraints
        else ""
    )
    return (
        f"{prefix}Create one new coherent photorealistic photograph with one main adult subject plus only the secondary people "
        "explicitly requested by the scene. Pictures 1 and 2 show the same main subject from the same source photograph; "
        "Picture 2 is a closer crop of Picture 1, not another person. The trained identity token "
        f"{token} applies exclusively to the main subject and never to any secondary person. Render the main subject as "
        f"unmistakably the exact {token} identity in Pictures 1 and 2, preserving current apparent age, facial proportions, "
        "eyes, eyebrows, nose, mouth, ears, jaw, hairline, hair color, and natural unretouched skin. Every secondary person "
        "is an unrelated individual with a different face, hair, age, build, and outfit; do not copy or approximate the main "
        "subject for them. Use the pictures only as identity evidence for the main subject. Do not copy their background, "
        "clothing, pose, framing, lighting, or expression. Render the whole frame as one genuine in-camera exposure with no "
        "face swap, pasted layer, duplicate identity, beauty filter, illustration, CGI, text, logo, or watermark. "
        f"New photo request: {guarded_scene.strip()}"
    )
