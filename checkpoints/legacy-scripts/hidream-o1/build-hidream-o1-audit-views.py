from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build full-frame thumbnail and exact-pixel grid crops for HiDream QA."
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with Image.open(args.image.resolve()) as opened:
        image = opened.convert("RGB")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    width, height = image.size
    thumb_width = 208
    thumb_height = max(1, round(height * thumb_width / width))
    image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS).save(
        output / "thumbnail.png"
    )
    dating_width = 104
    dating_height = max(1, round(height * dating_width / width))
    image.resize((dating_width, dating_height), Image.Resampling.LANCZOS).save(
        output / "dating-thumbnail.png"
    )

    grid = image.copy()
    draw = ImageDraw.Draw(grid)
    draw.line((width // 2, 0, width // 2, height), fill=(255, 0, 0), width=2)
    draw.line((0, height // 3, width, height // 3), fill=(255, 0, 0), width=2)
    draw.line((0, 2 * height // 3, width, 2 * height // 3), fill=(255, 0, 0), width=2)
    grid.save(output / "grid-overlay.png")

    for row in range(3):
        top = round(row * height / 3)
        bottom = round((row + 1) * height / 3)
        for column in range(2):
            left = round(column * width / 2)
            right = round((column + 1) * width / 2)
            image.crop((left, top, right, bottom)).save(
                output / f"crop-r{row + 1}-c{column + 1}.png"
            )

    print(f"{width}x{height} audit views: {output}")


if __name__ == "__main__":
    main()
