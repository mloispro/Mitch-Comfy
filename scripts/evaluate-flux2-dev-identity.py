from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_ROOT = REPO_ROOT / "custom_nodes" / "ComfyUI-AIToolkit-Training"
sys.path.insert(0, str(NODE_ROOT))

from identity_leakage import evaluate_identity_scope  # noqa: E402


CORE_SCENES = {"portrait", "waist-up-social", "near-profile-candid"}
EXPECTED_CROWD_FACE_COUNT = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the reproducible FLUX.2 Dev Mitch LoRA benchmark against "
            "genuine held-out photographs."
        )
    )
    parser.add_argument("--reference", action="append", required=True, type=Path)
    parser.add_argument(
        "--calibration-reference",
        action="append",
        type=Path,
        help=(
            "Optional genuine reference used only to derive strong/near thresholds. "
            "Defaults to all scoring references."
        ),
    )
    parser.add_argument(
        "--expected-reference-count",
        type=int,
        default=6,
        help=(
            "Exact number of genuine held-out references required. Defaults to six "
            "for compatibility with the original benchmark."
        ),
    )
    parser.add_argument(
        "--scene",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Generated solo scene. Repeat for all four benchmark scenes.",
    )
    parser.add_argument(
        "--core-scene-label",
        action="append",
        help="Scene label that must pass the core identity gate. Defaults to the legacy three labels.",
    )
    parser.add_argument(
        "--full-body-scene-label",
        default="full-body-walking",
        help="Exactly one scene label reserved for manual body/anatomy review.",
    )
    parser.add_argument("--crowd", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--insightface-root", type=Path)
    return parser.parse_args()


def normalized(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    return value / max(float(np.linalg.norm(value)), 1e-8)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(normalized(left), normalized(right)))


def load_faces(analyzer: FaceAnalysis, path: Path):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {path}")
    return analyzer.get(image)


def largest_face(faces):
    if not faces:
        return None
    return max(
        faces,
        key=lambda face: float(
            (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
        ),
    )


def prompted_crowd_main_index(faces, image_path: Path) -> int:
    """Select the centered foreground subject by prompt geometry, not likeness."""
    if not faces:
        raise ValueError("At least one crowd face is required")
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {image_path}")
    height, width = image.shape[:2]
    anchor_x, anchor_y = 0.50, 0.49
    scored = []
    for index, face in enumerate(faces):
        x1, y1, x2, y2 = (float(value) for value in face.bbox)
        center_x = ((x1 + x2) * 0.5) / width
        center_y = ((y1 + y2) * 0.5) / height
        area = max((x2 - x1) * (y2 - y1), 0.0) / max(width * height, 1)
        distance = (center_x - anchor_x) ** 2 + (center_y - anchor_y) ** 2
        scored.append((distance - 0.05 * area, index))
    return min(scored)[1]


def rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def parse_scene(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise RuntimeError(f"Scene must use LABEL=PATH syntax: {value}")
    label, raw_path = value.split("=", 1)
    if not label or not raw_path:
        raise RuntimeError(f"Scene must use LABEL=PATH syntax: {value}")
    return label, Path(raw_path).resolve()


def main() -> int:
    args = parse_args()
    references = [path.resolve() for path in args.reference]
    calibration_references = [
        path.resolve() for path in (args.calibration_reference or args.reference)
    ]
    scenes = [parse_scene(value) for value in args.scene]
    crowd_path = args.crowd.resolve()
    output_path = args.json_output.resolve()

    if args.expected_reference_count < 2:
        raise RuntimeError("Expected reference count must be at least two.")
    if len(references) != args.expected_reference_count:
        raise RuntimeError(
            "Expected exactly "
            f"{args.expected_reference_count} genuine held-outs, got {len(references)}."
        )
    if len(calibration_references) < 2:
        raise RuntimeError("At least two genuine calibration references are required.")
    if len(set(calibration_references)) != len(calibration_references):
        raise RuntimeError("Calibration references must be unique.")
    core_scene_labels = set(args.core_scene_label or CORE_SCENES)
    if not core_scene_labels:
        raise RuntimeError("At least one core scene label is required.")
    labels = {label for label, _ in scenes}
    required_labels = core_scene_labels | {args.full_body_scene_label}
    if labels != required_labels:
        raise RuntimeError(
            f"Expected scenes {sorted(required_labels)}, got {sorted(labels)}."
        )
    for path in [*references, *calibration_references, *(path for _, path in scenes), crowd_path]:
        if not path.is_file():
            raise RuntimeError(f"Image does not exist: {path}")

    model_root = (
        args.insightface_root.resolve()
        if args.insightface_root
        else Path.home() / ".insightface"
    )
    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(model_root),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))

    reference_faces = []
    for path in references:
        face = largest_face(load_faces(analyzer, path))
        if face is None:
            raise RuntimeError(f"No reference face detected: {path}")
        reference_faces.append(face)
    reference_embeddings = [normalized(face.normed_embedding) for face in reference_faces]
    calibration_faces = []
    for path in calibration_references:
        face = largest_face(load_faces(analyzer, path))
        if face is None:
            raise RuntimeError(f"No calibration face detected: {path}")
        calibration_faces.append(face)
    calibration_embeddings = [normalized(face.normed_embedding) for face in calibration_faces]
    pairwise = [
        cosine(left, right)
        for left, right in itertools.combinations(calibration_embeddings, 2)
    ]
    centroid = normalized(np.mean(np.stack(reference_embeddings), axis=0))
    reference_floor = min(pairwise)

    scene_reports = []
    for label, path in scenes:
        face = largest_face(load_faces(analyzer, path))
        if face is None:
            scene_reports.append(
                {
                    "label": label,
                    "path": str(path),
                    "calibrated_status": "face_not_detected",
                    "centroid_similarity": None,
                    "mean_reference_similarity": None,
                    "minimum_reference_similarity": None,
                    "per_reference_similarity": [],
                    "face_bbox": None,
                    "face_width_pixels": None,
                    "face_height_pixels": None,
                }
            )
            continue

        embedding = normalized(face.normed_embedding)
        similarities = [cosine(embedding, item) for item in reference_embeddings]
        centroid_similarity = cosine(embedding, centroid)
        mean_similarity = float(np.mean(similarities))
        if (
            centroid_similarity >= reference_floor - 0.02
            and mean_similarity >= reference_floor - 0.05
        ):
            calibrated_status = "strong_match"
        elif (
            centroid_similarity >= reference_floor - 0.08
            and mean_similarity >= reference_floor - 0.13
        ):
            calibrated_status = "near_match"
        else:
            calibrated_status = "identity_drift"
        bbox = [float(value) for value in face.bbox]
        scene_reports.append(
            {
                "label": label,
                "path": str(path),
                "calibrated_status": calibrated_status,
                "centroid_similarity": rounded(centroid_similarity),
                "mean_reference_similarity": rounded(mean_similarity),
                "minimum_reference_similarity": rounded(min(similarities)),
                "maximum_reference_similarity": rounded(max(similarities)),
                "per_reference_similarity": [rounded(value) for value in similarities],
                "detector_confidence": rounded(getattr(face, "det_score", None)),
                "face_bbox": [rounded(value) for value in bbox],
                "face_width_pixels": rounded(bbox[2] - bbox[0]),
                "face_height_pixels": rounded(bbox[3] - bbox[1]),
            }
        )

    ranked_detected = sorted(
        [item for item in scene_reports if item["centroid_similarity"] is not None],
        key=lambda item: (
            item["centroid_similarity"],
            item["minimum_reference_similarity"],
        ),
        reverse=True,
    )
    for rank, item in enumerate(ranked_detected, start=1):
        item["rank"] = rank

    crowd_faces = load_faces(analyzer, crowd_path)
    crowd_main_index = (
        prompted_crowd_main_index(crowd_faces, crowd_path) if crowd_faces else None
    )
    near_centroid_minimum = max(reference_floor - 0.08, 0.0)
    near_mean_minimum = max(reference_floor - 0.13, 0.0)
    crowd_report = evaluate_identity_scope(
        [normalized(face.normed_embedding) for face in crowd_faces],
        [face.bbox for face in crowd_faces],
        [float(face.det_score) for face in crowd_faces],
        centroid,
        near_centroid_minimum,
        preferred_main_index=crowd_main_index,
    ).as_dict()
    crowd_report["path"] = str(crowd_path)
    crowd_report["intended_main_selection"] = "prompted_center_foreground_anchor"
    crowd_report["expected_face_count"] = EXPECTED_CROWD_FACE_COUNT
    crowd_face_count_passed = len(crowd_faces) == EXPECTED_CROWD_FACE_COUNT
    crowd_report["face_count_passed"] = crowd_face_count_passed
    if not crowd_face_count_passed:
        crowd_report["failures"].append("unexpected_crowd_face_count")
        crowd_report["status"] = "rejected"
    if crowd_main_index is not None:
        crowd_main_embedding = normalized(crowd_faces[crowd_main_index].normed_embedding)
        crowd_per_reference = [
            cosine(crowd_main_embedding, reference) for reference in reference_embeddings
        ]
        crowd_mean_similarity = float(np.mean(crowd_per_reference))
    else:
        crowd_per_reference = []
        crowd_mean_similarity = -1.0
    crowd_report["main_mean_reference_similarity"] = rounded(crowd_mean_similarity)
    crowd_report["main_per_reference_similarity"] = [
        rounded(value) for value in crowd_per_reference
    ]
    crowd_report["main_centroid_minimum"] = rounded(near_centroid_minimum)
    crowd_report["main_mean_reference_minimum"] = rounded(near_mean_minimum)
    if crowd_mean_similarity < near_mean_minimum:
        crowd_report["failures"].append("main_identity_mean_below_threshold")
        crowd_report["status"] = "rejected"

    core_reports = [item for item in scene_reports if item["label"] in core_scene_labels]
    core_no_drift = all(
        item["calibrated_status"] in {"strong_match", "near_match"}
        for item in core_reports
    )
    core_strong_count = sum(
        item["calibrated_status"] == "strong_match" for item in core_reports
    )
    core_gate_passed = core_no_drift and core_strong_count >= 2
    crowd_failures = list(crowd_report.get("failures", []))
    crowd_main_identity_passed = not any(
        failure in {
            "main_identity_below_threshold",
            "main_identity_mean_below_threshold",
            "no_detected_face",
        }
        for failure in crowd_failures
    )
    crowd_leakage_failures = [
        failure
        for failure in crowd_failures
        if failure
        not in {
            "main_identity_below_threshold",
            "main_identity_mean_below_threshold",
            "no_detected_face",
            "unexpected_crowd_face_count",
        }
    ]
    crowd_gate_passed = (
        crowd_face_count_passed
        and crowd_main_identity_passed
        and not crowd_leakage_failures
    )

    report = {
        "method": "InsightFace AntelopeV2 glintr100 cosine similarity",
        "privacy": "All inference ran locally; no images were uploaded.",
        "scope": (
            "Automated identity similarity is a diagnostic, not proof of identity or "
            "overall image quality. Full-size and thumbnail review remains mandatory."
        ),
        "reference_calibration": {
            "paths": [str(path) for path in calibration_references],
            "pairwise_similarity": [rounded(value) for value in pairwise],
            "pairwise_minimum": rounded(reference_floor),
            "pairwise_mean": rounded(float(np.mean(pairwise))),
        },
        "scoring_references": {
            "paths": [str(path) for path in references],
            "count": len(references),
        },
        "scenes": scene_reports,
        "crowd_stress": crowd_report,
        "acceptance": {
            "core_scene_labels": sorted(core_scene_labels),
            "core_no_identity_drift": core_no_drift,
            "core_strong_match_count": core_strong_count,
            "core_requires_at_least_two_strong_matches": True,
            "core_gate_passed": core_gate_passed,
            "full_body_is_separate_stretch_goal": True,
            "crowd_main_identity_passed": crowd_main_identity_passed,
            "crowd_expected_face_count": EXPECTED_CROWD_FACE_COUNT,
            "crowd_face_count_passed": crowd_face_count_passed,
            "crowd_leakage_failures": crowd_leakage_failures,
            "crowd_gate_passed": crowd_gate_passed,
            "automatic_gates_passed": core_gate_passed and crowd_gate_passed,
            "manual_full_size_and_thumbnail_review_required": True,
            "promotion_eligible": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["acceptance"]["automatic_gates_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
