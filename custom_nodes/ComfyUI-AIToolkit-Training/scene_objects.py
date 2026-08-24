from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import torch


DETECTOR_NAME = "yolo11n.pt"
DETECTOR_CONFIDENCE = 0.25
_VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}
_DETECTOR = None


def _detector():
    global _DETECTOR
    if _DETECTOR is None:
        import folder_paths
        from ultralytics import YOLO

        path = Path(folder_paths.models_dir) / "ultralytics" / "bbox" / DETECTOR_NAME
        if not path.is_file():
            raise RuntimeError(f"Missing local scene-count detector: {path}")
        _DETECTOR = YOLO(str(path))
    return _DETECTOR


def count_scene_objects(image: torch.Tensor) -> dict:
    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    model = _detector()
    result = model.predict(
        source=rgb,
        imgsz=960,
        conf=DETECTOR_CONFIDENCE,
        device="cpu",
        verbose=False,
    )[0]
    labels = [model.names[int(class_id)] for class_id in result.boxes.cls]
    raw = Counter(labels)
    boxes = []
    for class_id, confidence, xyxy in zip(
        result.boxes.cls, result.boxes.conf, result.boxes.xyxy
    ):
        label = model.names[int(class_id)]
        if label != "person" and label not in _VEHICLE_CLASSES:
            continue
        boxes.append(
            {
                "class": label,
                "confidence": round(float(confidence), 4),
                "bbox": [round(float(value), 1) for value in xyxy],
            }
        )
    return {
        "model": DETECTOR_NAME,
        "confidence_threshold": DETECTOR_CONFIDENCE,
        "person": int(raw.get("person", 0)),
        "vehicle": int(sum(raw.get(name, 0) for name in _VEHICLE_CLASSES)),
        "vehicle_breakdown": {
            name: int(raw.get(name, 0)) for name in sorted(_VEHICLE_CLASSES) if raw.get(name, 0)
        },
        "boxes": boxes,
    }


def object_count_error(counts: dict, targets: dict[str, int]) -> int:
    return sum(abs(int(counts.get(name, 0)) - target) for name, target in targets.items())


def guarded_multi_person_count_error(
    counts: dict,
    targets: dict[str, int],
    requires_multiple_people: bool,
) -> int:
    """Score explicit count mistakes and require a real multi-person result when implied."""
    error = object_count_error(counts, targets)
    if requires_multiple_people and "person" not in targets:
        error += max(0, 2 - int(counts.get("person", 0)))
    return error
