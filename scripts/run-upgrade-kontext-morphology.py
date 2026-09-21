"""Prepare one prompt-policy refinement of the completed base-Kontext control."""
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
BASELINE = WORK / "kontext-canyon-adapter-off-control"
CASE = "kontext-canyon-explicit-high"
DESTINATION = WORK / CASE
BASELINE_ID = "c3aa6628-6003-41fb-ae14-6afb3894c75d"
OUTPUT_SHA = "623d06f702acd2d94c146c8bb54ebaadf73423b54c1ce2e64fe3e11098eff407"
CONTROL_HELPER = ROOT / "scripts/run-upgrade-kontext-base-control.py"
CONTROL_SHA = "8baa04c6cda1b86516da740e112264416419eb53d66caf51adbcc1c380e7ddc8"
PINS = {
    "experiment.json": "813df9742c161e59db7e67d3606c61e38a32fe6845b097c17c7fc860737612ec",
    "prompt-api.json": "b445335788436fcef8dc5ac2efa48254b88b362e385ac21190b34592a52bab34",
    "submission.json": "0ed0acb577c39b15dae0e5b574f043326cd03f4812d7ace73f632ba67d233901",
    "evaluation/audit.json": "d7c4f41db61311bc5c5ca018aeccb5c011e2cd95988846c8d912e4432a312b6a",
    "evaluation/history.json": "64aa47e44dbad0bb09fea2374e052ee5fc4535455296b13665a374b7278bb9e2",
}
SOURCE_PINS = {
    "nodes.py": "abec8a56cececc0579967752c24b4c1d8b4eaf2d327b106b9843bca126553105",
    "comfy/text_encoders/flux.py": "e25458ab048671953ef048276bb39dc27c7bfeee67821234833a80ed315e75a6",
    "comfy/text_encoders/t5_tokenizer/tokenizer.json": "d83c89be63f15850fe89464127d24e8c4b6ac688ccd58d6d2621cde703fa5d8f",
}
OLD_PROMPT = (
    "Beautify this person's face while maintaining a natural and realistic appearance. "
    "Make his existing slight asymmetric smile more relaxed and quietly confident, "
    "keeping his lips gently together with no visible teeth. Keep his natural eye shape, "
    "softly defined eyelid edges and natural bare skin around the eyes. Preserve his "
    "recognizable identity, exact pupil focus, head tilt, hairline and cheek width. "
    "Keep his body, phone, clothing, background, framing and lighting unchanged."
)
PROMPT = (
    "Edit only the man's face to look noticeably more handsome while remaining recognizably the same man. "
    "Give him more open, well-defined eyes with relaxed upper eyelids, naturally fuller well-shaped eyebrows, "
    "leaner cheeks and a more defined jaw. Give him a warmer, confident asymmetric closed-lip smile with "
    "both lips gently together and no visible teeth. Make his skin clearer and more even, reducing freckles, "
    "dark spots and deep forehead lines while retaining natural pores and light stubble. Preserve his nose, "
    "eye colour, pupil direction, head angle, forehead height, hairline and face scale. Keep his hair, body, "
    "clothing, background, lighting and framing unchanged. The result should remain a realistic photograph."
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def helpers():
    for digest in [CONTROL_SHA, OUTPUT_SHA, *PINS.values(), *SOURCE_PINS.values()]:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Every source pin must be exactly 64 lowercase hexadecimal characters.")
    if hashlib.sha256(CONTROL_HELPER.read_bytes()).hexdigest() != CONTROL_SHA:
        raise ValueError("Reviewed control helper changed.")
    control = run_path(str(CONTROL_HELPER))  # Definitions only; never control main().
    return control["helpers"]()  # Pins the original runner and current evaluator.


def token_length_guard(text):
    if text != PROMPT:
        raise ValueError("Exact approved morphology prompt changed.")
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(COMFY / "comfy/text_encoders/t5_tokenizer/tokenizer.json"))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    ids = tokenizer.encode(text, add_special_tokens=True).ids
    if not ids or ids[-1] != 1 or len(ids) > 256:
        raise ValueError("Prompt no longer fits native T5 default 256 with EOS.")
    return {"unpadded_token_count_including_eos": len(ids), "native_minimum_length": 256,
            "padding_override": False, "token_ids_sha256": hashlib.sha256(
                json.dumps(ids, separators=(",", ":")).encode("utf-8")).hexdigest()}


