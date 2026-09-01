#!/usr/bin/env python3
"""Build a thumbnail-only review sheet from the v2 step-200 gate manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def thumb(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8-sig"))

    cell_w, cell_h, label_h = 280, 350, 42
    columns = 6
    rows = 3
    canvas = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), "#17191d")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)

    for column, record in enumerate(data["held_outs"]):
        image = thumb(Path(record["path"]), (cell_w, cell_h))
        canvas.paste(image, (column * cell_w, label_h))
        draw.text((column * cell_w + 8, 10), record["label"], fill="white", font=font)

    variants = data["review_variants"]
    for row, scene in enumerate(("portrait", "waist-up-social"), start=1):
        y = row * (cell_h + label_h)
        for column, variant in enumerate(variants):
            path = variant["outputs"].get(scene)
            if not path:
                continue
            image = thumb(Path(path), (cell_w, cell_h))
            canvas.paste(image, (column * cell_w, y + label_h))
            draw.text((column * cell_w + 8, y + 10), f"{variant['label']} | {scene}", fill="white", font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, quality=94, subsampling=0)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
