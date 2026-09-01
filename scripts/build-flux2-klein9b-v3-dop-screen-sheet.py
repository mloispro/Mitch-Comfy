from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a visual Klein 9B LoRA checkpoint screen.")
    parser.add_argument("summary", type=Path)
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / filename), size=size)


def fit(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.contain(source.convert("RGB"), size, Image.Resampling.LANCZOS)
    tile = Image.new("RGB", size, (20, 21, 25))
    tile.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return tile


def coarse_sheet(summary: dict, summary_path: Path) -> tuple[Path, Path]:
    rows = sorted(summary["results"], key=lambda item: int(item["rank"]))
    first_outputs = set(rows[0]["outputs"]) if rows else set()
    if {"profile-image-left", "profile-image-right"}.issubset(first_outputs):
        view_keys = ("portrait", "profile-image-left", "profile-image-right")
        view_labels = ("PORTRAIT", "DOWN-LEFT ROOFTOP", "IMAGE-RIGHT PROFILE")
        tile = (168, 246)
        cell_w, cell_h = 536, 356
    else:
        view_keys = ("portrait", "near-profile-candid")
        view_labels = ("PORTRAIT", "DOWN-LEFT PROFILE")
        tile = (246, 360)
        cell_w, cell_h = 520, 470
    margin, gap, header = 24, 18, 78
    grid_rows = (len(rows) + 2) // 3
    canvas = Image.new(
        "RGB",
        (
            margin * 2 + cell_w * 3 + gap * 2,
            header + margin * 2 + cell_h * grid_rows + gap * (grid_rows - 1),
        ),
        (12, 13, 16),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 12), "KLEIN BASE 9B — AI-TOOLKIT DOP CHECKPOINT SCREEN", font=font(23, True), fill=(240, 241, 245))
    draw.text((margin, 44), "Held-out genuine references score identity; images use LoRA-only text-to-image", font=font(15), fill=(174, 185, 205))
    for index, row in enumerate(rows):
        grid_y, grid_x = divmod(index, 3)
        x = margin + grid_x * (cell_w + gap)
        y = header + margin + grid_y * (cell_h + gap)
        title = f"#{int(row['rank'])}  step {int(row['step'])}  strength {float(row['strength']):.2f}"
        draw.text((x, y), title, font=font(20, True), fill=(240, 240, 245))
        metrics = (
            f"avg {float(row['average_centroid_similarity']):.3f} · min {float(row['minimum_centroid_similarity']):.3f}"
            f" · strong {int(row['strong_count'])} · near {int(row['near_count'])}"
        )
        draw.text((x, y + 28), metrics, font=font(13), fill=(164, 203, 255))
        outputs = row["outputs"]
        for col, (key, label) in enumerate(zip(view_keys, view_labels, strict=True)):
            px = x + col * (tile[0] + 8)
            draw.text((px, y + 51), label, font=font(11, True), fill=(203, 184, 255))
            canvas.paste(fit(Path(outputs[key]), tile), (px, y + 72))
    sheet = summary_path.parent / "coarse-screen-sheet.png"
    preview = summary_path.parent / "coarse-screen-sheet-preview.jpg"
    canvas.save(sheet, format="PNG", compress_level=6)
    thumb = canvas.copy()
    thumb.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    thumb.save(preview, format="JPEG", quality=84, optimize=True, progressive=True)
    return sheet, preview


def full_sheet(summary: dict, summary_path: Path) -> tuple[Path, Path]:
    rows = sorted(summary["results"], key=lambda item: int(item["rank"]))
    first_outputs = set(rows[0]["outputs"]) if rows else set()
    if {"profile-image-left", "profile-image-right"}.issubset(first_outputs):
        keys = (
            "portrait",
            "waist-up-social",
            "profile-image-left",
            "profile-image-right",
            "full-body-walking",
            "crowd",
        )
        labels = ("PORTRAIT", "SOCIAL", "LEFT PROFILE", "RIGHT PROFILE", "FULL BODY", "GROUP")
        tile = (164, 240)
    else:
        keys = ("portrait", "waist-up-social", "near-profile-candid", "full-body-walking", "crowd")
        labels = ("PORTRAIT", "SOCIAL", "PROFILE", "FULL BODY", "GROUP")
        tile = (190, 278)
    margin, gap, header, row_label = 22, 8, 82, 70
    width = margin * 2 + tile[0] * len(keys) + gap * (len(keys) - 1)
    row_h = row_label + tile[1] + 18
    canvas = Image.new("RGB", (width, header + margin * 2 + row_h * len(rows)), (12, 13, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 12), "KLEIN BASE 9B — TOP CHECKPOINTS × LORA STRENGTH", font=font(22, True), fill=(240, 241, 245))
    draw.text((margin, 44), "Intended group subject must pass identity and every bystander must remain distinct", font=font(14), fill=(174, 185, 205))
    for index, row in enumerate(rows):
        y = header + margin + index * row_h
        passed = bool(row["automatic_gates_passed"])
        color = (118, 224, 155) if passed else (255, 134, 134)
        title = f"#{int(row['rank'])}  step {int(row['step'])}  strength {float(row['strength']):.2f}  {'AUTO PASS' if passed else 'AUTO FAIL'}"
        draw.text((margin, y), title, font=font(18, True), fill=color)
        metrics = (
            f"core strong {int(row['core_strong_match_count'])} · group centroid {float(row['crowd_main_centroid_similarity']):.3f}"
            f" · group mean {float(row['crowd_main_mean_reference_similarity']):.3f} · full-body {row['full_body_status']}"
        )
        draw.text((margin, y + 27), metrics, font=font(13), fill=(164, 203, 255))
        for col, (key, label) in enumerate(zip(keys, labels, strict=True)):
            x = margin + col * (tile[0] + gap)
            draw.text((x, y + 49), label, font=font(12, True), fill=(203, 184, 255))
            canvas.paste(fit(Path(row["outputs"][key]), tile), (x, y + row_label))
    sheet = summary_path.parent / "full-screen-sheet.png"
    preview = summary_path.parent / "full-screen-sheet-preview.jpg"
    canvas.save(sheet, format="PNG", compress_level=6)
    thumb = canvas.copy()
    thumb.thumbnail((1000, 1600), Image.Resampling.LANCZOS)
    thumb.save(preview, format="JPEG", quality=84, optimize=True, progressive=True)
    return sheet, preview


def main() -> None:
    args = parse_args()
    summary_path = args.summary.resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    count = len(summary.get("results", []))
    output_keys = set(summary["results"][0].get("outputs", {})) if count else set()
    if {"full-body-walking", "crowd"}.issubset(output_keys):
        sheet, preview = full_sheet(summary, summary_path)
    elif count >= 1 and (
        {"portrait", "near-profile-candid"}.issubset(output_keys)
        or {"portrait", "profile-image-left", "profile-image-right"}.issubset(output_keys)
    ):
        sheet, preview = coarse_sheet(summary, summary_path)
    else:
        raise RuntimeError(f"Could not classify screen with {count} results and outputs {sorted(output_keys)}")
    summary["contact_sheet"] = str(sheet)
    summary["contact_sheet_preview"] = str(preview)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"SHEET={sheet}")
    print(f"PREVIEW={preview}")


if __name__ == "__main__":
    main()
