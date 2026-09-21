"""Prepare one causal canyon adapter-off control; no automatic generation."""
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
BASELINE = WORK / "beautygrpo-canyon-fixed-recipe"
CASE = "kontext-canyon-adapter-off-control"
DESTINATION = WORK / CASE
BASELINE_ID = "2c7b50ea-9468-4ab3-bd35-e3d33f229d56"
NODES_SHA = "abec8a56cececc0579967752c24b4c1d8b4eaf2d327b106b9843bca126553105"
EVALUATOR_SHA = "22177888adef8a4568cd26bdc84254ba2a6c5d05696fdd7267978093b573393e"
PINS = {
    "experiment.json": "fcba77a4498adf4cd335187a761b85e07c4dd2334d53e70b95a13fd380e60d3e",
    "prompt-api.json": "80cd0daf2275db085c82540d249f70c6098eab5fd312270f14860d3a608b415b",
    "submission.json": "baae5a0d4f06074c06ce0b704baa8f32d303b1fe976d266b0e577fff5f606845",
    "evaluation/audit.json": "f7133370274a85744dcc318f984e1b35139da22e00cdecc281a6a6ab44ca8ecc",
    "evaluation/history.json": "9e810288e86676dc2e6190c10a6c926c2201aa81097d5f9166a1e6b54f2310f1",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def helpers():
    if not EVALUATOR_SHA:
        raise ValueError("Updated evaluator must be reviewed and pinned before use.")
    loaded = []
    for name, expected in (
        ("run-upgrade-beautygrpo.py", "08e0c5973622220355fb4058f8bedbab40122b8b1face9cdcfc631e30f8acb07"),
        ("evaluate-upgrade-beautygrpo.py", EVALUATOR_SHA),
    ):
        path = ROOT / "scripts" / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Reviewed helper changed: " + name)
        loaded.append(run_path(str(path)))  # Import definitions, never main().
    return loaded


def verified_manifest(helper, evaluator):
    sha, api = helper["sha"], helper["api"]
    for name, expected in PINS.items():
        if sha(BASELINE / name) != expected:
            raise ValueError("Pinned completed canyon evidence changed: " + name)
    if sha(COMFY / "nodes.py") != NODES_SHA:
        raise ValueError("Reviewed zero-strength native loader changed.")
    baseline = read_json(BASELINE / "experiment.json")
    audit = read_json(BASELINE / "evaluation/audit.json")
    prompt_id, history, output, adapter = evaluator["successful_output"](BASELINE, baseline)
    if (prompt_id != BASELINE_ID or prompt_id != audit["prompt_id"]
            or history != read_json(BASELINE / "evaluation/history.json")
            or history["status"]["messages"] != audit["history_messages"]
            or audit["manifest_sha256"] != PINS["experiment.json"]
            or audit["submission_sha256"] != PINS["submission.json"]
            or output != Path(audit["output"]["path"]).resolve() or sha(output) != audit["output"]["sha256"]
            or adapter != audit["adapter"] or baseline["source"] != audit["source"]):
        raise ValueError("Exact completed canyon history/PNG differs from its saved audit.")
    graph = copy.deepcopy(baseline["prompt"])
    if read_json(BASELINE / "prompt-api.json") != graph or graph["2"]["inputs"]["strength_model"] != 1.0:
        raise ValueError("Expected the unchanged adapter1.0 baseline graph.")
    source = baseline["source"]
    for field, hash_field in (("path", "sha256"), ("original_path", "original_sha256")):
        if sha(Path(source[field])) != source[hash_field]:
            raise ValueError("Exact canyon source changed.")
    if (COMFY / "input" / graph["5"]["inputs"]["image"]).resolve() != Path(source["path"]).resolve():
        raise ValueError("Graph source differs from the audited staged canyon input.")
    for path in (Path(source["path"]), output):
        with Image.open(path) as image:
            if image.size != (1024, 1024):
                raise ValueError("Pinned prepared source or baseline output dimensions changed.")
    for item in baseline["models"] + baseline["other_models"]:
        path = Path(item.get("installed", item.get("path")))
        if not path.resolve().is_relative_to((COMFY / "models").resolve()) or sha(path) != item["sha256"]:
            raise ValueError("Pinned model artifact changed: " + str(path))
        print("Verified " + path.name, flush=True)
    graph["2"]["inputs"]["strength_model"] = 0.0
    graph["14"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/" + CASE + "/raw"
    restored = copy.deepcopy(graph)
    differences = []
    for node_id, field in (("2", "strength_model"), ("14", "filename_prefix")):
        before, after = baseline["prompt"][node_id]["inputs"][field], graph[node_id]["inputs"][field]
        if before == after:
            raise ValueError("Expected exactly the strength1-to0 and output-prefix changes.")
        differences.append({"path": "/" + node_id + "/inputs/" + field, "before": before, "after": after})
        restored[node_id]["inputs"][field] = before
    if restored != baseline["prompt"]:
        raise ValueError("Adapter-off control changed another graph field.")
    info = api(8188, "object_info")
    for node in graph.values():
        if node["class_type"] not in info:
            raise ValueError("Required native node is unavailable: " + node["class_type"])
    for node_id, field in (("1", "unet_name"), ("2", "lora_name"), ("3", "clip_name1"), ("3", "clip_name2"), ("4", "vae_name")):
        node = graph[node_id]
        if node["inputs"][field] not in info[node["class_type"]]["input"]["required"][field][0]:
            raise ValueError("Exact baseline model name is unavailable: " + node["inputs"][field])
    manifest = copy.deepcopy(baseline)
    manifest["baseline_adapter_coverage"] = manifest.pop("coverage")
    manifest.pop("fixed_recipe_scope", None)
    manifest.update({
        "status": "prepared_not_queued_not_accepted", "stage": "one_causal_beauty_adapter_off_control",
        "prompt": graph, "graph_differences": differences, "candidate_label": "KONTEXT - ADAPTER OFF",
        "active_beauty_adapter": False, "active_lora_count": 0, "diagnostic_control_only": True,
        "source_role": "Native Kontext source-latent edit conditioning only; no active BeautyGRPO or character adapter. "
                       "This control does not demonstrate a trained face-retouching identity signal or identity correction.",
        "control_scope": "Only BeautyGRPO model strength1.0-to0.0 and output prefix change. "
                         "Same source preparation, prompt, base/text/VAE models, seed, steps, sampler and guidance. No new strength sweep.",
        "model_inventory_scope": "All baseline model hashes verified; BeautyGRPO is provenance-only and bypassed during inference.",
        "zero_adapter_loader": {"path": str(COMFY / "nodes.py"), "sha256": NODES_SHA, "lines": [735, 736, 737, 767, 768],
            "mechanism": "LoraLoaderModelOnly passes strength_clip0. LoraLoader returns the input model when both strengths are0, before resolving or reading the adapter."},
        "baseline": {"run": str(BASELINE), "prompt_id": prompt_id, "evidence_sha256": PINS,
            "output_path": str(output), "output_sha256": audit["output"]["sha256"]},
        "comparison_path": str(output), "comparison_sha256": audit["output"]["sha256"],
        "comparison_label": "BEAUTYGRPO 1.0", "implementation_sha256": sha(Path(__file__)),
        "helper_pins": {"run-upgrade-beautygrpo.py": "08e0c5973622220355fb4058f8bedbab40122b8b1face9cdcfc631e30f8acb07",
                        "evaluate-upgrade-beautygrpo.py": EVALUATOR_SHA},
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path, help="Own last terminal job proving retained3090 cache.")
    args = parser.parse_args()
    if any((DESTINATION / name).exists() for name in ("submission-intent.json", "submission.json")):
        raise ValueError("Submission already attempted; no blind resubmission.")
    if args.execute:
        if not all((DESTINATION / name).is_file() for name in ("experiment.json", "prompt-api.json", "preparation.json")):
            raise ValueError("Prepare and review this exact control before --execute.")
        if args.previous_run is None:
            raise ValueError("Execution requires --previous-run for the owned-cache guard.")
    elif DESTINATION.exists():
        raise ValueError("Preserve the existing prepared control.")
    if (COMFY / "output/upgrade-high-20260907" / CASE).exists():
        raise ValueError("Control output directory exists; inspect it before proceeding.")
    helper, evaluator = helpers()
    sha = helper["sha"]
    preflight = [helper["idle"](args.previous_run)]
    manifest = verified_manifest(helper, evaluator)
    preflight.append(helper["idle"](args.previous_run))
    if not args.execute:
        DESTINATION.mkdir(parents=True, exist_ok=False)
        write_new(DESTINATION / "experiment.json", manifest)
        write_new(DESTINATION / "prompt-api.json", manifest["prompt"])
        write_new(DESTINATION / "preparation.json", {"status": "prepared_only_no_submission", "preflight": preflight,
            "manifest_sha256": sha(DESTINATION / "experiment.json"), "graph_sha256": sha(DESTINATION / "prompt-api.json")})
        print("Prepared only; review before execution: " + str(DESTINATION))
        return
    preparation = read_json(DESTINATION / "preparation.json")
    if read_json(DESTINATION / "experiment.json") != manifest or read_json(DESTINATION / "prompt-api.json") != manifest["prompt"]:
        raise ValueError("Prepared immutable manifest or graph changed.")
    for filename, field in (("experiment.json", "manifest_sha256"), ("prompt-api.json", "graph_sha256")):
        if sha(DESTINATION / filename) != preparation[field]:
            raise ValueError("Prepared bytes changed: " + filename)
    client_id = "kontext-base-control-" + uuid.uuid4().hex
    write_new(DESTINATION / "submission-intent.json", {"client_id": client_id,
        "status": "attempt_started_no_blind_resubmission", "fresh_preflight": preflight,
        "manifest_sha256": preparation["manifest_sha256"], "graph_sha256": preparation["graph_sha256"]})
    result = helper["api"](8188, "prompt", {"prompt": manifest["prompt"], "client_id": client_id})
    write_new(DESTINATION / "submission.json", result)
    print(json.dumps(result), flush=True)
    if result.get("node_errors") or not result.get("prompt_id"):
        raise RuntimeError("Submission rejected; preserve all evidence.")


if __name__ == "__main__":
    main()
