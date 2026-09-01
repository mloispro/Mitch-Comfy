from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "templates" / "hidream-o1" / "image_hidream_o1_full.source.json"
OUTPUT = (
    ROOT
    / "checkpoints"
    / "legacy-workflows"
    / "experiments"
    / "HiDream-O1 Full Native 2-Reference Dating Identity - Test.json"
)

MODEL = "hidream_o1_image_fp8_scaled.safetensors"
REFERENCE_1 = "20260815_165446.jpg"
REFERENCE_2 = "20260818_173106.jpg"
SEED = 8675601
WIDTH = 1728
HEIGHT = 2304
STEPS = 40

PROMPT = (
    "References 1 and 2 are genuine photographs of Mitch, the same real man, and define the exact "
    "identity of the only main subject. Create a completely new photorealistic vertical rear-camera "
    "smartphone photograph of that exact same man at a relaxed neighborhood restaurant patio in early "
    "evening. Preserve his current apparent age, high forehead and hairline, short light-brown hair, "
    "blue-gray eye shape and spacing, nose, ears, mouth, narrow jaw, faint natural stubble, lean build, "
    "and unretouched skin texture. Frame him naturally from the waist upward, slightly off center, with "
    "a mild three-quarter face, both eyes comfortably open, and a small relaxed smile while he looks a "
    "few degrees past the camera toward a friend. He wears a simple deep-navy open-collar shirt. Show "
    "ordinary patio tables, varied unrelated diners, planters, storefront windows, and warm practical "
    "lights at believable depth. Use an eye-level handheld 1x phone-camera view, normal automatic "
    "exposure, restrained HDR, natural deep focus, slight shadow noise, and imperfect candid framing. "
    "Keep every background person distinct from Mitch. The result must look like an ordinary dating-"
    "profile snapshot, with no beauty filter, studio lighting, face smoothing, portrait-mode blur, "
    "cinematic grading, text, logo, or watermark."
)


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_nodes = {node["id"]: node for node in source["nodes"]}

    def clone(node_id: int, *, new_id: int | None = None) -> dict:
        node = copy.deepcopy(source_nodes[node_id])
        if new_id is not None:
            node["id"] = new_id
        for item in node.get("inputs", []):
            item["link"] = None
        for item in node.get("outputs", []):
            item["links"] = []
        node["mode"] = 0
        return node

    checkpoint = clone(6)
    checkpoint["pos"] = [-1600, -20]
    checkpoint["widgets_values"] = [MODEL]

    model_noise = clone(124)
    model_noise["pos"] = [-1160, -20]
    model_noise["widgets_values"] = [8.0]

    seam_smoothing = clone(232)
    seam_smoothing["pos"] = [-750, -20]
    seam_smoothing["title"] = "Official Full late patch-seam smoothing"
    seam_smoothing["widgets_values"] = [0.8, 1.0, "single_shift", "ramp_2_4", "median", 1.0]

    ref_1 = clone(213)
    ref_1["pos"] = [-1600, 230]
    ref_1["title"] = "Reference 1 - genuine front/near-front photo"
    ref_1["widgets_values"] = [REFERENCE_1, "image"]

    ref_2 = clone(213, new_id=214)
    ref_2["pos"] = [-1600, 650]
    ref_2["title"] = "Reference 2 - genuine complementary angle"
    ref_2["widgets_values"] = [REFERENCE_2, "image"]

    positive = clone(110)
    positive["pos"] = [-1160, 230]
    positive["size"] = [520, 520]
    positive["title"] = "Frozen HiDream prompt - same as Dev comparison"
    positive["widgets_values"] = [PROMPT]

    negative = clone(188)
    negative["pos"] = [-1160, 790]
    negative["title"] = "Empty negative prompt (official Full template)"
    negative["widgets_values"] = [""]

    references = clone(104)
    references["pos"] = [-560, 290]
    references["title"] = "Native subject personalization: two genuine photos"

    latent = clone(156)
    latent["pos"] = [-560, 590]
    latent["title"] = "Official trained portrait canvas (~4 MP)"
    latent["widgets_values"] = [WIDTH, HEIGHT, 1]

    scheduler = clone(112)
    scheduler["pos"] = [-160, 240]
    scheduler["widgets_values"] = ["normal", STEPS, 1]

    sampler_select = clone(230)
    sampler_select["pos"] = [-160, 420]
    sampler_select["widgets_values"] = ["dpmpp_2m_sde_gpu"]

    sampler = clone(108)
    sampler["pos"] = [180, 80]
    sampler["widgets_values"] = [True, SEED, "fixed", 5.0]

    decode = clone(105)
    decode["pos"] = [520, 100]

    save = clone(227)
    save["pos"] = [800, 100]
    save["widgets_values"] = ["hidream-o1-reference-dating-full-v1/frozen-comparison-1728x2304"]

    note = clone(226, new_id=234)
    note["pos"] = [-560, 790]
    note["size"] = [690, 330]
    note["title"] = "Controlled Full-model comparison"
    note["widgets_values"] = [
        "This graph uses the official undistilled HiDream-O1 Full ComfyUI recipe: noise scale 8, "
        "40 steps, CFG 5, normal scheduler, DPM++ 2M SDE GPU, and late patch-seam smoothing. "
        "The two genuine references, prompt, order, seed, and trained 1728x2304 canvas are frozen "
        "from the Dev result. No character LoRA, face swap, mask, restoration, output refiner, or "
        "prompt enhancer is present. The tested Full result improved the waist-up restaurant "
        "composition but was slower, smoother, and weaker in identity than Dev. Disabling seam "
        "smoothing exposed severe patch-grid artifacts. This is a preserved research baseline, not "
        "an approved dating-photo recipe."
    ]

    nodes = [
        checkpoint,
        model_noise,
        seam_smoothing,
        ref_1,
        ref_2,
        positive,
        negative,
        references,
        latent,
        scheduler,
        sampler_select,
        sampler,
        decode,
        save,
        note,
    ]
    by_id = {node["id"]: node for node in nodes}
    for order, node in enumerate(nodes):
        node["order"] = order

    links: list[list] = []

    def connect(origin_id: int, origin_slot: int, target_id: int, input_name: str, kind: str) -> None:
        link_id = len(links) + 1
        target_inputs = by_id[target_id].get("inputs", [])
        target_slot = next(
            index for index, value in enumerate(target_inputs) if value["name"] == input_name
        )
        target_inputs[target_slot]["link"] = link_id
        output = by_id[origin_id]["outputs"][origin_slot]
        output.setdefault("links", []).append(link_id)
        links.append([link_id, origin_id, origin_slot, target_id, target_slot, kind])

    connect(6, 0, 124, "model", "MODEL")
    connect(124, 0, 232, "model", "MODEL")
    connect(6, 1, 110, "clip", "CLIP")
    connect(6, 1, 188, "clip", "CLIP")
    connect(110, 0, 104, "positive", "CONDITIONING")
    connect(188, 0, 104, "negative", "CONDITIONING")
    connect(213, 0, 104, "images.image_1", "IMAGE")
    connect(214, 0, 104, "images.image_2", "IMAGE")
    connect(124, 0, 112, "model", "MODEL")
    connect(232, 0, 108, "model", "MODEL")
    connect(104, 0, 108, "positive", "CONDITIONING")
    connect(104, 1, 108, "negative", "CONDITIONING")
    connect(230, 0, 108, "sampler", "SAMPLER")
    connect(112, 0, 108, "sigmas", "SIGMAS")
    connect(156, 0, 108, "latent_image", "LATENT")
    connect(108, 0, 105, "samples", "LATENT")
    connect(6, 2, 105, "vae", "VAE")
    connect(105, 0, 227, "images", "IMAGE")

    workflow = copy.deepcopy(source)
    workflow["id"] = str(uuid.uuid4())
    workflow["revision"] = 0
    workflow["last_node_id"] = max(by_id)
    workflow["last_link_id"] = len(links)
    workflow["nodes"] = nodes
    workflow["links"] = links
    workflow["groups"] = []
    workflow["definitions"] = {"subgraphs": []}
    workflow["extra"]["ds"] = {"scale": 0.7, "offset": [1700, 340]}

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
