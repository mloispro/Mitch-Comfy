from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare generated faces with multiple genuine photos using the local "
            "InsightFace AntelopeV2 recognition model."
        )
    )
    parser.add_argument(
        "--reference",
        action="append",
        required=True,
        help="Genuine reference image path. Repeat for multiple held-out views.",
    )
    parser.add_argument(
        "--candidate",
        action="append",
        required=True,
        help="Generated candidate image path. Repeat to rank several candidates.",
    )
    parser.add_argument(
        "--calibration-reference",
        action="append",
        help=(
            "Optional genuine reference used only to derive strong/near thresholds. "
            "Repeat for a stable calibration subset; defaults to all --reference values."
        ),
    )
    parser.add_argument(
        "--candidate-label",
        action="append",
        help="Optional label paired by position with each --candidate value.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path for a clean JSON report in addition to stdout.",
    )
    parser.add_argument(
        "--insightface-root",
        help=(
            "Optional InsightFace model root. Defaults to the current user's "
            "~/.insightface directory."
        ),
    )
    return parser.parse_args()


def normalized_embedding(face) -> np.ndarray:
    embedding = np.asarray(face.normed_embedding, dtype=np.float32)
    return embedding / max(float(np.linalg.norm(embedding)), 1e-8)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(
        np.dot(left, right)
        / max(float(np.linalg.norm(left) * np.linalg.norm(right)), 1e-8)
    )


def largest_face(analyzer: FaceAnalysis, path: Path):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {path}")
    faces = analyzer.get(image)
    if not faces:
        raise RuntimeError(f"No face detected: {path}")
    return max(
        faces,
        key=lambda face: float(
            (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
        ),
    )


def rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def main() -> None:
    args = parse_args()
    references = [Path(value).resolve() for value in args.reference]
    calibration_references = [
        Path(value).resolve() for value in (args.calibration_reference or args.reference)
    ]
    candidates = [Path(value).resolve() for value in args.candidate]
    labels = args.candidate_label or [path.stem for path in candidates]
    if len(references) < 2:
        raise RuntimeError("Use at least two genuine references for held-out calibration.")
    if len(calibration_references) < 2:
        raise RuntimeError("Use at least two genuine calibration references.")
    if len(labels) != len(candidates):
        raise RuntimeError("Use exactly one --candidate-label for each --candidate.")
    for path in [*references, *calibration_references, *candidates]:
        if not path.is_file():
            raise RuntimeError(f"Image does not exist: {path}")

    model_root = (
        Path(args.insightface_root).resolve()
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

    reference_faces = [largest_face(analyzer, path) for path in references]
    reference_embeddings = [normalized_embedding(face) for face in reference_faces]
    calibration_faces = [largest_face(analyzer, path) for path in calibration_references]
    calibration_embeddings = [normalized_embedding(face) for face in calibration_faces]
    reference_pairwise = [
        cosine(left, right)
        for left, right in itertools.combinations(calibration_embeddings, 2)
    ]
    centroid = np.mean(np.stack(reference_embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)

    reference_floor = min(reference_pairwise)
    reference_mean = float(np.mean(reference_pairwise))
    ranked = []
    for path, label in zip(candidates, labels, strict=True):
        face = largest_face(analyzer, path)
        embedding = normalized_embedding(face)
        face_bbox = [float(value) for value in face.bbox]
        similarities = [cosine(embedding, reference) for reference in reference_embeddings]
        centroid_similarity = cosine(embedding, centroid)
        mean_similarity = float(np.mean(similarities))
        minimum_similarity = min(similarities)
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
        ranked.append(
            {
                "label": label,
                "path": str(path),
                "centroid_similarity": rounded(centroid_similarity),
                "mean_reference_similarity": rounded(mean_similarity),
                "minimum_reference_similarity": rounded(minimum_similarity),
                "maximum_reference_similarity": rounded(max(similarities)),
                "per_reference_similarity": [rounded(value) for value in similarities],
                "calibrated_status": calibrated_status,
                "detector_confidence": rounded(getattr(face, "det_score", None)),
                "face_bbox": [rounded(value) for value in face_bbox],
                "face_width_pixels": rounded(face_bbox[2] - face_bbox[0]),
                "face_height_pixels": rounded(face_bbox[3] - face_bbox[1]),
            }
        )

    ranked.sort(
        key=lambda item: (
            item["centroid_similarity"],
            item["minimum_reference_similarity"],
        ),
        reverse=True,
    )
    for position, candidate in enumerate(ranked, start=1):
        candidate["rank"] = position
        candidate["within_genuine_pairwise_floor"] = (
            candidate["minimum_reference_similarity"] >= reference_floor
        )

    report = {
        "method": "InsightFace AntelopeV2 glintr100 cosine similarity",
        "privacy": "All inference ran locally; no images were uploaded.",
        "scope": (
            "Useful for automated ranking and drift rejection. It is not proof of "
            "identity and does not measure overall photo quality."
        ),
        "reference_calibration": {
            "paths": [str(path) for path in calibration_references],
            "pairwise_similarity": [rounded(value) for value in reference_pairwise],
            "pairwise_minimum": rounded(reference_floor),
            "pairwise_mean": rounded(reference_mean),
        },
        "scoring_references": {
            "paths": [str(path) for path in references],
            "count": len(references),
        },
        "candidates": ranked,
    }
    rendered = json.dumps(report, indent=2)
    if args.json_output:
        output_path = Path(args.json_output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
