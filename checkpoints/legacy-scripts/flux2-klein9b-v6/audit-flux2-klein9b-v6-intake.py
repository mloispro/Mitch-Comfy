#!/usr/bin/env python3
"""Audit genuine-photo intake for the next FLUX.2 Klein Base 9B identity LoRA.

The gate is intentionally stricter than a normal image inventory.  The V3/V5
experiments proved that caption labels such as "near profile" and nominal
"full body" framing are insufficient when measured yaw or face detail is too
small.  This script measures the actual face pose and pixel coverage locally,
checks a locked role/split design, and refuses exact or near duplicates.

No image is modified or uploaded.  Automated face similarity is diagnostic;
the user's genuine/unedited attestation and full-size visual review remain
required.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import textwrap
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
TRIGGER = "m1tch_person"
EXPECTED_EXISTING_MANIFEST_SHA256 = (
    "D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003"
)
DEFAULT_EXISTING_MANIFEST = ROOT / "datasets" / "mitch-identity-stills-v3" / "manifest.json"
DEFAULT_REFERENCES = (
    ROOT / "datasets" / "mitch-identity-stills-v4-klein9b" / "validation" / "val_03_navy_upper_body.jpg",
    ROOT / "datasets" / "mitch-identity-stills-v4-klein9b" / "validation" / "val_04_window_small_smile.jpg",
    ROOT / "datasets" / "mitch-identity-stills-v4-klein9b" / "validation" / "val_05_balcony_opposite_angle.jpg",
    ROOT / "datasets" / "mitch-identity-stills-v4-klein9b" / "validation" / "val_06_car_daylight.jpg",
)
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
REQUIRED_COUNTS = {
    ("profile_image_left", "train"): 2,
    ("profile_image_left", "validation"): 1,
    ("profile_image_right", "train"): 2,
    ("profile_image_right", "validation"): 1,
    ("body", "train"): 2,
}
ATTESTATIONS = (
    "genuine_camera_still",
    "not_video_frame",
    "no_generated_pixels",
    "no_identity_edit",
    "no_beauty_filter",
    "no_face_or_body_restoration",
)
ROLE_LIMITS = {
    "profile_image_left": {"yaw_min": -80.0, "yaw_max": -45.0, "face_height": 350.0},
    "profile_image_right": {"yaw_min": 45.0, "yaw_max": 80.0, "face_height": 350.0},
    "three_quarter_image_left": {"yaw_min": -40.0, "yaw_max": -20.0, "face_height": 350.0},
    "three_quarter_image_right": {"yaw_min": 20.0, "yaw_max": 40.0, "face_height": 350.0},
    "body": {"yaw_min": -35.0, "yaw_max": 35.0, "face_height": 200.0},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument("--existing-manifest", type=Path, default=DEFAULT_EXISTING_MANIFEST)
    parser.add_argument("--reference", action="append", type=Path)
    parser.add_argument("--insightface-root", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_embedding(face: Any) -> np.ndarray:
    embedding = np.asarray(face.normed_embedding, dtype=np.float32)
    return embedding / max(float(np.linalg.norm(embedding)), 1e-8)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(
        np.dot(left, right)
        / max(float(np.linalg.norm(left) * np.linalg.norm(right)), 1e-8)
    )


def rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        return ImageOps.exif_transpose(opened).convert("RGB")


def dhash(image: Image.Image) -> str:
    reduced = ImageOps.grayscale(image).resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(
        reduced.get_flattened_data()
        if hasattr(reduced, "get_flattened_data")
        else reduced.getdata()
    )
    value = 0
    for row in range(8):
        for column in range(8):
            value = (value << 1) | int(
                pixels[row * 9 + column] > pixels[row * 9 + column + 1]
            )
    return f"{value:016x}"


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def face_crop_sharpness(image_bgr: np.ndarray, bbox: np.ndarray) -> float:
    height, width = image_bgr.shape[:2]
    x1, y1, x2, y2 = [int(round(float(value))) for value in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    crop = image_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def build_analyzer(model_root: Path | None) -> FaceAnalysis:
    kwargs: dict[str, Any] = {
        "name": "antelopev2",
        "providers": ["CPUExecutionProvider"],
        "allowed_modules": ["detection", "recognition", "landmark_3d_68"],
    }
    if model_root is not None:
        kwargs["root"] = str(model_root.resolve())
    analyzer = FaceAnalysis(**kwargs)
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    return analyzer


def faces_for(analyzer: FaceAnalysis, image: Image.Image):
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    return bgr, analyzer.get(bgr)


def largest_face(faces: list[Any]):
    return max(
        faces,
        key=lambda face: float(
            (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
        ),
    )


def render_contact_sheet(records: list[dict[str, Any]], destination: Path) -> None:
    columns, tile_width, image_height, label_height = 3, 440, 400, 148
    rows = (len(records) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (columns * tile_width, 54 + rows * (image_height + label_height)),
        "#111318",
    )
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.load_default(size=20)
    label_font = ImageFont.load_default(size=14)
    draw.text((16, 14), "Klein 9B V6 genuine-photo intake audit", fill="#f4f4f5", font=title_font)
    for index, record in enumerate(records):
        row, column = divmod(index, columns)
        x = column * tile_width
        y = 54 + row * (image_height + label_height)
        path_text = record.get("path")
        if path_text and Path(path_text).is_file():
            image = load_rgb(Path(path_text))
            preview = ImageOps.contain(image, (tile_width - 16, image_height - 16))
            px = x + (tile_width - preview.width) // 2
            py = y + (image_height - preview.height) // 2
            sheet.paste(preview, (px, py))
        color = "#69db7c" if record.get("valid") else "#ff6b6b"
        lines = [
            textwrap.shorten(
                f"{record.get('id', '<missing>')}  {record.get('split', '?')}",
                width=48,
                placeholder="...",
            ),
            str(record.get("role", "?")),
            (
                f"yaw {record.get('yaw_degrees', '?')}  face {record.get('face_height_pixels', '?')}px  "
                f"sharp {record.get('face_sharpness', '?')}"
            ),
            "PASS"
            if record.get("valid")
            else textwrap.shorten(
                "; ".join(record.get("errors", [])[:2]),
                width=54,
                placeholder="...",
            ),
        ]
        for line_index, line in enumerate(lines):
            draw.text(
                (x + 8, y + image_height + 6 + line_index * 24),
                line,
                fill=color if line_index == 3 else "#e4e4e7",
                font=label_font,
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=92, subsampling=0)


def write_report(report: dict[str, Any], output: Path) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main() -> None:
    args = parse_args()
    spec_path = args.spec.resolve()
    output_path = args.json_output.resolve()
    global_errors: list[str] = []
    global_warnings: list[str] = []
    record_reports: list[dict[str, Any]] = []

    if not spec_path.is_file():
        report = {
            "schema_version": 1,
            "valid": False,
            "errors": [f"Intake spec is missing: {spec_path}"],
            "records": [],
        }
        write_report(report, output_path)
        raise SystemExit(2)

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        report = {
            "schema_version": 1,
            "valid": False,
            "errors": [f"Could not parse intake spec: {exc}"],
            "records": [],
        }
        write_report(report, output_path)
        raise SystemExit(2)

    if spec.get("schema_version") != 1:
        global_errors.append("spec.schema_version must equal 1")
    if spec.get("trigger_word") != TRIGGER:
        global_errors.append(f"spec.trigger_word must equal {TRIGGER}")
    intake_root_value = spec.get("intake_root")
    intake_root = Path(intake_root_value).resolve() if intake_root_value else None
    if intake_root is None or not intake_root.is_dir():
        global_errors.append(f"intake_root is missing or not a directory: {intake_root_value}")

    raw_records = spec.get("records")
    if not isinstance(raw_records, list):
        raw_records = []
        global_errors.append("spec.records must be a list")
    if len(raw_records) != 8:
        global_errors.append(f"Exactly 8 new records are required; found {len(raw_records)}")

    role_counts = Counter(
        (str(record.get("role")), str(record.get("split")))
        for record in raw_records
        if isinstance(record, dict)
    )
    if role_counts != Counter(REQUIRED_COUNTS):
        global_errors.append(
            "Role/split counts must be exactly: "
            + ", ".join(
                f"{role}/{split}={count}"
                for (role, split), count in REQUIRED_COUNTS.items()
            )
        )

    ids = [str(record.get("id", "")) for record in raw_records if isinstance(record, dict)]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        global_errors.append("Every record id must be nonempty and unique")

    existing_manifest = args.existing_manifest.resolve()
    existing_hashes: set[str] = set()
    existing_manifest_hash: str | None = None
    if not existing_manifest.is_file():
        global_errors.append(f"Existing dataset manifest is missing: {existing_manifest}")
    else:
        existing_manifest_hash = sha256(existing_manifest).upper()
        if existing_manifest_hash != EXPECTED_EXISTING_MANIFEST_SHA256:
            global_errors.append(
                "Existing dataset manifest changed: "
                f"expected {EXPECTED_EXISTING_MANIFEST_SHA256}, found {existing_manifest_hash}"
            )
        existing = json.loads(existing_manifest.read_text(encoding="utf-8-sig"))
        existing_hashes = {
            str(record.get("dataset_sha256", "")).lower()
            for record in existing.get("records", [])
            if record.get("dataset_sha256")
        }

    references = tuple(path.resolve() for path in (args.reference or DEFAULT_REFERENCES))
    missing_references = [str(path) for path in references if not path.is_file()]
    if missing_references:
        global_errors.append("Missing identity references: " + ", ".join(missing_references))

    prelim: list[dict[str, Any]] = []
    for raw in raw_records:
        raw = raw if isinstance(raw, dict) else {}
        errors: list[str] = []
        warnings: list[str] = []
        record_id = str(raw.get("id", ""))
        role = str(raw.get("role", ""))
        split = str(raw.get("split", ""))
        session = str(raw.get("session", "")).strip()
        file_value = raw.get("file")
        path = (intake_root / str(file_value)).resolve() if intake_root and file_value else None
        if not session:
            errors.append("session is required")
        if path is None or not path.is_file():
            errors.append(f"image is missing: {file_value}")
        elif intake_root is not None and not path.is_relative_to(intake_root):
            errors.append("image resolves outside intake_root")
        elif path.suffix.lower() not in ALLOWED_SUFFIXES:
            errors.append(f"unsupported still-image suffix: {path.suffix}")

        caption = str(raw.get("caption", "")).strip()
        if split == "train":
            if not caption.startswith(TRIGGER, 0):
                errors.append("training caption must start with m1tch_person")
            if caption.count(TRIGGER) != 1:
                errors.append("training caption must contain the trigger exactly once")
        elif split == "validation" and caption:
            errors.append("validation records must not contain a training caption")

        attestations = raw.get("attestations") if isinstance(raw.get("attestations"), dict) else {}
        for field in ATTESTATIONS:
            if attestations.get(field) is not True:
                errors.append(f"attestation must be true: {field}")
        if role == "body" and attestations.get("full_or_three_quarter_body_visible") is not True:
            errors.append("body record requires full_or_three_quarter_body_visible=true")

        item: dict[str, Any] = {
            "id": record_id,
            "path": str(path) if path else None,
            "source_file": str(file_value) if file_value is not None else None,
            "role": role,
            "split": split,
            "session": session,
            "caption": caption,
            "attestations": attestations,
            "errors": errors,
            "warnings": warnings,
        }
        prelim.append(item)

    analyzable = (
        not missing_references
        and all(
            item["path"] and Path(item["path"]).is_file()
            and Path(item["path"]).suffix.lower() in ALLOWED_SUFFIXES
            for item in prelim
        )
    )
    analyzer = build_analyzer(args.insightface_root) if analyzable else None
    centroid: np.ndarray | None = None
    reference_pairwise: list[float] = []
    if analyzer is not None:
        reference_embeddings = []
        for path in references:
            image = load_rgb(path)
            _, faces = faces_for(analyzer, image)
            if not faces:
                global_errors.append(f"No face detected in locked reference: {path}")
                continue
            reference_embeddings.append(normalized_embedding(largest_face(faces)))
        if len(reference_embeddings) == len(references):
            reference_pairwise = [
                cosine(left, right)
                for left, right in itertools.combinations(reference_embeddings, 2)
            ]
            centroid = np.mean(np.stack(reference_embeddings), axis=0)
            centroid /= max(float(np.linalg.norm(centroid)), 1e-8)

    seen_hashes: dict[str, str] = {}
    seen_dhashes: list[tuple[str, str]] = []
    for item in prelim:
        path = Path(item["path"]) if item.get("path") else None
        if analyzer is None or path is None or not path.is_file():
            item["valid"] = False
            record_reports.append(item)
            continue
        image = load_rgb(path)
        width, height = image.size
        file_hash = sha256(path)
        perceptual_hash = dhash(image)
        item.update(
            {
                "sha256": file_hash,
                "dhash": perceptual_hash,
                "width": width,
                "height": height,
                "short_side_pixels": min(width, height),
            }
        )
        if min(width, height) < 1024:
            item["errors"].append("image short side must be at least 1024 pixels")
        if file_hash.lower() in existing_hashes:
            item["errors"].append("exact image already exists in the locked V3 source pool")
        if file_hash in seen_hashes:
            item["errors"].append(f"exact duplicate of intake record {seen_hashes[file_hash]}")
        else:
            seen_hashes[file_hash] = item["id"]
        for other_id, other_hash in seen_dhashes:
            distance = hamming(perceptual_hash, other_hash)
            if distance <= 4:
                item["errors"].append(
                    f"near-duplicate of intake record {other_id} (dHash distance {distance})"
                )
        seen_dhashes.append((item["id"], perceptual_hash))

        image_bgr, faces = faces_for(analyzer, image)
        item["detected_face_count"] = len(faces)
        if len(faces) != 1:
            item["errors"].append(f"exactly one face must be detected; found {len(faces)}")
        if not faces:
            item["valid"] = False
            record_reports.append(item)
            continue
        face = largest_face(faces)
        bbox = np.asarray(face.bbox, dtype=np.float32)
        pose = np.asarray(getattr(face, "pose", [np.nan, np.nan, np.nan]), dtype=np.float32)
        face_width = float(bbox[2] - bbox[0])
        face_height = float(bbox[3] - bbox[1])
        confidence = float(getattr(face, "det_score", 0.0))
        yaw = float(pose[1])
        sharpness = face_crop_sharpness(image_bgr, bbox)
        similarity = (
            cosine(normalized_embedding(face), centroid) if centroid is not None else None
        )
        item.update(
            {
                "face_bbox": [rounded(value) for value in bbox],
                "face_width_pixels": rounded(face_width),
                "face_height_pixels": rounded(face_height),
                "face_height_fraction": rounded(face_height / max(height, 1)),
                "detector_confidence": rounded(confidence),
                "pitch_degrees": rounded(float(pose[0])),
                "yaw_degrees": rounded(yaw),
                "roll_degrees": rounded(float(pose[2])),
                "face_sharpness": rounded(sharpness),
                "identity_centroid_similarity_diagnostic": rounded(similarity),
            }
        )
        if confidence < 0.75:
            item["errors"].append(f"face detector confidence {confidence:.3f} is below 0.75")
        limits = ROLE_LIMITS.get(item["role"])
        if limits is None:
            item["errors"].append(f"unsupported role: {item['role']}")
        else:
            if not limits["yaw_min"] <= yaw <= limits["yaw_max"]:
                item["errors"].append(
                    f"measured yaw {yaw:.1f} is outside {limits['yaw_min']:.0f}..{limits['yaw_max']:.0f} for {item['role']}"
                )
            if face_height < limits["face_height"]:
                item["errors"].append(
                    f"face height {face_height:.1f}px is below {limits['face_height']:.0f}px for {item['role']}"
                )
        if sharpness < 80.0:
            item["errors"].append(
                f"normalized face sharpness {sharpness:.1f} is below 80.0"
            )
        if similarity is not None and similarity < 0.35:
            item["warnings"].append(
                "very low identity-centroid diagnostic; verify current appearance manually"
            )
        item["valid"] = len(item["errors"]) == 0
        record_reports.append(item)

    training_sessions = Counter(
        item["session"] for item in prelim if item["split"] == "train" and item["session"]
    )
    overloaded = {session: count for session, count in training_sessions.items() if count > 3}
    if overloaded:
        global_errors.append(
            "No capture session may contribute more than three training images: "
            + ", ".join(f"{session}={count}" for session, count in sorted(overloaded.items()))
        )

    by_role_split: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in prelim:
        by_role_split[(item["role"], item["split"])].append(item)
    for role in ("profile_image_left", "profile_image_right"):
        train_sessions = {
            item["session"] for item in by_role_split[(role, "train")] if item["session"]
        }
        validation_sessions = {
            item["session"]
            for item in by_role_split[(role, "validation")]
            if item["session"]
        }
        if len(train_sessions) != 2:
            global_errors.append(f"{role} training photos must come from two distinct sessions")
        if train_sessions & validation_sessions:
            global_errors.append(
                f"{role} validation session must be independent from both training sessions"
            )
    body_sessions = {
        item["session"] for item in by_role_split[("body", "train")] if item["session"]
    }
    if len(body_sessions) != 2:
        global_errors.append("The two body training photos must use two distinct sessions")

    valid = not global_errors and all(item.get("valid") for item in record_reports)
    report = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "valid": valid,
        "purpose": "Measured genuine-photo intake gate for FLUX.2 Klein Base 9B identity V6",
        "privacy": "All image and face analysis ran locally; no photographs were uploaded.",
        "spec": str(spec_path),
        "spec_sha256": sha256(spec_path),
        "intake_root": str(intake_root) if intake_root else None,
        "trigger_word": TRIGGER,
        "required_counts": [
            {"role": role, "split": split, "count": count}
            for (role, split), count in REQUIRED_COUNTS.items()
        ],
        "existing_manifest": str(existing_manifest),
        "existing_manifest_sha256": existing_manifest_hash,
        "identity_references": [str(path) for path in references],
        "reference_pairwise_minimum": rounded(min(reference_pairwise)) if reference_pairwise else None,
        "reference_pairwise_mean": rounded(float(np.mean(reference_pairwise))) if reference_pairwise else None,
        "thresholds": {
            "short_side_pixels_minimum": 1024,
            "face_detector_confidence_minimum": 0.75,
            "normalized_face_sharpness_minimum": 80.0,
            "near_duplicate_dhash_distance_maximum": 4,
            "role_limits": ROLE_LIMITS,
        },
        "session_counts_training": dict(sorted(training_sessions.items())),
        "errors": global_errors,
        "warnings": global_warnings,
        "records": record_reports,
    }
    write_report(report, output_path)
    if args.contact_sheet:
        render_contact_sheet(record_reports, args.contact_sheet.resolve())
    raise SystemExit(0 if valid else 2)


if __name__ == "__main__":
    main()
