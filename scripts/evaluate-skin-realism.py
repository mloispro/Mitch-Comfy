"""Local face-crop texture diagnostics for controlled realism A/B tests.

The metrics flag overly smooth or overly sharpened candidates; they do not prove
photorealism. The contact sheet remains the primary visual diagnostic.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument("--candidate-label", action="append", default=[])
    parser.add_argument(
        "--contact-sheet",
        default=".downloads/skin-evals/contact-sheet.png",
    )
    return parser.parse_args()


def analyzer():
    from insightface.app import FaceAnalysis

    root = Path.home() / ".insightface"
    app = FaceAnalysis(
        name="antelopev2",
        root=str(root),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection"],
    )
    app.prepare(ctx_id=-1, det_size=(640, 640))
    return app


def largest_face(app, bgr: np.ndarray):
    faces = app.get(bgr)
    if not faces:
        raise RuntimeError("No face detected")
    return max(
        faces,
        key=lambda face: float(
            (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
        ),
    )


def ellipse_mask(height: int, width: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(
        mask,
        (width // 2, int(height * 0.52)),
        (max(1, int(width * 0.38)), max(1, int(height * 0.45))),
        0,
        0,
        360,
        255,
        -1,
    )
    return mask


def crop_box(image: np.ndarray, bbox, expansion: float = 1.55) -> np.ndarray:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in bbox]
    side = max(x2 - x1, y2 - y1) * expansion
    center_x = (x1 + x2) * 0.5
    center_y = (y1 + y2) * 0.5 - (y2 - y1) * 0.05
    left = max(0, int(round(center_x - side * 0.5)))
    top = max(0, int(round(center_y - side * 0.5)))
    right = min(width, int(round(center_x + side * 0.5)))
    bottom = min(height, int(round(center_y + side * 0.5)))
    return image[top:bottom, left:right]


def face_roi(image: np.ndarray, bbox) -> np.ndarray:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = [int(round(value)) for value in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    return image[y1:y2, x1:x2]


def metrics(image: np.ndarray, face) -> dict:
    roi = face_roi(image, face.bbox)
    if roi.size == 0:
        raise RuntimeError("Detected face crop is empty")
    height, width = roi.shape[:2]
    normalized = cv2.resize(roi, (256, 256), interpolation=cv2.INTER_LANCZOS4)
    mask = ellipse_mask(256, 256).astype(bool)
    gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lab = cv2.cvtColor(normalized, cv2.COLOR_BGR2LAB).astype(np.float32)

    low_luma = cv2.GaussianBlur(gray, (0, 0), 5.0)
    micro_residual = gray - cv2.GaussianBlur(gray, (0, 0), 1.25)
    mid_residual = gray - low_luma
    low_a = cv2.GaussianBlur(lab[:, :, 1], (0, 0), 5.0)
    low_b = cv2.GaussianBlur(lab[:, :, 2], (0, 0), 5.0)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)

    chroma_points = np.stack([low_a[mask], low_b[mask]], axis=1)
    chroma_centered = chroma_points - np.median(chroma_points, axis=0)
    chroma_distance = np.linalg.norm(chroma_centered, axis=1)
    luma_values = gray[mask]
    hist = cv2.calcHist(
        [np.uint8(np.clip(gray, 0, 255))], [0], np.uint8(mask) * 255, [64], [0, 256]
    ).reshape(-1)
    probabilities = hist / max(float(hist.sum()), 1.0)
    probabilities = probabilities[probabilities > 0]
    entropy = -float(np.sum(probabilities * np.log2(probabilities)))

    bbox_width = float(face.bbox[2] - face.bbox[0])
    bbox_height = float(face.bbox[3] - face.bbox[1])
    return {
        "face_width_px": round(bbox_width, 1),
        "face_height_px": round(bbox_height, 1),
        "detector_confidence": round(float(face.det_score), 4),
        "luma_dynamic_range_p90": round(
            float(np.percentile(luma_values, 95) - np.percentile(luma_values, 5)), 3
        ),
        "low_frequency_chroma_variation": round(
            float(np.percentile(chroma_distance, 75)), 3
        ),
        "mid_frequency_luma_variation": round(float(np.std(mid_residual[mask])), 3),
        "micro_luma_variation": round(float(np.std(micro_residual[mask])), 3),
        "normalized_laplacian_variance": round(float(np.var(laplacian[mask])), 3),
        "luma_entropy_bits": round(entropy, 3),
    }


def labeled_tile(crop: np.ndarray, label: str, stats: dict) -> np.ndarray:
    target = 420
    canvas = np.full((target + 88, target, 3), 245, dtype=np.uint8)
    scale = min(target / crop.shape[1], target / crop.shape[0])
    resized = cv2.resize(
        crop,
        (max(1, int(round(crop.shape[1] * scale))), max(1, int(round(crop.shape[0] * scale)))),
        interpolation=cv2.INTER_LANCZOS4,
    )
    x = (target - resized.shape[1]) // 2
    y = (target - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    cv2.putText(canvas, label, (10, target + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (20, 20, 20), 1, cv2.LINE_AA)
    summary = (
        f"face {stats['face_width_px']:.0f}px | chroma {stats['low_frequency_chroma_variation']:.1f} | "
        f"mid {stats['mid_frequency_luma_variation']:.1f} | micro {stats['micro_luma_variation']:.1f}"
    )
    cv2.putText(canvas, summary, (10, target + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.putText(
        canvas,
        f"lap {stats['normalized_laplacian_variance']:.1f} | entropy {stats['luma_entropy_bits']:.2f}",
        (10, target + 76),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (40, 40, 40),
        1,
        cv2.LINE_AA,
    )
    return canvas


def main() -> None:
    args = parse_args()
    references = [Path(path).resolve() for path in args.reference]
    candidates = [Path(path).resolve() for path in args.candidate]
    candidate_labels = args.candidate_label or [path.stem for path in candidates]
    if len(candidate_labels) != len(candidates):
        raise RuntimeError("Use one --candidate-label for each --candidate")
    entries = [
        *(('reference', path.name, path) for path in references),
        *(("candidate", label, path) for label, path in zip(candidate_labels, candidates, strict=True)),
    ]
    if not entries:
        raise RuntimeError("Supply at least one reference or candidate")

    app = analyzer()
    results = []
    tiles = []
    for kind, label, path in entries:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"Could not read image: {path}")
        face = largest_face(app, image)
        stats = metrics(image, face)
        results.append({"kind": kind, "label": label, "path": str(path), **stats})
        tiles.append(labeled_tile(crop_box(image, face.bbox), f"{kind}: {label}", stats))

    columns = 2
    rows = math.ceil(len(tiles) / columns)
    blank = np.full_like(tiles[0], 245)
    while len(tiles) < rows * columns:
        tiles.append(blank.copy())
    sheet = np.vstack(
        [np.hstack(tiles[row * columns : (row + 1) * columns]) for row in range(rows)]
    )
    output = Path(args.contact_sheet).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), sheet):
        raise RuntimeError(f"Could not write contact sheet: {output}")
    print(
        json.dumps(
            {
                "scope": "Local diagnostic only; metrics flag texture extremes and do not prove realism.",
                "contact_sheet": str(output),
                "entries": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
