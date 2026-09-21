"""Prepare one final evidence-driven character-strength0.45 High refinement.

Exact matched token/prompt/source/phone/sampling retained. No further native
strength or prompt variants are authorized by this experiment. Default no queue.
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
BASELINE = ROOT / "work/upgrade-high-20260907/third-native-high-character-matched"
DESTINATION = ROOT / "work/upgrade-high-20260907/third-native-high-character-midpoint"
BASELINE_RAW = COMFY / "output/upgrade-high-20260907/third-native-high-character-matched/raw_00001_.png"
MATCHED_SCRIPT = ROOT / "scripts/run-upgrade-native-high-character-matched.py"
PINS = {
    MATCHED_SCRIPT: "bb61c975c76abd4c3938429156edeb7adc2624cd9ba5757c00acfb04d36abb5b",
    BASELINE / "experiment.json": "7f5c1a9b7d91c9c1c619bbee3d44980309e1090ec3f6d093984f1264dacd659b",
    BASELINE / "prompt-api.json": "f5cef0f612bb45a7c363b85a1659e7884434906b343c25234d8ffa23b03d6e1e",
    BASELINE / "submission.json": "ebf061cd90ea1bfcfb9bbb2f7538488edda303000367280a8b2e07e0c50ab23a",
    BASELINE_RAW: "101dd28439c9d7cde30049a9a2b3af162c4771584eb56d068cf5fdd0e117ee72",
}


def load_helpers():
    if hashlib.sha256(MATCHED_SCRIPT.read_bytes()).hexdigest() != PINS[MATCHED_SCRIPT]:
        raise ValueError("Reviewed matched-character preparation changed.")
    matched = run_path(str(MATCHED_SCRIPT))
    fallback, pilot, helper = matched["load_helpers"]()
    return matched, fallback, pilot, helper


def build_verified_manifest(matched, fallback, pilot, helper):
    for path, expected in PINS.items():
        if helper.sha(path) != expected:
            raise ValueError("Pinned matched0.9 evidence changed: " + str(path))
    baseline = helper.read_json(BASELINE / "experiment.json")
    graph = helper.clean_graph(baseline["prompt"])
    verified = matched["build_verified_manifest"](fallback, pilot, helper)
    if {key: value for key, value in baseline.items() if key != "preparation_snapshot"} != verified:
        raise ValueError("Matched0.9 baseline differs from exact revalidated preparation.")
    if helper.read_json(BASELINE / "prompt-api.json") != graph:
        raise ValueError("Matched standalone graph mismatch.")
    prompt_id = helper.read_json(BASELINE / "submission.json")["prompt_id"]
    history = helper.api("history/" + prompt_id).get(prompt_id)
    if not history or not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("Exact matched0.9 baseline has not succeeded.")
    if history["prompt"][1] != prompt_id or helper.clean_graph(history["prompt"][2]) != graph:
        raise ValueError("Matched live graph mismatch.")
    images = history["outputs"]["27"]["images"]
    if len(images) != 1 or images[0]["type"] != "output":
        raise ValueError("Require one matched0.9 PNG output.")
    if (COMFY / "output" / images[0].get("subfolder", "") / images[0]["filename"]).resolve() != BASELINE_RAW.resolve():
        raise ValueError("Matched history points to a different image.")
    with Image.open(BASELINE_RAW) as image:
        if image.size != (816, 1088) or helper.clean_graph(json.loads(image.info["prompt"])) != graph:
            raise ValueError("Matched PNG graph/dimensions mismatch.")
    if graph["2"]["inputs"]["strength_model"] != .9 or not graph["6"]["inputs"]["text"].startswith("m1tch_person. "):
        raise ValueError("Require the exact trained-token matched0.9 endpoint.")
    graph["2"]["inputs"]["strength_model"] = .45
    graph["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-native-high-character-midpoint/raw"
    diff = helper.differences(helper.clean_graph(baseline["prompt"]), graph)
    if {item["path"] for item in diff} != {"/2/inputs/strength_model", "/27/inputs/filename_prefix"}:
        raise ValueError("Midpoint may change only strength0.9->0.45 and output prefix.")
    manifest = copy.deepcopy(baseline)
    manifest.pop("preparation_snapshot", None)
    manifest.pop("supersedes_unexecuted_trial", None)
    manifest.pop("superseded_trial_reason", None)
    manifest.update({
        "stage": "genuine_third_native_high_final_existing_character_midpoint_refinement",
        "baseline_run": str(BASELINE), "baseline_prompt_id": prompt_id,
        "baseline_manifest_sha256": PINS[BASELINE / "experiment.json"],
        "baseline_output": {"path": str(BASELINE_RAW), "sha256": PINS[BASELINE_RAW]},
        "comparison_path": str(BASELINE_RAW), "comparison_sha256": PINS[BASELINE_RAW],
        "comparison_label": "MATCHED HIGH CHARACTER 0.9", "identity_strength": .45,
        "prompt": graph, "graph_differences": diff,
        "identity_conditioning_bundle": {"existing_character_lora_strength": .45, "trained_token_prefix": "m1tch_person.",
            "comparison": "one strength-only refinement versus matched0.9 with trained token fixed", "weight_only_causal_ablation": True},
        "identity_mechanism": "Same genuine native Klein edit-source conditioning plus existing trained character LoRA and its m1tch_person token. Only character adapter strength is reduced from matched0.9 to0.45; source/reference packing, prompt/token and phone model remain fixed. This is a single controlled refinement, not new training.",
        "conditioning_trace": "Original genuine photograph -> LoadImage100 -> same1MP bicubic ImageScale101 -> Flux2 VAEEncode102 -> ReferenceLatent103 positive/104 negative -> CFGGuider21. Existing characterLoRA2 at0.45 and phoneLoRA3 at0.25 modify Base9B model1 -> same50-step Euler from EmptyFlux2Latent816x1088.",
        "research_scope": "One final evidence-driven intermediate strength. Character-OFF High produced visible generic beauty with .573564 identity; matched0.9 restored .825755 identity but suppressed distinct High gains. Test whether0.45 retains a useful amount of both. Only midpoint versus matched0.9 is a pure strength comparison: the historical OFF endpoint also omitted the trained token. No additional native strengths or prompts after this result.",
        "acceptance": "Visually clearer flattering High eyes/brows/expression versus matched0.9 and historical fidelity, while recognizably Mitch, maintaining closed lips/pupil focus/head pose, natural skin/hair and detailed room. Compare five genuine references excluding true source and full/crop/thumbnail sheets including both endpoints. A higher identity index alone or generic dark brows is not acceptance. Decide after this one midpoint; no subsequent native strength/prompt grid.",
        "limitation": "The OFF High endpoint used no trained token, so do not claim a pure strength curve across all endpoints. Midpoint0.45 versus matched0.9 changes only adapter strength. Phone0.25 and canonical phone-trigger omission remain fixed. Base9B BF16 weights cast to FP8 at runtime. Single-photo results do not prove production readiness.",
        "live_baseline_verified": {"prompt_id": prompt_id, "status": "success", "output_node": "27",
            "output_sha256": PINS[BASELINE_RAW], "saved_live_and_png_graphs_equal": True},
        "final_native_refinement": True,
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path, help="Saved owned terminal-success run for retained RTX3090 cache.")
    args = parser.parse_args()
    if (DESTINATION / "submission-intent.json").exists() or (DESTINATION / "submission.json").exists():
        raise ValueError("Submission already attempted; inspect saved evidence, never resubmit blindly.")
    if not args.execute and DESTINATION.exists():
        raise ValueError("Prepared destination exists; preserve it.")
    if args.execute and not (DESTINATION / "experiment.json").is_file():
        raise ValueError("Prepare and review the midpoint before execution.")
    matched, fallback, pilot, helper = load_helpers()
    initial = helper.worker_snapshot(enforce_idle=args.execute, previous_run=args.previous_run)
    manifest = build_verified_manifest(matched, fallback, pilot, helper)
    if not args.execute:
        manifest["preparation_snapshot"] = initial
        DESTINATION.mkdir(parents=True)
        (DESTINATION / "experiment.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (DESTINATION / "prompt-api.json").write_text(json.dumps(manifest["prompt"], indent=2), encoding="utf-8")
        print(json.dumps({"status": "prepared_only", "run": str(DESTINATION), "differences": manifest["graph_differences"]}, indent=2))
        return
    prepared = helper.read_json(DESTINATION / "experiment.json")
    if {key: value for key, value in prepared.items() if key != "preparation_snapshot"} != manifest:
        raise ValueError("Prepared midpoint differs from fresh verified evidence.")
    if helper.read_json(DESTINATION / "prompt-api.json") != manifest["prompt"]:
        raise ValueError("Standalone midpoint graph mismatch.")
    final = helper.worker_snapshot(enforce_idle=True, previous_run=args.previous_run)
    client_id = "upgrade-native-high-midpoint-" + uuid.uuid4().hex
    intent = {"status": "submission_attempt_started", "client_id": client_id,
        "manifest_sha256": helper.sha(DESTINATION / "experiment.json"), "preflight": [initial, final]}
    (DESTINATION / "submission-intent.json").write_text(json.dumps(intent, indent=2), encoding="utf-8")
    result = helper.api("prompt", body={"prompt": manifest["prompt"], "client_id": client_id})
    (DESTINATION / "submission.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
