from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "templates" / "hidream-o1" / "image_hidream_o1_dev.source.json"
OUTPUT = (
    ROOT
    / "checkpoints"
    / "legacy-workflows"
    / "experiments"
    / "HiDream-O1 Dev Native 3-Reference Dating Identity - Seed Screen.json"
)

MODEL = "hidream_o1_image_dev_fp8_scaled.safetensors"
REFERENCES = [
    "hidream-o1-ref-01-sweater-front-neutral.jpg",
    "hidream-o1-ref-02-opposite-profile.jpg",
    "hidream-o1-ref-03-laundry-angle.jpg",
]
SEED = 8675601
WIDTH = 1728
HEIGHT = 2304
STEPS = 28

PROMPT = (
    "References 1, 2, and 3 are genuine photographs of Mitch, the same real man, and define the exact "
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
    checkpoint["pos"] = [-1540, -20]
    checkpoint["widgets_values"] = [MODEL]

    model_noise = clone(124)
    model_noise["pos"] = [-1060, -20]
    model_noise["widgets_values"] = [7.6]

    reference_nodes = []
    for index, filename in enumerate(REFERENCES):
        node = clone(213, new_id=213 + index)
        node["pos"] = [-1540, 230 + index * 420]
        node["title"] = f"Reference {index + 1} - genuine identity photo"
        node["widgets_values"] = [filename, "image"]
        reference_nodes.append(node)

    positive = clone(110)
    positive["pos"] = [-1100, 230]
    positive["size"] = [540, 520]
    positive["title"] = "Frozen baseline scene prompt (three references named)"
    positive["widgets_values"] = [PROMPT]

    negative = clone(188)
    negative["pos"] = [-1100, 790]
    negative["title"] = "Empty negative prompt (official Dev recipe)"
    negative["widgets_values"] = [""]

    references = clone(104)
    references["pos"] = [-500, 290]
    references["size"] = [280, 150]
    references["title"] = "Native subject personalization: three genuine photos"
    references["inputs"].append(
        {
            "label": "image_3",
            "name": "images.image_3",
            "shape": 7,
            "type": "IMAGE",
            "link": None,
        }
    )

    latent = clone(156)
    latent["pos"] = [-500, 590]
    latent["title"] = "Official trained portrait canvas (~4 MP)"
    latent["widgets_values"] = [WIDTH, HEIGHT, 1]

    scheduler = clone(112)
    scheduler["pos"] = [-160, 40]
    scheduler["widgets_values"] = ["normal", STEPS, 1]

    sampler_lcm = clone(125)
    sampler_lcm["pos"] = [-160, 220]
    sampler_lcm["widgets_values"] = [1, 1, 2.5]

    sampler = clone(108)
    sampler["pos"] = [180, 80]
    sampler["widgets_values"] = [True, SEED, "fixed", 1]

    decode = clone(105)
    decode["pos"] = [520, 100]

    save = clone(227)
    save["pos"] = [800, 100]
    save["widgets_values"] = ["hidream-o1-reference-dating-3ref-v1/seed-8675601"]

    note = clone(226, new_id=230)
    note["pos"] = [-500, 790]
    note["size"] = [650, 330]
    note["title"] = "Experiment lock and limits"
    note["widgets_values"] = [
        "HiDream-O1 Dev native subject-driven personalization receives three genuine photos: "
        "a high-resolution front view, a high-resolution opposite near-profile, and a newer "
        "independent-session angle. Reference order is fixed. The checkpoint, 1728x2304 canvas, "
        "28-step LCM recipe, CFG 1, noise scale 7.6, and baseline scene are unchanged; only the "
        "necessary reference count wording changed. Seed 8675601 is the strict stronger-reference "
        "A/B against the prior two-reference run. No LoRA, face swap, mask, restoration, refinement, "
        "or upload is present. Identity metrics are diagnostics and require visual review."
    ]

    nodes = [
        checkpoint,
        model_noise,
        *reference_nodes,
        positive,
        negative,
        references,
        latent,
        scheduler,
        sampler_lcm,
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
    connect(6, 1, 110, "clip", "CLIP")
    connect(6, 1, 188, "clip", "CLIP")
    connect(110, 0, 104, "positive", "CONDITIONING")
    connect(188, 0, 104, "negative", "CONDITIONING")
    for index, node in enumerate(reference_nodes):
        connect(node["id"], 0, 104, f"images.image_{index + 1}", "IMAGE")
    connect(124, 0, 112, "model", "MODEL")
    connect(124, 0, 108, "model", "MODEL")
    connect(104, 0, 108, "positive", "CONDITIONING")
    connect(104, 1, 108, "negative", "CONDITIONING")
    connect(125, 0, 108, "sampler", "SAMPLER")
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
    workflow["extra"]["ds"] = {"scale": 0.68, "offset": [1740, 330]}

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
