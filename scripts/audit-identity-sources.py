#!/usr/bin/env python3
"""Create deterministic contact sheets for identity-dataset source media.

The script is intentionally read-only with respect to the source directory. It
writes an inventory and review sheets beneath the requested output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi"}
TILE_WIDTH = 320
IMAGE_HEIGHT = 300
LABEL_HEIGHT = 72
SHEET_COLUMNS = 4


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_still(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        return ImageOps.exif_transpose(opened).convert("RGB")


def difference_hash(image: Image.Image) -> str:
    reduced = ImageOps.grayscale(image).resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(reduced.getdata())
    value = 0
    for row in range(8):
        for column in range(8):
            value = (value << 1) | int(
                pixels[row * 9 + column] > pixels[row * 9 + column + 1]
            )
    return f"{value:016x}"


def exif_summary(path: Path) -> dict[str, str | int]:
    with Image.open(path) as opened:
        exif = opened.getexif()
    fields = {
        271: "make",
        272: "model",
        274: "orientation",
        305: "software",
        306: "modified_at",
        36867: "captured_at",
    }
    return {
        label: value
        for tag, label in fields.items()
        if (value := exif.get(tag)) not in (None, "")
    }


def hamming_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def frame_to_image(frame) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def render_sheet(items: list[tuple[Image.Image, list[str]]], destination: Path) -> None:
    rows = (len(items) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
    sheet = Image.new(
        "RGB",
        (SHEET_COLUMNS * TILE_WIDTH, rows * (IMAGE_HEIGHT + LABEL_HEIGHT)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (image, labels) in enumerate(items):
        x = (index % SHEET_COLUMNS) * TILE_WIDTH
        y = (index // SHEET_COLUMNS) * (IMAGE_HEIGHT + LABEL_HEIGHT)
        fitted = ImageOps.contain(image, (TILE_WIDTH, IMAGE_HEIGHT))
        image_x = x + (TILE_WIDTH - fitted.width) // 2
        image_y = y + (IMAGE_HEIGHT - fitted.height) // 2
        sheet.paste(fitted, (image_x, image_y))
        for line_index, label in enumerate(labels[:4]):
            draw.text((x + 5, y + IMAGE_HEIGHT + 4 + 15 * line_index), label, fill="black", font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=92, subsampling=0)


def sample_video(path: Path, interval_seconds: float) -> tuple[list[dict], list[tuple[Image.Image, list[str]]]]:
    capture = cv2.VideoCapture(str(path))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if fps > 0 else 0.0
    records: list[dict] = []
    sheet_items: list[tuple[Image.Image, list[str]]] = []
    timestamp = 0.0
    while timestamp <= duration + 1e-6:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = capture.read()
        if ok:
            height, width = frame.shape[:2]
            records.append({"timestamp_seconds": round(timestamp, 3), "width": width, "height": height})
            sheet_items.append(
                (
                    frame_to_image(frame),
                    [path.name, f"t={timestamp:.1f}s", f"{width}x{height}"],
                )
            )
        timestamp += interval_seconds
    capture.release()
    return records, sheet_items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--video-interval", type=float, default=2.0)
    parser.add_argument(
        "--stills-per-sheet",
        type=int,
        default=0,
        help="Split stills into numbered review sheets; 0 writes one combined sheet.",
    )
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    stills = sorted(
        path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    videos = sorted(
        path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )

    inventory = {"source_dir": str(source_dir), "stills": [], "videos": []}
    still_sheet: list[tuple[Image.Image, list[str]]] = []
    for path in stills:
        image = load_still(path)
        inventory["stills"].append(
            {
                "path": str(path),
                "filename": path.name,
                "width": image.width,
                "height": image.height,
                "sha256": sha256(path),
                "dhash": difference_hash(image),
                "exif": exif_summary(path),
            }
        )
        still_sheet.append((image, [path.name, f"{image.width}x{image.height}"]))

    inventory["near_duplicate_pairs"] = [
        {
            "left": left["filename"],
            "right": right["filename"],
            "dhash_distance": hamming_distance(left["dhash"], right["dhash"]),
        }
        for index, left in enumerate(inventory["stills"])
        for right in inventory["stills"][index + 1 :]
        if hamming_distance(left["dhash"], right["dhash"]) <= 4
    ]

    if args.stills_per_sheet > 0:
        for index in range(0, len(still_sheet), args.stills_per_sheet):
            sheet_number = index // args.stills_per_sheet + 1
            render_sheet(
                still_sheet[index : index + args.stills_per_sheet],
                output_dir / f"source-stills-contact-sheet-{sheet_number:02d}.jpg",
            )
    else:
        render_sheet(still_sheet, output_dir / "source-stills-contact-sheet.jpg")

    for path in videos:
        records, sheet_items = sample_video(path, args.video_interval)
        inventory["videos"].append(
            {
                "path": str(path),
                "filename": path.name,
                "sha256": sha256(path),
                "sample_interval_seconds": args.video_interval,
                "sampled_frames": records,
            }
        )
        render_sheet(sheet_items, output_dir / f"{path.stem}-contact-sheet.jpg")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "source-inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "stills": len(stills),
                "videos": len(videos),
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
