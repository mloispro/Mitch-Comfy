from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CUSTOM_IDENTITY_PRESET = "Custom — write your own scene"
CUSTOM_GROUP_PRESET = "Custom — uploaded group photo"

GROUP_PROFILE = "GROUP — front only (one Mitch)"
SOLO_LEFT_PROFILE = "SOLO — front + left-facing angle"
SOLO_RIGHT_PROFILE = "SOLO — front + right-facing angle"
FULL_BODY_PROFILE = "FULL BODY — front + body proportions"


IDENTITY_SCENE_PRESETS = {
    CUSTOM_IDENTITY_PRESET: {
        "key": "custom",
        "prompt": "",
        "profile": SOLO_RIGHT_PROFILE,
        "thumbnail": "identity-custom.jpg",
    },
    "Founder editorial — modern studio": {
        "key": "founder-editorial",
        "profile": SOLO_RIGHT_PROFILE,
        "thumbnail": "identity-founder-editorial.jpg",
        "prompt": (
            "A premium but authentic personal-brand portrait of m1tch_person in a bright modern creative studio "
            "beside a large window. He wears a tailored charcoal overshirt over a white crew-neck shirt, with relaxed "
            "confidence and a subtle natural closed-lip half-smile."
        ),
    },
    "Cooking candid — warm modern kitchen": {
        "key": "cooking-candid",
        "profile": SOLO_RIGHT_PROFILE,
        "thumbnail": "identity-cooking-candid.jpg",
        "prompt": (
            "A candid photograph of m1tch_person preparing and plating a simple dinner in a tasteful modern home "
            "kitchen at early evening. He wears a fitted dark navy crew-neck T-shirt and looks quietly capable and "
            "warm, with believable complete hands and fresh ingredients."
        ),
    },
    "Golden-hour rooftop — linen shirt": {
        "key": "golden-hour-rooftop",
        "profile": SOLO_RIGHT_PROFILE,
        "thumbnail": "identity-golden-hour-rooftop.jpg",
        "prompt": (
            "A vertical candid portrait of m1tch_person on an elegant rooftop terrace during golden hour near the city "
            "skyline. He wears a pale blue linen shirt with an open collar and casually rolled sleeves, with relaxed "
            "posture and a warm restrained closed-lip smile."
        ),
    },
    "Night city balcony — black open-collar shirt": {
        "key": "night-city-balcony",
        "profile": SOLO_RIGHT_PROFILE,
        "thumbnail": "identity-night-city-balcony.jpg",
        "prompt": (
            "A vertical candid nighttime rooftop phone photograph of m1tch_person standing at a high balcony railing. "
            "His torso faces nearly toward the camera while his head turns and tilts gently down toward image-right. "
            "Both complete arms extend diagonally outward to the railing. He wears a fitted black short-sleeve "
            "open-collar shirt, dark trousers, a dark wristwatch, and a flattering contemporary textured side-part "
            "with a subtle low taper. Dense city lights spread below a deep teal-black sky. Direct phone flash, natural "
            "skin texture, mild high-ISO grain, and generous dark sky above his head."
        ),
    },
    "Rooftop cocktail — city lights": {
        "key": "rooftop-cocktail-city-lights",
        "profile": SOLO_LEFT_PROFILE,
        "thumbnail": "identity-rooftop-cocktail.jpg",
        "prompt": (
            "A vertical candid rooftop cocktail portrait at night. m1tch_person is framed from head through upper thighs "
            "in a fitted black long-sleeve button-up shirt with an open collar and a completely bare neck. His arm at "
            "image-left rests naturally on a wooden railing while that hand holds a short clear tumbler; his other hand "
            "rests in his trouser pocket at image-right. He wears a simple metal wristwatch, gives a relaxed restrained "
            "closed-lip smile, and looks slightly off-camera toward image-left. Dense city lights fill the background, "
            "with warm rooftop string lights and a few distant patrons at image-right. Natural direct phone flash, "
            "realistic hands, natural skin, and seamless nighttime integration."
        ),
    },
    "Amalfi balcony — white linen": {
        "key": "amalfi-balcony",
        "profile": SOLO_RIGHT_PROFILE,
        "thumbnail": "identity-amalfi-balcony.jpg",
        "prompt": (
            "A vertical vacation photograph of m1tch_person on a Positano balcony above the Amalfi coast in warm "
            "late-afternoon sun. He wears a relaxed white linen shirt and rests one complete hand on the railing, with "
            "the blue sea and colorful hillside town clearly visible."
        ),
    },
    "Italian lake boat — relaxed travel": {
        "key": "italian-lake-boat",
        "profile": FULL_BODY_PROFILE,
        "thumbnail": "identity-italian-lake-boat.jpg",
        "prompt": (
            "A close vertical rear-phone travel photograph of m1tch_person seated on the white bow edge of a motorboat "
            "on Lake Como. He wears a lightweight white linen button-down shirt with rolled sleeves, pale beige linen "
            "shorts, black rectangular sunglasses, and a wristwatch. One knee is raised toward the camera and both "
            "complete arms brace naturally on the side rails. Dark green water, lakeside villas, forested mountains, "
            "exposed cliffs, and a bright sky fill the background."
        ),
    },
    "Elegant restaurant — understated evening": {
        "key": "elegant-restaurant",
        "profile": SOLO_RIGHT_PROFILE,
        "thumbnail": "identity-elegant-restaurant.jpg",
        "prompt": (
            "A vertical evening portrait of m1tch_person seated at an elegant modern restaurant table beside a small "
            "warm lamp. He wears a fitted gray blazer over a black open-collar shirt and has a thoughtful relaxed "
            "closed-lip expression. Restrained luxury, natural skin, believable hands, and ordinary phone-camera depth."
        ),
    },
    "Cat lover — Ragdoll": {
        "key": "ragdoll-cat",
        "profile": SOLO_LEFT_PROFILE,
        "thumbnail": "identity-ragdoll-cat.jpg",
        "prompt": (
            "A relaxed home photograph of m1tch_person in a clean black zip hoodie gently holding a large fluffy "
            "Ragdoll cat. He looks down at the cat with an affectionate natural closed-lip smile. Both complete arms "
            "support the cat comfortably, with anatomically believable hands, soft window light, and realistic fur."
        ),
    },
    "Toddler moment — warm family candid": {
        "key": "toddler-moment",
        "profile": GROUP_PROFILE,
        "thumbnail": "identity-toddler-moment.jpg",
        "prompt": (
            "A warm candid lifestyle photograph of m1tch_person sharing a natural playful moment with one fully clothed "
            "toddler in a bright comfortable home. Mitch is clearly the adult subject, with a gentle relaxed expression "
            "and believable protective hand placement. The toddler has a distinct unrelated face and age-appropriate "
            "proportions. Natural window light, realistic skin, complete hands and limbs, and an unposed family snapshot."
        ),
    },
    "Dog lover — small Golden Shepherd puppy": {
        "key": "golden-shepherd-puppy",
        "profile": SOLO_LEFT_PROFILE,
        "thumbnail": "identity-golden-shepherd-puppy.jpg",
        "prompt": (
            "A relaxed home lifestyle photograph of m1tch_person gently holding a small Golden Shepherd puppy, a young "
            "Golden Retriever and German Shepherd mix with soft golden-tan fur and slightly darker ears. Mitch looks "
            "down at the puppy with a warm restrained closed-lip smile. Both complete arms support the puppy comfortably "
            "with natural hands, soft window light, realistic fur and skin, and an authentic candid snapshot."
        ),
    },
    "Golf course — tropical morning": {
        "key": "golf-course",
        "profile": FULL_BODY_PROFILE,
        "thumbnail": "identity-golf-course.jpg",
        "prompt": (
            "A full-body candid photograph of m1tch_person walking naturally on a beautiful tropical golf course in "
            "clear morning light. He wears a fitted black golf polo and tailored gray trousers, carrying one golf club "
            "with easy athletic posture. Show both complete arms, hands, legs, and feet with believable proportions."
        ),
    },
    "Weekend lake — fitted T-shirt": {
        "key": "weekend-lake",
        "profile": FULL_BODY_PROFILE,
        "thumbnail": "identity-weekend-lake.jpg",
        "prompt": (
            "A natural weekend photograph of m1tch_person standing at the end of a wooden lake dock in clear morning "
            "light. He wears a fitted heather-blue crew-neck T-shirt and casual dark trousers, with a relaxed stance and "
            "a small closed-lip smile. Calm water and a green shoreline extend behind him."
        ),
    },
    "Downtown menswear — sunrise": {
        "key": "downtown-menswear",
        "profile": FULL_BODY_PROFILE,
        "thumbnail": "identity-downtown-menswear.jpg",
        "prompt": (
            "A natural full-body menswear photograph of m1tch_person on a clean downtown sidewalk just after sunrise. "
            "He wears a fitted black bomber jacket over a muted gray shirt with dark trousers, natural posture, subtle "
            "urban depth, complete hands and feet, and the texture of an unretouched editorial photograph."
        ),
    },
}


