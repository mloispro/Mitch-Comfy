"""Prepare one source-only, no-character native Klein High prompt refinement.

Default prepares and validates only. After parent review, --execute submits once
on an idle RTX3090 with owned terminal-cache evidence. No free/restart/training.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import uuid

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
CONTROL = ROOT / "work/upgrade-high-20260907/third-no-character-control"
DESTINATION = ROOT / "work/upgrade-high-20260907/third-native-high-pilot"
CONTROL_RAW = COMFY / "output/upgrade-high-20260907/third-no-character-control/raw_00001_.png"
HELPER = ROOT / "scripts/run-upgrade-no-character-control.py"
PINS = {
    HELPER: "48942abd62a4ec18966b55430b723496fafb7ebec4004dcf8cdb2f78ad9b406f",
    CONTROL / "experiment.json": "532cb766c286e11a1d13f16db1fe110253109d5cf1b1571b99fe67db808d3565",
    CONTROL / "prompt-api.json": "40f859d8911b251ad57af2019e517a04827f38ba66e696601ed97288b47dd957",
    CONTROL / "submission.json": "bc443a16c50469c49e1c1cf7c3300bfc842c3c9ed1ddc7a8bd226af9e2ebb45c",
    CONTROL_RAW: "7b15351e61c74fd6276c1a077b7e1fa5916b0e842b6538d9c30204395e446663",
}
PROMPT = (
    "Retouch this photograph of the same man into a clearly more handsome but still believable version of himself. "
    "Preserve his recognizable identity, original head tilt and face direction, eye color and exact pupil focus. "
    "Keep the camera angle, framing, face position and size, hairline, ears, shoulders, navy sweatshirt, white neckline and the entire room unchanged. "
    "Give his eyes a more attractive relaxed almond-shaped upper-lid contour, without widening them or moving the irises. "
    "Refine the eyebrows into fuller naturally groomed brows following their existing direction and asymmetry. "
    "Keep his characteristic asymmetric closed-lip smile, subtly make it more confident and appealing, and soften the tense crease between the eyebrows. "
    "Keep lips together with absolutely no visible teeth. "
    "Make the cheek and jaw contours slightly leaner and more defined, not rounded or puffy; keep his forehead proportions unchanged. "
    "Give him a visibly fresher, well-rested appearance: soften forehead lines, remove freckles and isolated dark skin spots, keep fine irregular pores and realistic short stubble. "
    "Apply a subtle healthy tan and restrained warm highlights to a few existing hair strands, preserving natural hair texture and shape. "
    "Preserve the actual indoor light and the photographic character of the image. "
    "Keep the whole room detailed and legible with realistic phone-camera depth of field: natural painted-wall texture, straight closet edges, shelf and hanging clothes. "
    "The result should be a flattering real casual photograph of the same man, not a different person or an airbrushed beauty filter."
)


def load_helper():
    # Check before import: only the reviewed guard implementation is executable.
    import hashlib
    if hashlib.sha256(HELPER.read_bytes()).hexdigest() != PINS[HELPER]:
        raise ValueError("The reviewed no-character guard changed; review before reuse.")
    spec = importlib.util.spec_from_file_location("upgrade_no_character_guard", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_verified_manifest(helper):
    for path, expected in PINS.items():
        if helper.sha(path) != expected:
            raise ValueError("Pinned control evidence changed: " + str(path))
    control = helper.read_json(CONTROL / "experiment.json")
    control_graph = helper.clean_graph(control["prompt"])
    if helper.read_json(CONTROL / "prompt-api.json") != control_graph:
        raise ValueError("Control standalone graph differs from its saved manifest.")
    prompt_id = helper.read_json(CONTROL / "submission.json")["prompt_id"]
    live_history = helper.api("history/" + prompt_id)
    if prompt_id not in live_history:
        raise ValueError("Completed control is missing from live RTX3090 history.")
    history = live_history[prompt_id]
    if not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("Control is not a terminal successful generation.")
    if helper.clean_graph(history["prompt"][2]) != control_graph:
        raise ValueError("Control live executed graph differs from saved evidence.")
    outputs = history["outputs"]["27"]["images"]
    if len(outputs) != 1 or outputs[0]["type"] != "output":
        raise ValueError("Control output must be one ordinary saved PNG.")
    output_path = (COMFY / "output" / outputs[0]["subfolder"] / outputs[0]["filename"]).resolve()
    if output_path != CONTROL_RAW.resolve():
        raise ValueError("Live control history points to a different output file.")
    with Image.open(CONTROL_RAW) as image:
        if image.size != (816, 1088):
            raise ValueError("Control output dimensions changed.")
        if helper.clean_graph(json.loads(image.info["prompt"])) != control_graph:
            raise ValueError("Control embedded PNG graph differs from live/saved evidence.")
    source = control["source"]
    if not source["genuine"] or source["upstream_character_lora"]:
        raise ValueError("This pilot requires an original genuine source with no character-LoRA lineage.")
    for key, hash_key in (("path", "sha256"), ("original_path", "original_sha256"),
                          ("preparation_provenance", "preparation_provenance_sha256")):
        if helper.sha(source[key]) != source[hash_key]:
            raise ValueError("Pinned genuine source provenance changed: " + source[key])
    if control["reference_mode"] != "source_only" or len(control["references"]) != 1:
        raise ValueError("Pilot must retain the single native edit-source reference.")
    if control_graph["2"]["inputs"]["strength_model"] != 0.0:
        raise ValueError("The control has active character weights.")
    graph = copy.deepcopy(control_graph)
    graph["6"]["inputs"]["text"] = PROMPT
    graph["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-native-high-pilot/raw"
    diff = helper.differences(control_graph, graph)
    if {item["path"] for item in diff} != {"/6/inputs/text", "/27/inputs/filename_prefix"}:
        raise ValueError("Only the positive prompt and output prefix may change.")
    if (graph["1"]["inputs"]["weight_dtype"], graph["3"]["inputs"]["strength_model"],
        graph["20"]["inputs"]["noise_seed"], graph["21"]["inputs"]["cfg"],
        graph["22"]["inputs"]["sampler_name"], graph["23"]["inputs"]["steps"]) != (
            "fp8_e4m3fn", .25, 8675412, 4.0, "euler", 50):
        raise ValueError("Protected model/sampling settings do not match the reviewed control.")
    info = helper.api("object_info")
    for node in graph.values():
        if node["class_type"] not in info:
            raise ValueError("Required node is not visible: " + node["class_type"])
    for node_id, field in (("1", "unet_name"), ("2", "lora_name"), ("3", "lora_name"),
                           ("4", "clip_name"), ("5", "vae_name")):
        node = graph[node_id]
        if node["inputs"][field] not in info[node["class_type"]]["input"]["required"][field][0]:
            raise ValueError("Exact control model is not visible: " + node["inputs"][field])
    for model in control["verified_models"]:
        if helper.sha(model["path"]) != model["sha256"]:
            raise ValueError("Pinned control model changed: " + model["path"])
        print("Verified " + Path(model["path"]).name, flush=True)
    zero = control["character_loader_zero_behavior"]
    if helper.sha(zero["implementation"]) != zero["sha256"]:
        raise ValueError("Character-loader zero-strength behavior changed.")
    manifest = copy.deepcopy(control)
    manifest.pop("preparation_snapshot", None)
    manifest.update({
        "status": "prepared_not_queued_not_promoted",
        "stage": "genuine_third_native_no_character_high_prompt_pilot",
        "baseline_run": str(CONTROL), "baseline_prompt_id": prompt_id,
        "baseline_manifest_sha256": PINS[CONTROL / "experiment.json"],
        "baseline_output": {"path": str(CONTROL_RAW), "sha256": PINS[CONTROL_RAW]},
        "graph_differences": diff, "effective_prompt": PROMPT, "prompt": graph,
        "comparison_path": str(CONTROL_RAW), "comparison_sha256": PINS[CONTROL_RAW],
        "comparison_label": "NO-CHARACTER SOURCE-FIDELITY CONTROL",
        "research_scope": "Exactly one positive-prompt refinement of the completed native source-only no-character control. No strength grid, different model, seed, steps, dimensions, source order, reference packing, postprocessing or production changes.",
        "identity_mechanism": "The original genuine photograph supplies training-supported native Klein edit-reference latent conditioning. No active character adapter, separate face embedding or downstream face patch. The source-only control has completed, but similarity and visual review remain required; this is not an identity-lock claim.",
        "acceptance": "High must visibly improve eyes/brows, expression, skin and cheek definition versus the no-character source-fidelity control, while remaining recognizably Mitch against five other genuine photographs. Reject changed gaze/head angle, invented teeth, puffier cheeks, enlarged forehead, plastic skin/hair, lost room detail or whole-frame realism. Diagnostic similarity is not a beauty score. Production promotion requires the broader photo-set review.",
        "limitation": "This single prompt refinement changes semantic editing goals, including replacing the inactive character trigger text with the same-man description. It cannot establish general High acceptance from one photograph, and prompt instructions do not guarantee pupil or identity preservation. Both pilot and control use the same runtime graph/settings, with Base9B BF16 weights cast to FP8 at runtime.",
        "live_control_verified": {"prompt_id": prompt_id, "status": "success", "output_node": "27",
            "output_sha256": PINS[CONTROL_RAW], "saved_live_and_png_graphs_equal": True},
        "submission_guard": {"implementation": str(HELPER), "sha256": PINS[HELPER],
            "ports_inspected": [8188, 8189, 8190], "locked_gpu": "RTX 3090", "locked_port": 8188,
            "owned_terminal_cache_required_above_mib": 4096, "explicit_free": False, "worker_restart": False},
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path,
        help="Saved owned terminal-success job, needed for retained RTX3090 cache.")
    args = parser.parse_args()
    if (DESTINATION / "submission-intent.json").exists() or (DESTINATION / "submission.json").exists():
        raise ValueError("A submission was already attempted; inspect evidence, never resubmit blindly.")
    if not args.execute and DESTINATION.exists():
        raise ValueError("Prepared destination exists; preserve it.")
    if args.execute and not (DESTINATION / "experiment.json").is_file():
        raise ValueError("Prepare and review the graph before executing it.")
    helper = load_helper()
    initial = helper.worker_snapshot(enforce_idle=args.execute, previous_run=args.previous_run)
    manifest = build_verified_manifest(helper)
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
        raise ValueError("Prepared manifest differs from newly verified evidence; no submission.")
    if helper.read_json(DESTINATION / "prompt-api.json") != manifest["prompt"]:
        raise ValueError("Standalone graph differs from the reviewed manifest.")
    final = helper.worker_snapshot(enforce_idle=True, previous_run=args.previous_run)
    client_id = "upgrade-native-high-" + uuid.uuid4().hex
    intent = {"status": "submission_attempt_started", "client_id": client_id,
        "manifest_sha256": helper.sha(DESTINATION / "experiment.json"), "preflight": [initial, final]}
    (DESTINATION / "submission-intent.json").write_text(json.dumps(intent, indent=2), encoding="utf-8")
    result = helper.api("prompt", body={"prompt": manifest["prompt"], "client_id": client_id})
    (DESTINATION / "submission.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
