from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "custom_nodes"
    / "ComfyUI-AIToolkit-Training"
    / "web"
    / "assets"
    / "scene-presets"
)
PREVIEW_OUTPUT = ROOT / "work" / "flux2-klein9b-visual-presets"
SIZE = (300, 210)


CARDS = {
    "identity-custom.jpg": ("Custom scene", None, (61, 72, 87)),
    "identity-founder-editorial.jpg": (
        "Founder editorial",
        Path(r"C:\projects\AI-Tools\ComfyUI\output\identity-eval\flux2-dev-v2\high-value\high-value-20260827-231336-founder-editorial_00001_.png"),
        (55, 73, 82),
    ),
    "identity-cooking-candid.jpg": (
        "Cooking candid",
        Path(r"C:\projects\AI-Tools\ComfyUI\output\flux2-dev-mitch-scene-studio\prompt-only\20260828-001713-561452\photo_00001_.png"),
        (96, 69, 45),
    ),
    "identity-golden-hour-rooftop.jpg": (
        "Golden-hour rooftop",
        Path(r"C:\projects\AI-Tools\ComfyUI\output\identity-eval\flux2-dev-v2\attractive-candids\attractive-candid-20260827-234853-golden-hour-candid_00001_.png"),
        (125, 81, 43),
    ),
    "identity-night-city-balcony.jpg": (
        "Night city balcony",
        ROOT / "work" / "identity-studio-night-rooftop-20260831" / "02-night-rooftop-right-facing-bare-neck.png",
        (35, 55, 70),
    ),
    "identity-rooftop-cocktail.jpg": (
        "Rooftop cocktail",
        ROOT / "assets" / "comfy-input" / "klein9b-scene-presets" / "identity-rooftop-cocktail-city-lights.jpg",
        (45, 54, 70),
    ),
    "identity-amalfi-balcony.jpg": (
        "Amalfi balcony",
        ROOT / "assets" / "comfy-input" / "dating-scenes" / "dating-06-amalfi.png",
        (76, 123, 156),
    ),
    "identity-italian-lake-boat.jpg": (
        "Italian lake boat",
        ROOT / "work" / "lake-como-mitch-reference-match" / "mitch-lake-como-boat-v1.png",
        (62, 105, 111),
    ),
    "identity-elegant-restaurant.jpg": (
        "Elegant restaurant",
        ROOT / "assets" / "comfy-input" / "dating-scenes" / "dating-08-restaurant.png",
        (83, 58, 42),
    ),
    "identity-ragdoll-cat.jpg": (
        "Ragdoll cat",
        ROOT / "assets" / "comfy-input" / "dating-scenes" / "dating-03-cat-ragdoll.png",
        (81, 78, 75),
    ),
    "identity-toddler-moment.jpg": ("Toddler moment", None, (121, 83, 62)),
    "identity-golden-shepherd-puppy.jpg": ("Golden Shepherd puppy", None, (126, 92, 47)),
    "identity-golf-course.jpg": (
        "Golf course",
        ROOT / "assets" / "comfy-input" / "dating-scenes" / "dating-05-golfer.png",
        (55, 105, 52),
    ),
    "identity-weekend-lake.jpg": (
        "Weekend lake",
        Path(r"C:\projects\AI-Tools\ComfyUI\output\identity-eval\flux2-dev-v2\high-value\high-value-20260827-231336-weekend-lake_00001_.png"),
        (54, 101, 118),
    ),
    "identity-downtown-menswear.jpg": ("Downtown menswear", None, (67, 72, 80)),
    "group-custom.jpg": ("Custom group upload", None, (72, 65, 82)),
    "group-approved-lounge.jpg": (
        "Approved lounge",
        ROOT / "assets" / "comfy-input" / "klein9b-scene-presets" / "group-approved-lounge-center.png",
        (95, 62, 39),
    ),
    "group-night-out-a.jpg": (
        "Night out A",
        ROOT / "assets" / "comfy-input" / "dating-scenes" / "dating-01-night-out-a.png",
        (105, 67, 38),
    ),
    "group-night-out-b.jpg": (
        "Night out B",
        ROOT / "assets" / "comfy-input" / "dating-scenes" / "dating-02-night-out-b.png",
        (105, 67, 38),
    ),
    "group-amber-booth.jpg": (
        "Amber booth",
        ROOT / "assets" / "comfy-input" / "klein9b-scene-presets" / "group-amber-booth-four-friends.jpg",
        (109, 70, 40),
    ),
}


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def placeholder(label: str, color: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", SIZE, color)
    draw = ImageDraw.Draw(image)
    for y in range(SIZE[1]):
        factor = 0.65 + 0.35 * (1.0 - y / max(SIZE[1] - 1, 1))
        shade = tuple(round(channel * factor) for channel in color)
        draw.line((0, y, SIZE[0], y), fill=shade)
    short = "\n".join(textwrap.wrap(label, width=18))
    box = draw.multiline_textbbox((0, 0), short, font=font(27, True), spacing=5, align="center")
    width = box[2] - box[0]
    height = box[3] - box[1]
    draw.multiline_text(
        ((SIZE[0] - width) / 2, (SIZE[1] - height) / 2 - 8),
        short,
        font=font(27, True),
        fill=(244, 244, 244),
        spacing=5,
        align="center",
    )
    return image


def build_card(label: str, source: Path | None, color: tuple[int, int, int]) -> Image.Image:
    if source is not None and source.is_file():
        with Image.open(source) as opened:
            image = ImageOps.fit(
                ImageOps.exif_transpose(opened).convert("RGB"),
                SIZE,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.38),
            )
    else:
        image = placeholder(label, color)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, SIZE[1] - 48, SIZE[0], SIZE[1]), fill=(8, 10, 13, 210))
    display = label if len(label) <= 26 else label[:24] + "…"
    draw.text((12, SIZE[1] - 36), display, font=font(20, True), fill=(255, 255, 255, 255))
    return image


def build_preview_sheet(filenames: list[str], title: str, output_name: str) -> None:
    columns = 3
    gap = 14
    header = 72
    rows = (len(filenames) + columns - 1) // columns
    width = columns * SIZE[0] + (columns + 1) * gap
    height = header + rows * SIZE[1] + (rows + 1) * gap
    sheet = Image.new("RGB", (width, height), (15, 19, 21))
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, 19), title, font=font(30, True), fill=(239, 246, 245))
    for index, filename in enumerate(filenames):
        with Image.open(OUTPUT / filename) as opened:
            card = opened.convert("RGB")
        x = gap + (index % columns) * (SIZE[0] + gap)
        y = header + gap + (index // columns) * (SIZE[1] + gap)
        sheet.paste(card, (x, y))
    PREVIEW_OUTPUT.mkdir(parents=True, exist_ok=True)
    sheet.save(PREVIEW_OUTPUT / output_name, quality=91, optimize=True)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, (label, source, color) in CARDS.items():
        card = build_card(label, source, color)
        card.save(OUTPUT / filename, quality=88, optimize=True)
    build_preview_sheet(
        [name for name in CARDS if name.startswith("identity-")],
        "Identity Studio — click a scene card",
        "identity-preset-gallery.jpg",
    )
    build_preview_sheet(
        [name for name in CARDS if name.startswith("group-")],
        "Group Scene Studio — click a layout card",
        "group-preset-gallery.jpg",
    )
    print(f"Wrote {len(CARDS)} visual preset cards to {OUTPUT}")


if __name__ == "__main__":
    main()
