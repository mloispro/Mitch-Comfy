"""Prepare a fixed-recipe canyon generalization test; never submit by default."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
from runpy import run_path
import uuid

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
WORK = ROOT / "work/upgrade-high-20260907"
BASELINE = WORK / "beautygrpo-mirror-expression-refinement"
CASE = "beautygrpo-canyon-fixed-recipe"
DESTINATION = WORK / CASE
SOURCE = Path("C:/Users/Mitch/AppData/Local/Temp/codex-clipboard-5411229e-4e9c-47ee-996a-78a8ebef887d.png")
SOURCE_SHA = "e12c0c3d417e8174f0b82d4e44b7f41d237a4c5ef85beaa8a64d84476efe6aa9"
STAGED = COMFY / "input/mitch-beautygrpo-canyon-contained-edgepad-e12c0c3d.png"
PINS = {
    "experiment.json": "b1947910e8ebec340ddd222fa4417174624c04f63eb8bd5a3bf8d59d66123b9d",
    "prompt-api.json": "461ee90213b4edaa77cf4fb53068acedec7f3c0795d74ac447e79863d37876c7",
    "submission.json": "fcf32b1000fc1969ddaa02af34e98c9906e569f3976b77fc0acd8baddf4c86a6",
    "evaluation/audit.json": "eca799da2e62566c65e72ffa81a0ea21ad1bfc128ee5cdf4bb8c6656a4d7755a",
    "evaluation/history.json": "832bc3b389853d2cd4954fc3d74aad1aba430a22481ca5de674ec7b68df7421a",
}
HELPER_PINS = {
    "run-upgrade-beautygrpo.py": "08e0c5973622220355fb4058f8bedbab40122b8b1face9cdcfc631e30f8acb07",
    "evaluate-upgrade-beautygrpo.py": "d6c13469327069875180fe01e12e8da86301dd7a415f6abf695a8e6246358917",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def helpers():
    loaded = []
    for name, expected in HELPER_PINS.items():
        path = ROOT / "scripts" / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Reviewed helper changed: " + name)
        loaded.append(run_path(str(path)))  # Only definitions/imports, never main().
    return loaded


def source_bytes(sha):
    if sha(SOURCE) != SOURCE_SHA:
        raise ValueError("Exact user-supplied canyon source changed.")
    with Image.open(SOURCE) as image:
        orientation = image.getexif().get(274, 1)
        original = ImageOps.exif_transpose(image).convert("RGB")
        if image.size != (693, 701) or original.size != (693, 701):
            raise ValueError("Expected the complete693x701 canyon attachment.")
        contained = ImageOps.contain(original, (1024, 1024), Image.Resampling.BILINEAR)
    if contained.size != (1012, 1024):
        raise ValueError("Unexpected uniform-contain integer pixel dimensions.")
    padded = Image.new("RGB", (1024, 1024))
    padded.paste(contained, (6, 0))
    # Replicate edge columns into padding; no original content is removed.
    padded.paste(contained.crop((0, 0, 1, 1024)).resize((6, 1024), Image.Resampling.NEAREST), (0, 0))
    padded.paste(contained.crop((1011, 0, 1012, 1024)).resize((6, 1024), Image.Resampling.NEAREST), (1018, 0))
    padded.info.clear()
    encoded = io.BytesIO()
    padded.save(encoded, format="PNG")
    data = encoded.getvalue()
    return data, {
        "path": str(STAGED), "sha256": hashlib.sha256(data).hexdigest(), "genuine": False,
        "original_path": str(SOURCE), "original_sha256": SOURCE_SHA, "upstream_character_lora": "unknown",
        "provenance": "User-supplied attachment; unknown/possibly synthetic. Never a genuine identity anchor.",
        "preparation": {
            "method": "PIL BILINEAR uniform contain, then replicated-edge padding",
            "exif_orientation": orientation, "normalized_orientation": True,
            "original_size": [693, 701], "content_size": [1012, 1024], "prepared_size": [1024, 1024],
            "uniform_scale": 1024 / 701, "integer_grid_scales_xy": [1012 / 693, 1024 / 701],
            "scale_rounding": "Aspect-preserving contain rounded to integer output dimensions; no independent-axis stretch",
            "content_rectangle_xyxy_exclusive": [6, 0, 1018, 1024],
            "padding_left_top_right_bottom": [6, 0, 6, 0], "crop": False, "face_edits": False,
        },
    }


def verified_manifest(helper, evaluator):
    sha, api = helper["sha"], helper["api"]
    for name, expected in PINS.items():
        if sha(BASELINE / name) != expected:
            raise ValueError("Pinned completed refinement changed: " + name)
    baseline = read_json(BASELINE / "experiment.json")
    audit = read_json(BASELINE / "evaluation/audit.json")
    prompt_id, history, output, adapter = evaluator["successful_output"](BASELINE, baseline)
    if (history != read_json(BASELINE / "evaluation/history.json") or prompt_id != audit["prompt_id"]
            or audit["manifest_sha256"] != PINS["experiment.json"]
            or audit["submission_sha256"] != PINS["submission.json"]
            or history["status"]["messages"] != audit["history_messages"]
            or output != Path(audit["output"]["path"]).resolve() or sha(output) != audit["output"]["sha256"]
            or adapter != audit["adapter"] or baseline["source"] != audit["source"]):
        raise ValueError("Completed refinement history/PNG evidence differs from its saved audit.")
    graph = copy.deepcopy(baseline["prompt"])
    if read_json(BASELINE / "prompt-api.json") != graph:
        raise ValueError("Baseline standalone graph differs.")
    with Image.open(output) as image:
        if image.size != (1024, 1024):
            raise ValueError("Baseline output dimensions changed.")
    for field, hash_field in (("path", "sha256"), ("original_path", "original_sha256")):
        if sha(Path(baseline["source"][field])) != baseline["source"][hash_field]:
            raise ValueError("Completed refinement source changed.")
    for item in baseline["models"] + baseline["other_models"]:
        path = Path(item.get("installed", item.get("path")))
        if not path.resolve().is_relative_to((COMFY / "models").resolve()) or sha(path) != item["sha256"]:
            raise ValueError("Pinned installed model changed: " + str(path))
        print("Verified " + path.name, flush=True)
    data, source = source_bytes(sha)
    graph["5"]["inputs"]["image"] = STAGED.name
    graph["14"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/" + CASE + "/raw"
    restored = copy.deepcopy(graph)
    differences = []
    for node_id, field in (("5", "image"), ("14", "filename_prefix")):
        before, after = baseline["prompt"][node_id]["inputs"][field], graph[node_id]["inputs"][field]
        if before == after:
            raise ValueError("Expected exactly a new source and output prefix.")
        differences.append({"path": "/" + node_id + "/inputs/" + field, "before": before, "after": after})
        restored[node_id]["inputs"][field] = before
    if restored != baseline["prompt"]:
        raise ValueError("Fixed-recipe graph changes more than source and output prefix.")
    info = api(8188, "object_info")
    for node in graph.values():
        if node["class_type"] not in info:
            raise ValueError("Required node is not visible: " + node["class_type"])
    for node_id, field in (("1", "unet_name"), ("2", "lora_name"), ("3", "clip_name1"), ("3", "clip_name2"), ("4", "vae_name")):
        node = graph[node_id]
        if node["inputs"][field] not in info[node["class_type"]]["input"]["required"][field][0]:
            raise ValueError("Exact model is not visible: " + node["inputs"][field])
    manifest = copy.deepcopy(baseline)
    for field in ("comparison_path", "comparison_sha256", "comparison_label", "refinement_scope"):
        manifest.pop(field, None)
    manifest.update({
        "status": "prepared_not_queued_not_accepted", "stage": "fixed_recipe_canyon_generalization",
        "source": source, "prompt": graph, "graph_differences": differences,
        "source_role": "Native source-latent conditioning preserves supplied likeness, not identity correction. "
                       "The possibly synthetic input is not a genuine evaluation anchor.",
        "upstream_character_lora": "unknown", "phone_appearance": "User-supplied image; capture provenance unknown",
        "additional_prompt_tuning": False, "fixed_recipe_scope": "Only LoadImage and output prefix change; "
            "the completed expression-refinement prompt, all models/strengths, seed, sampler, steps and guidance stay fixed.",
        "input_identity_diagnostic": {"centroid_similarity": 0.754768, "genuine_reference_count": 6,
            "scope": "Prior diagnostic for the original693x701 attachment, not recomputed on the padded input or identity proof"},
        "output_policy": "Archive unchanged raw1024x1024 output including padded frame; no unpadding or postprocessing in this test",
        "baseline": {"run": str(BASELINE), "prompt_id": prompt_id, "evidence_sha256": PINS,
            "output_path": str(output), "output_sha256": audit["output"]["sha256"]},
        "implementation_sha256": sha(Path(__file__)), "helper_pins": HELPER_PINS,
    })
    return manifest, data


def stage_source(data, expected_sha, sha, execute):
    if not STAGED.exists():
        if execute:
            raise ValueError("Prepared staged source is missing; preserve the experiment.")
        temporary = STAGED.with_name(STAGED.name + "." + uuid.uuid4().hex + ".tmp")
        with temporary.open("xb") as handle:
            handle.write(data)
        # Windows rename fails if the target appears concurrently; never replace.
        temporary.rename(STAGED)
    if sha(STAGED) != expected_sha:
        raise ValueError("Existing staged source differs; never overwrite it.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path, help="Own last terminal job proving retained3090 cache.")
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
        raise ValueError("Output directory already exists; inspect it before proceeding.")
    helper, evaluator = helpers()
    sha = helper["sha"]
    preflight = [helper["idle"](args.previous_run)]
    manifest, data = verified_manifest(helper, evaluator)
    stage_source(data, manifest["source"]["sha256"], sha, args.execute)
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
    client_id = "beautygrpo-canyon-" + uuid.uuid4().hex
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
