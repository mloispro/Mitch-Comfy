from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the exact three-way restaurant gate sheet.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--plate", required=True, type=Path)
    parser.add_argument("--refined", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plate-score", required=True, type=float)
    parser.add_argument("--refined-score", required=True, type=float)
    parser.add_argument("--title", default="RESTAURANT IDENTITY GATE")
    parser.add_argument("--summary")
    parser.add_argument("--source-label", default="SOURCE")
    parser.add_argument("--plate-label", default="KLEIN 9B 4-REF")
    parser.add_argument("--refined-label", default="9B → BASE 4B IDENTITY")
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    contained = ImageOps.contain(image.convert("RGB"), size, Image.Resampling.LANCZOS)
    tile = Image.new("RGB", size, (18, 18, 20))
    tile.paste(
        contained,
        ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2),
    )
    return tile


def main() -> None:
    args = parse_args()
    for path in (args.source, args.plate, args.refined):
        if not path.is_file():
            raise FileNotFoundError(path)

    tile_size = (400, 600)
    margin, gap, header = 28, 16, 112
    canvas = Image.new(
        "RGB",
        (margin * 2 + tile_size[0] * 3 + gap * 2, margin * 2 + header + tile_size[1]),
        (12, 13, 16),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 18), args.title, font=font(27, True), fill=(245, 245, 247))
    summary = args.summary or (
        f"Klein 9B {args.plate_score:.4f}  →  whole-frame Base 4B {args.refined_score:.4f}"
    )
    draw.text(
        (margin, 57),
        summary,
        font=font(21),
        fill=(173, 207, 255),
    )

    items = [
        (args.source, args.source_label, (255, 216, 125)),
        (args.plate, args.plate_label, (117, 218, 196)),
        (args.refined, args.refined_label, (170, 145, 255)),
    ]
    for index, (path, label, color) in enumerate(items):
        x = margin + index * (tile_size[0] + gap)
        y = margin + header
        with Image.open(path) as image:
            canvas.paste(fit(image, tile_size), (x, y))
        draw.rectangle((x, y, x + tile_size[0], y + 38), fill=(10, 10, 12))
        draw.text((x + 8, y + 7), label, font=font(19, True), fill=color)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, format="PNG", compress_level=6)
    print(args.output)


if __name__ == "__main__":
    main()
