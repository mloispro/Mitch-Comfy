"""CPU-only evaluation of the exact genuine-third character-LoRA removal control.

Reads the completed 8188 job only; never queues generation or changes its PNG.
The separate BeautyGRPO evaluator retains its strict adapter requirements.
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
RUN = ROOT / "work/upgrade-high-20260907/third-no-character-control"
utility = run_path(str(ROOT / "scripts/evaluate-upgrade-beautygrpo.py"))
sha = utility["sha"]
read = utility["read"]
clean_graph = utility["graph_without_cache_markers"]
LABEL = "CHARACTER LORA 0 RAW"
BASELINE_LABEL = "CHARACTER LORA 0.9 RAW"


def verify_result(run, manifest):
    submission = json.loads((run / "submission.json").read_text(encoding="utf-8"))
    prompt_id = submission["prompt_id"]
    with urllib.request.urlopen("http://127.0.0.1:8188/history/" + prompt_id, timeout=30) as response:
        history = json.load(response).get(prompt_id)
    if not history or not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("This exact no-character job has not completed successfully.")
    expected = clean_graph(manifest["prompt"])
    if history["prompt"][1] != prompt_id or clean_graph(history["prompt"][2]) != expected:
        raise ValueError("Successful history graph differs from the submitted no-character control.")
    if manifest["output_node"] != "27" or manifest["identity_strength"] != 0 or manifest["turbo"] is not False:
        raise ValueError("Not the prescribed no-character/TurboOFF control.")
    if not manifest["phone_camera_style"] or manifest["phone_camera_style_strength"] != .25:
        raise ValueError("Phone style must be ON at0.25.")
    baseline_manifest_path = Path(manifest["baseline_run"]) / "experiment.json"
    if sha(baseline_manifest_path) != manifest["baseline_manifest_sha256"]:
        raise ValueError("Recorded0.9 baseline manifest changed.")
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8-sig"))
    baseline_graph = clean_graph(baseline_manifest["prompt"])
    expected_control = copy.deepcopy(baseline_graph)
    expected_control["2"]["inputs"]["strength_model"] = 0.0
    expected_control["27"]["inputs"]["filename_prefix"] = "upgrade-high-20260907/third-no-character-control/raw"
    if expected_control != expected:
        raise ValueError("More changed than character strength and output prefix.")
    adapters = {key: node["inputs"] for key, node in expected.items() if "lora" in node["class_type"].lower()}
    if set(adapters) != {"2", "3"} or adapters["2"]["strength_model"] != 0 or adapters["3"]["strength_model"] != .25:
        raise ValueError("Unexpected character/phone adapter settings.")
    if adapters["2"]["lora_name"] != "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors":
        raise ValueError("Unexpected disabled character adapter.")
    if adapters["3"]["lora_name"].replace("\\", "/") != "smartphone-snapshot/FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors":
        raise ValueError("Unexpected active phone adapter.")
    zero_loader = manifest["character_loader_zero_behavior"]
    if sha(Path(zero_loader["implementation"])) != zero_loader["sha256"]:
        raise ValueError("Verified zero-strength bypass implementation changed.")
    images = history["outputs"]["27"]["images"]
    if len(images) != 1 or images[0]["type"] != "output":
        raise ValueError("Expected one native saved output.")
    item = images[0]
    output = (COMFY / "output" / item.get("subfolder", "") / item["filename"]).resolve()
    if not output.is_relative_to((COMFY / "output").resolve()):
        raise ValueError("Unsafe output path.")
    with Image.open(output) as image:
        if image.size != (816, 1088) or clean_graph(json.loads(image.info["prompt"])) != expected:
            raise ValueError("Output dimensions or embedded graph do not match the no-character control.")
    baseline = Path(manifest["baseline_output"]["path"])
    if sha(baseline) != manifest["baseline_output"]["sha256"]:
        raise ValueError("Recorded0.9 baseline raw image changed.")
    with Image.open(baseline) as image:
        if image.size != (816, 1088) or clean_graph(json.loads(image.info["prompt"])) != baseline_graph:
            raise ValueError("Actual baseline PNG does not match its recorded graph.")
    return prompt_id, history, output, baseline, adapters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args()
    run = args.run.resolve()
    if run != RUN.resolve():
        raise ValueError("This evaluator is specific to the prepared third no-character control.")
    destination = run / "evaluation"
    if destination.exists():
        raise ValueError("Preserve the existing evaluation directory.")
    manifest = json.loads((run / "experiment.json").read_text(encoding="utf-8"))
    prompt_id, history, output, baseline, adapters = verify_result(run, manifest)
    source, references, exclusions = utility["source_and_references"](manifest)
    if len(references) != 5 or len(exclusions) != 1 or not exclusions[0]["path"].endswith("val_03_navy_upper_body.jpg"):
        raise ValueError("Score against the five other genuine photographs, excluding the true third original.")
    photos = {"SOURCE": read(source), BASELINE_LABEL: read(baseline), LABEL: read(output)}
    root = Path.home() / ".insightface"
    models = root / "models/antelopev2"
    if not all((models / name).is_file() for name in ("scrfd_10g_bnkps.onnx", "glintr100.onnx", "1k3d68.onnx")):
        raise ValueError("Installed CPU scoring weights missing; no automatic downloads.")
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
    for label in (BASELINE_LABEL, LABEL):
        result = results[label]
        source_result = results["SOURCE"]
        comparisons[label] = {
            "identity_centroid_delta_from_source": result["identity_centroid"] - source_result["identity_centroid"],
            "max_pose_delta_from_source": float(np.abs(np.array(result["pose"]) - source_result["pose"]).max()),
            "max_eye_coordinate_delta_from_source": float(np.abs(np.array(result["eye_coordinates"]) - source_result["eye_coordinates"]).max()),
            "mouth_corner_mean_error_from_source": float(np.linalg.norm(np.array(result["mouth_corner_coordinates"]) - source_result["mouth_corner_coordinates"], axis=1).mean()),
        }
    report = {"status": "evaluated_pending_visual_review_not_promoted", "prompt_id": prompt_id,
        "source": manifest["source"], "baseline": manifest["baseline_output"],
        "output": {"path": str(output), "sha256": sha(output)}, "adapters": adapters,
        "manifest_sha256": sha(run / "experiment.json"),
        "references": [{"path": str(path), "sha256": sha(path)} for path in references],
        "excluded_source_references": exclusions, "results": results, "source_comparisons": comparisons,
        "no_character_minus_character_identity": results[LABEL]["identity_centroid"] - results[BASELINE_LABEL]["identity_centroid"],
        "graph_differences": manifest["graph_differences"], "source_pixels_preserved_by_postprocess": False,
        "active_character_lora": False, "upstream_character_lora": False,
        "phone_camera_style": True, "phone_camera_style_strength": .25, "turbo": False,
        "scoring_execution_provider": "CPUExecutionProvider", "gaze_repair_applied": False,
        "history_messages": history["status"].get("messages", []), "production_promoted": False,
        "limitation": "Single genuine-source character-strength control. Original source is excluded from recognition scoring. Historical0.9 baseline is not a same-runtime rerun. Scores are diagnostics, not beauty, realism, no-teeth or identity-lock proof. Comparison images resize for display; native PNGs are unchanged."}
    destination.mkdir()
    (destination / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    utility["comparison_sheets"](destination, photos, detections)
    (destination / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
