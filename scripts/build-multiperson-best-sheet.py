#!/usr/bin/env python3
"""Build the final one-page best-of sheet from the completed visual audit."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMFY_OUTPUT = Path(r"C:\projects\AI-Tools\ComfyUI\output")
DESTINATION = PROJECT_ROOT / "output" / "multiperson-best-of"


WINNERS = [
    {
        "rank": 1,
        "badge": "BEST OVERALL",
        "title": "Outdoor café — strongest realism + identity",
        "relative_path": r"flux2-identity-experiments\lora-4b\full-plus-face-crop-2.0x\20260821-223510-743424\photo_00001_.png",
        "identity": 0.7649,
        "people": 13,
        "faces": 2,
        "created": "FLUX.2 Klein Base 4B FP8 + Mitch identity LoRA (checkpoint 1,250, strength 0.6). One genuine reference + automatic 2× face crop; 30 Euler steps, guidance 4, seed 8675310. No face swap.",
        "review": "Most convincing single frame. Strong likeness, believable skin/camera texture, and coherent café background. Reads as a real phone portrait, although the secondary people are contextual rather than a posed group.",
    },
    {
        "rank": 2,
        "badge": "BEST CANDID",
        "title": "Brick sidewalk — best face/scene integration",
        "relative_path": r"flux2-reference-studio-v104\4-references\20260823-013320-468512\photo_00001_.png",
        "identity": 0.7556,
        "people": 7,
        "faces": 2,
        "created": "Easy Social Photos v1.0.4: Klein 9B KV four-step scene layout → masked Klein Base 4B identity pass. Four genuine references; best identity LoRA at 0.4; 20 Euler steps, guidance 2; seed 8675347.",
        "review": "Very good likeness and natural street detail with no obvious pasted-face boundary. The people and bicycles hold together well. Also a multi-person environment rather than a true group pose.",
    },
    {
        "rank": 3,
        "badge": "BEST LARGE CROWD",
        "title": "Night street — strongest dense-crowd result",
        "relative_path": r"research\faceonly-9b-crowd-seed2\targeted-raw_00001_.png",
        "identity": 0.7420,
        "people": 17,
        "faces": 15,
        "created": "Klein 9B KV FP8 crowd plate with two references, four Euler steps, seed 8675313 → targeted ReActor inswapper_128 replacement on only the main face (RetinaFace detection, no face restorer).",
        "review": "Best crowd spacing, motion, and environmental realism. Identity lock is much better than the untouched 9B plate. The main face is a little cleaner/brighter than the crowd, but it is the least distracting crowd finish.",
    },
    {
        "rank": 4,
        "badge": "BEST TRUE GROUP",
        "title": "Warm lounge — best small-group composition",
        "relative_path": r"dating-app-pack\01-night-out-a\final_00002_.png",
        "identity": 0.7383,
        "people": 5,
        "faces": 4,
        "created": "Qwen Image 2512 FP8 + four-step Lightning LoRA + Samsung phone-style LoRA, then ReActor inswapper_128 identity finish. Four Euler steps at CFG 1.",
        "review": "The clearest genuine group-photo winner: distinct people, plausible seating, usable likeness, and a coherent flash-lit room. It is more polished/staged than the two FLUX winners, so use it selectively.",
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        attempt = f"{current} {word}".strip()
        if current and draw.textlength(attempt, font=face) > width:
            lines.append(current)
            current = word
        else:
            current = attempt
    if current:
        lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    face: ImageFont.FreeTypeFont,
    fill: str,
    width: int,
    line_gap: int = 5,
) -> int:
    x, y = xy
    line_height = face.size + line_gap
    lines = wrap(draw, text, face, width)
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += line_height
    return y


def contain(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#0d1117")
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    sheet_w, sheet_h = 1900, 2820
    margin = 56
    gap = 30
    header_h = 170
    footer_h = 300
    tile_w = (sheet_w - margin * 2 - gap) // 2
    tile_h = (sheet_h - margin * 2 - header_h - footer_h - gap) // 2
    preview_size = (tile_w - 44, 650)

    sheet = Image.new("RGB", (sheet_w, sheet_h), "#eeeae2")
    draw = ImageDraw.Draw(sheet)
    title = font(48, bold=True)
    subtitle = font(22)
    badge_font = font(18, bold=True)
    tile_title = font(25, bold=True)
    metric_font = font(18, bold=True)
    body = font(16)
    small = font(14)
    footer_title = font(25, bold=True)
    footer_body = font(18)

    draw.text((margin, 40), "Best multi-person results from the full ComfyUI output archive", font=title, fill="#17202a")
    draw.text(
        (margin, 105),
        "1,229 usable images screened • 660 multi-person candidates • identity scored against four genuine references • final choice by visual review",
        font=subtitle,
        fill="#4e5964",
    )

    manifest_rows = []
    for index, item in enumerate(WINNERS):
        col = index % 2
        row = index // 2
        x = margin + col * (tile_w + gap)
        y = margin + header_h + row * (tile_h + gap)
        draw.rounded_rectangle(
            (x, y, x + tile_w, y + tile_h),
            radius=18,
            fill="#ffffff",
            outline="#cbc5ba",
            width=2,
        )
        badge_width = int(draw.textlength(item["badge"], font=badge_font)) + 34
        draw.rounded_rectangle((x + 22, y + 20, x + 22 + badge_width, y + 55), radius=10, fill="#1f6f5f")
        draw.text((x + 39, y + 26), item["badge"], font=badge_font, fill="#ffffff")
        draw.text((x + 22, y + 70), f"#{item['rank']}  {item['title']}", font=tile_title, fill="#182129")
        image = contain(COMFY_OUTPUT / item["relative_path"], preview_size)
        sheet.paste(image, (x + 22, y + 112))
        text_y = y + 112 + preview_size[1] + 14
        draw.text(
            (x + 22, text_y),
            f"Audit identity {item['identity']:.3f}   •   people {item['people']}   •   detected faces {item['faces']}",
            font=metric_font,
            fill="#1f6f5f",
        )
        text_y += 34
        draw.text((x + 22, text_y), "CREATED WITH", font=badge_font, fill="#182129")
        text_y = draw_wrapped(draw, (x + 22, text_y + 26), item["created"], body, "#39434c", tile_w - 44)
        text_y += 10
        draw.text((x + 22, text_y), "WHY IT MADE THE SHEET", font=badge_font, fill="#182129")
        text_y = draw_wrapped(draw, (x + 22, text_y + 26), item["review"], body, "#39434c", tile_w - 44)
        display_path = item["relative_path"].replace("\\", "/")
        draw.text((x + 22, y + tile_h - 30), display_path, font=small, fill="#7a7f84")
        manifest_rows.append({**item, "absolute_path": str(COMFY_OUTPUT / item["relative_path"])})

    footer_y = sheet_h - footer_h - margin + 20
    draw.rounded_rectangle(
        (margin, footer_y, sheet_w - margin, sheet_h - margin),
        radius=18,
        fill="#17202a",
    )
    left_x = margin + 32
    right_x = sheet_w // 2 + 12
    top_y = footer_y + 28
    draw.text((left_x, top_y), "WHAT ACTUALLY WORKED", font=footer_title, fill="#b9f0df")
    worked = [
        "FLUX.2 Klein Base 4B + the trained identity LoRA produced the most natural likeness.",
        "For dense crowds, use Klein 9B for the scene plate, then change only the chosen main face.",
        "Secondary people work best when small, off-axis, varied, and not arranged as a frontal row.",
    ]
    y = top_y + 42
    for text in worked:
        y = draw_wrapped(draw, (left_x, y), f"•  {text}", footer_body, "#f3f5f6", 780, 8) + 8

    draw.text((right_x, top_y), "WHAT DID NOT HOLD UP", font=footer_title, fill="#ffc9bf")
    failed = [
        "Untouched Klein 9B crowd generations: good scenes, weak Mitch identity.",
        "Complex café attempts with whole-subject regeneration: repeated cars/people and skin-spot artifacts.",
        "Repeated face-swap/restoration passes: sharper identity, but plastic skin and a pasted-face look.",
    ]
    y = top_y + 42
    for text in failed:
        y = draw_wrapped(draw, (right_x, y), f"•  {text}", footer_body, "#f3f5f6", 780, 8) + 8

    sheet_path = DESTINATION / "multiperson-best-of-sheet.png"
    sheet.save(sheet_path, compress_level=6)
    (DESTINATION / "multiperson-best-of.json").write_text(
        json.dumps(manifest_rows, indent=2), encoding="utf-8"
    )
    csv_path = DESTINATION / "multiperson-best-of.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0].keys()))
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(sheet_path)
    print(csv_path)


if __name__ == "__main__":
    main()
