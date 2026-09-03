from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare generated-image edges with a saved Canny structural guide. "
            "This is a tolerant layout diagnostic, not a perceptual quality score."
        )
    )
    parser.add_argument("--guide", required=True, type=Path)
    parser.add_argument("--candidate", action="append", required=True, type=Path)
    parser.add_argument("--label", action="append", required=True)
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def load_gray(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"Could not read image: {path}")
    return image


def candidate_edges(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)
    return cv2.Canny(blurred, round(0.20 * 255), round(0.60 * 255))


def distance_to_edges(edges: np.ndarray) -> np.ndarray:
    return cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)


def rounded(value: float) -> float:
    return round(float(value), 4)


def main() -> None:
    args = parse_args()
    if len(args.candidate) != len(args.label):
        raise RuntimeError("Use exactly one --label for each --candidate.")

    guide_gray = load_gray(args.guide.resolve())
    guide_binary = np.where(guide_gray >= 128, 255, 0).astype(np.uint8)
    results = []
    for path, label in zip(args.candidate, args.label, strict=True):
        resolved = path.resolve()
        gray = load_gray(resolved)
        height, width = gray.shape
        guide = cv2.resize(guide_binary, (width, height), interpolation=cv2.INTER_NEAREST)
        edges = candidate_edges(gray)
        guide_mask = guide > 0
        candidate_mask = edges > 0
        if not np.any(guide_mask) or not np.any(candidate_mask):
            raise RuntimeError(f"No usable edges for {resolved}")

        tolerance = max(2, round(3 * max(width, height) / 1024))
        guide_distances = distance_to_edges(edges)[guide_mask]
        candidate_distances = distance_to_edges(guide)[candidate_mask]
        recall = float(np.mean(guide_distances <= tolerance))
        precision = float(np.mean(candidate_distances <= tolerance))
        f1 = 2.0 * precision * recall / max(precision + recall, 1e-8)
        results.append(
            {
                "label": label,
                "path": str(resolved),
                "width": width,
                "height": height,
                "tolerance_pixels": tolerance,
                "guide_edge_recall": rounded(recall),
                "candidate_edge_precision": rounded(precision),
                "tolerant_edge_f1": rounded(f1),
                "guide_to_candidate_mean_distance": rounded(np.mean(guide_distances)),
                "guide_to_candidate_p90_distance": rounded(np.percentile(guide_distances, 90)),
            }
        )

    report = {
        "method": "Canny 0.20/0.60 with tolerant bidirectional edge matching",
        "scope": (
            "Higher recall/F1 and lower guide-to-candidate distance indicate closer "
            "structural alignment; visual review remains required."
        ),
        "guide": str(args.guide.resolve()),
        "candidates": results,
    }
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
