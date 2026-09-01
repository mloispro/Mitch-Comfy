from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def font(size: int):
    for candidate in (
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def fitted(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as opened:
        return ImageOps.fit(opened.convert("RGB"), size, method=Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a full nine-scene Z-Image LoRA comparison sheet.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    scenes = manifest["scenes"]
    if len(scenes) != 9:
        raise RuntimeError(f"Expected nine scenes, got {len(scenes)}")

    cell = (416, 608)
    gutter = 18
    label_height = 52
    header_height = 76
    title_height = 74
    width = gutter + 3 * (cell[0] + gutter)
    height = title_height + header_height + 3 * (label_height + cell[1] + gutter) + gutter
    sheet = Image.new("RGB", (width, height), "#15171a")
    draw = ImageDraw.Draw(sheet)
    title_font = font(28)
    header_font = font(22)
    label_font = font(18)
    draw.text((gutter, 18), "Z-Image Base identity LoRA — nine-scene comparison", fill="white", font=title_font)
    headers = ("Original Z-Image raw", "Final scene target", "New Z-Image LoRA")
    for col, header in enumerate(headers):
        x = gutter + col * (cell[0] + gutter)
        draw.text((x, title_height + 18), header, fill="#a9d4ff", font=header_font)

    for index, scene in enumerate(scenes):
        row = index // 3
        subcol = index % 3
        block_width = width // 3
        # Lay out each scene as a horizontal three-image strip in a 3x3 scene grid.
        # A full-resolution sheet per scene is also written below for close review.
        scene_paths = [Path(scene[key]) for key in ("original_raw", "final_target", "new_image")]
        for path in scene_paths:
            if not path.is_file():
                raise RuntimeError(f"Comparison image is missing: {path}")

    # The all-scenes overview uses one representative new image per scene so it remains readable.
    overview_cell = (360, 526)
    overview_width = gutter + 3 * (overview_cell[0] + gutter)
    overview_height = title_height + 3 * (label_height + overview_cell[1] + gutter) + gutter
    overview = Image.new("RGB", (overview_width, overview_height), "#15171a")
    overview_draw = ImageDraw.Draw(overview)
    overview_draw.text((gutter, 18), "Selected Z-Image LoRA — nine original scenes", fill="white", font=title_font)
    for index, scene in enumerate(scenes):
        row, col = divmod(index, 3)
        x = gutter + col * (overview_cell[0] + gutter)
        y = title_height + row * (label_height + overview_cell[1] + gutter)
        overview_draw.text((x, y + 8), f"{index + 1:02d}  {scene['label']}", fill="#a9d4ff", font=label_font)
        overview.paste(fitted(Path(scene["new_image"]), overview_cell), (x, y + label_height))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    overview.save(args.output, quality=95)

    detail_dir = args.output.parent / f"{args.output.stem}-details"
    detail_dir.mkdir(parents=True, exist_ok=True)
    for index, scene in enumerate(scenes):
        detail = Image.new("RGB", (width, title_height + header_height + cell[1] + gutter), "#15171a")
        detail_draw = ImageDraw.Draw(detail)
        detail_draw.text((gutter, 18), f"{index + 1:02d}  {scene['label']}", fill="white", font=title_font)
        for col, (header, key) in enumerate(zip(headers, ("original_raw", "final_target", "new_image"))):
            x = gutter + col * (cell[0] + gutter)
            detail_draw.text((x, title_height + 18), header, fill="#a9d4ff", font=header_font)
            detail.paste(fitted(Path(scene[key]), cell), (x, title_height + header_height))
        detail.save(detail_dir / f"{index + 1:02d}-{scene['slug']}.jpg", quality=95)

    print(json.dumps({"overview": str(args.output), "details": str(detail_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
