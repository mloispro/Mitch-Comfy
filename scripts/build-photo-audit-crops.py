from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build exact-resolution tiles and display-size views for photographic QA."
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source_path = args.image.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as opened:
        image = opened.convert("RGB")

    width, height = image.size
    if (width, height) != (896, 1344):
        raise ValueError(f"Expected 896x1344 source, received {width}x{height}.")

    image.resize((224, 336), Image.Resampling.LANCZOS).save(
        output / "thumbnail-25-percent.png"
    )
    image.resize((112, 168), Image.Resampling.LANCZOS).save(
        output / "dating-thumbnail.png"
    )
    boxes = {
        "01-top-left.png": (0, 0, 448, 448),
        "02-top-right.png": (448, 0, 896, 448),
        "03-middle-left.png": (0, 448, 448, 896),
        "04-middle-right.png": (448, 448, 896, 896),
        "05-bottom-left.png": (0, 896, 448, 1344),
        "06-bottom-right.png": (448, 896, 896, 1344),
    }
    for name, box in boxes.items():
        image.crop(box).save(output / name)


if __name__ == "__main__":
    main()
