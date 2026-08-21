from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "workflows" / "production" / "Qwen 2512 + ReActor - 9 Dating Photos.json"
EDIT_TEMPLATE_PATH = ROOT / "workflows" / "production" / "Qwen + ReActor Single-Person Scene Match.json"
OUTPUT_PATH = ROOT / "workflows" / "experiments" / "EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos.json"


SCENES = [
    {
        "number": 1,
        "slug": "01-night-out-a",
        "label": "NIGHT OUT A - WARM LOUNGE",
        "ref": "front",
        "target": "the third visible person from the left, the foreground man seated on the tan leather couch",
        "preserve": "exactly four people and four faces, the other three friends, their positions and identities, the curved tan booth, drinks, navy suit, open-collar white shirt, pose, hands, warm amber lighting, camera angle and vertical composition",
    },
    {
        "number": 2,
        "slug": "02-night-out-b",
        "label": "NIGHT OUT B - GROUP COUCH",
        "ref": "front",
        "target": "the second visible person from the left, the central primary man seated among the group",
        "preserve": "exactly four people and four faces, the other three friends, every seating position, clothing, drinks, couch, warm lounge lighting, camera angle and vertical composition",
    },
    {
        "number": 3,
        "slug": "03-cat-ragdoll",
        "label": "CAT LOVER - RAGDOLL",
        "ref": "right",
        "target": "the sole man holding the Ragdoll cat",
        "preserve": "the exact cat, the man's pose and gaze, hoodie, arms, hands, living-room background, lighting, camera angle and vertical composition",
    },
    {
        "number": 4,
        "slug": "04-cat-tabby",
        "label": "CAT LOVER - TABBY",
        "ref": "left",
        "target": "the sole man holding the tabby cat",
        "preserve": "the exact cat, the man's pose and gaze, hoodie, arms, hands, living-room background, lighting, camera angle and vertical composition",
    },
    {
        "number": 5,
        "slug": "05-golfer",
        "label": "GOLFER - TROPICAL COURSE",
        "ref": "front",
        "target": "the sole man walking on the golf course",
        "preserve": "his walking direction and limb positions, golf club, glove, black golf shirt, gray trousers, shoes, tropical course, lighting, camera angle and vertical composition",
        "template": "mitch-workbench-dating-05-golfer-safe.png",
    },
    {
        "number": 6,
        "slug": "06-amalfi",
        "label": "AMALFI - POSITANO BALCONY",
        "ref": "front",
        "target": "the sole man on the Positano balcony",
        "preserve": "his exact close three-quarter framing and relaxed railing pose, white linen shirt, both attached arms and complete hands, balcony railing, Positano coast, sea, lighting, camera angle and vertical composition; do not zoom out, reveal new legs, add shorts, or change the pose",
    },
    {
        "number": 7,
        "slug": "07-lake-boat",
        "label": "ITALIAN LAKE - CLASSIC BOAT",
        "ref": "front",
        "target": "the sole man on the classic lake boat",
        "preserve": "his exact waist-up braced pose with both attached arms and complete hands resting on the boat sides, sunglasses, open-collar long-sleeved white linen shirt, white shorts visible only to the existing crop, boat, lake, mountains, houses, lighting, camera angle and vertical composition; do not create a standing pose, lengthen the torso, reveal new legs, or move either hand",
    },
    {
        "number": 8,
        "slug": "08-restaurant",
        "label": "ELEGANT RESTAURANT",
        "ref": "front",
        "target": "the sole man seated at the restaurant table",
        "preserve": "his chin-on-hand pose, hand and fingers, gray jacket, black shirt, table, lamp, restaurant background, lighting, camera angle and vertical composition",
        "scene_correction": (
            "Correct the target's unrealistic short-sleeved jacket: give him a normal fitted long-sleeved gray blazer "
            "that covers both upper arms and reaches the wrists, while preserving the chin-on-hand pose and hand position. "
        ),
    },
    {
        "number": 9,
        "slug": "09-night-city",
        "label": "NIGHT CITY BALCONY",
        "ref": "left",
        "target": "the sole man leaning on the high balcony",
        "preserve": "his exact downward three-quarter head angle with eyes looking down and away from the camera, both attached arms in their original positions, both complete hands touching the railing, black open-collar shirt, black trousers, watch, glass balcony, city lights, lighting, camera angle and vertical composition; do not make eye contact, turn him toward the camera, hide an arm behind his torso, detach a hand, or change the pose",
    },
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reset_node(node: dict, node_id: int, pos: list[float], title: str) -> dict:
    node = copy.deepcopy(node)
    node["id"] = node_id
    node["pos"] = pos
    node["title"] = title
    for inp in node.get("inputs", []):
        if "link" in inp:
            inp["link"] = None
    for out in node.get("outputs", []):
        if "links" in out:
            out["links"] = None
    return node


def set_widget(node: dict, values) -> None:
    node["widgets_values"] = values


def standard_prompt(scene: dict) -> str:
    return (
        f"Picture 1 is the target photograph. Replace only {scene['target']} with the same real man "
        "shown in Picture 2. Picture 2 is the sole authority for his complete head identity: face and skull "
        "shape, forehead, hairline, short brown hair, ears, eyes, nose, mouth, jaw, age and natural skin texture. "
        "Give him a realistic slim-to-average build with medium-to-narrow natural shoulders, a modest chest, "
        "lean average arms, a straight torso and a natural waist. He is not muscular, broad-shouldered, bulky, "
        "bodybuilder shaped or strongly V-tapered. "
        f"{scene.get('scene_correction', '')}Preserve {scene['preserve']}. Do not copy Picture 2's clothing or background. "
        "Do not add, remove or duplicate any person or face. Photorealistic candid phone-camera detail."
    )


def rebuild_node_links(workflow: dict) -> None:
    nodes = {int(node["id"]): node for node in workflow["nodes"]}
    for node in nodes.values():
        for inp in node.get("inputs", []):
            if "link" in inp:
                inp["link"] = None
        for out in node.get("outputs", []):
            if "links" in out:
                out["links"] = []
    for link in workflow["links"]:
        link_id, src, src_slot, dst, dst_slot, _ = link
        nodes[int(src)]["outputs"][int(src_slot)]["links"].append(int(link_id))
        nodes[int(dst)]["inputs"][int(dst_slot)]["link"] = int(link_id)
    for node in nodes.values():
        for out in node.get("outputs", []):
            if "links" in out and not out["links"]:
                out["links"] = None


def build() -> dict:
    w = load(BASE_PATH)
    t = load(EDIT_TEMPLATE_PATH)
    tnodes = {int(node["id"]): node for node in t["nodes"]}
    nodes = {int(node["id"]): node for node in w["nodes"]}

    # Preserve the old workflow file; this builder only creates a separate v3 workflow.
    w["id"] = "a7841b7b-970b-4c21-9bc6-8a2c19f2ae31"
    w["revision"] = 0

    # Expand and rewrite the quick panel.
    note = nodes[1]
    note["size"] = [780, 790]
    note["widgets_values"] = [
        "EASY RUN\n\n"
        "1. CREATE NEW PHOTOS\n"
        "   false = approved exact scenes (fastest and recommended first run)\n"
        "   true = make new scene drafts from the editable prompts\n\n"
        "2. TABBY FULL HEAD IDENTITY LOCK\n"
        "   true = Qwen fixes the tabby scene head before ReActor\n"
        "   The other eight scenes use the faster, more reliable direct ReActor route.\n\n"
        "3. REACTOR FACE FINISH\n"
        "   true = proven blended three-photo identity model + GPEN detail\n"
        "   GPEN 0.70 improved eight scoreable scenes by 3.75 points over the CodeFormer finish\n\n"
        "   Eight scenes automatically use the proven ReActor-only route.\n"
        "   This preserves the original gaze, arms, hands, body proportions and scene composition.\n\n"
        "4. PHONE CAMERA STRENGTH\n"
        "   ONLY WORKS WHEN #1 CREATE NEW PHOTOS IS TRUE\n"
        "   0 off | 0.45 subtle | 0.65 recommended\n"
        "   It cannot change approved images when #1 is false.\n\n"
        "5. FACE DETAIL\n"
        "   0.70 validated GPEN identity/detail balance\n"
        "   0.55 softer | 0.70 recommended | 0.85 stronger restoration\n\n"
        "BODY LIMIT\n"
        "   No genuine unobstructed full-body reference is available. The golfer is anatomy-safe but its body is not identity-verified.\n"
        "   Add a neutral full-body front photo (and preferably a side photo) before calling body shape exact.\n\n"
        "Click Run. The workflow saves Stage 1, the optional tabby Qwen lock, and final outputs separately."
    ]
    nodes[2]["pos"] = [820.0, -2730.0]
    nodes[136]["pos"] = [820.0, -2240.0]
    nodes[2]["title"] = "1 - CREATE NEW PHOTOS? false exact | true new"
    nodes[2]["widgets_values"] = [False]
    nodes[5]["widgets_values"] = ["samsung_qwen2512.safetensors", 0.65]
    nodes[136]["title"] = "4 - PHONE LOOK | ACTIVE ONLY WHEN #1 IS TRUE | 0 off | 0.65 on"
    nodes[136]["widgets_values"] = [0.65]
    nodes[17]["title"] = "PROVEN BLENDED 3-PHOTO IDENTITY MODEL - ALL SCENES"

    next_node = 137
    next_link = max(int(link[0]) for link in w["links"]) + 1

    def add_node(template: dict, pos, title, widgets=None) -> dict:
        nonlocal next_node
        node = reset_node(template, next_node, [float(pos[0]), float(pos[1])], title)
        if widgets is not None:
            set_widget(node, widgets)
        w["nodes"].append(node)
        nodes[next_node] = node
        next_node += 1
        return node

    def add_link(src: int, src_slot: int, dst: int, dst_slot: int, link_type: str) -> int:
        nonlocal next_link
        link_id = next_link
        next_link += 1
        w["links"].append([link_id, src, src_slot, dst, dst_slot, link_type])
        return link_id

    # User controls.
    identity_control = add_node(nodes[2], [820, -2600], "2 - TABBY FULL HEAD IDENTITY LOCK", [True])
    reactor_control = add_node(nodes[2], [1260, -2600], "3 - REACTOR FACE FINISH", [True])
    detail_control = add_node(nodes[136], [1260, -2360], "5 - GPEN FACE DETAIL | 0.70 recommended", [0.70])

    # Shared Qwen Image Edit 2511 model and pose-matched identity bank.
    edit_unet = add_node(tnodes[1], [-3720, -210], "QWEN EDIT 2511 - FULL HEAD LOCK", ["qwen_image_edit_2511_fp8mixed.safetensors", "fp8_e4m3fn"])
    edit_lora = add_node(tnodes[2], [-3300, -210], "QWEN EDIT 2511 - 4 STEP LIGHTNING", ["Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", 1.0])
    edit_sampling = add_node(tnodes[3], [-2740, -210], "QWEN EDIT MODEL SAMPLING", [3.1])
    edit_clip = add_node(tnodes[4], [-3720, -30], "QWEN EDIT TEXT ENCODER", ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "qwen_image", "default"])
    edit_vae = add_node(tnodes[5], [-3310, -30], "QWEN EDIT VAE", ["qwen_image_vae.safetensors"])
    edit_negative = add_node(tnodes[6], [-2880, -30], "QWEN EDIT NEGATIVE - LEAVE EMPTY", [""])
    add_link(edit_unet["id"], 0, edit_lora["id"], 0, "MODEL")
    add_link(edit_lora["id"], 0, edit_sampling["id"], 0, "MODEL")
    add_link(edit_clip["id"], 0, edit_negative["id"], 0, "CLIP")

    front_load = add_node(tnodes[10], [-2050, -400], "QWEN ID BANK - FRONT", ["mitch-workbench-qwen-id-front.png", "image"])
    left_load = add_node(tnodes[10], [-1610, -400], "QWEN ID BANK - LEFT", ["mitch-workbench-qwen-id-left.png", "image"])
    right_load = add_node(tnodes[10], [-1170, -400], "QWEN ID BANK - RIGHT", ["mitch-workbench-qwen-id-right.png", "image"])
    front_scale = add_node(tnodes[20], [-2050, 120], "FRONT ID - 1 MP", ["lanczos", 1.0, 1])
    left_scale = add_node(tnodes[20], [-1610, 120], "LEFT ID - 1 MP", ["lanczos", 1.0, 1])
    right_scale = add_node(tnodes[20], [-1170, 120], "RIGHT ID - 1 MP", ["lanczos", 1.0, 1])
    for loader, scaler in ((front_load, front_scale), (left_load, left_scale), (right_load, right_scale)):
        add_link(loader["id"], 0, scaler["id"], 0, "IMAGE")
    ref_scales = {"front": front_scale["id"], "left": left_scale["id"], "right": right_scale["id"]}

    # Central controls drive the existing shared nodes.
    nodes[18]["title"] = "GPEN-BFR-512 FACE DETAIL — IDENTITY WINNER"
    nodes[18]["widgets_values"] = [True, "GPEN-BFR-512.onnx", "Lanczos", 0.70, 0.50, False]
    add_link(detail_control["id"], 0, 18, 3, "FLOAT")

    # Remove old Stage-1 image links and angle-specific face-model links to ReActor.
    # Every scene will use the three-photo blended model that won the measured A/B test.
    replaced_link_ids = set()
    for scene in SCENES:
        base = 19 + 13 * (scene["number"] - 1)
        switch_id = base + 5
        reactor_id = base + 9
        for link in w["links"]:
            if int(link[1]) == switch_id and int(link[3]) == reactor_id and str(link[5]) == "IMAGE":
                replaced_link_ids.add(int(link[0]))
            if int(link[3]) == reactor_id and str(link[5]) == "FACE_MODEL":
                replaced_link_ids.add(int(link[0]))
    w["links"] = [link for link in w["links"] if int(link[0]) not in replaced_link_ids]

    qwen_template = {n["type"]: n for n in t["nodes"]}
    # The template has multiple nodes of some types; these exact IDs are known-good examples.
    scale_template = tnodes[31]
    size_template = tnodes[32]
    latent_template = tnodes[33]
    encode_template = tnodes[34]
    sampler_template = tnodes[35]
    decode_template = tnodes[36]
    preview_template = tnodes[37]
    save_template = tnodes[38]
    switch_template = nodes[24]

    for scene in SCENES:
        number = scene["number"]
        base = 19 + 13 * (number - 1)
        selected_id = base + 5
        preview_stage1_id = base + 6
        save_stage1_id = base + 7
        options_id = base + 8
        reactor_id = base + 9
        always_id = base + 10
        preview_final_id = base + 11
        save_final_id = base + 12
        y = -1540 + 1120 * (number - 1)

        if scene.get("template"):
            nodes[base]["widgets_values"] = [scene["template"], "image"]

        # Make room for the Qwen identity/build stage.
        nodes[options_id]["pos"] = [5050.0, float(y + 20)]
        nodes[reactor_id]["pos"] = [5500.0, float(y + 10)]
        nodes[always_id]["pos"] = [5970.0, float(y + 120)]
        nodes[preview_final_id]["pos"] = [6400.0, float(y)]
        nodes[save_final_id]["pos"] = [6400.0, float(y + 530)]
        nodes[preview_final_id]["title"] = f"{number:02d} FINAL - GENUINE FACE"
        nodes[save_final_id]["title"] = f"{number:02d} SAVE FINAL"
        nodes[save_stage1_id]["widgets_values"] = [f"dating-app-easy-experimental-v8/{scene['slug']}/stage1"]
        nodes[save_final_id]["widgets_values"] = [f"dating-app-easy-experimental-v8/{scene['slug']}/final"]
        nodes[reactor_id]["title"] = f"{number:02d} REACTOR - PROVEN BLENDED 3-PHOTO IDENTITY"
        reactor_enabled_slot = next(i for i, item in enumerate(nodes[reactor_id]["inputs"]) if item["name"] == "enabled")
        reactor_image_slot = next(i for i, item in enumerate(nodes[reactor_id]["inputs"]) if item["name"] == "input_image")
        reactor_face_model_slot = next(i for i, item in enumerate(nodes[reactor_id]["inputs"]) if item["name"] == "face_model")
        add_link(reactor_control["id"], 0, reactor_id, reactor_enabled_slot, "BOOLEAN")
        add_link(17, 0, reactor_id, reactor_face_model_slot, "FACE_MODEL")

        # Whole-frame Qwen editing can duplicate identities, redraw limbs, or fail while streaming its large model.
        # Direct ReActor scored better for the ragdoll and restaurant scenes, so only the tabby branch retains Qwen.
        if number != 4:
            if number in (1, 2):
                nodes[reactor_id]["title"] = f"{number:02d} MULTI-PERSON CHECKPOINT - TARGETED REACTOR ONLY"
                nodes[preview_final_id]["title"] = f"{number:02d} FINAL - ONE TARGETED IDENTITY"
            elif number in (5, 6, 7, 9):
                nodes[reactor_id]["title"] = f"{number:02d} POSE-SAFE CHECKPOINT - REACTOR ONLY"
                nodes[preview_final_id]["title"] = f"{number:02d} FINAL - ORIGINAL POSE + GENUINE FACE"
            else:
                nodes[reactor_id]["title"] = f"{number:02d} IDENTITY WINNER - DIRECT REACTOR ONLY"
                nodes[preview_final_id]["title"] = f"{number:02d} FINAL - DIRECT GENUINE FACE"
            add_link(selected_id, 0, reactor_id, reactor_image_slot, "IMAGE")
            continue

        target_scale = add_node(scale_template, [2500, y], f"{number:02d} QWEN TARGET - 1.5 MP", ["lanczos", 1.5, 1])
        size = add_node(size_template, [2500, y + 220], f"{number:02d} TARGET SIZE")
        latent = add_node(latent_template, [2500, y + 380], f"{number:02d} EDIT LATENT", [512, 512, 1])
        encode = add_node(encode_template, [2920, y], f"{number:02d} IDENTITY PROMPT - POSE PRESERVING", [standard_prompt(scene)])
        sampler = add_node(sampler_template, [3370, y], f"{number:02d} STANDARD QWEN LOCK", [84033000 + number, "fixed", 4, 1.0, "euler", "simple", 1.0])
        decode = add_node(decode_template, [3730, y + 40], f"{number:02d} STANDARD DECODE")
        add_link(selected_id, 0, target_scale["id"], 0, "IMAGE")
        add_link(target_scale["id"], 0, size["id"], 0, "IMAGE")
        add_link(size["id"], 0, latent["id"], 0, "INT")
        add_link(size["id"], 1, latent["id"], 1, "INT")
        add_link(edit_clip["id"], 0, encode["id"], 0, "CLIP")
        add_link(edit_vae["id"], 0, encode["id"], 1, "VAE")
        add_link(target_scale["id"], 0, encode["id"], 2, "IMAGE")
        add_link(ref_scales[scene["ref"]], 0, encode["id"], 3, "IMAGE")
        add_link(edit_sampling["id"], 0, sampler["id"], 0, "MODEL")
        add_link(encode["id"], 0, sampler["id"], 1, "CONDITIONING")
        add_link(edit_negative["id"], 0, sampler["id"], 2, "CONDITIONING")
        add_link(latent["id"], 0, sampler["id"], 3, "LATENT")
        add_link(sampler["id"], 0, decode["id"], 0, "LATENT")
        add_link(edit_vae["id"], 0, decode["id"], 1, "VAE")

        chosen_edit_id = decode["id"]

        lock_switch = add_node(switch_template, [4470, y], f"{number:02d} FULL HEAD LOCK | false off | true on", [True])
        qwen_preview = add_node(preview_template, [4470, y + 220], f"{number:02d} STAGE 2 - QWEN HEAD IDENTITY")
        qwen_save = add_node(save_template, [4470, y + 730], f"{number:02d} SAVE QWEN LOCK", [f"dating-app-easy-experimental-v8/{scene['slug']}/qwen-lock"])
        add_link(selected_id, 0, lock_switch["id"], 0, "IMAGE")
        add_link(chosen_edit_id, 0, lock_switch["id"], 1, "IMAGE")
        add_link(identity_control["id"], 0, lock_switch["id"], 2, "BOOLEAN")
        add_link(lock_switch["id"], 0, qwen_preview["id"], 0, "IMAGE")
        add_link(lock_switch["id"], 0, qwen_save["id"], 0, "IMAGE")
        add_link(lock_switch["id"], 0, reactor_id, reactor_image_slot, "IMAGE")

    # Expand scene groups and add a shared Qwen group.
    for group in w.get("groups", []):
        if 3 <= int(group["id"]) <= 11:
            group["bounding"][2] = 6960.0
            group["bounding"][3] = 1040.0
    w.setdefault("groups", []).append(
        {
            "id": 12,
            "title": "QWEN EDIT 2511 - FULL HEAD IDENTITY FOR SAFE CLOSE SCENES",
            "bounding": [-3790.0, -510.0, 3540.0, 950.0],
            "color": "#4f6f52",
            "font_size": 24,
            "flags": {},
        }
    )
    w["groups"][0]["bounding"] = [-70.0, -2820.0, 1770.0, 980.0]

    # Open on the control panel.
    w.setdefault("extra", {}).setdefault("ds", {})["scale"] = 0.52
    w["extra"]["ds"]["offset"] = [150, 2860]
    w["extra"]["frontendVersion"] = "1.45.15"

    w["last_node_id"] = max(int(node["id"]) for node in w["nodes"])
    w["last_link_id"] = max(int(link[0]) for link in w["links"])
    rebuild_node_links(w)
    return w


if __name__ == "__main__":
    workflow = build()
    OUTPUT_PATH.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    print(f"nodes={len(workflow['nodes'])} links={len(workflow['links'])}")
