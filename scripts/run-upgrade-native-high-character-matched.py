"""Prepare the one training-matched existing-character native High fallback.

Identity conditioning ON bundles LoRA0.9 and its trained m1tch_person token.
Default only prepares. Parent review and --execute are required to queue once.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from runpy import run_path
import uuid


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "work/upgrade-high-20260907/third-native-high-character-matched"
FALLBACK_SCRIPT = ROOT / "scripts/run-upgrade-native-high-character-control.py"
FALLBACK_SCRIPT_SHA256 = "795c937a1bbb7a3fb7d98d7f4f48007e9d38d72d8a9f77e417a87a8d2312593e"
TRIGGER = "m1tch_person."


def load_helpers():
    if hashlib.sha256(FALLBACK_SCRIPT.read_bytes()).hexdigest() != FALLBACK_SCRIPT_SHA256:
        raise ValueError("The reviewed source/model/history validation implementation changed.")
    fallback = run_path(str(FALLBACK_SCRIPT))
    pilot, helper = fallback["load_helpers"]()
    return fallback, pilot, helper


def build_verified_manifest(fallback, pilot, helper):
    # Reuse strict read-only validation only, never the superseded trial's main
    # or submission path. This validates actual char0 High history/PNG and all
    # genuine-source, model and ancestor graph pins before building this case.
    manifest = fallback["build_verified_manifest"](pilot, helper)
    baseline = helper.read_json(fallback["BASELINE"] / "experiment.json")
    manifest["prompt"]["6"]["inputs"]["text"] = TRIGGER + " " + pilot["PROMPT"]
    manifest["prompt"]["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-native-high-character-matched/raw"
    diff = helper.differences(helper.clean_graph(baseline["prompt"]), manifest["prompt"])
    if {item["path"] for item in diff} != {"/2/inputs/strength_model", "/6/inputs/text", "/27/inputs/filename_prefix"}:
        raise ValueError("Matched fallback must change exactly identity weight, trained-token prefix and output prefix.")
    if manifest["prompt"]["6"]["inputs"]["text"] != "m1tch_person. " + baseline["effective_prompt"]:
        raise ValueError("All semantic High instructions must remain unchanged after the trained-token prefix.")
    manifest.update({
        "stage": "genuine_third_native_high_training_matched_existing_character_fallback",
        "effective_prompt": manifest["prompt"]["6"]["inputs"]["text"], "graph_differences": diff,
        "character_trigger": TRIGGER, "character_trigger_present": True,
        "identity_conditioning_bundle": {"existing_character_lora_strength": .9, "trained_token_prefix": TRIGGER,
            "comparison": "training-matched existing-character conditioning ON versus OFF", "weight_only_causal_ablation": False},
        "identity_mechanism": "Original genuine source supplies native Klein edit-reference latent conditioning. The existing compatible Klein9B character adapter at strength0.9 plus its trained m1tch_person token provide the supported character identity-conditioning mechanism. These are enabled together; this is not a weight-only ablation. No new training, face swap, face patch or separate identity adapter.",
        "research_scope": "One training-matched existing-character mechanism test after the native source-only High prompt lost likeness (.814684 fidelity to .573564 High). Restore the user-permitted existing LoRA with its trained token. Exactly three JSON differences: character weight, token-only prompt prefix and output prefix. All High semantics, phone settings, source/reference layout and sampling remain fixed. This is the last native existing-character mechanism test before the acceptance decision, not a prompt/strength grid.",
        "acceptance": "The training-matched existing-character bundle must restore recognizable likeness while retaining clearly stronger flattering eyes/brows and a natural source-like closed-lip expression, skin/hair realism and detailed room. Compare source, char0 High, matched char0.9 High and historical char0.9 fidelity using five genuine references and full/crop/thumbnail review. Reject generic brow/eye replacement, unchanged beauty versus fidelity, invented teeth, gaze/pose drift, puffiness or whole-frame damage. If it fails, do not continue a native prompt/strength grid.",
        "limitation": "Not a weight-only causal test: the identity-conditioning bundle changes both LoRA strength0->0.9 and adds its trained m1tch_person token. Exact High semantic wording is otherwise unchanged. Phone adapter remains active0.25 and its canonical trigger is omitted in both paired High images. Base9B BF16 weights are cast to FP8 at runtime. One genuine photo cannot establish broad production High acceptance.",
        "supersedes_unexecuted_trial": str(ROOT / "work/upgrade-high-20260907/third-native-high-character-control"),
        "superseded_trial_reason": "Weight-only preparation omitted the trained character token; preserved without execution, not a failed-result claim.",
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path,
        help="Saved owned terminal-success experiment, needed for retained RTX3090 cache.")
    args = parser.parse_args()
    if (DESTINATION / "submission-intent.json").exists() or (DESTINATION / "submission.json").exists():
        raise ValueError("Submission already attempted; inspect evidence and never resubmit blindly.")
    if not args.execute and DESTINATION.exists():
        raise ValueError("Prepared destination already exists; preserve it.")
    if args.execute and not (DESTINATION / "experiment.json").is_file():
        raise ValueError("Prepare and review the matched graph before executing it.")
    fallback, pilot, helper = load_helpers()
    initial = helper.worker_snapshot(enforce_idle=args.execute, previous_run=args.previous_run)
    manifest = build_verified_manifest(fallback, pilot, helper)
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
        raise ValueError("Prepared matched evidence differs from fresh verification; no submission.")
    if helper.read_json(DESTINATION / "prompt-api.json") != manifest["prompt"]:
        raise ValueError("Standalone matched graph differs from reviewed manifest.")
    final = helper.worker_snapshot(enforce_idle=True, previous_run=args.previous_run)
    client_id = "upgrade-native-high-character-matched-" + uuid.uuid4().hex
    intent = {"status": "submission_attempt_started", "client_id": client_id,
        "manifest_sha256": helper.sha(DESTINATION / "experiment.json"), "preflight": [initial, final]}
    (DESTINATION / "submission-intent.json").write_text(json.dumps(intent, indent=2), encoding="utf-8")
    result = helper.api("prompt", body={"prompt": manifest["prompt"], "client_id": client_id})
    (DESTINATION / "submission.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
