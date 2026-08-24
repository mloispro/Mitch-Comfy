#!/usr/bin/env python3
"""Build numbered visual-review sheets from the multi-person audit JSON."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=96)
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#111418")
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def shortened(path: str, limit: int = 54) -> str:
    value = path.replace("\\", "/")
    if len(value) <= limit:
        return value
    return "…" + value[-(limit - 1) :]


def main() -> None:
    args = parse_args()
    rows = json.loads(args.audit.read_text(encoding="utf-8"))
    excluded = (
        "selected-references",
        "lora-dataset",
        "stage1_",
        "debug-native",
        "person-mask",
        "contact-sheet",
    )
    eligible = [
        row
        for row in rows
        if int(row.get("yolo_people") or 0) >= 2
        and row.get("identity_score") not in (None, "")
        and float(row["identity_score"]) >= 0.65
        and not any(part in row["relative_path"].lower() for part in excluded)
    ]
    eligible.sort(
        key=lambda row: (
            float(row["identity_score"]),
            int(row.get("yolo_people") or 0),
        ),
        reverse=True,
    )
    unique = []
    seen = set()
    for row in eligible:
        key = row.get("dhash") or row.get("sha256")
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
        if len(unique) >= args.limit:
            break

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    per_page = 12
    columns = 4
    rows_per_page = 3
    tile_w, tile_h = 410, 690
    image_size = (380, 570)
    margin = 28
    gap = 18
    title_h = 80
    width = margin * 2 + columns * tile_w + (columns - 1) * gap
    height = margin * 2 + title_h + rows_per_page * tile_h + (rows_per_page - 1) * gap
    title_font = font(30, bold=True)
    label_font = font(16, bold=True)
    small_font = font(13)

    for page_index in range(math.ceil(len(unique) / per_page)):
        page_rows = unique[page_index * per_page : (page_index + 1) * per_page]
        sheet = Image.new("RGB", (width, height), "#f2f0eb")
        draw = ImageDraw.Draw(sheet)
        draw.text(
            (margin, margin),
            f"Multi-person candidates — identity-ranked visual review — page {page_index + 1}",
            fill="#17191c",
            font=title_font,
        )
        for local_index, row in enumerate(page_rows):
            number = page_index * per_page + local_index + 1
            col = local_index % columns
            grid_row = local_index // columns
            x = margin + col * (tile_w + gap)
            y = margin + title_h + grid_row * (tile_h + gap)
            draw.rounded_rectangle(
                (x, y, x + tile_w, y + tile_h),
                radius=12,
                fill="#ffffff",
                outline="#d0cdc6",
                width=2,
            )
            preview = fit_image(Path(row["path"]), image_size)
            sheet.paste(preview, (x + 15, y + 15))
            label_y = y + 15 + image_size[1] + 10
            draw.text(
                (x + 15, label_y),
                f"#{number}  ID {float(row['identity_score']):.4f}  people {row['yolo_people']}  faces {row.get('face_count', '')}",
                fill="#17191c",
                font=label_font,
            )
            draw.text(
                (x + 15, label_y + 25),
                shortened(row["relative_path"]),
                fill="#4b5056",
                font=small_font,
            )
            model = row.get("report_model") or row.get("workflow_models") or "metadata unavailable"
            draw.text(
                (x + 15, label_y + 48),
                shortened(str(model), 52),
                fill="#4b5056",
                font=small_font,
            )
            manifest.append({"number": number, **row})
        target = args.out_dir / f"candidates-{page_index + 1:02d}.jpg"
        sheet.save(target, quality=92, subsampling=0)
        print(target)

    (args.out_dir / "candidate-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
