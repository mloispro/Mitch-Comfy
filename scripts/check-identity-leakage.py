from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_ROOT = REPO_ROOT / "custom_nodes" / "ComfyUI-AIToolkit-Training"
sys.path.insert(0, str(NODE_ROOT))

from identity_leakage import evaluate_identity_scope  # noqa: E402


def _faces(analyzer, path: Path):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure main-identity strength and leakage into secondary faces."
    )
    parser.add_argument("--reference", action="append", required=True, type=Path)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--main-minimum", type=float, default=0.75)
    args = parser.parse_args()

    from insightface.app import FaceAnalysis

    model_root = Path.home() / ".insightface"
    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(model_root),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    reference_embeddings = []
    for path in args.reference:
        faces = _faces(analyzer, path)
        if not faces:
            raise RuntimeError(f"No reference face detected in {path}")
        face = max(
            faces,
            key=lambda item: float(
                (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
            ),
        )
        reference_embeddings.append(np.asarray(face.normed_embedding, dtype=np.float32))
    centroid = np.mean(np.stack(reference_embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)

    results = []
    for path in args.images:
        faces = _faces(analyzer, path)
        report = evaluate_identity_scope(
            [np.asarray(face.normed_embedding, dtype=np.float32) for face in faces],
            [face.bbox for face in faces],
            [float(face.det_score) for face in faces],
            centroid,
            args.main_minimum,
        )
        results.append({"image": str(path), **report.as_dict()})
    print(json.dumps(results, indent=2))
    return 0 if all(item["status"] == "passed" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
