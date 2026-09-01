#!/usr/bin/env python3
"""Build a labeled contact sheet for a FLUX.2 Dev high-value scene run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    scenes = data["scenes"]
    outputs = data["outputs"]
    thumb_size = (416, 624)
    label_height = 48
    gap = 12
    columns = 3
    rows = (len(scenes) + columns - 1) // columns
    width = columns * thumb_size[0] + (columns + 1) * gap
    height = rows * (thumb_size[1] + label_height) + (rows + 1) * gap
    canvas = Image.new("RGB", (width, height), "#17191d")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=20)

    for index, scene in enumerate(scenes):
        row, column = divmod(index, columns)
        x = gap + column * (thumb_size[0] + gap)
        y = gap + row * (thumb_size[1] + label_height + gap)
        path = Path(outputs[scene["label"]])
        with Image.open(path) as source:
            thumb = ImageOps.fit(source.convert("RGB"), thumb_size, method=Image.Resampling.LANCZOS)
        canvas.paste(thumb, (x, y + label_height))
        draw.text((x + 8, y + 12), scene["label"], fill="white", font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, quality=95, subsampling=0)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