GROUP_SCENE_PRESETS = {
    CUSTOM_GROUP_PRESET: {
        "key": "custom-group",
        "thumbnail": "group-custom.jpg",
        "source_asset": None,
        "source_sha256": None,
        "target_x": 0.50,
        "target_y": 0.44,
        "head_scale": 0.92,
        "prompt": "",
    },
    "Approved lounge — central Mitch": {
        "key": "approved-lounge-center",
        "thumbnail": "group-approved-lounge.jpg",
        "source_asset": "assets/comfy-input/klein9b-scene-presets/group-approved-lounge-center.png",
        "source_sha256": "1B26AC58A4FAD8D03F69DB7A4085C31B6682C71ACBE22D5AEE51F9E53FA0332B",
        "target_x": 0.50,
        "target_y": 0.44,
        "head_scale": 0.92,
        "prompt": (
            "Create one photorealistic vertical phone-flash group photograph matching Picture 1. Four adults sit "
            "closely on the rust-orange booth, with a partial fifth person at the extreme image-right edge. The central "
            "seated man is m1tch_person from Picture 2, wearing a fitted dark navy suit and crisp white open-collar "
            "shirt. His lips rest gently together, their corners rise only slightly, and his eyes engage softly with "
            "the camera. Both complete forearms extend down and his separate hands rest on his thighs. Keep every "
            "surrounding person distinct and unrelated. Preserve the copper wall, amber perimeter light, booth, low "
            "table, ordinary smartphone perspective, direct flash, and seamless natural detail."
        ),
    },
    "Night out A — corner booth": {
        "key": "night-out-a",
        "thumbnail": "group-night-out-a.jpg",
        "source_asset": "assets/comfy-input/dating-scenes/dating-01-night-out-a.png",
        "source_sha256": "A7C6E79FBDE486F5B0656734929212E28903DD3E171B72DB030F300A41242E6E",
        "target_x": 0.52,
        "target_y": 0.30,
        "head_scale": 0.92,
        "prompt": (
            "Create one photorealistic vertical phone-flash lounge photograph matching Picture 1. The seated foreground "
            "man is m1tch_person in a dark navy suit and open-collar white shirt. Three unrelated adult friends remain "
            "around and behind him with clearly distinct faces. Preserve the caramel corner booth, relaxed crossed-leg "
            "pose, warm amber wall, small tables, drinks, direct flash, and exactly one Mitch."
        ),
    },
    "Night out B — group booth": {
        "key": "night-out-b",
        "thumbnail": "group-night-out-b.jpg",
        "source_asset": "assets/comfy-input/dating-scenes/dating-02-night-out-b.png",
        "source_sha256": "112BC35873374EA85B8F5C2C4A58E028FFA45160CBBAA851DD71413991CAC68F",
        "target_x": 0.46,
        "target_y": 0.33,
        "head_scale": 0.92,
        "prompt": (
            "Create one photorealistic vertical phone-flash group photograph matching Picture 1. The central seated man "
            "is m1tch_person in a fitted navy suit and open-collar white shirt. Four unrelated adult friends surround "
            "him with clearly different faces, hair, and ages. Preserve the curved amber booth, close social spacing, "
            "low cocktail table, glasses, direct flash, and exactly one Mitch."
        ),
    },
    "Amber booth — four friends": {
        "key": "amber-booth-four-friends",
        "thumbnail": "group-amber-booth.jpg",
        "source_asset": "assets/comfy-input/klein9b-scene-presets/group-amber-booth-four-friends.jpg",
        "source_sha256": "1F6E9C7A4AC4C6E152D2B54ECB9007732EC4799201B287B7F543700EF8D0204B",
        "target_x": 0.51,
        "target_y": 0.45,
        "head_scale": 0.92,
        "prompt": (
            "Create one photorealistic vertical phone-flash group photograph matching Picture 1. Four adults sit on "
            "the rust-orange curved booth. The central seated man is m1tch_person, wearing a fitted navy suit and crisp "
            "white open-collar shirt, with both complete hands resting naturally near his knees. A brunette woman at "
            "image-left holds a martini glass, a blonde woman sits close at his image-right, and a dark-haired man in a "
            "denim jacket sits farther right. Every bystander has a clearly distinct unrelated face, hair, and age. "
            "Preserve the large curved amber wall light, textured wall, booth, wooden tables, glasses, plates, casual "
            "spacing, ordinary smartphone perspective, direct flash, and exactly one Mitch."
        ),
    },
}


