#!/usr/bin/env python3
"""Inventory ComfyUI outputs and score multi-person identity candidates.

This is a read-only audit of the ComfyUI output tree. It uses the same local
YOLO and InsightFace models as the production nodes, then writes machine-readable
results into this repository for human visual review.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from insightface.app import FaceAnalysis
from ultralytics import YOLO


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".avif"}
SKIP_NAME_PARTS = (
    "contact-sheet",
    "contact_sheet",
    "comparison_",
    "person-mask",
    "identity-mask",
    "layout-mask",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--yolo-model", type=Path, required=True)
    parser.add_argument("--insightface-root", type=Path, required=True)
    parser.add_argument("--reference", action="append", type=Path, default=[])
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--scan-chunk", type=int, default=32)
    return parser.parse_args()


def image_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        lowered = path.name.lower()
        if any(part in lowered for part in SKIP_NAME_PARTS):
            continue
        paths.append(path)
    return sorted(paths)


def exact_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def difference_hash(path: Path) -> str:
    with Image.open(path) as image:
        gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        values = np.asarray(gray, dtype=np.int16)
    bits = values[:, 1:] > values[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def nearest_report(path: Path, root: Path) -> Path | None:
    current = path.parent
    while current == root or root in current.parents:
        for name in ("report.json", "identity-lock-report.json"):
            candidate = current / name
            if candidate.is_file():
                return candidate
        if current == root:
            break
        current = current.parent
    return None


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def first_value(data: Any, keys: set[str]) -> Any:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys and value not in (None, "", [], {}):
                return value
        for value in data.values():
            found = first_value(value, keys)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(data, list):
        for value in data:
            found = first_value(value, keys)
            if found not in (None, "", [], {}):
                return found
    return None


def report_summary(report: dict[str, Any]) -> dict[str, Any]:
    model = report.get("model")
    if not model and isinstance(report.get("models"), dict):
        model = report["models"].get("diffusion", {}).get("name")
    if not model:
        model = first_value(report, {"unet_name", "ckpt_name"})
    route = report.get("generation_route") or report.get("purpose")
    prompt = (
        report.get("requested_scene_prompt")
        or first_value(report.get("settings", {}), {"brief"})
        or first_value(report, {"prompt"})
    )
    score = report.get("identity_similarity_to_reference_centroid")
    if score is None:
        score = first_value(
            report,
            {
                "main_identity_similarity",
                "mean_final_identity",
                "similarity_to_reference_centroid",
            },
        )
    return {
        "report_model": model or "",
        "report_route": route or "",
        "report_identity": score if isinstance(score, (int, float)) else "",
        "report_prompt": str(prompt or "").replace("\n", " ")[:1200],
    }


def png_workflow_summary(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".png":
        return {}
    try:
        with Image.open(path) as image:
            raw = image.info.get("prompt")
        if not raw:
            return {}
        prompt = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}
    if not isinstance(prompt, dict):
        return {}
    models: list[str] = []
    loras: list[str] = []
    swaps: list[str] = []
    texts: list[str] = []
    seeds: list[str] = []
    settings: list[str] = []
    for node in prompt.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        for key in ("unet_name", "ckpt_name"):
            value = inputs.get(key)
            if isinstance(value, str):
                models.append(value)
        value = inputs.get("lora_name")
        if isinstance(value, str):
            loras.append(value)
        value = inputs.get("swap_model")
        if isinstance(value, str):
            swaps.append(value)
        value = inputs.get("text")
        if isinstance(value, str) and len(value) > 20:
            texts.append(value.replace("\n", " "))
        if isinstance(inputs.get("seed"), (int, float)):
            seeds.append(str(inputs["seed"]))
        if isinstance(inputs.get("steps"), (int, float)):
            settings.append(f"{int(inputs['steps'])} steps")
        if isinstance(inputs.get("cfg"), (int, float)):
            settings.append(f"CFG {inputs['cfg']}")
        if isinstance(inputs.get("sampler_name"), str):
            settings.append(inputs["sampler_name"])
    return {
        "workflow_models": " | ".join(dict.fromkeys(models)),
        "workflow_loras": " | ".join(dict.fromkeys(loras)),
        "workflow_swaps": " | ".join(dict.fromkeys(swaps)),
        "workflow_seeds": " | ".join(dict.fromkeys(seeds)),
        "workflow_settings": " | ".join(dict.fromkeys(settings)),
        "workflow_prompt": (max(texts, key=len) if texts else "")[:1200],
    }


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))


def face_analyzer(root: Path) -> FaceAnalysis:
    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(root),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    return analyzer


def normalized_embedding(face: Any) -> np.ndarray:
    value = np.asarray(face.normed_embedding, dtype=np.float32)
    return value / max(float(np.linalg.norm(value)), 1e-8)


def reference_centroid(analyzer: FaceAnalysis, paths: list[Path]) -> np.ndarray:
    embeddings: list[np.ndarray] = []
    for path in paths:
        faces = analyzer.get(cv2.cvtColor(read_rgb(path), cv2.COLOR_RGB2BGR))
        if not faces:
            raise RuntimeError(f"No reference face detected: {path}")
        face = max(faces, key=lambda item: float(np.prod(item.bbox[2:] - item.bbox[:2])))
        embeddings.append(normalized_embedding(face))
    centroid = np.mean(np.stack(embeddings), axis=0)
    return centroid / max(float(np.linalg.norm(centroid)), 1e-8)


def main_identity(analyzer: FaceAnalysis, centroid: np.ndarray, path: Path) -> dict[str, Any]:
    faces = analyzer.get(cv2.cvtColor(read_rgb(path), cv2.COLOR_RGB2BGR))
    scored = []
    for face in faces:
        embedding = normalized_embedding(face)
        score = float(np.dot(embedding, centroid))
        area = float(np.prod(face.bbox[2:] - face.bbox[:2]))
        scored.append((score, area, face))
    if not scored:
        return {"face_count": 0, "identity_score": "", "identity_face_area": ""}
    best = max(scored, key=lambda item: item[0])
    return {
        "face_count": len(scored),
        "identity_score": round(best[0], 4),
        "identity_face_area": round(best[1], 1),
    }


def main() -> None:
    args = parse_args()
    output_root = args.output_root.resolve()
    paths = image_paths(output_root)
    print(f"Screening {len(paths)} images with YOLO...", flush=True)
    model = YOLO(str(args.yolo_model))
    rows: list[dict[str, Any]] = []
    for chunk_start in range(0, len(paths), args.scan_chunk):
        chunk = paths[chunk_start : chunk_start + args.scan_chunk]
        results = model.predict(
            source=[str(path) for path in chunk],
            imgsz=args.imgsz,
            conf=0.25,
            device=args.device,
            batch=args.batch,
            stream=False,
            verbose=False,
        )
        for path, result in zip(chunk, results):
            people = 0
            for class_id in result.boxes.cls:
                if model.names[int(class_id)] == "person":
                    people += 1
            with Image.open(path) as image:
                width, height = image.size
            report_path = nearest_report(path, output_root)
            report = load_json(report_path)
            row: dict[str, Any] = {
                "path": str(path),
                "relative_path": str(path.relative_to(output_root)),
                "top_folder": path.relative_to(output_root).parts[0],
                "width": width,
                "height": height,
                "yolo_people": people,
                "sha256": exact_hash(path),
                "dhash": difference_hash(path),
                "report_path": str(report_path or ""),
            }
            row.update(report_summary(report))
            row.update(png_workflow_summary(path))
            rows.append(row)
        scanned = min(chunk_start + len(chunk), len(paths))
        multi = sum(int(item["yolo_people"]) >= 2 for item in rows)
        print(
            f"YOLO {scanned}/{len(paths)}; multi-person candidates: {multi}",
            flush=True,
        )

    candidates = [row for row in rows if int(row["yolo_people"]) >= 2]
    print(f"Scoring identity in {len(candidates)} multi-person candidates...", flush=True)
    analyzer = face_analyzer(args.insightface_root)
    centroid = reference_centroid(analyzer, args.reference)
    for index, row in enumerate(candidates, start=1):
        row.update(main_identity(analyzer, centroid, Path(row["path"])))
        if index % 25 == 0 or index == len(candidates):
            print(f"Identity {index}/{len(candidates)}", flush=True)

    for row in rows:
        row.setdefault("face_count", "")
        row.setdefault("identity_score", "")
        row.setdefault("identity_face_area", "")

    args.results.parent.mkdir(parents=True, exist_ok=True)
    json_path = args.results.with_suffix(".json")
    csv_path = args.results.with_suffix(".csv")
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    fieldnames = sorted({key for row in rows for key in row})
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {csv_path}", flush=True)


if __name__ == "__main__":
    main()
