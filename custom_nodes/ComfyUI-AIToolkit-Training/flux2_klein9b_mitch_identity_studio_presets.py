from __future__ import annotations


GROUP_PROFILE = "GROUP — front only (one Mitch)"
SOLO_LEFT_PROFILE = "SOLO — front + left-facing angle"
SOLO_RIGHT_PROFILE = "SOLO — front + right-facing angle"
FULL_BODY_PROFILE = "FULL BODY — front + body proportions"
PROMPTING_STRATEGY = "bfl-flux2-positive-natural-language-v2"


REFERENCE_CATALOG = {
    "front": {
        "file": "mitch-klein9b-ref-front-neutral-v2.jpg",
        "role": "neutral frontal face and upper-body identity",
        "sha256": "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33",
    },
    "left": {
        "file": "mitch-klein9b-ref-left-3q-v2.jpg",
        "role": "face turned toward image-left",
        "sha256": "1DBEDEE1F712222F4E183D0B7648AA4739510CD86DB8B097697D2CB2C4ECEB08",
    },
    "right": {
        "file": "mitch-klein9b-ref-right-3q-v2.jpg",
        "role": "face turned toward image-right",
        "sha256": "2F502B5233950BB01808FC3168540D54B8CC3A09894E2895D003C10A69EAA3BA",
    },
    "body": {
        "file": "flux2-dev-ref-04-full-body.jpg",
        "role": "lean full-body proportions only",
        "sha256": "C5F57CC155075071F8F761356E3AD1153AA0BCE55825A52226B2A4E8A19365FC",
    },
}


REFERENCE_PROFILES = {
    GROUP_PROFILE: ("front",),
    SOLO_LEFT_PROFILE: ("front", "left"),
    SOLO_RIGHT_PROFILE: ("front", "right"),
    FULL_BODY_PROFILE: ("front", "body"),
}


def compose_effective_prompt(reference_profile: str, scene_prompt: str) -> str:
    if reference_profile not in REFERENCE_PROFILES:
        raise ValueError(f"Unknown reference profile: {reference_profile}")
    scene = " ".join(scene_prompt.strip().split())
    if not scene:
        raise ValueError("Describe the new photograph before queuing.")

    keys = REFERENCE_PROFILES[reference_profile]
    if keys == ("front",):
        reference_contract = (
            "Picture 1 shows m1tch_person, the one named central or foreground man. Match his identity, "
            "apparent age, face proportions, hairline, and natural skin. Use the new scene description "
            "for his clothing, pose, lighting, and setting. Every other adult is an unrelated individual "
            "with a clearly different face, hair, and age. The final photograph contains one Mitch."
        )
    else:
        roles = "; ".join(
            f"Picture {index} {REFERENCE_CATALOG[key]['role']}"
            for index, key in enumerate(keys, start=1)
        )
        reference_contract = (
            f"All reference pictures show the same real man, m1tch_person. {roles}. Match his identity, "
            "apparent age, face proportions, hairline, and body proportions. Use the new scene description "
            "for clothing, background, camera, pose, and lighting. Render one Mitch."
        )

    return " ".join(
        (
            reference_contract,
            scene,
            "His neck is bare, with no necklace, chain, pendant, or neck jewelry.",
            "Create one coherent photorealistic whole-frame image with natural skin texture, current apparent age, "
            "short brown hair and hairline, recognizable face geometry, complete limbs, coherent hands, believable "
            "body proportions, and seamless photographic integration. The final image is an uncaptioned, unbranded "
            "photograph.",
        )
    )
