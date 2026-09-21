"""CPU-only audit of the exact native no-character High prompt pilot.

Independently verifies High, its no-character control and historical character0.9
baseline. The strict BeautyGRPO and no-character evaluators are not modified.
"""
from __future__ import annotations

import argparse
import copy
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
RUN = ROOT / "work/upgrade-high-20260907/third-native-high-pilot"
CONTROL = ROOT / "work/upgrade-high-20260907/third-no-character-control"
pilot = run_path(str(ROOT / "scripts/run-upgrade-native-high-pilot.py"))
control_evaluator = run_path(str(ROOT / "scripts/evaluate-upgrade-no-character-control.py"))
utility = control_evaluator["utility"]
sha, read = utility["sha"], utility["read"]
clean_graph = utility["graph_without_cache_markers"]
LOW = "NO-CHARACTER SOURCE-FIDELITY CONTROL"
HIGH = "NATIVE HIGH NO CHARACTER"
CHAR = "HISTORICAL CHARACTER 0.9"


def verify_result(manifest):
    for path, expected in pilot["PINS"].items():
        if sha(path) != expected:
            raise ValueError("Pinned no-character control evidence changed: " + str(path))
    control_manifest = json.loads((CONTROL / "experiment.json").read_text(encoding="utf-8"))
    control_id, control_history, control_raw, character_raw, adapters = control_evaluator["verify_result"](CONTROL, control_manifest)
    if manifest["baseline_run"] != str(CONTROL) or manifest["baseline_prompt_id"] != control_id:
        raise ValueError("Native High must compare with the exact completed no-character control.")
    if manifest["baseline_manifest_sha256"] != sha(CONTROL / "experiment.json"):
        raise ValueError("Native High control manifest hash mismatch.")
    expected = copy.deepcopy(clean_graph(control_manifest["prompt"]))
    expected["6"]["inputs"]["text"] = pilot["PROMPT"]
    expected["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-native-high-pilot/raw"
    if clean_graph(manifest["prompt"]) != expected or manifest["effective_prompt"] != pilot["PROMPT"]:
        raise ValueError("High graph differs beyond the exact approved positive prompt and output prefix.")
    if json.loads((RUN / "prompt-api.json").read_text(encoding="utf-8")) != expected:
        raise ValueError("Native High standalone graph does not match its manifest.")
    for field in ("source", "references", "verified_models", "identity_strength", "phone_camera_style",
                  "phone_camera_style_strength", "turbo", "seed", "steps", "cfg", "sampler", "width", "height"):
        if manifest[field] != control_manifest[field]:
            raise ValueError("Native High changed protected control field: " + field)
    submission = json.loads((RUN / "submission.json").read_text(encoding="utf-8"))
    prompt_id = submission["prompt_id"]
    with urllib.request.urlopen("http://127.0.0.1:8188/history/" + prompt_id, timeout=30) as response:
        history = json.load(response).get(prompt_id)
    if not history or not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("The exact native High pilot has not successfully completed.")
    if history["prompt"][1] != prompt_id or clean_graph(history["prompt"][2]) != expected:
        raise ValueError("Executed native High graph differs from the prepared graph.")
    images = history["outputs"]["27"]["images"]
    if len(images) != 1 or images[0]["type"] != "output":
        raise ValueError("Expected exactly one ordinary native High saved output.")
    item = images[0]
    output = (COMFY / "output" / item.get("subfolder", "") / item["filename"]).resolve()
    if not output.is_relative_to((COMFY / "output/upgrade-high-20260907/third-native-high-pilot").resolve()):
        raise ValueError("High output is outside the exact pilot output directory.")
    with Image.open(output) as image:
        if image.size != (816, 1088) or clean_graph(json.loads(image.info["prompt"])) != expected:
            raise ValueError("Native High dimensions or embedded PNG graph mismatch.")
    if sha(control_raw) != manifest["baseline_output"]["sha256"]:
        raise ValueError("Native High control PNG hash mismatch.")
    return prompt_id, history, output, control_raw, character_raw, adapters, control_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args()
    if args.run.resolve() != RUN.resolve():
        raise ValueError("This evaluator is specific to the reviewed genuine-third native High pilot.")
    destination = RUN / "evaluation"
    if destination.exists():
        raise ValueError("Preserve the existing evaluation directory.")
    manifest = json.loads((RUN / "experiment.json").read_text(encoding="utf-8"))
    prompt_id, history, output, control_raw, character_raw, adapters, control_history = verify_result(manifest)
    source, references, exclusions = utility["source_and_references"](manifest)
    if len(references) != 5 or len(exclusions) != 1 or not exclusions[0]["path"].endswith("val_03_navy_upper_body.jpg"):
        raise ValueError("Identity scoring must exclude the true source and use five other genuine photos.")
    photos = {"SOURCE": read(source), LOW: read(control_raw), HIGH: read(output), CHAR: read(character_raw)}
    root = Path.home() / ".insightface"
    models = root / "models/antelopev2"
    if not all((models / name).is_file() for name in ("scrfd_10g_bnkps.onnx", "glintr100.onnx", "1k3d68.onnx")):
        raise ValueError("Existing local CPU scoring models are missing; no automatic downloads.")
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
    for label in (LOW, HIGH, CHAR):
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
        "high_minus_no_character_control_identity": results[HIGH]["identity_centroid"] - results[LOW]["identity_centroid"],
        "graph_differences": manifest["graph_differences"], "source_pixels_preserved_by_postprocess": False,
        "active_character_lora": False, "upstream_character_lora": False,
        "phone_camera_style": True, "phone_camera_style_strength": .25, "turbo": False,
        "scoring_execution_provider": "CPUExecutionProvider", "gaze_repair_applied": False,
        "history_messages": history["status"].get("messages", []), "production_promoted": False,
        "limitation": "One genuine photograph and one prompt-only native High refinement. Similarity, gaze and smile landmarks are diagnostics, not beauty/realism/identity-lock proof. The character0.9 image is a historical comparison, not a same-runtime control. Native output PNGs are not altered; comparison sheets resize only for display."}
    destination.mkdir()
    (destination / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (destination / "control-history.json").write_text(json.dumps(control_history, indent=2), encoding="utf-8")
    utility["comparison_sheets"](destination, photos, detections)
    (destination / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
