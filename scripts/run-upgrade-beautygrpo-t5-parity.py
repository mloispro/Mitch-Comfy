"""One T5-padding correction of the fixed active-BeautyGRPO canyon recipe."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from runpy import run_path
import uuid

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
WORK = ROOT / "work/upgrade-high-20260907"
BASELINE = WORK / "beautygrpo-canyon-fixed-recipe"
CASE = "beautygrpo-canyon-t5-512"
DESTINATION = WORK / CASE
CONTROL_HELPER = ROOT / "scripts/run-upgrade-kontext-base-control.py"
CONTROL_HELPER_SHA = "8baa04c6cda1b86516da740e112264416419eb53d66caf51adbcc1c380e7ddc8"
SOURCE_PINS = {
    "comfy_extras/nodes_cond.py": "fb4c9abaaeaa96633344a3f30830fe1a2a7cb72b1d1a1bbc020cb30e566b6806",
    "comfy/text_encoders/flux.py": "e25458ab048671953ef048276bb39dc27c7bfeee67821234833a80ed315e75a6",
    "comfy/sd1_clip.py": "c5a7a9ab305253cdbcdb0d728d80aa1fb6408632561d09c7745fbe8e0c8e7cef",
    "comfy/text_encoders/sd3_clip.py": "a0588e05fd80d5822fded80f7defb86d98afbabd312a528b0f47cf3f6af09407",
    "comfy/sd.py": "3b71a1a71a78ee327c24201f8d522393eb111264b3569d8b3a24bd9149d77f4f",
    "comfy/text_encoders/t5_tokenizer/tokenizer.json": "d83c89be63f15850fe89464127d24e8c4b6ac688ccd58d6d2621cde703fa5d8f",
    "comfy/text_encoders/t5_tokenizer/tokenizer_config.json": "391561cbd46ecf582321c6ef32f832647ae89bdd2ae7c7d536b9d22754834da2",
    "comfy/text_encoders/t5_tokenizer/special_tokens_map.json": "65d84a9271d68f1230ab99518c00f0f7eaef95c7b363001595ba6fa662d434b1",
}


def helpers():
    for name, expected in SOURCE_PINS.items():
        if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            raise ValueError("Native source SHA256 must contain exactly64 hexadecimal characters: " + name)
    if hashlib.sha256(CONTROL_HELPER.read_bytes()).hexdigest() != CONTROL_HELPER_SHA:
        raise ValueError("Reviewed completed-canyon verification helper changed.")
    control = run_path(str(CONTROL_HELPER))
    # Its helpers pin the original idle/API/SHA functions and updated evaluator.
    helper, evaluator = control["helpers"]()
    return control, helper, evaluator


def token_length_guard(text):
    # Only tokenizer IDs, no text-encoder weights, Torch or Comfy imports.
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(COMFY / "comfy/text_encoders/t5_tokenizer/tokenizer.json"))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    ids = tokenizer.encode(text, add_special_tokens=True).ids
    if len(ids) != 101 or ids[-1] != 1 or len(ids) > 512:
        raise ValueError("This correction is only verified for the fixed101-token prompt including EOS.")
    ids_sha = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
    padded_sha = hashlib.sha256(json.dumps(ids + [0] * (512 - len(ids)), separators=(",", ":")).encode()).hexdigest()
    if (ids_sha != "2757538817bf7b16370a1d5b8d514ff47442ede36c191ad6a7d57098d4bdae8d"
            or padded_sha != "6e8471557e8089894f0795f4f21030a31f6710408141b3253ab8e0cc90fe2030"):
        raise ValueError("Fixed prompt token IDs differ from the independently verified native/author sequence.")
    return {"unpadded_token_count_including_eos": len(ids), "eos_token_id": ids[-1],
            "target_minimum_length": 512, "minimum_extra_padding": 0,
            "min_length_is_not_max_length": True, "fixed_prompt_shorter_than_target_verified": True,
            "token_ids_sha256": ids_sha, "expected_native_padded_ids_sha256": padded_sha,
            "pad_token_id": 0, "padding_token_count": 411}


def build_manifest(control, helper, evaluator):
    sha, api = helper["sha"], helper["api"]
    # Reuse only read-only evidence validation: no preparation/submission/main.
    # This checks pinned canyon manifest/history/audit/PNG/source/all models and
    # native loaders. Its adapter-off graph is discarded, never submitted.
    evidence = control["verified_manifest"](helper, evaluator)
    baseline = control["read_json"](BASELINE / "experiment.json")
    if evidence["baseline"]["prompt_id"] != "2c7b50ea-9468-4ab3-bd35-e3d33f229d56":
        raise ValueError("Expected the completed active-BeautyGRPO canyon baseline.")
    for name, expected in SOURCE_PINS.items():
        if sha(COMFY / name) != expected:
            raise ValueError("Reviewed native tokenizer implementation changed: " + name)
    graph = copy.deepcopy(baseline["prompt"])
    token_evidence = token_length_guard(graph["8"]["inputs"]["text"])
    if "15" in graph or graph["8"]["inputs"]["clip"] != ["3", 0] or graph["2"]["inputs"]["strength_model"] != 1.0:
        raise ValueError("Baseline is not the fixed active-adapter/direct-CLIP recipe.")
    option_node = {"class_type": "T5TokenizerOptions", "inputs": {"clip": ["3", 0], "min_padding": 0, "min_length": 512}}
    graph["15"] = option_node
    graph["8"]["inputs"]["clip"] = ["15", 0]
    graph["14"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/" + CASE + "/raw"
    restored = copy.deepcopy(graph)
    restored.pop("15")
    restored["8"]["inputs"]["clip"] = ["3", 0]
    restored["14"]["inputs"]["filename_prefix"] = baseline["prompt"]["14"]["inputs"]["filename_prefix"]
    if restored != baseline["prompt"]:
        raise ValueError("T5 correction changes another graph field.")
    info = api(8188, "object_info")
    if "T5TokenizerOptions" not in info:
        raise ValueError("Native T5TokenizerOptions is not live; no custom node replacement is allowed.")
    required = info["T5TokenizerOptions"]["input"]["required"]
    for name, value in (("min_padding", 0), ("min_length", 512)):
        definition = required[name]
        if definition[0] != "INT" or not definition[1]["min"] <= value <= definition[1]["max"]:
            raise ValueError("Live native tokenizer-option schema differs: " + name)
    manifest = copy.deepcopy(baseline)
    manifest.pop("fixed_recipe_scope", None)
    manifest.update({
        "status": "prepared_not_queued_not_accepted", "stage": "single_t5_minimum_padding_correction",
        "prompt": graph, "candidate_label": "BEAUTYGRPO T5 512", "active_beauty_adapter": True,
        "graph_differences": [
            {"path": "/15", "before": None, "after": option_node},
            {"path": "/8/inputs/clip", "before": ["3", 0], "after": ["15", 0]},
            {"path": "/14/inputs/filename_prefix", "before": baseline["prompt"]["14"]["inputs"]["filename_prefix"],
             "after": graph["14"]["inputs"]["filename_prefix"]},
        ],
        "tokenizer_correction": {**token_evidence, "baseline_minimum_length": 256,
            "mechanism": "Native T5TokenizerOptions clones CLIP, sets per-encode tokenizer options, and FluxTokenizer forwards kwargs. "
                         "T5 minimum length512 pads this fixed101-token prompt; it does not truncate arbitrary longer prompts. "
                         "The same node8 conditioning also feeds the existing zeroed negative conditioning.",
            "scope": "Only T5 padding configuration changes conditioning; no prompt, LoRA, sampler, source or resolution change.",
            "source_sha256": SOURCE_PINS},
        "author_bit_exact": False,
        "remaining_author_differences": list(baseline["backend_differences"]) + [
            "Fixed expression-refinement prompt differs from author default",
            "Canyon input uses aspect-preserving contain and narrow edge padding instead of author direct square resize",
            "Padding correction does not establish bit-identical text embeddings or Diffusers pipeline output",
        ],
        "baseline": evidence["baseline"], "comparison_path": evidence["comparison_path"],
        "comparison_sha256": evidence["comparison_sha256"], "comparison_label": "BEAUTYGRPO T5 256",
        "implementation_sha256": sha(Path(__file__)),
        "helper_pins": {**evidence["helper_pins"], "run-upgrade-kontext-base-control.py": CONTROL_HELPER_SHA},
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path, help="Own latest successful run proving retained3090 cache; not hardcoded to the recipe baseline.")
    args = parser.parse_args()
    if any((DESTINATION / name).exists() for name in ("submission-intent.json", "submission.json")):
        raise ValueError("Submission already attempted; no blind resubmission.")
    if args.execute:
        if not all((DESTINATION / name).is_file() for name in ("experiment.json", "prompt-api.json", "preparation.json")):
            raise ValueError("Prepare and review this exact correction before --execute.")
        if args.previous_run is None:
            raise ValueError("Execution requires --previous-run for the owned-cache guard.")
    elif DESTINATION.exists():
        raise ValueError("Preserve the existing prepared correction.")
    if (COMFY / "output/upgrade-high-20260907" / CASE).exists():
        raise ValueError("Output directory already exists; inspect it before proceeding.")
    control, helper, evaluator = helpers()
    sha, read_json, write_new = helper["sha"], control["read_json"], control["write_new"]
    preflight = [helper["idle"](args.previous_run)]
    manifest = build_manifest(control, helper, evaluator)
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
    client_id = "beautygrpo-t5-512-" + uuid.uuid4().hex
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
