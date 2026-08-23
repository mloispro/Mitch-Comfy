from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_ROOT = REPO_ROOT / "custom_nodes" / "ComfyUI-AIToolkit-Training"
sys.path.insert(0, str(NODE_ROOT))

from head_integrity import measure_head_integrity  # noqa: E402


def _main_face_component(probability: np.ndarray, face_bbox) -> np.ndarray:
    binary = (probability >= 0.35).astype(np.uint8)
    count, labels, _, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    x1, y1, x2, y2 = [int(round(float(value))) for value in face_bbox]
    height, width = binary.shape
    x1, x2 = max(0, x1), min(width, x2)
    y1, y2 = max(0, y1), min(height, y2)
    face_labels = labels[y1:y2, x1:x2]
    candidates = [label for label in range(1, count) if np.any(face_labels == label)]
    if not candidates:
        raise RuntimeError("Human segmentation did not overlap the detected face.")
    selected = max(
        candidates,
        key=lambda label: int(np.count_nonzero(face_labels == label)),
    )
    return (labels == selected).astype(np.uint8)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the narrow full-head integrity gate used by Easy Social Photos."
    )
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument(
        "--comfy-root", type=Path, default=Path(r"C:\projects\AI-Tools\ComfyUI")
    )
    args = parser.parse_args()

    from insightface.app import FaceAnalysis
    from rembg import new_session, remove

    model_root = Path.home() / ".insightface"
    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(model_root),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    os.environ["U2NET_HOME"] = str(args.comfy_root / "models" / "rembg")
    session = new_session("u2net_human_seg")

    results = []
    for image_path in args.images:
        rgb = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)
        faces = analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if not faces:
            results.append({"image": str(image_path), "status": "rejected", "error": "no face"})
            continue
        face = max(
            faces,
            key=lambda item: float(
                (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
            ),
        )
        raw = remove(
            Image.fromarray(rgb),
            session=session,
            only_mask=True,
            post_process_mask=True,
        )
        probability = np.asarray(raw.convert("L"), dtype=np.float32) / 255.0
        component = _main_face_component(probability, face.bbox)
        report = measure_head_integrity(component, face.bbox, getattr(face, "kps", None))
        results.append({"image": str(image_path), **report.as_dict()})
    print(json.dumps(results, indent=2))
    return 0 if all(item["status"] == "passed" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
