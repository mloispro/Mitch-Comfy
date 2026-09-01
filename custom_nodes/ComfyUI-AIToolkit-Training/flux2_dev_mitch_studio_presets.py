from __future__ import annotations


MODE_PROMPT_ONLY = "PROMPT ONLY — create a new scene"
MODE_SCENE_RESTAGE = "SCENE IMAGE — replace the main man with Mitch"
NO_SCENE_IMAGE = "No scene image (prompt-only)"
CUSTOM_PRESET = "Custom — write your own scene"


SCENE_PRESETS = {
    CUSTOM_PRESET: "",
    "Founder editorial — modern studio": (
        "A premium but authentic personal-brand portrait in a bright modern creative studio beside "
        "a large window, wearing a tailored charcoal overshirt over a white crew-neck shirt, relaxed "
        "confidence and a subtle natural half-smile."
    ),
    "Cooking candid — warm modern kitchen": (
        "Preparing and plating a simple dinner in a tasteful modern home kitchen at early evening, "
        "wearing a fitted dark navy crew-neck T-shirt, sleeves naturally hugging the arms, quietly "
        "capable and warm, with believable hands and fresh ingredients."
    ),
    "Golden-hour rooftop — linen shirt": (
        "On an elegant rooftop terrace during golden hour, framed near the city skyline, wearing a "
        "pale blue linen shirt with an open collar and casually rolled sleeves, relaxed posture and a "
        "warm restrained smile."
    ),
    "Night city balcony — black open-collar shirt": (
        "Leaning naturally on a glass high-rise balcony above city lights at night, wearing a fitted "
        "black open-collar short-sleeved shirt and a simple watch, both hands naturally touching the "
        "railing, confident but unposed."
    ),
    "Amalfi balcony — white linen": (
        "On a Positano balcony above the Amalfi coast in late-afternoon sun, wearing a relaxed white "
        "linen shirt and resting one hand on the railing, with the sea and hillside town clearly visible."
    ),
    "Italian lake boat — relaxed travel": (
        "Seated naturally on a classic wooden boat on an Italian lake, wearing an open-collar white "
        "linen shirt and refined sunglasses, hands resting believably on the boat while mountains and "
        "lakeside villas recede behind him."
    ),
    "Elegant restaurant — understated evening": (
        "Seated at an elegant modern restaurant table beside a small warm lamp, wearing a fitted gray "
        "blazer over a black open-collar shirt, with a thoughtful relaxed expression and restrained luxury."
    ),
    "Cat lover — relaxed at home": (
        "At home in a softly lit living room, wearing a clean black zip hoodie while gently holding a "
        "large fluffy Ragdoll cat, looking down at the cat with an affectionate natural smile and "
        "anatomically believable hands."
    ),
    "Golf course — tropical morning": (
        "Walking naturally on a beautiful tropical golf course in clear morning light, wearing a fitted "
        "black golf polo and tailored gray trousers, carrying one golf club with easy athletic posture."
    ),
    "Night out — seated with friends": (
        "Seated comfortably in the center of a warm upscale lounge booth, wearing a dark navy suit and "
        "open-collar white shirt, with three visually unmistakable unrelated friends: a Black man with a "
        "shaved head and close beard on the left, an East Asian woman with a chin-length black bob on the "
        "right, and a Latina woman with long curly dark hair farther back. Their facial geometry, hairlines, "
        "skin tones, and clothing differ clearly from m1tch_person. Keep every face fully inside the frame, "
        "with relaxed social energy, drinks on the table, and natural spacing."
    ),
    "Night out — cocktail bar candid": (
        "Standing at an intimate cocktail bar with two unrelated adult friends, wearing a fitted dark "
        "jacket over a muted shirt, caught mid-conversation with easy social warmth while amber practical "
        "lights shape the room."
    ),
    "Weekend lake — fitted T-shirt": (
        "At the end of a wooden lake dock in clear morning light, wearing a fitted heather-blue crew-neck "
        "T-shirt, relaxed stance and a small genuine smile, with calm water and a green shoreline behind him."
    ),
    "Downtown menswear — sunrise": (
        "On a clean downtown sidewalk just after sunrise, wearing a fitted black bomber jacket over a "
        "muted gray shirt, natural posture and subtle urban depth, like an unretouched menswear editorial."
    ),
}


