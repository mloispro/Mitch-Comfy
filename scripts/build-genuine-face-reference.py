from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from insightface.app import FaceAnalysis


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the production-style square face view from a genuine reference photo."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--expansion", type=float, default=2.0)
    args = parser.parse_args()

    source = args.source.resolve()
    destination = args.destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing reference: {destination}")
    if not source.is_file():
        raise FileNotFoundError(source)
    if args.expansion < 1.3 or args.expansion > 2.5:
        raise ValueError("Expansion must be between 1.3 and 2.5.")

    with Image.open(source) as opened:
        rgb = np.asarray(ImageOps.exif_transpose(opened).convert("RGB"))

    model_root = Path.home() / ".insightface"
    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(model_root),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    faces = analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError("No face was detected in the genuine reference photo.")

    face = max(
        faces,
        key=lambda item: float(
            (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
        ),
    )
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    face_width = x2 - x1
    face_height = y2 - y1
    side = max(face_width, face_height) * args.expansion
    center_x = (x1 + x2) * 0.5
    center_y = (y1 + y2) * 0.5 - face_height * 0.12
    left = max(0, int(round(center_x - side * 0.5)))
    top = max(0, int(round(center_y - side * 0.5)))
    right = min(width, int(round(center_x + side * 0.5)))
    bottom = min(height, int(round(center_y + side * 0.5)))
    if right - left < 128 or bottom - top < 128:
        raise RuntimeError("The detected face is too small for a reliable identity crop.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb[top:bottom, left:right]).save(destination, quality=96)
    print(
        f"saved={destination}|source={source}|bbox={left},{top},{right},{bottom}|"
        f"detector_confidence={float(face.det_score):.4f}|expansion={args.expansion:.2f}"
    )


if __name__ == "__main__":
    main()
