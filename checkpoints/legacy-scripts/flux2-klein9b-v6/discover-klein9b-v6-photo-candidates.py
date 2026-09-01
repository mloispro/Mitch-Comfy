#!/usr/bin/env python3
"""Discover usable V6 identity-LoRA photographs already present in Mitch photos.

This is a read-only local inventory. It measures actual face pose, pixel coverage,
sharpness, identity similarity, EXIF provenance, and duplicate status. It does not
copy, edit, or upload photographs. Automated role suggestions are only a shortlist
for full-size human review; body framing and genuine-camera provenance remain
manual gates.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import textwrap
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import ExifTags, Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
REFERENCE_PATHS = (
    ROOT / "datasets" / "mitch-identity-stills-v3" / "validation" / "val_03_navy_upper_body.jpg",
    ROOT / "datasets" / "mitch-identity-stills-v3" / "validation" / "val_04_window_small_smile.jpg",
    ROOT / "datasets" / "mitch-identity-stills-v3" / "validation" / "val_05_balcony_opposite_angle.jpg",
    ROOT / "datasets" / "mitch-identity-stills-v3" / "validation" / "val_06_car_daylight.jpg",
)
MANIFEST_PATH = ROOT / "datasets" / "mitch-identity-stills-v3" / "manifest.json"
ROLE_LIMITS = {
    "profile_image_left": (-80.0, -45.0, 350.0),
    "profile_image_right": (45.0, 80.0, 350.0),
    "three_quarter_image_left": (-40.0, -20.0, 350.0),
    "three_quarter_image_right": (20.0, 40.0, 350.0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    parser.add_argument("--shortlist-sheet", type=Path, required=True)
    parser.add_argument("--body-sheet", type=Path, required=True)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--insightface-root", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        return ImageOps.exif_transpose(opened).convert("RGB")


def normalized(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    return value / max(float(np.linalg.norm(value)), 1e-8)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(normalized(left), normalized(right)))


def rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


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


def face_sharpness(image_bgr: np.ndarray, bbox: np.ndarray) -> float:
    height, width = image_bgr.shape[:2]
    x1, y1, x2, y2 = [int(round(float(value))) for value in bbox]
    crop = image_bgr[max(y1, 0) : min(y2, height), max(x1, 0) : min(x2, width)]
    if crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def exif_summary(path: Path) -> dict[str, Any]:
    values: dict[str, Any] = {}
    try:
        with Image.open(path) as image:
            raw = image.getexif()
            for key, value in raw.items():
                name = ExifTags.TAGS.get(key, str(key))
                if name in {
                    "Make",
                    "Model",
                    "Software",
                    "DateTime",
                    "DateTimeOriginal",
                    "DateTimeDigitized",
                    "Orientation",
                    "LensModel",
                }:
                    values[name] = str(value)
    except Exception as exc:
        values["read_error"] = str(exc)
    return values


def build_analyzer(model_root: Path | None) -> FaceAnalysis:
    kwargs: dict[str, Any] = {
        "name": "antelopev2",
        "providers": ["CPUExecutionProvider"],
        "allowed_modules": ["detection", "recognition", "landmark_3d_68"],
    }
    if model_root:
        kwargs["root"] = str(model_root.resolve())
    analyzer = FaceAnalysis(**kwargs)
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    return analyzer


def largest_face(faces: list[Any]):
    return max(
        faces,
        key=lambda face: float(
            (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
        ),
    )


def eligible_roles(
    *,
    yaw: float,
    face_height: float,
    face_fraction: float,
    short_side: int,
    confidence: float,
    sharpness: float,
    face_count: int,
    overlap: bool,
) -> list[str]:
    common = (
        face_count == 1
        and confidence >= 0.75
        and short_side >= 1024
        and sharpness >= 80.0
        and not overlap
    )
    roles = []
    if common:
        for role, (minimum, maximum, required_height) in ROLE_LIMITS.items():
            if minimum <= yaw <= maximum and face_height >= required_height:
                roles.append(role)
        if -35.0 <= yaw <= 35.0 and face_height >= 200.0 and face_fraction <= 0.24:
            roles.append("body_framing_candidate_manual_review")
    return roles


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path(r"C:\Windows\Fonts") / name
    try:
        return ImageFont.truetype(str(path), size=size)
    except Exception:
        return ImageFont.load_default(size=size)


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    preview = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    tile = Image.new("RGB", size, "#111318")
    tile.paste(preview, ((size[0] - preview.width) // 2, (size[1] - preview.height) // 2))
    return tile


def render_sheet(records: list[dict[str, Any]], destination: Path, title: str) -> None:
    columns, tile_w, image_h, label_h = 4, 330, 360, 138
    rows = (len(records) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * tile_w, 58 + rows * (image_h + label_h)), "#0d0f13")
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 14), title, font=font(22, True), fill="#f4f4f5")
    for index, record in enumerate(records):
        row, column = divmod(index, columns)
        x, y = column * tile_w, 58 + row * (image_h + label_h)
        image = load_rgb(Path(record["path"]))
        canvas.paste(fit(image, (tile_w - 16, image_h - 16)), (x + 8, y + 8))
        roles = record.get("eligible_roles", [])
        color = "#69db7c" if roles else ("#ffd43b" if record.get("identity_similarity", 0) >= 0.35 else "#ff6b6b")
        lines = [
            textwrap.shorten(record["name"], width=42, placeholder="..."),
            (
                f"yaw {record.get('yaw_degrees')}°  face {record.get('face_height_pixels')}px  "
                f"frac {record.get('face_height_fraction')}"
            ),
            (
                f"sharp {record.get('face_sharpness')}  id {record.get('identity_similarity')}  "
                f"faces {record.get('detected_face_count')}"
            ),
            textwrap.shorten(
                ", ".join(roles) if roles else "; ".join(record.get("rejection_reasons", [])[:2]),
                width=50,
                placeholder="...",
            ),
        ]
        for line_index, line in enumerate(lines):
            draw.text(
                (x + 8, y + image_h + 5 + line_index * 29),
                line,
                font=font(13, line_index == 0),
                fill=color if line_index == 3 else "#e4e4e7",
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=90, optimize=True, progressive=True, subsampling=0)


def main() -> int:
    args = parse_args()
    scan_root = args.root.resolve()
    if not scan_root.is_dir():
        raise RuntimeError(f"Scan root is missing: {scan_root}")
    iterator = scan_root.rglob("*") if args.recursive else scan_root.iterdir()
    paths = sorted(
        path.resolve()
        for path in iterator
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not paths:
        raise RuntimeError(f"No images found: {scan_root}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    existing_hashes = {
        str(record["dataset_sha256"]).lower() for record in manifest["records"]
    }
    analyzer = build_analyzer(args.insightface_root)
    reference_embeddings = []
    for path in REFERENCE_PATHS:
        bgr = cv2.cvtColor(np.asarray(load_rgb(path)), cv2.COLOR_RGB2BGR)
        faces = analyzer.get(bgr)
        if not faces:
            raise RuntimeError(f"No face detected in identity reference: {path}")
        reference_embeddings.append(normalized(largest_face(faces).normed_embedding))
    centroid = normalized(np.mean(np.stack(reference_embeddings), axis=0))

    records: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    seen_dhashes: list[tuple[str, str]] = []
    for path in paths:
        image = load_rgb(path)
        width, height = image.size
        file_hash = sha256(path)
        visual_hash = dhash(image)
        bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        faces = analyzer.get(bgr)
        exact_overlap = file_hash.lower() in existing_hashes
        exact_duplicate_of = seen_hashes.get(file_hash)
        near_duplicates = [
            {"name": name, "dhash_distance": hamming(visual_hash, other_hash)}
            for name, other_hash in seen_dhashes
            if hamming(visual_hash, other_hash) <= 4
        ]
        seen_hashes.setdefault(file_hash, path.name)
        seen_dhashes.append((path.name, visual_hash))
        record: dict[str, Any] = {
            "name": path.name,
            "path": str(path),
            "sha256": file_hash,
            "dhash": visual_hash,
            "width": width,
            "height": height,
            "short_side_pixels": min(width, height),
            "detected_face_count": len(faces),
            "exact_existing_dataset_overlap": exact_overlap,
            "exact_duplicate_of": exact_duplicate_of,
            "near_duplicates": near_duplicates,
            "exif": exif_summary(path),
            "eligible_roles": [],
            "rejection_reasons": [],
        }
        if not faces:
            record["rejection_reasons"].append("no face detected")
            records.append(record)
            continue
        face = largest_face(faces)
        bbox = np.asarray(face.bbox, dtype=np.float32)
        pose = np.asarray(getattr(face, "pose", [np.nan, np.nan, np.nan]), dtype=np.float32)
        face_height = float(bbox[3] - bbox[1])
        yaw = float(pose[1])
        confidence = float(getattr(face, "det_score", 0.0))
        sharpness = face_sharpness(bgr, bbox)
        similarity = cosine(face.normed_embedding, centroid)
        face_fraction = face_height / max(height, 1)
        record.update(
            {
                "face_bbox": [rounded(value) for value in bbox],
                "face_width_pixels": rounded(float(bbox[2] - bbox[0])),
                "face_height_pixels": rounded(face_height),
                "face_height_fraction": rounded(face_fraction),
                "detector_confidence": rounded(confidence),
                "pitch_degrees": rounded(float(pose[0])),
                "yaw_degrees": rounded(yaw),
                "roll_degrees": rounded(float(pose[2])),
                "face_sharpness": rounded(sharpness),
                "identity_similarity": rounded(similarity),
            }
        )
        roles = eligible_roles(
            yaw=yaw,
            face_height=face_height,
            face_fraction=face_fraction,
            short_side=min(width, height),
            confidence=confidence,
            sharpness=sharpness,
            face_count=len(faces),
            overlap=exact_overlap,
        )
        record["eligible_roles"] = roles
        if len(faces) != 1:
            record["rejection_reasons"].append(f"detected {len(faces)} faces")
        if min(width, height) < 1024:
            record["rejection_reasons"].append("short side below 1024px")
        if confidence < 0.75:
            record["rejection_reasons"].append("detector confidence below 0.75")
        if sharpness < 80:
            record["rejection_reasons"].append("face sharpness below 80")
        if exact_overlap:
            record["rejection_reasons"].append("already in V3 dataset")
        if exact_duplicate_of:
            record["rejection_reasons"].append(f"exact duplicate of {exact_duplicate_of}")
        if near_duplicates:
            record["rejection_reasons"].append("near duplicate within scan")
        if similarity < 0.35:
            record["rejection_reasons"].append("low Mitch identity diagnostic")
        if not roles and not record["rejection_reasons"]:
            record["rejection_reasons"].append("clear photo but outside missing-view geometry")
        records.append(record)

    role_counts = Counter(role for record in records for role in record["eligible_roles"])
    shortlist = [record for record in records if record["eligible_roles"]]
    shortlist.sort(
        key=lambda item: (
            int(any(role.startswith("profile_") for role in item["eligible_roles"])),
            int("body_framing_candidate_manual_review" in item["eligible_roles"]),
            float(item.get("identity_similarity") or -1),
            float(item.get("face_height_pixels") or -1),
        ),
        reverse=True,
    )
    all_sorted = sorted(
        records,
        key=lambda item: (
            int(bool(item["eligible_roles"])),
            abs(float(item.get("yaw_degrees") or 0.0)),
            float(item.get("identity_similarity") or -1),
        ),
        reverse=True,
    )
    body_manual_review = [
        record
        for record in records
        if record.get("detected_face_count") == 1
        and not record.get("exact_existing_dataset_overlap")
        and float(record.get("identity_similarity") or -1) >= 0.35
        and int(record.get("short_side_pixels") or 0) >= 768
        and float(record.get("face_sharpness") or 0) >= 80
        and float(record.get("face_height_pixels") or 0) >= 200
        and float(record.get("face_height_fraction") or 1) <= 0.35
        and abs(float(record.get("yaw_degrees") or 0)) <= 35
    ]
    body_manual_review.sort(
        key=lambda item: (
            float(item.get("face_height_fraction") or 1),
            -float(item.get("face_height_pixels") or 0),
        )
    )
    report = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "valid": True,
        "purpose": "Local discovery of existing genuine-photo candidates for Klein 9B V6",
        "privacy": "All analysis ran locally; no photographs were copied, modified, or uploaded.",
        "scan_root": str(scan_root),
        "recursive": bool(args.recursive),
        "image_count": len(records),
        "locked_existing_manifest": str(MANIFEST_PATH),
        "identity_references": [str(path) for path in REFERENCE_PATHS],
        "thresholds": {
            "short_side_minimum": 1024,
            "detector_confidence_minimum": 0.75,
            "face_sharpness_minimum": 80.0,
            "role_limits": ROLE_LIMITS,
            "body_face_height_minimum": 200,
            "body_face_fraction_maximum": 0.24,
        },
        "role_counts": dict(sorted(role_counts.items())),
        "shortlist_count": len(shortlist),
        "shortlist": shortlist,
        "body_manual_review_count": len(body_manual_review),
        "body_manual_review": body_manual_review,
        "records": records,
    }
    output = args.json_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    render_sheet(all_sorted, args.contact_sheet.resolve(), "Mitch photos — all top-level images ranked for V6")
    render_sheet(shortlist, args.shortlist_sheet.resolve(), "Mitch photos — measured V6 role shortlist")
    render_sheet(
        body_manual_review,
        args.body_sheet.resolve(),
        "Mitch photos — possible body framing, manual review required",
    )
    print(json.dumps({
        "image_count": len(records),
        "shortlist_count": len(shortlist),
        "role_counts": dict(sorted(role_counts.items())),
        "json": str(output),
        "contact_sheet": str(args.contact_sheet.resolve()),
        "shortlist_sheet": str(args.shortlist_sheet.resolve()),
        "body_manual_review_count": len(body_manual_review),
        "body_sheet": str(args.body_sheet.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