CAMERA_STYLES = {
    "Dating app — natural smartphone": (
        "An authentic rear-smartphone photograph with believable handheld framing, restrained HDR, "
        "ordinary lens perspective, natural skin texture, subtle sensor grain, and no beauty filter."
    ),
    "Premium lifestyle — natural": (
        "Premium but believable 50mm lifestyle photography with soft directional light, realistic pores, "
        "true apparent age, refined composition, and no plastic skin or beauty retouching."
    ),
    "Professional editorial — natural": (
        "A clean professional editorial photograph with restrained retouching, realistic skin and hair, "
        "natural body proportions, controlled depth of field, and believable color."
    ),
    "Prompt decides": "",
}


FRAMINGS = {
    "Head and shoulders": "Frame him from the shoulders upward with a naturally large, readable face.",
    "Waist-up": "Frame him from the waist upward; do not reveal knees, lower legs, or feet.",
    "Three-quarter body": "Frame him from head to mid-thigh with both arms and hands naturally visible.",
    "Full body": "Show his entire body and both feet with believable lean-to-average proportions.",
    "Prompt decides": "",
}


MOMENTS = {
    "Looking at camera": "He looks naturally toward the camera without a forced pose.",
    "Candid — looking away": (
        "His body remains readable but his head turns about twenty-five to thirty-five degrees and his "
        "eyes look clearly off-camera; there is absolutely no eye contact with the lens."
    ),
    "Action": "Capture him naturally mid-action with believable body mechanics rather than a posed stance.",
    "Prompt decides": "",
}


CANVASES = {
    "Portrait — 832 × 1248": (832, 1248),
    "Square — 1024 × 1024": (1024, 1024),
    "Landscape — 1248 × 832": (1248, 832),
}


def compose_scene_text(scene_preset: str, custom_scene_prompt: str) -> str:
    if scene_preset not in SCENE_PRESETS:
        raise ValueError(f"Unknown scene preset: {scene_preset}")
    custom = " ".join(custom_scene_prompt.strip().split())
    preset = SCENE_PRESETS[scene_preset]
    if scene_preset == CUSTOM_PRESET:
        if not custom:
            raise ValueError("Write a custom scene or choose a preset.")
        return custom
    if custom:
        return f"{preset} Additional creative direction: {custom}"
    return preset


def compose_effective_prompt(
    scene_mode: str,
    scene_preset: str,
    custom_scene_prompt: str,
    camera_style: str,
    framing: str,
    moment: str,
) -> str:
    if scene_mode not in (MODE_PROMPT_ONLY, MODE_SCENE_RESTAGE):
        raise ValueError(f"Unknown scene mode: {scene_mode}")
    if camera_style not in CAMERA_STYLES:
        raise ValueError(f"Unknown camera style: {camera_style}")
    if framing not in FRAMINGS:
        raise ValueError(f"Unknown framing: {framing}")
    if moment not in MOMENTS:
        raise ValueError(f"Unknown moment: {moment}")

    scene = compose_scene_text(scene_preset, custom_scene_prompt)
    identity = (
        "m1tch_person is the clearly featured adult man. Keep his recognizable forehead and hairline, "
        "short brown hair, eye shape and spacing, nose, mouth, jaw and chin, current apparent age, lean-to-average "
        "build, and natural skin texture. Any secondary people must have distinct unrelated faces and must not "
        "resemble m1tch_person."
    )
    rendering = " ".join(
        part for part in (CAMERA_STYLES[camera_style], FRAMINGS[framing], MOMENTS[moment]) if part
    )

    if scene_mode == MODE_PROMPT_ONLY:
        return " ".join(
            part
            for part in (
                "Create one completely new photorealistic photograph.",
                identity,
                scene,
                rendering,
                "One continuous in-camera scene; no face-swap look, collage, selective face sharpening, text, logo, or watermark.",
            )
            if part
        )

    reference_contract = (
        "Picture 1 is a scene and composition reference, not an identity reference. Recreate Picture 1 as a new "
        "photograph. Replace only its primary adult man with m1tch_person; if no man is present, place m1tch_person "
        "naturally into the main-subject position. Preserve the useful location, crop, camera angle, pose or action, "
        "prop relationships, clothing category, and lighting from Picture 1. Do not copy the original man's face, "
        "skull, hair, skin, ethnicity, apparent age, or identity. Remove any screenshot controls, borders, captions, "
        "progress bars, interface elements, logos, and watermarks from the recreated photograph."
    )
    return " ".join(
        part
        for part in (
            reference_contract,
            identity,
            f"Scene intent: {scene}",
            rendering,
            "The result is one coherent photograph, not a face swap, mask, composite, or pasted head.",
        )
        if part
    )
