"""Prepare one existing-character-LoRA fallback control for native Klein High.

Changes only character strength0->0.9 and output prefix. Default never submits.
--execute requires review and fresh idle RTX3090/owned-terminal-cache evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from runpy import run_path
import uuid

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
BASELINE = ROOT / "work/upgrade-high-20260907/third-native-high-pilot"
DESTINATION = ROOT / "work/upgrade-high-20260907/third-native-high-character-control"
BASELINE_RAW = COMFY / "output/upgrade-high-20260907/third-native-high-pilot/raw_00001_.png"
PILOT_SCRIPT = ROOT / "scripts/run-upgrade-native-high-pilot.py"
PINS = {
    PILOT_SCRIPT: "7c24015966f9a6615276ce6273a6ee44b924cf7908e504187341c1f4f0c4669f",
    BASELINE / "experiment.json": "3a2acdccec49b0ac1c0f103bc9252949570c24534590fa897ed44537536f94ab",
    BASELINE / "prompt-api.json": "b705ea345ba90fdfe361aa62a5dd98b9f4b6b8d646094733c83509f79e8e3b7a",
    BASELINE / "submission.json": "b00dba0d9aa00e3a197862524d9bd4a0ca8ab8964386ab2512095bb4842cd872",
    BASELINE_RAW: "cf86a1bcef245a0d032e77388a86fe3c982630e73be9da47dbbdca343433f07b",
}


def load_helpers():
    if hashlib.sha256(PILOT_SCRIPT.read_bytes()).hexdigest() != PINS[PILOT_SCRIPT]:
        raise ValueError("The reviewed native High pilot implementation changed.")
    pilot = run_path(str(PILOT_SCRIPT))
    return pilot, pilot["load_helper"]()


def build_verified_manifest(pilot, helper):
    for path, expected in PINS.items():
        if helper.sha(path) != expected:
            raise ValueError("Pinned completed native High evidence changed: " + str(path))
    baseline = helper.read_json(BASELINE / "experiment.json")
    baseline_graph = helper.clean_graph(baseline["prompt"])
    # Re-run the existing source/model/author-layout verification through its
    # reviewed implementation; do not mutate or re-prepare that earlier run.
    revalidated = pilot["build_verified_manifest"](helper)
    if {key: value for key, value in baseline.items() if key != "preparation_snapshot"} != revalidated:
        raise ValueError("Completed High baseline differs from its exact reviewed preparation.")
    if helper.read_json(BASELINE / "prompt-api.json") != baseline_graph:
        raise ValueError("Baseline standalone graph differs from manifest.")
    prompt_id = helper.read_json(BASELINE / "submission.json")["prompt_id"]
    history = helper.api("history/" + prompt_id).get(prompt_id)
    if not history or not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("The exact no-character High baseline has not completed successfully.")
    if history["prompt"][1] != prompt_id or helper.clean_graph(history["prompt"][2]) != baseline_graph:
        raise ValueError("Completed High history graph differs from saved baseline.")
    images = history["outputs"]["27"]["images"]
    if len(images) != 1 or images[0]["type"] != "output":
        raise ValueError("Expected exactly one native High baseline output.")
    output = (COMFY / "output" / images[0].get("subfolder", "") / images[0]["filename"]).resolve()
    if output != BASELINE_RAW.resolve():
        raise ValueError("Completed High output path differs from its pinned output.")
    with Image.open(BASELINE_RAW) as image:
        if image.size != (816, 1088) or helper.clean_graph(json.loads(image.info["prompt"])) != baseline_graph:
            raise ValueError("Native High baseline PNG dimensions/graph mismatch.")
    if baseline_graph["2"]["inputs"]["strength_model"] != 0 or baseline_graph["6"]["inputs"]["text"] != pilot["PROMPT"]:
        raise ValueError("The exact no-character High prompt baseline is required.")
    graph = copy.deepcopy(baseline_graph)
    graph["2"]["inputs"]["strength_model"] = .9
    graph["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-native-high-character-control/raw"
    diff = helper.differences(baseline_graph, graph)
    if {item["path"] for item in diff} != {"/2/inputs/strength_model", "/27/inputs/filename_prefix"}:
        raise ValueError("Fallback may change only character strength and output prefix.")
    info = helper.api("object_info")
    for node in graph.values():
        if node["class_type"] not in info:
            raise ValueError("Required native node is not visible: " + node["class_type"])
    for node_id, field in (("1", "unet_name"), ("2", "lora_name"), ("3", "lora_name"),
                           ("4", "clip_name"), ("5", "vae_name")):
        node = graph[node_id]
        if node["inputs"][field] not in info[node["class_type"]]["input"]["required"][field][0]:
            raise ValueError("Exact existing model is not visible: " + node["inputs"][field])
    manifest = copy.deepcopy(baseline)
    manifest.pop("preparation_snapshot", None)
    manifest.pop("live_control_verified", None)
    manifest.update({
        "status": "prepared_not_queued_not_promoted",
        "stage": "genuine_third_native_high_existing_character_fallback_control",
        "baseline_run": str(BASELINE), "baseline_prompt_id": prompt_id,
        "baseline_manifest_sha256": PINS[BASELINE / "experiment.json"],
        "baseline_output": {"path": str(BASELINE_RAW), "sha256": PINS[BASELINE_RAW]},
        "graph_differences": diff, "prompt": graph, "identity_strength": .9,
        "active_character_lora": True, "new_character_training": False,
        "comparison_path": str(BASELINE_RAW), "comparison_sha256": PINS[BASELINE_RAW],
        "comparison_label": "NATIVE HIGH CHARACTER 0",
        "identity_mechanism": "Genuine source photograph supplies native Klein edit-reference latent conditioning; the existing compatible Klein9B character adapter now also supplies learned identity weights at strength0.9. This restores the existing supported identity constraint during the exact failed strong High prompt. No face swap, face patch, separate identity adapter or new training.",
        "conditioning_trace": "Original genuine photograph -> LoadImage100 -> same1MP bicubic ImageScale101 -> full Flux2 VAEEncode102 -> ReferenceLatent103 positive/104 negative -> CFGGuider21. Existing characterLoRA2 at0.9 and phoneLoRA3 at0.25 modify Base9B model1 -> same50-step Euler from EmptyFlux2Latent816x1088.",
        "research_scope": "One character-weight-only mechanism control after native source-only High caused measured identity loss (.814684 fidelity control to .573564 High). Restores the existing user-permitted character adapter; no prompt or parameter grid, no new training and no production changes.",
        "acceptance": "Restore recognizable likeness versus the exact no-character High while retaining clearly stronger flattering eyes/brows, natural source-like closed-lip expression, skin/hair realism and room detail. Compare against the genuine source, no-character High and historical character0.9 source-fidelity output. Reject generic eye/brow replacement, identity loss, unchanged beauty versus fidelity, invented teeth, gaze/pose drift, puffiness or whole-frame damage. If this fails, stop the native prompt/strength grid and diagnose the mechanism.",
        "limitation": "Exact High prompt intentionally unchanged, including its omission of the canonical smartphone trigger and character trigger token. Only existing character model weight strength changes. Phone adapter remains active0.25 in both members of the pair. Runtime uses Base9B BF16 model cast to FP8. This is one genuine-photo test and cannot by itself prove broad High acceptance.",
        "phone_canonical_trigger_present": False,
        "live_baseline_verified": {"prompt_id": prompt_id, "status": "success", "output_node": "27",
            "output_sha256": PINS[BASELINE_RAW], "saved_live_and_png_graphs_equal": True},
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path,
        help="Saved owned terminal-success experiment, required for retained RTX3090 cache.")
    args = parser.parse_args()
    if (DESTINATION / "submission-intent.json").exists() or (DESTINATION / "submission.json").exists():
        raise ValueError("Submission was already attempted; inspect evidence and do not resubmit blindly.")
    if not args.execute and DESTINATION.exists():
        raise ValueError("Prepared destination already exists; preserve it.")
    if args.execute and not (DESTINATION / "experiment.json").is_file():
        raise ValueError("Prepare and review the graph before executing it.")
    pilot, helper = load_helpers()
    initial = helper.worker_snapshot(enforce_idle=args.execute, previous_run=args.previous_run)
    manifest = build_verified_manifest(pilot, helper)
    if not args.execute:
        manifest["preparation_snapshot"] = initial
        DESTINATION.mkdir(parents=True)
        (DESTINATION / "experiment.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (DESTINATION / "prompt-api.json").write_text(json.dumps(manifest["prompt"], indent=2), encoding="utf-8")
        print(json.dumps({"status": "prepared_only", "run": str(DESTINATION),
            "differences": manifest["graph_differences"]}, indent=2))
        return
    prepared = helper.read_json(DESTINATION / "experiment.json")
    if {key: value for key, value in prepared.items() if key != "preparation_snapshot"} != manifest:
        raise ValueError("Prepared evidence differs from fresh verification; no submission.")
    if helper.read_json(DESTINATION / "prompt-api.json") != manifest["prompt"]:
        raise ValueError("Standalone graph differs from reviewed manifest.")
    final = helper.worker_snapshot(enforce_idle=True, previous_run=args.previous_run)
    client_id = "upgrade-native-high-character-" + uuid.uuid4().hex
    intent = {"status": "submission_attempt_started", "client_id": client_id,
        "manifest_sha256": helper.sha(DESTINATION / "experiment.json"), "preflight": [initial, final]}
    (DESTINATION / "submission-intent.json").write_text(json.dumps(intent, indent=2), encoding="utf-8")
    result = helper.api("prompt", body={"prompt": manifest["prompt"], "client_id": client_id})
    (DESTINATION / "submission.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
