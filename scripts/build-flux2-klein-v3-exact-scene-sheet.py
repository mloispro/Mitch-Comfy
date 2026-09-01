from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


COMFY_INPUT = Path(r"C:\projects\AI-Tools\ComfyUI\input")
OUTPUT_ROOT = Path(
    r"C:\projects\AI-Tools\ComfyUI\output\gpu-4070\flux2-generated-photo-identity-edit"
)
DESTINATION = Path(
    r"C:\projects\AI-Tools\Mitch-Comfy\work\exact-scene-klein-v3"
)
SCENES = [
    (1, "night out A", "mitch-workbench-dating-01-night-out-a.png"),
    (2, "night out B", "mitch-workbench-dating-02-night-out-b.png"),
    (3, "ragdoll cat", "mitch-workbench-dating-03-cat-ragdoll.png"),
    (4, "tabby cat", "mitch-workbench-dating-04-cat-tabby.png"),
    (5, "golfer", "mitch-workbench-dating-05-golfer-safe.png"),
    (6, "Amalfi", "mitch-workbench-dating-06-amalfi.png"),
    (7, "lake boat", "mitch-workbench-dating-07-lake-boat.png"),
    (8, "restaurant", "mitch-workbench-dating-08-restaurant.png"),
    (9, "night rooftop", "mitch-workbench-dating-09-night-city.png"),
]
PREFERRED_STRATEGIES = {
    1: "full_head_identity_lock",
    2: "full_head_identity_lock",
    3: "full_head_identity_lock",
    4: "full_head_identity_lock",
    5: "full_head_identity_lock",
    6: "full_head_identity_lock",
    7: "full_head_identity_lock",
    8: "full_head_identity_lock",
    9: "internal_face_geometry_lock",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def latest_report(source_name: str, strategy: str) -> tuple[Path, dict]:
    candidates = []
    for report_path in OUTPUT_ROOT.rglob("report.json"):
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if report.get("purpose") != "exact_supplied_scene_klein_v3_identity_lora":
            continue
        if abs(float(report.get("denoise_strength", -1)) - 0.65) > 1e-6:
            continue
        if report.get("mask_strategy") != strategy:
            continue
        if Path(report.get("scene_plate", "")).name != source_name:
            continue
        candidates.append((report_path.stat().st_mtime_ns, report_path, report))
    if not candidates:
        raise RuntimeError(
            f"No v3 exact-scene report found for {source_name} with {strategy}"
        )
    _, path, report = max(candidates, key=lambda item: item[0])
    return path, report


def outside_mask_metrics(source: Image.Image, output: Image.Image, mask: Image.Image) -> dict:
    source_rgb = np.asarray(source.convert("RGB"), dtype=np.int16)
    output_rgb = np.asarray(output.convert("RGB"), dtype=np.int16)
    mask_l = np.asarray(mask.convert("L"), dtype=np.uint8)
    outside = mask_l <= 1
    absolute = np.abs(output_rgb - source_rgb).astype(np.float32)
    outside_values = absolute[outside]
    return {
        "mean_absolute_rgb_delta_outside_transition": round(float(outside_values.mean()), 4),
        "p95_absolute_rgb_delta_outside_transition": round(
            float(np.percentile(outside_values, 95)), 4
        ),
        "fraction_outside_pixels_over_8_levels": round(
            float(np.mean(np.max(absolute, axis=2)[outside] > 8)), 6
        ),
        "transition_mask_area_fraction": round(float(np.mean(mask_l > 1)), 6),
    }


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    contained = ImageOps.contain(image.convert("RGB"), size, Image.Resampling.LANCZOS)
    tile = Image.new("RGB", size, (18, 18, 20))
    tile.paste(
        contained,
        ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2),
    )
    return tile


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    rows = []
    selected = []
    selected_directory = DESTINATION / "selected"
    selected_directory.mkdir(parents=True, exist_ok=True)
    for number, label, source_name in SCENES:
        strategy = PREFERRED_STRATEGIES[number]
        report_path, report = latest_report(source_name, strategy)
        folder = report_path.parent
        source_path = COMFY_INPUT / source_name
        output_path = folder / "final_00001_.png"
        mask_path = folder / "transition-mask_00001_.png"
        with Image.open(source_path) as source_image, Image.open(output_path) as output_image, Image.open(
            mask_path
        ) as mask_image:
            preservation = outside_mask_metrics(source_image, output_image, mask_image)
        identity = report["identity"]
        selected_path = selected_directory / f"{number:02d}-{label.replace(' ', '-')}.png"
        shutil.copy2(output_path, selected_path)
        row = {
            "scene": number,
            "label": label,
            "source": str(source_path),
            "output": str(output_path),
            "selected_output": str(selected_path),
            "report": str(report_path),
            "edit_strategy": strategy,
            "identity_similarity": float(identity["main_identity_similarity"]),
            "identity_status": identity["status"],
            "detected_faces": int(identity["detected_face_count"]),
            "maximum_secondary_identity_similarity": float(
                identity["maximum_secondary_identity_similarity"]
            ),
            "target_face_index_left_to_right": int(
                report["target_face_index_left_to_right"]
            ),
            "face_geometry": report["face_geometry"]["status"],
            "head_integrity": report["head_integrity"]["status"],
            "acceptance": report["acceptance"]["status"],
            "acceptance_failures": report["acceptance"]["failures"],
            "preservation": preservation,
        }
        rows.append(row)
        selected.append((row, source_path, selected_path))

    tile_w, tile_h = 282, 412
    cell_w, cell_h = tile_w * 2 + 28, tile_h + 92
    margin, gap = 26, 20
    canvas = Image.new(
        "RGB",
        (margin * 2 + cell_w * 3 + gap * 2, margin * 2 + cell_h * 3 + gap * 2),
        (12, 13, 16),
    )
    draw = ImageDraw.Draw(canvas)
    title_font = font(23, bold=True)
    small_font = font(17)
    label_font = font(18, bold=True)
    for index, (row, source_path, output_path) in enumerate(selected):
        col, grid_row = index % 3, index // 3
        x = margin + col * (cell_w + gap)
        y = margin + grid_row * (cell_h + gap)
        with Image.open(source_path) as source, Image.open(output_path) as output:
            canvas.paste(fit(source, (tile_w, tile_h)), (x, y + 58))
            canvas.paste(fit(output, (tile_w, tile_h)), (x + tile_w + 8, y + 58))
        draw.text((x, y), f"{row['scene']:02d}  {row['label']}", font=title_font, fill=(245, 245, 247))
        secondary = row["maximum_secondary_identity_similarity"]
        suffix = f" · secondary max {secondary:.3f}" if secondary >= 0 else ""
        draw.text(
            (x, y + 30),
            f"identity {row['identity_similarity']:.3f}{suffix}",
            font=small_font,
            fill=(173, 207, 255),
        )
        draw.text((x + 6, y + 62), "SOURCE", font=label_font, fill=(255, 216, 125))
        draw.text(
            (x + tile_w + 14, y + 62), "V3 LoRA", font=label_font, fill=(131, 229, 177)
        )

    sheet_path = DESTINATION / "source-vs-flux2-klein-v3-exact-scenes.png"
    canvas.save(sheet_path, format="PNG", compress_level=6)
    verification = {
        "schema_version": 1,
        "method": "FLUX.2 Klein Base 4B + v3 identity LoRA + indexed internal-face latent editing",
        "lora": r"aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors",
        "lora_sha256": "c43d7c1fca404a8b316a9d0c8756e140033e4763532628f62facc791f0b8a149",
        "gpu": "NVIDIA GeForce RTX 4070",
        "settings": {"lora_strength": 1.2, "denoise_strength": 0.65, "steps": 20},
        "contact_sheet": str(sheet_path),
        "scenes": rows,
    }
    verification_path = DESTINATION / "verification.json"
    verification_path.write_text(json.dumps(verification, indent=2), encoding="utf-8")
    print(f"SHEET={sheet_path}")
    print(f"VERIFICATION={verification_path}")


if __name__ == "__main__":
    main()
