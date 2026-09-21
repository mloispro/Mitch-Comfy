"""Strict CPU audit of the training-matched existing-character High fallback.

Requires the precise identity bundle (LoRA0.9 plus trained token) and fixed High
semantics. Does not submit jobs or modify prior trials, evaluators or images.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from runpy import run_path
import sys
import urllib.request

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
RUN = ROOT / "work/upgrade-high-20260907/third-native-high-character-matched"
BASELINE = ROOT / "work/upgrade-high-20260907/third-native-high-pilot"
matched = run_path(str(ROOT / "scripts/run-upgrade-native-high-character-matched.py"))
if hashlib.sha256(matched["FALLBACK_SCRIPT"].read_bytes()).hexdigest() != matched["FALLBACK_SCRIPT_SHA256"]:
    raise ValueError("Reviewed fallback verification implementation changed.")
runner = run_path(str(matched["FALLBACK_SCRIPT"]))
prior = run_path(str(ROOT / "scripts/evaluate-upgrade-native-high-pilot.py"))
utility = prior["utility"]
sha, read = utility["sha"], utility["read"]
clean_graph = utility["graph_without_cache_markers"]
CHAR0 = "NATIVE HIGH CHARACTER OFF"
MATCHED = "NATIVE HIGH MATCHED CHARACTER ON"
FIDELITY = "HISTORICAL FIDELITY CHARACTER 0.9"


def verify_result(manifest):
    for path, expected in runner["PINS"].items():
        if sha(path) != expected:
            raise ValueError("Pinned no-character High evidence changed: " + str(path))
    baseline_manifest = json.loads((BASELINE / "experiment.json").read_text(encoding="utf-8"))
    baseline_id, baseline_history, baseline_raw, _, fidelity_raw, _, _ = prior["verify_result"](baseline_manifest)
    if manifest["baseline_run"] != str(BASELINE) or manifest["baseline_prompt_id"] != baseline_id:
        raise ValueError("Matched fallback must compare with the exact completed character-OFF High.")
    if manifest["baseline_manifest_sha256"] != sha(BASELINE / "experiment.json"):
        raise ValueError("Matched baseline manifest hash mismatch.")
    expected = copy.deepcopy(clean_graph(baseline_manifest["prompt"]))
    expected["2"]["inputs"]["strength_model"] = .9
    expected["6"]["inputs"]["text"] = "m1tch_person. " + baseline_manifest["effective_prompt"]
    expected["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-native-high-character-matched/raw"
    if clean_graph(manifest["prompt"]) != expected or manifest["effective_prompt"] != expected["6"]["inputs"]["text"]:
        raise ValueError("Matched graph changed beyond identity weight, trained-token prefix and output prefix.")
    if json.loads((RUN / "prompt-api.json").read_text(encoding="utf-8")) != expected:
        raise ValueError("Matched standalone graph differs from its manifest.")
    if manifest["identity_strength"] != .9 or not manifest["active_character_lora"] or manifest["new_character_training"]:
        raise ValueError("Require existing-character0.9 and no new training.")
    if manifest["character_trigger"] != "m1tch_person." or not manifest["character_trigger_present"]:
        raise ValueError("Require the exact existing character's trained token.")
    if manifest["identity_conditioning_bundle"]["weight_only_causal_ablation"] is not False:
        raise ValueError("Matched activation is a bundled mechanism test, not a weight-only ablation.")
    for field in ("source", "references", "verified_models", "phone_camera_style",
                  "phone_camera_style_strength", "turbo", "seed", "steps", "cfg", "sampler", "width", "height"):
        if manifest[field] != baseline_manifest[field]:
            raise ValueError("Matched fallback changed a protected comparison field: " + field)
    submission = json.loads((RUN / "submission.json").read_text(encoding="utf-8"))
    prompt_id = submission["prompt_id"]
    with urllib.request.urlopen("http://127.0.0.1:8188/history/" + prompt_id, timeout=30) as response:
        history = json.load(response).get(prompt_id)
    if not history or not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("The exact matched existing-character High has not completed successfully.")
    if history["prompt"][1] != prompt_id or clean_graph(history["prompt"][2]) != expected:
        raise ValueError("Executed matched graph differs from reviewed evidence.")
    images = history["outputs"]["27"]["images"]
    if len(images) != 1 or images[0]["type"] != "output":
        raise ValueError("Require exactly one ordinary matched output.")
    item = images[0]
    output = (COMFY / "output" / item.get("subfolder", "") / item["filename"]).resolve()
    if not output.is_relative_to((COMFY / "output/upgrade-high-20260907/third-native-high-character-matched").resolve()):
        raise ValueError("Output is outside the exact matched output directory.")
    with Image.open(output) as image:
        if image.size != (816, 1088) or clean_graph(json.loads(image.info["prompt"])) != expected:
            raise ValueError("Matched PNG dimensions or embedded graph mismatch.")
    if sha(baseline_raw) != manifest["baseline_output"]["sha256"]:
        raise ValueError("Pinned no-character High PNG changed.")
    adapters = {key: node["inputs"] for key, node in expected.items() if "lora" in node["class_type"].lower()}
    if set(adapters) != {"2", "3"} or adapters["2"]["strength_model"] != .9 or adapters["3"]["strength_model"] != .25:
        raise ValueError("Unexpected matched adapters or strengths.")
    return prompt_id, history, output, baseline_raw, fidelity_raw, adapters, baseline_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args()
    if args.run.resolve() != RUN.resolve():
        raise ValueError("This evaluator is specific to the one training-matched existing-character High.")
    destination = RUN / "evaluation"
    if destination.exists():
        raise ValueError("Preserve the existing evaluation directory.")
    manifest = json.loads((RUN / "experiment.json").read_text(encoding="utf-8"))
    prompt_id, history, output, baseline_raw, fidelity_raw, adapters, baseline_history = verify_result(manifest)
    source, references, exclusions = utility["source_and_references"](manifest)
    if len(references) != 5 or len(exclusions) != 1 or not exclusions[0]["path"].endswith("val_03_navy_upper_body.jpg"):
        raise ValueError("Exclude the genuine source from scoring and use five other genuine photographs.")
    photos = {"SOURCE": read(source), CHAR0: read(baseline_raw), MATCHED: read(output), FIDELITY: read(fidelity_raw)}
    root = Path.home() / ".insightface"
    models = root / "models/antelopev2"
    if not all((models / name).is_file() for name in ("scrfd_10g_bnkps.onnx", "glintr100.onnx", "1k3d68.onnx")):
        raise ValueError("Existing CPU scoring weights missing; no automatic downloads.")
    from insightface.app import FaceAnalysis

    sys.path.insert(0, str(ROOT / "custom_nodes/ComfyUI-AIToolkit-Training"))
    import flux2_klein9b_source_gaze_lock as gaze
    from experimental_upgrade_smile_balance import measure_smile

    cv2.setNumThreads(4)
    analyzer = FaceAnalysis(name="antelopev2", root=str(root), providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"])
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))

    def face(rgb):
        found = analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if len(found) != 1:
            raise ValueError("Exactly one detected face is required for unambiguous scoring.")
        return found[0]

    vectors = [face(read(path)).normed_embedding for path in references]
    centroid = np.mean(vectors, axis=0)
    centroid /= np.linalg.norm(centroid)
    results, detections = {}, {}
    for label, rgb in photos.items():
        detected = face(rgb)
        detections[label] = detected
        points, method = gaze._detect_refined_landmarks(rgb)
        smile = measure_smile(points)
        results[label] = {"identity_centroid": float(detected.normed_embedding @ centroid),
            "per_reference_similarity": [float(detected.normed_embedding @ vector) for vector in vectors],
            "pose": detected.pose.tolist(), "pose_order": "pitch_yaw_roll",
            "eye_coordinates": [gaze._eye_measurement(points, eye)["coordinate"].tolist() for eye in gaze._EYES],
            "mouth_opening_ratio": float(smile["opening_ratio"]), "smile_lift": float(smile["smile_lift"]),
            "mouth_corner_coordinates": smile["corner_coordinates"].tolist(),
            "face_bbox": detected.bbox.tolist(), "landmark_method": method,
            "dimensions": {"width": int(rgb.shape[1]), "height": int(rgb.shape[0])}}
    comparisons = {}
    for label in (CHAR0, MATCHED, FIDELITY):
        result, original = results[label], results["SOURCE"]
        comparisons[label] = {
            "identity_centroid_delta_from_source": result["identity_centroid"] - original["identity_centroid"],
            "max_pose_delta_from_source": float(np.abs(np.array(result["pose"]) - original["pose"]).max()),
            "max_eye_coordinate_delta_from_source": float(np.abs(np.array(result["eye_coordinates"]) - original["eye_coordinates"]).max()),
            "mouth_corner_mean_error_from_source": float(np.linalg.norm(np.array(result["mouth_corner_coordinates"]) - original["mouth_corner_coordinates"], axis=1).mean()),
        }
    report = {"status": "evaluated_pending_visual_review_not_promoted", "prompt_id": prompt_id,
        "source": manifest["source"], "baseline": manifest["baseline_output"],
        "output": {"path": str(output), "sha256": sha(output)}, "adapters": adapters,
        "manifest_sha256": sha(RUN / "experiment.json"),
        "references": [{"path": str(path), "sha256": sha(path)} for path in references],
        "excluded_source_references": exclusions, "results": results, "source_comparisons": comparisons,
        "matched_character_on_minus_off_identity": results[MATCHED]["identity_centroid"] - results[CHAR0]["identity_centroid"],
        "matched_high_minus_historical_fidelity_identity": results[MATCHED]["identity_centroid"] - results[FIDELITY]["identity_centroid"],
        "graph_differences": manifest["graph_differences"], "source_pixels_preserved_by_postprocess": False,
        "identity_conditioning_bundle": manifest["identity_conditioning_bundle"],
        "active_character_lora": True, "character_lora_strength": .9, "character_trigger_present": True,
        "character_trigger": "m1tch_person.", "new_character_training": False,
        "upstream_character_lora": False, "phone_camera_style": True, "phone_camera_style_strength": .25,
        "phone_canonical_trigger_present": False, "turbo": False,
        "scoring_execution_provider": "CPUExecutionProvider", "gaze_repair_applied": False,
        "history_messages": history["status"].get("messages", []), "production_promoted": False,
        "limitation": "One bundled existing-character mechanism ON/OFF test: LoRA0.9 plus trained token, not a weight-only causal ablation. All semantic High instructions are unchanged. Similarity/gaze/smile landmarks are diagnostics, not beauty/realism/identity-lock proof. Fidelity0.9 is historical. Original PNGs are unchanged; comparison sheets resize only for display. Canonical phone trigger remains absent in both High images."}
    destination.mkdir()
    (destination / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (destination / "baseline-history.json").write_text(json.dumps(baseline_history, indent=2), encoding="utf-8")
    utility["comparison_sheets"](destination, photos, detections)
    (destination / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
