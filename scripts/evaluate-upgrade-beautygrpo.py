"""Read one completed local BeautyGRPO experiment and evaluate it on CPU.

No generation, model downloads, face repair, or changes to the source/output PNG.
Optional manifest fields: comparison_path, comparison_sha256, comparison_label;
candidate_label distinguishes explicitly labeled adapter-off causal controls.
source.original_path/original_sha256 identify the original of a resized input.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
REFERENCE_DIRECTORY = ROOT / "datasets/mitch-identity-stills-v3/validation"
REFERENCE_PINS = {
    "val_01_surf_full_body.jpg": "d17aa33ee7f90b135e2a9167059ddbb4437b7578b3b4ec9c9b10f1d9836d8901",
    "val_02_body_mirror_sleeveless.jpg": "4b32845393fbcbf6ea0ca80068c48af10db52bc81909dba9638370bc7ee0a622",
    "val_03_navy_upper_body.jpg": "fef084d60982754250ab76a7320d71228c96255b2d5244b7461f77b67ce929cf",
    "val_04_window_small_smile.jpg": "2ebeb864b970168ea05c74275aa240c4122795a2050e51534c554acb3ecec6eb",
    "val_05_balcony_opposite_angle.jpg": "648f5643d58526c65eacab5ae0e0570cad9f7ef34fbd568ca74b47a7f6615032",
    "val_06_car_daylight.jpg": "feb62e762b990fb9979d730d9ba0a8d08c0cb81832db6eab308fe760c4a98b4d",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def path_from_manifest(value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def read(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(ImageOps.exif_transpose(image).convert("RGB"))


def graph_without_cache_markers(graph: dict) -> dict:
    result = copy.deepcopy(graph)
    for node in result.values():
        node.pop("is_changed", None)
    return result


def successful_output(run: Path, manifest: dict) -> tuple[str, dict, Path, dict]:
    submission = json.loads((run / "submission.json").read_text(encoding="utf-8"))
    prompt_id = submission["prompt_id"]
    # This experiment belongs to the explicitly locked primary worker.
    with urllib.request.urlopen(
        "http://127.0.0.1:8188/history/" + str(prompt_id), timeout=30
    ) as response:
        history = json.load(response).get(prompt_id)
    if not history or not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise ValueError("This exact job has not completed successfully; no output evaluated.")
    expected = graph_without_cache_markers(manifest["prompt"])
    history_prompt = history.get("prompt", [])
    if len(history_prompt) < 3 or history_prompt[1] != prompt_id:
        raise ValueError("History does not identify the requested job.")
    if graph_without_cache_markers(history_prompt[2]) != expected:
        raise ValueError("Live job graph differs from the experiment manifest.")
    output_node = str(manifest.get("output_node", "14"))
    outputs = history["outputs"][output_node]["images"]
    if len(outputs) != 1 or outputs[0]["type"] != "output":
        raise ValueError("Expected exactly one saved output image.")
    item = outputs[0]
    output = (COMFY / "output" / item.get("subfolder", "") / item["filename"]).resolve()
    if not output.is_relative_to((COMFY / "output").resolve()):
        raise ValueError("Output path escapes the ComfyUI output directory.")
    with Image.open(output) as image:
        executed = graph_without_cache_markers(json.loads(image.info["prompt"]))
    if executed != expected:
        raise ValueError("Saved PNG graph differs from the experiment manifest.")
    adapter_nodes = [node for node in executed.values() if "lora" in node["class_type"].lower()]
    if len(adapter_nodes) != 1 or adapter_nodes[0]["class_type"] not in ("LoraLoaderModelOnly", "LoraLoader"):
        raise ValueError("Expected exactly one explicit standard BeautyGRPO LoRA loader.")
    adapter = adapter_nodes[0]["inputs"]
    if adapter["lora_name"].replace("\\", "/") != "beautygrpo/BeautyGRPO.safetensors":
        raise ValueError("Unexpected adapter; a character/other LoRA is not this experiment.")
    return prompt_id, history, output, adapter


def source_and_references(manifest: dict) -> tuple[Path, list[Path], list[dict]]:
    descriptor = manifest["source"]
    source = path_from_manifest(descriptor["path"])
    source_hash = sha(source)
    if source_hash != descriptor["sha256"].lower():
        raise ValueError("Source bytes differ from the experiment manifest.")
    excluded_hashes = {source_hash}
    original_path = descriptor.get("original_path")
    original_hash = descriptor.get("original_sha256")
    if original_path:
        actual = sha(path_from_manifest(original_path))
        if not original_hash or actual != original_hash.lower():
            raise ValueError("A source original requires its matching SHA256.")
        excluded_hashes.add(actual)
    elif original_hash:
        excluded_hashes.add(original_hash.lower())
    references, exclusions = [], []
    for name, expected in REFERENCE_PINS.items():
        path = REFERENCE_DIRECTORY / name
        if sha(path) != expected:
            raise ValueError("Pinned genuine evaluation photograph changed: " + name)
        if expected in excluded_hashes:
            exclusions.append({"path": str(path), "sha256": expected, "reason": "source or genuine source original"})
        else:
            references.append(path)
    if len(references) < 2:
        raise ValueError("At least two independent genuine photographs are required.")
    return source, references, exclusions


def comparison_sheets(destination: Path, photos: dict, detections: dict) -> None:
    for crop, filename, height in (
        (False, "source-candidate-full.jpg", 1024),
        (True, "source-candidate-face.jpg", 512),
        (False, "source-candidate-thumbnail.jpg", 360),
    ):
        panels = []
        for name, rgb in photos.items():
            image = Image.fromarray(rgb)
            if crop:
                box = detections[name].bbox
                pad = float(box[2] - box[0]) * 0.15
                left, top, right, bottom = np.rint(box + [-pad, -pad, pad, pad]).astype(int)
                image = image.crop((max(0, left), max(0, top), min(image.width, right), min(image.height, bottom)))
            image = image.resize((max(1, round(image.width * height / image.height)), height), Image.Resampling.LANCZOS)
            panels.append((name, image))
        sheet = Image.new("RGB", (sum(image.width for _, image in panels), height + 36), (20, 20, 20))
        draw = ImageDraw.Draw(sheet)
        x = 0
        for name, image in panels:
            sheet.paste(image, (x, 36))
            draw.text((x + 6, 9), name, fill="white")
            x += image.width
        sheet.save(destination / filename, quality=97)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to((ROOT / "work").resolve()):
        raise ValueError("Use a saved workspace experiment.")
    destination = run / "evaluation"
    if destination.exists():
        raise ValueError("Preserve the existing evaluation; destination already exists.")
    manifest = json.loads((run / "experiment.json").read_text(encoding="utf-8"))
    prompt_id, history, output, adapter = successful_output(run, manifest)
    candidate_label = str(manifest.get("candidate_label", "BEAUTYGRPO HIGH"))
    if not candidate_label.strip() or candidate_label == "SOURCE":
        raise ValueError("Candidate label must distinguish the generated result from its source.")
    active_adapter = float(adapter["strength_model"]) != 0 or float(adapter.get("strength_clip", 0)) != 0
    if "active_beauty_adapter" in manifest and manifest["active_beauty_adapter"] is not active_adapter:
        raise ValueError("Manifest adapter-activity claim differs from the executed strengths.")
    source, references, exclusions = source_and_references(manifest)
    photos = {"SOURCE": read(source)}
    comparison = None
    if manifest.get("comparison_path"):
        comparison_path = path_from_manifest(manifest["comparison_path"])
        comparison_hash = sha(comparison_path)
        if manifest.get("comparison_sha256") and comparison_hash != manifest["comparison_sha256"].lower():
            raise ValueError("Comparison photograph changed.")
        label = str(manifest.get("comparison_label", "CURRENT LOW"))
        if label in ("SOURCE", candidate_label):
            raise ValueError("Comparison label must distinguish the three panels.")
        photos[label] = read(comparison_path)
        comparison = {"path": str(comparison_path), "sha256": comparison_hash, "label": label}
    photos[candidate_label] = read(output)

    insightface_root = Path.home() / ".insightface"
    models = insightface_root / "models/antelopev2"
    required = ("scrfd_10g_bnkps.onnx", "glintr100.onnx", "1k3d68.onnx")
    if not all((models / name).is_file() for name in required):
        raise ValueError("Existing CPU scoring models are missing; automatic downloads are disabled.")
    from insightface.app import FaceAnalysis

    sys.path.insert(0, str(ROOT / "custom_nodes/ComfyUI-AIToolkit-Training"))
    import flux2_klein9b_source_gaze_lock as gaze
    from experimental_upgrade_smile_balance import measure_smile

    cv2.setNumThreads(4)
    analyzer = FaceAnalysis(name="antelopev2", root=str(insightface_root),
        providers=["CPUExecutionProvider"], allowed_modules=["detection", "recognition", "landmark_3d_68"])
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))

    def face(rgb):
        detected = analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if not detected:
            raise ValueError("No face detected in a source, candidate, comparison or scoring reference.")
        return max(detected, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]))), len(detected)

    vectors = [face(read(path))[0].normed_embedding for path in references]
    centroid = np.mean(vectors, axis=0)
    centroid /= np.linalg.norm(centroid)
    results, detections = {}, {}
    for name, rgb in photos.items():
        detected, count = face(rgb)
        if count != 1:
            raise ValueError("Expression evaluation needs one unambiguous face per comparison image: " + name)
        detections[name] = detected
        points, landmark_method = gaze._detect_refined_landmarks(rgb)
        smile = measure_smile(points)
        results[name] = {
            "identity_centroid": float(detected.normed_embedding @ centroid),
            "per_reference_similarity": [float(detected.normed_embedding @ vector) for vector in vectors],
            "pose": detected.pose.tolist(), "pose_order": "pitch_yaw_roll",
            "mouth_opening_ratio": float(smile["opening_ratio"]),
            "smile_lift": float(smile["smile_lift"]),
            "mouth_corner_coordinates": smile["corner_coordinates"].tolist(),
            "eye_coordinates": [gaze._eye_measurement(points, eye)["coordinate"].tolist() for eye in gaze._EYES],
            "landmark_method": landmark_method, "face_bbox": detected.bbox.tolist(),
            "detected_faces": count, "primary_selection": "single detected face",
            "dimensions": {"width": int(rgb.shape[1]), "height": int(rgb.shape[0])},
        }
    source_result, candidate = results["SOURCE"], results[candidate_label]
    source_aspect = photos["SOURCE"].shape[1] / photos["SOURCE"].shape[0]
    candidate_aspect = photos[candidate_label].shape[1] / photos[candidate_label].shape[0]
    report = {
        "status": "evaluated_pending_visual_review_not_promoted", "prompt_id": prompt_id,
        "source": manifest["source"], "output": {"path": str(output), "sha256": sha(output)},
        "comparison": comparison, "manifest_sha256": sha(run / "experiment.json"),
        "submission_sha256": sha(run / "submission.json"), "adapter": adapter,
        "candidate_label": candidate_label, "active_beauty_adapter": active_adapter,
        "references": [{"path": str(path), "sha256": sha(path)} for path in references],
        "excluded_source_references": exclusions, "source_hashes_excluded_from_reference_set": True,
        "results": results,
        "identity_centroid_delta": candidate["identity_centroid"] - source_result["identity_centroid"],
        "max_pose_delta": float(np.abs(np.array(source_result["pose"]) - candidate["pose"]).max()),
        "max_eye_coordinate_delta": float(np.abs(np.array(source_result["eye_coordinates"]) - candidate["eye_coordinates"]).max()),
        "source_aspect_ratio": source_aspect, "output_aspect_ratio": candidate_aspect,
        "aspect_relative_error": abs(candidate_aspect / source_aspect - 1),
        "character_lora_in_executed_graph": False,
        "upstream_character_lora": False if manifest["source"].get("genuine") is True else manifest["source"].get("upstream_character_lora", "unknown"),
        "history_messages": history["status"].get("messages", []),
        "scoring_execution_provider": "CPUExecutionProvider", "gaze_repair_applied": False,
        "production_promoted": False,
        "limitation": "Recognition, pose, iris and lip measurements are diagnostics, not proof of attractiveness, identical gaze, teeth absence, realism or identity lock. Source may be synthetic; only the pinned genuine photographs are scoring anchors. Comparison sheets resize for display; original output is unchanged.",
    }
    destination.mkdir()
    (destination / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    comparison_sheets(destination, photos, detections)
    (destination / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
