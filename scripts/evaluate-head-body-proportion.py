from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the main face width against the detected person's visible body "
            "box. This is a local proportion diagnostic, not an anatomy classifier."
        )
    )
    parser.add_argument("--image", action="append", required=True)
    parser.add_argument("--label", action="append")
    parser.add_argument(
        "--detector",
        default=(
            r"C:\projects\AI-Tools\ComfyUI\models\ultralytics\bbox\yolo11n.pt"
        ),
    )
    return parser.parse_args()


def bbox_area(box: np.ndarray) -> float:
    return max(0.0, float(box[2] - box[0])) * max(0.0, float(box[3] - box[1]))


def contains(box: np.ndarray, point: tuple[float, float]) -> bool:
    return bool(box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3])


def main() -> None:
    args = parse_args()
    paths = [Path(value).resolve() for value in args.image]
    labels = args.label or [path.stem for path in paths]
    if len(labels) != len(paths):
        raise RuntimeError("Use exactly one --label for each --image.")
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"Image does not exist: {path}")

    detector_path = Path(args.detector).resolve()
    if not detector_path.is_file():
        raise RuntimeError(f"Person detector does not exist: {detector_path}")

    face_analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(Path.home() / ".insightface"),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection"],
    )
    face_analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    person_detector = YOLO(str(detector_path))

    results = []
    for path, label in zip(paths, labels, strict=True):
        bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise RuntimeError(f"Could not read image: {path}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        faces = face_analyzer.get(bgr)
        if not faces:
            raise RuntimeError(f"No face detected: {path}")
        face = max(faces, key=lambda item: bbox_area(np.asarray(item.bbox)))
        face_box = np.asarray(face.bbox, dtype=np.float32)
        face_center = (
            float((face_box[0] + face_box[2]) * 0.5),
            float((face_box[1] + face_box[3]) * 0.5),
        )

        prediction = person_detector.predict(
            source=rgb, imgsz=960, conf=0.25, device="cpu", verbose=False
        )[0]
        person_boxes = [
            np.asarray(box, dtype=np.float32)
            for class_id, box in zip(
                prediction.boxes.cls.cpu().numpy(),
                prediction.boxes.xyxy.cpu().numpy(),
                strict=True,
            )
            if person_detector.names[int(class_id)] == "person"
        ]
        containing = [box for box in person_boxes if contains(box, face_center)]
        candidates = containing or person_boxes
        if not candidates:
            raise RuntimeError(f"No person detected: {path}")
        person_box = max(candidates, key=bbox_area)

        face_width = float(face_box[2] - face_box[0])
        face_height = float(face_box[3] - face_box[1])
        person_width = float(person_box[2] - person_box[0])
        person_height = float(person_box[3] - person_box[1])
        results.append(
            {
                "label": label,
                "path": str(path),
                "image_size": [int(rgb.shape[1]), int(rgb.shape[0])],
                "face_bbox": [round(float(value), 1) for value in face_box],
                "person_bbox": [round(float(value), 1) for value in person_box],
                "face_to_person_width": round(face_width / max(person_width, 1.0), 4),
                "face_to_person_height": round(face_height / max(person_height, 1.0), 4),
                "face_detection_confidence": round(float(face.det_score), 4),
                "scope": (
                    "Main detected face divided by the visible detected person box; "
                    "compare like-for-like framing and confirm visually."
                ),
            }
        )

    print(json.dumps({"results": results}, indent=2))


if __name__ == "__main__":
    main()
