"""Prepare one prompt-only BeautyGRPO refinement; submit only after separate review.

Uses the same genuine source as the completed author-prompt control. No model
downloads, image preparation, postprocessing, production edits, or auto-resubmits.
"""
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
WORK = ROOT / "work/upgrade-high-20260907"
BASELINE = WORK / "beautygrpo-mirror-author"
CASE = "beautygrpo-mirror-expression-refinement"
DESTINATION = WORK / CASE
OUTPUT_PREFIX = "upgrade-high-20260907/" + CASE + "/raw"
HELPER = ROOT / "scripts/run-upgrade-beautygrpo.py"
HELPER_SHA = "08e0c5973622220355fb4058f8bedbab40122b8b1face9cdcfc631e30f8acb07"
BASELINE_ID = "52c67455-5c40-4618-94ac-9b12b6dfab58"
BASELINE_RAW = COMFY / "output/upgrade-high-20260907/beautygrpo-mirror-author/raw_00001_.png"
BASELINE_RAW_SHA = "0ae41ac14a10a2f4c5ef2fc5c98aa3fb6607839a0c3ee7f04758a089a3207f7a"
PINS = {
    "experiment.json": "5809369c5403a7107daa69c3188249d72c8875774cf2dfd72d87385248c4f33b",
    "prompt-api.json": "65b826305279f3fc6d876a033b64b1f92d202b691783c3c1a3d87e07d116517a",
    "submission.json": "50eab041cdbcf6fd586e08b97487b4b167f66958e4e3523886d4840c9ea26236",
    "evaluation/audit.json": "4d2a2c23a8c2fe1fe075eab4a6ad054f8c7e6b02c2c179f882b0a6df13783c51",
    "evaluation/history.json": "50f7cb4fb5e29bc4d66c7c1cede44579e1076fbdc513c9e6c3d0fa79303145b7",
}
PROMPT = (
    "Beautify this person's face while maintaining a natural and realistic appearance. "
    "Make his existing slight asymmetric smile more relaxed and quietly confident, "
    "keeping his lips gently together with no visible teeth. Keep his natural eye shape, "
    "softly defined eyelid edges and natural bare skin around the eyes. Preserve his "
    "recognizable identity, exact pupil focus, head tilt, hairline and cheek width. "
    "Keep his body, phone, clothing, background, framing and lighting unchanged."
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def helpers():
    # Verify before importing any helper code. run_path does not call its main().
    if hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
        raise ValueError("Reviewed BeautyGRPO helper changed.")
    return run_path(str(HELPER))


def clean_graph(graph):
    result = copy.deepcopy(graph)
    for node in result.values():
        node.pop("is_changed", None)
    return result


def refined_graph(baseline_graph):
    graph = copy.deepcopy(baseline_graph)
    graph["8"]["inputs"]["text"] = PROMPT
    graph["14"]["inputs"]["filename_prefix"] = OUTPUT_PREFIX
    differences = [
        {"path": "/8/inputs/text", "before": baseline_graph["8"]["inputs"]["text"], "after": PROMPT},
        {"path": "/14/inputs/filename_prefix", "before": baseline_graph["14"]["inputs"]["filename_prefix"],
         "after": OUTPUT_PREFIX},
    ]
    restored = copy.deepcopy(graph)
    for node, field in (("8", "text"), ("14", "filename_prefix")):
        restored[node]["inputs"][field] = baseline_graph[node]["inputs"][field]
    if restored != baseline_graph or any(item["before"] == item["after"] for item in differences):
        raise ValueError("Expected exactly the prompt and output-prefix changes.")
    return graph, differences


def verified_manifest(helper):
    sha, api = helper["sha"], helper["api"]
    for name, expected in PINS.items():
        if sha(BASELINE / name) != expected:
            raise ValueError("Pinned baseline evidence changed: " + name)
    baseline = read_json(BASELINE / "experiment.json")
    audit = read_json(BASELINE / "evaluation/audit.json")
    saved_history = read_json(BASELINE / "evaluation/history.json")
    graph = clean_graph(baseline["prompt"])
    if read_json(BASELINE / "prompt-api.json") != graph:
        raise ValueError("Baseline standalone graph differs from its manifest.")
    if (read_json(BASELINE / "submission.json")["prompt_id"] != BASELINE_ID
            or audit["prompt_id"] != BASELINE_ID
            or audit["manifest_sha256"] != PINS["experiment.json"]
            or audit["submission_sha256"] != PINS["submission.json"]):
        raise ValueError("Saved audit does not identify the pinned baseline run.")
    history = api(8188, "history/" + BASELINE_ID).get(BASELINE_ID)
    if history != saved_history or not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("Exact baseline job must match the saved successful history.")
    if history["prompt"][1] != BASELINE_ID or clean_graph(history["prompt"][2]) != graph:
        raise ValueError("Executed baseline graph differs from its manifest.")
    if history["status"]["messages"] != audit["history_messages"]:
        raise ValueError("Baseline terminal messages differ from its audit.")
    images = history["outputs"]["14"]["images"]
    if len(images) != 1 or images[0]["type"] != "output":
        raise ValueError("Expected one exact baseline output.")
    item = images[0]
    output = (COMFY / "output" / item.get("subfolder", "") / item["filename"]).resolve()
    if (output != BASELINE_RAW.resolve() or Path(audit["output"]["path"]).resolve() != output
            or audit["output"]["sha256"] != BASELINE_RAW_SHA or sha(output) != BASELINE_RAW_SHA):
        raise ValueError("Baseline output does not match the saved audit.")
    with Image.open(output) as image:
        if image.size != (1024, 1024) or clean_graph(json.loads(image.info["prompt"])) != graph:
            raise ValueError("Baseline PNG dimensions or embedded graph changed.")
    source = baseline["source"]
    if source != audit["source"] or source["genuine"] is not True or source["upstream_character_lora"] is not False:
        raise ValueError("Require the exact genuine source, never the generated baseline.")
    for field, hash_field in (("path", "sha256"), ("original_path", "original_sha256")):
        if sha(Path(source[field])) != source[hash_field]:
            raise ValueError("Pinned genuine source changed: " + field)
    if (COMFY / "input" / graph["5"]["inputs"]["image"]).resolve() != Path(source["path"]).resolve():
        raise ValueError("LoadImage must use the genuine staged source.")
    with Image.open(source["path"]) as image:
        if image.size != (1024, 1024):
            raise ValueError("Genuine staged source dimensions changed.")
    for model in baseline["models"] + baseline["other_models"]:
        path = Path(model.get("installed", model.get("path")))
        if not path.resolve().is_relative_to((COMFY / "models").resolve()):
            raise ValueError("Pinned installed model must remain local.")
        if sha(path) != model["sha256"]:
            raise ValueError("Installed model changed: " + str(path))
        print("Verified " + path.name, flush=True)
    graph, differences = refined_graph(graph)
    info = api(8188, "object_info")
    for node in graph.values():
        if node["class_type"] not in info:
            raise ValueError("Required live node unavailable: " + node["class_type"])
    for node_id, field in (("1", "unet_name"), ("2", "lora_name"), ("3", "clip_name1"),
                           ("3", "clip_name2"), ("4", "vae_name")):
        node = graph[node_id]
        if node["inputs"][field] not in info[node["class_type"]]["input"]["required"][field][0]:
            raise ValueError("Exact model is not visible: " + node["inputs"][field])
    manifest = copy.deepcopy(baseline)
    manifest.pop("preflight")
    manifest.update({
        "status": "prepared_not_queued_not_accepted", "stage": "one_controlled_expression_prompt_refinement",
        "prompt": graph, "graph_differences": differences,
        "author_default_prompt": False, "prompt_refinement_not_author_default": True,
        "refinement_scope": "Only node8 text changes conditioning; node14 output prefix separates artifacts. "
                            "Same genuine source, models, adapter strength, source preparation, seed, sampler and steps. "
                            "Expression and preservation instructions are hypotheses, not verified output guarantees.",
        "baseline": {"run": str(BASELINE), "prompt_id": BASELINE_ID, "evidence_sha256": PINS,
                     "output_path": str(BASELINE_RAW), "output_sha256": BASELINE_RAW_SHA},
        "comparison_path": str(BASELINE_RAW), "comparison_sha256": BASELINE_RAW_SHA,
        "comparison_label": "BEAUTYGRPO AUTHOR PROMPT",
        "gpu_lock": "RTX 3090 / port8188", "helper_sha256": HELPER_SHA,
        "implementation_sha256": sha(Path(__file__)),
    })
    return manifest


def write_new(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def check_prepared(manifest, sha):
    if read_json(DESTINATION / "experiment.json") != manifest:
        raise ValueError("Prepared immutable manifest differs from freshly verified evidence.")
    if read_json(DESTINATION / "prompt-api.json") != manifest["prompt"]:
        raise ValueError("Prepared standalone graph differs from the verified refinement.")
    preparation = read_json(DESTINATION / "preparation.json")
    for filename, field in (("experiment.json", "manifest_sha256"), ("prompt-api.json", "graph_sha256")):
        if sha(DESTINATION / filename) != preparation[field]:
            raise ValueError("Prepared file bytes changed after review: " + filename)
    return preparation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path, help="Owned last successful run for the retained3090-cache guard.")
    args = parser.parse_args()
    if any((DESTINATION / name).exists() for name in ("submission-intent.json", "submission.json")):
        raise ValueError("Submission already attempted; inspect evidence, never resubmit blindly.")
    if args.execute:
        if not all((DESTINATION / name).is_file() for name in ("experiment.json", "prompt-api.json", "preparation.json")):
            raise ValueError("Prepare and review this exact run first; --execute cannot prepare it.")
        if args.previous_run is None:
            raise ValueError("Execution requires --previous-run for the owned-cache guard.")
    elif DESTINATION.exists():
        raise ValueError("Prepared destination already exists; preserve it for review.")
    if (COMFY / "output/upgrade-high-20260907" / CASE).exists():
        raise ValueError("Refinement output directory already exists; inspect it before proceeding.")
    helper = helpers()
    sha = helper["sha"]
    preflight = [helper["idle"](args.previous_run)]
    manifest = verified_manifest(helper)
    preflight.append(helper["idle"](args.previous_run))
    if not args.execute:
        DESTINATION.mkdir(parents=True, exist_ok=False)
        write_new(DESTINATION / "experiment.json", manifest)
        write_new(DESTINATION / "prompt-api.json", manifest["prompt"])
        write_new(DESTINATION / "preparation.json", {
            "status": "prepared_only_no_submission", "preflight": preflight,
            "manifest_sha256": sha(DESTINATION / "experiment.json"),
            "graph_sha256": sha(DESTINATION / "prompt-api.json"),
        })
        print("Prepared only; review before --execute: " + str(DESTINATION))
        return
    check_prepared(manifest, sha)
    client_id = "beautygrpo-expression-" + uuid.uuid4().hex
    # A failed/uncertain HTTP request leaves this exclusive intent in place.
    write_new(DESTINATION / "submission-intent.json", {
        "client_id": client_id, "status": "attempt_started_no_blind_resubmission",
        "manifest_sha256": sha(DESTINATION / "experiment.json"),
        "graph_sha256": sha(DESTINATION / "prompt-api.json"), "fresh_preflight": preflight,
    })
    result = helper["api"](8188, "prompt", {"prompt": manifest["prompt"], "client_id": client_id})
    write_new(DESTINATION / "submission.json", result)
    print(json.dumps(result), flush=True)
    if result.get("node_errors") or not result.get("prompt_id"):
        raise RuntimeError("Live validation rejected the refinement; preserve submission evidence.")


if __name__ == "__main__":
    main()