def changed_graph(baseline):
    before = baseline["prompt"]
    if (before["2"]["inputs"]["strength_model"] != 0.0
            or before["8"]["inputs"] != {"clip": ["3", 0], "text": OLD_PROMPT}
            or any(n["class_type"] == "T5TokenizerOptions" for n in before.values())
            or "15" in before):
        raise ValueError("Expected the exact adapter-off/direct-CLIP/default-T5 baseline.")
    graph = copy.deepcopy(before)
    graph["8"]["inputs"]["text"] = PROMPT
    graph["14"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/" + CASE + "/raw"
    restored, differences = copy.deepcopy(graph), []
    for node, field in (("8", "text"), ("14", "filename_prefix")):
        old, new = before[node]["inputs"][field], graph[node]["inputs"][field]
        if old == new:
            raise ValueError("Expected exactly the prompt and output-prefix changes.")
        differences.append({"path": "/" + node + "/inputs/" + field, "before": old, "after": new})
        restored[node]["inputs"][field] = old
    if restored != before:
        raise ValueError("Unexpected graph mutation beyond prompt and prefix.")
    return graph, differences


def verified_manifest(helper, evaluator):
    sha, api = helper["sha"], helper["api"]
    for name, expected in PINS.items():
        if sha(BASELINE / name) != expected:
            raise ValueError("Pinned completed base-control evidence changed: " + name)
    for name, expected in SOURCE_PINS.items():
        if sha(COMFY / name) != expected:
            raise ValueError("Reviewed native source changed: " + name)
    baseline = read_json(BASELINE / "experiment.json")
    audit = read_json(BASELINE / "evaluation/audit.json")
    prompt_id, history, output, adapter = evaluator["successful_output"](BASELINE, baseline)
    if (prompt_id != BASELINE_ID or prompt_id != audit["prompt_id"]
            or history != read_json(BASELINE / "evaluation/history.json")
            or history["status"]["messages"] != audit["history_messages"]
            or audit["manifest_sha256"] != PINS["experiment.json"]
            or audit["submission_sha256"] != PINS["submission.json"]
            or output != Path(audit["output"]["path"]).resolve()
            or sha(output) != OUTPUT_SHA or audit["output"]["sha256"] != OUTPUT_SHA
            or adapter != audit["adapter"] or baseline["source"] != audit["source"]
            or audit["active_beauty_adapter"] is not False):
        raise ValueError("Exact completed base-control history/PNG differs from its saved audit.")
    if read_json(BASELINE / "prompt-api.json") != baseline["prompt"]:
        raise ValueError("Saved baseline API graph differs from its manifest.")
    source = baseline["source"]
    for field, hash_field in (("path", "sha256"), ("original_path", "original_sha256")):
        if sha(Path(source[field])) != source[hash_field]:
            raise ValueError("Exact original or staged canyon source changed.")
    if ((COMFY / "input" / baseline["prompt"]["5"]["inputs"]["image"]).resolve()
            != Path(source["path"]).resolve() or source["genuine"] is not False):
        raise ValueError("Graph source or its non-genuine provenance changed.")
    for path in (Path(source["path"]), output):
        with Image.open(path) as image:
            if image.size != (1024, 1024):
                raise ValueError("Prepared input or output dimensions changed.")
    for item in baseline["models"] + baseline["other_models"]:
        path = Path(item.get("installed", item.get("path")))
        if not path.resolve().is_relative_to((COMFY / "models").resolve()) or sha(path) != item["sha256"]:
            raise ValueError("Pinned model artifact changed: " + str(path))
        print("Verified " + path.name, flush=True)
    graph, differences = changed_graph(baseline)
    token_evidence = token_length_guard(graph["8"]["inputs"]["text"])
    info = api(8188, "object_info")
    for node in graph.values():
        if node["class_type"] not in info:
            raise ValueError("Required native node is unavailable: " + node["class_type"])
    for node_id, field in (("1", "unet_name"), ("2", "lora_name"), ("3", "clip_name1"), ("3", "clip_name2"), ("4", "vae_name")):
        node = graph[node_id]
        if node["inputs"][field] not in info[node["class_type"]]["input"]["required"][field][0]:
            raise ValueError("Exact baseline model name unavailable: " + node["inputs"][field])
    manifest = copy.deepcopy(baseline)
    manifest.pop("control_scope", None)
    manifest.update({
        "status": "prepared_not_queued_not_accepted", "stage": "one_base_kontext_prompt_policy_refinement",
        "prompt": graph, "graph_differences": differences, "candidate_label": "KONTEXT - EXPLICIT HIGH",
        "active_beauty_adapter": False, "active_lora_count": 0, "diagnostic_control_only": False,
        "experimental_candidate": True, "additional_prompt_tuning": True,
        "prompt_policy_scope": "Sole controlled prompt-policy refinement of the base-Kontext fidelity control: "
            "explicit eyes, brows, cheeks, jaw, smile and skin requests. Only text and output prefix change. "
            "No continuation of the closed Klein/active-BeautyGRPO line; no strength or T5-padding change.",
        "source_role": "Edit source: LoadImage5 -> VAEEncode7 -> ReferenceLatent9 -> FluxGuidance10 -> "
            "KSampler12 positive conditioning, using native Kontext trained image-edit/reference conditioning. "
            "The same source also enters latent_image at denoise1. No separate face embedding or identity lock; "
            "source fidelity is a prediction requiring visual and genuine-reference evaluation, not identity correction.",
        "mechanism_primary_source": "https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev",
        "research_gate": "docs/upgrade-high-explicit-features-2026-09-07.md",
        "t5_conditioning": token_evidence, "native_source_pins": SOURCE_PINS,
        "baseline": {"run": str(BASELINE), "prompt_id": prompt_id, "evidence_sha256": PINS,
            "output_path": str(output), "output_sha256": OUTPUT_SHA},
        "comparison_path": str(output), "comparison_sha256": OUTPUT_SHA,
        "comparison_label": "KONTEXT - ADAPTER OFF", "implementation_sha256": sha(Path(__file__)),
        "helper_pins": {**baseline["helper_pins"], CONTROL_HELPER.name: CONTROL_SHA},
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path, help="Own last terminal job proving retained 3090 cache.")
    args = parser.parse_args()
    if any((DESTINATION / name).exists() for name in ("submission-intent.json", "submission.json")):
        raise ValueError("Submission already attempted; no blind resubmission.")
    if args.execute:
        if not all((DESTINATION / name).is_file() for name in ("experiment.json", "prompt-api.json", "preparation.json")):
            raise ValueError("Prepare and review this exact experiment before --execute.")
        if args.previous_run is None:
            raise ValueError("Execution requires --previous-run for the owned-cache guard.")
    elif DESTINATION.exists():
        raise ValueError("Preserve the existing prepared experiment.")
    if (COMFY / "output/upgrade-high-20260907" / CASE).exists():
        raise ValueError("Experiment output directory exists; inspect before proceeding.")
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
    client_id = "kontext-morphology-" + uuid.uuid4().hex
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
