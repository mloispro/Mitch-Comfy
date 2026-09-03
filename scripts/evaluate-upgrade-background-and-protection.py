from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure background detail gain and protected-pixel stability for a masked upgrade."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--edit-mask", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    return parser.parse_args()


def load_color(path: Path) -> np.ndarray:
    image = cv2.imread(str(path.resolve()), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {path}")
    return image


def largest_border_component(binary: np.ndarray) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    candidates: list[tuple[int, int]] = []
    height, width = binary.shape
    for label in range(1, count):
        component = labels == label
        touches_border = bool(
            component[0].any()
            or component[-1].any()
            or component[:, 0].any()
            or component[:, -1].any()
        )
        if touches_border:
            candidates.append((int(stats[label, cv2.CC_STAT_AREA]), label))
    if not candidates:
        raise RuntimeError("Edit mask has no background component touching the image border.")
    selected = max(candidates)[1]
    return (labels == selected).astype(np.uint8)


def detail_metrics(gray: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    selected = mask.astype(bool)
    if int(selected.sum()) < 1000:
        raise RuntimeError("Background evaluation region is too small.")
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(sobel_x, sobel_y)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    canny = cv2.Canny(gray, 64, 160)
    return {
        "mean_gradient": float(np.mean(gradient[selected])),
        "mean_absolute_laplacian": float(np.mean(np.abs(laplacian[selected]))),
        "canny_edge_fraction": float(np.mean(canny[selected] > 0)),
    }


def rounded(value: float) -> float:
    return round(float(value), 6)


def main() -> None:
    args = parse_args()
    source = load_color(args.source)
    candidate = load_color(args.candidate)
    mask_image = cv2.imread(str(args.edit_mask.resolve()), cv2.IMREAD_GRAYSCALE)
    if mask_image is None:
        raise RuntimeError(f"Could not read edit mask: {args.edit_mask}")
    height, width = candidate.shape[:2]
    source = cv2.resize(source, (width, height), interpolation=cv2.INTER_CUBIC)
    mask_image = cv2.resize(mask_image, (width, height), interpolation=cv2.INTER_LINEAR)

    background = largest_border_component((mask_image >= 250).astype(np.uint8))
    background = cv2.erode(background, np.ones((9, 9), np.uint8), iterations=1)
    protected = (mask_image <= 2).astype(np.uint8)
    protected = cv2.erode(protected, np.ones((5, 5), np.uint8), iterations=1)

    source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    candidate_gray = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY)
    source_detail = detail_metrics(source_gray, background)
    candidate_detail = detail_metrics(candidate_gray, background)
    absolute_error = np.abs(candidate.astype(np.float32) - source.astype(np.float32))
    protected_error = absolute_error[protected.astype(bool)]

    gains = {
        key: candidate_detail[key] / max(source_detail[key], 1e-8)
        for key in source_detail
    }
    report = {
        "method": "OpenCV background-only gradients/Laplacian/Canny plus protected-region pixel error",
        "scope": (
            "Diagnostic of visible high-frequency detail and source stability; it does not prove that "
            "synthesized background detail is factually correct."
        ),
        "source": str(args.source.resolve()),
        "candidate": str(args.candidate.resolve()),
        "edit_mask": str(args.edit_mask.resolve()),
        "size": [width, height],
        "background_pixel_fraction": rounded(float(background.mean())),
        "protected_pixel_fraction": rounded(float(protected.mean())),
        "source_background": {key: rounded(value) for key, value in source_detail.items()},
        "candidate_background": {
            key: rounded(value) for key, value in candidate_detail.items()
        },
        "background_detail_gain": {key: rounded(value) for key, value in gains.items()},
        "protected_region_mae_8bit": rounded(float(np.mean(protected_error))),
        "protected_region_p99_error_8bit": rounded(
            float(np.percentile(protected_error, 99))
        ),
    }
    args.json_output.resolve().write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
