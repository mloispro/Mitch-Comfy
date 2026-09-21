"""Prepare one exact Klein source-only character-LoRA removal control.

Default: prepare and validate only. --execute submits the saved graph once after
fresh source/model and idle-RTX3090 checks. No cache release, restart or training.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request
import uuid

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
BASELINE = ROOT / "work/upgrade-source-faithful-20260903/third-source-native-preserve"
DESTINATION = ROOT / "work/upgrade-high-20260907/third-no-character-control"
PROVENANCE = ROOT / "work/upgrade-source-faithful-20260903/third-source/provenance.json"
BASELINE_RAW = COMFY / "output/upgrade-source-faithful/third-source-native-preserve/raw_00001_.png"
PINS = {
    BASELINE / "experiment.json": "5e1fed11d821080494af80958e515a703ae29e29ef2cd743b04eae7bd644c7ef",
    BASELINE / "submission.json": "0edbc5f0d8724e44fe64b69125f896c7d75630a2319e07f49b1fc202bfeaa25b",
    PROVENANCE: "1d4a9577fa6fe31dd24fe93025161facdee9ca020d683316a551f7ca10a5d10e",
    BASELINE_RAW: "3f0cc682a9cb440f54e40fb750e87e105498a7a4c90d4c35020427381fdcc54a",
    COMFY / "nodes.py": "abec8a56cececc0579967752c24b4c1d8b4eaf2d327b106b9843bca126553105",
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def api(route, port=8188, body=None):
    request = urllib.request.Request("http://127.0.0.1:" + str(port) + "/" + route,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def clean_graph(graph):
    result = copy.deepcopy(graph)
    for node in result.values():
        node.pop("is_changed", None)
    return result


def differences(before, after, prefix=""):
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return [difference for key in before for difference in differences(before[key], after[key], prefix + "/" + key)]
    if before == after:
        return []
    return [{"path": prefix, "before": before, "after": after}]


def worker_snapshot(enforce_idle=False, previous_run=None):
    workers = []
    for port in (8188, 8189, 8190):
        try:
            stats, queue = api("system_stats", port), api("queue", port)
        except Exception:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.5):
                    pass
            except OSError:
                if port in (8188, 8189):
                    raise RuntimeError("Required worker cannot be inspected: " + str(port))
                workers.append({"port": port, "online": False})
                continue
            raise RuntimeError("Listening worker cannot be inspected: " + str(port))
        row = {"port": port, "online": True, "device": stats["devices"][0]["name"],
            "running": len(queue["queue_running"]), "pending": len(queue["queue_pending"])}
        workers.append(row)
        if port == 8188 and "RTX 3090" not in row["device"]:
            raise RuntimeError("This workflow remains locked to RTX3090 / port8188.")
        if enforce_idle and "3090" in row["device"] and (row["running"] or row["pending"]):
            raise RuntimeError("Preserve active3090 work; this control was not submitted.")
    hardware = subprocess.check_output(["nvidia-smi", "--query-gpu=index,name,memory.used,utilization.gpu",
        "--format=csv,noheader,nounits"], text=True)
    rows = [line.split(",") for line in hardware.splitlines() if "RTX 3090" in line]
    if len(rows) != 1:
        raise RuntimeError("Ambiguous3090 hardware inventory.")
    owned = None
    if enforce_idle:
        if int(rows[0][3].strip()) > 10:
            raise RuntimeError("3090 is active outside the queue; preserve it.")
        if int(rows[0][2].strip()) > 4096:
            if previous_run is None:
                raise RuntimeError("Retained3090 memory requires a saved --previous-run proving owned terminal cache.")
            previous = previous_run.resolve()
            if not previous.is_relative_to((ROOT / "work").resolve()):
                raise ValueError("Owned-cache evidence must be a saved workspace experiment.")
            expected_id = read_json(previous / "submission.json")["prompt_id"]
            latest = api("history?max_items=1")
            if list(latest) != [expected_id]:
                raise RuntimeError("Latest3090 job differs from the supplied owned-cache evidence.")
            history = latest[expected_id]
            if not history["status"]["completed"] or history["status"]["status_str"] != "success":
                raise RuntimeError("Owned previous job is not a terminal success.")
            if clean_graph(history["prompt"][2]) != clean_graph(read_json(previous / "experiment.json")["prompt"]):
                raise RuntimeError("Owned cached graph differs from the saved experiment.")
            owned = {"prompt_id": expected_id, "previous_run": str(previous)}
    return {"workers": workers, "hardware": hardware, "owned_cache": owned,
        "explicit_free": False, "worker_restart": False}


def build_verified_manifest():
    for path, expected in PINS.items():
        if sha(path) != expected:
            raise ValueError("Pinned original evidence or loader implementation changed: " + str(path))
    baseline = read_json(BASELINE / "experiment.json")
    provenance = read_json(PROVENANCE)
    baseline_graph = clean_graph(baseline["prompt"])
    with Image.open(BASELINE_RAW) as image:
        executed = clean_graph(json.loads(image.info["prompt"]))
        if image.size != (816, 1088):
            raise ValueError("Baseline output dimensions changed.")
    if executed != baseline_graph:
        raise ValueError("Recorded source-only baseline graph differs from its actual PNG graph.")
    if baseline["reference_mode"] != "source_only" or len(baseline["references"]) != 1:
        raise ValueError("Baseline must contain one native source reference.")
    if baseline_graph["2"]["inputs"]["strength_model"] != .9:
        raise ValueError("Expected the earlier character strength0.9 control.")
    source = baseline["references"][0]
    original = Path(provenance["source"])
    if not provenance["genuine"] or provenance["face_edits"]:
        raise ValueError("Third source provenance is not an unedited genuine photograph.")
    if sha(original) != provenance["source_sha256"] or sha(source["path"]) != source["sha256"].lower():
        raise ValueError("Genuine original or exact staged source has changed.")
    if source["sha256"].lower() != provenance["output_sha256"]:
        raise ValueError("Staged source does not match original-photo preparation provenance.")
    with Image.open(original) as image:
        if ImageOps.exif_transpose(image).size != (813, 1084):
            raise ValueError("Unexpected EXIF-oriented genuine original dimensions.")
    with Image.open(source["path"]) as image:
        if image.size != (816, 1088):
            raise ValueError("Source preparation dimensions changed.")
    graph = copy.deepcopy(baseline_graph)
    graph["2"]["inputs"]["strength_model"] = 0.0
    graph["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-no-character-control/raw"
    diff = differences(baseline_graph, graph)
    if {item["path"] for item in diff} != {"/2/inputs/strength_model", "/27/inputs/filename_prefix"}:
        raise ValueError("Control changes more than character strength and output prefix.")
    info = api("object_info")
    for node in graph.values():
        if node["class_type"] not in info:
            raise ValueError("Required native node is not visible: " + node["class_type"])
    for node_id, field in (("1", "unet_name"), ("2", "lora_name"), ("3", "lora_name"), ("4", "clip_name"), ("5", "vae_name")):
        node = graph[node_id]
        if node["inputs"][field] not in info[node["class_type"]]["input"]["required"][field][0]:
            raise ValueError("Exact baseline model name is not visible: " + node["inputs"][field])
    verified = []
    for model in baseline["verified_models"]:
        actual = sha(model["path"])
        if actual != model["sha256"].lower():
            raise ValueError("Protected baseline model changed: " + model["path"])
        verified.append({"path": model["path"], "sha256": actual})
        print("Verified " + Path(model["path"]).name, flush=True)
    return {
        "status": "prepared_not_queued_not_promoted", "stage": "genuine_third_character_lora_removal_control",
        "baseline_run": str(BASELINE), "baseline_prompt_id": read_json(BASELINE / "submission.json")["prompt_id"],
        "baseline_manifest_sha256": PINS[BASELINE / "experiment.json"],
        "baseline_output": {"path": str(BASELINE_RAW), "sha256": PINS[BASELINE_RAW]},
        "source": {"path": source["path"], "sha256": source["sha256"].lower(), "genuine": True,
            "original_path": str(original), "original_sha256": provenance["source_sha256"],
            "original_exif_oriented_size": [813, 1084], "prepared_size": [816, 1088],
            "preparation_provenance": str(PROVENANCE), "preparation_provenance_sha256": PINS[PROVENANCE],
            "upstream_character_lora": False},
        "reference_mode": "source_only", "references": baseline["references"],
        "identity_strength": 0.0, "phone_camera_style": True, "phone_camera_style_strength": .25,
        "turbo": False, "seed": 8675412, "steps": 50, "cfg": 4, "sampler": "euler",
        "width": 816, "height": 1088, "output_node": "27", "verified_models": verified,
        "graph_differences": diff, "effective_prompt": baseline["effective_prompt"], "prompt": graph,
        "character_loader_zero_behavior": {"implementation": str(COMFY / "nodes.py"),
            "sha256": PINS[COMFY / "nodes.py"], "lines": [735, 736, 737, 767, 768],
            "mechanism": "LoraLoaderModelOnly calls load_lora with strength_clip0; strength_model0 returns the original model before reading or patching the character adapter."},
        "identity_mechanism": "Genuine source photograph supplies native edit-reference latent conditioning to Base9B; no active character adapter or separate identity embedding. Preservation is a hypothesis tested against the fixed0.9 control, not an identity-lock claim.",
        "conditioning_trace": "LoadImage100 -> same1MP bicubic ImageScale101 -> full Flux2 VAEEncode102 -> ReferenceLatent103 positive and104 negative -> CFGGuider21 ->50-step Euler from EmptyFlux2Latent816x1088.",
        "author_template": baseline["author_template"],
        "primary_sources": ["https://github.com/black-forest-labs/flux2", "https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B"],
        "research_scope": "One removal ablation of the already validated native source-only graph. No new graph mechanism, portrait slot, prompt, crop, sampler or finishing stage.",
        "comparison_path": str(BASELINE_RAW), "comparison_sha256": PINS[BASELINE_RAW],
        "comparison_label": "CHARACTER LORA 0.9 RAW", "source_original_excluded_from_scoring": str(original),
        "acceptance": "Compare raw source/0.9/0 outputs on likeness against the other five genuine photos, source expression and pupil focus, hairline/head pose, skin realism and room detail. This is source-fidelity diagnosis, not stronger-High acceptance.",
        "production_changed": False, "postprocess": False,
        "limitation": "The unchanged m1tch_person text token remains to isolate only the weight change. Current runtime may differ from September3; historical baseline comparison is not a same-runtime rerun.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-run", type=Path, help="Saved owned terminal-success job, required only for occupied3090 cache.")
    args = parser.parse_args()
    if (DESTINATION / "submission-intent.json").exists() or (DESTINATION / "submission.json").exists():
        raise ValueError("Already attempted submission; inspect saved intent/history and never resubmit blindly.")
    if not args.execute and DESTINATION.exists():
        raise ValueError("Prepared destination exists; preserve it.")
    if args.execute and not (DESTINATION / "experiment.json").is_file():
        raise ValueError("Prepare and review the graph first.")
    initial = worker_snapshot(enforce_idle=args.execute, previous_run=args.previous_run)
    manifest = build_verified_manifest()
    if not args.execute:
        manifest["preparation_snapshot"] = initial
        DESTINATION.mkdir(parents=True)
        (DESTINATION / "experiment.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (DESTINATION / "prompt-api.json").write_text(json.dumps(manifest["prompt"], indent=2), encoding="utf-8")
        print(json.dumps({"status": "prepared_only", "run": str(DESTINATION), "differences": manifest["graph_differences"]}, indent=2))
        return
    prepared = read_json(DESTINATION / "experiment.json")
    if {key: value for key, value in prepared.items() if key != "preparation_snapshot"} != manifest:
        raise ValueError("Prepared manifest differs from fresh verified evidence; no submission.")
    if read_json(DESTINATION / "prompt-api.json") != manifest["prompt"]:
        raise ValueError("Prepared standalone graph differs from the reviewed manifest.")
    final = worker_snapshot(enforce_idle=True, previous_run=args.previous_run)
    client_id = "upgrade-no-character-" + uuid.uuid4().hex
    intent = {"status": "submission_attempt_started", "client_id": client_id,
        "manifest_sha256": sha(DESTINATION / "experiment.json"), "preflight": [initial, final]}
    (DESTINATION / "submission-intent.json").write_text(json.dumps(intent, indent=2), encoding="utf-8")
    result = api("prompt", body={"prompt": manifest["prompt"], "client_id": client_id})
    (DESTINATION / "submission.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