def _clean(value: str) -> str:
    return " ".join((value or "").strip().split())


def resolve_identity_scene(scene_preset: str, custom_scene_prompt: str) -> tuple[str, dict]:
    if scene_preset not in IDENTITY_SCENE_PRESETS:
        raise ValueError(f"Unknown Identity Studio scene preset: {scene_preset}")
    record = IDENTITY_SCENE_PRESETS[scene_preset]
    custom = _clean(custom_scene_prompt)
    if scene_preset == CUSTOM_IDENTITY_PRESET:
        if not custom:
            raise ValueError("Write a custom scene or choose a visual preset.")
        return custom, record
    prompt = record["prompt"]
    if custom:
        prompt = f"{prompt} Additional scene direction: {custom}"
    return prompt, record


def resolve_group_scene(scene_preset: str, custom_scene_prompt: str) -> tuple[str, dict]:
    if scene_preset not in GROUP_SCENE_PRESETS:
        raise ValueError(f"Unknown Group Scene Studio preset: {scene_preset}")
    record = GROUP_SCENE_PRESETS[scene_preset]
    custom = _clean(custom_scene_prompt)
    if scene_preset == CUSTOM_GROUP_PRESET:
        if not custom:
            raise ValueError("Describe the uploaded group photograph or choose a visual preset.")
        return custom, record
    prompt = record["prompt"]
    if custom:
        prompt = f"{prompt} Additional scene direction: {custom}"
    return prompt, record


def preset_asset_path(record: dict) -> Path | None:
    relative = record.get("source_asset")
    return None if not relative else PROJECT_ROOT / relative
