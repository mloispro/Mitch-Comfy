from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_ROOT = REPO_ROOT / "custom_nodes" / "ComfyUI-AIToolkit-Training"
sys.path.insert(0, str(NODE_ROOT))

from identity_leakage import evaluate_identity_scope  # noqa: E402


VALIDATION_ROOT = REPO_ROOT / "datasets" / "mitch-identity-stills-v3" / "validation"
REFERENCE_PAIRWISE_FLOOR = 0.5533
NEAR_CENTROID_MINIMUM = REFERENCE_PAIRWISE_FLOOR - 0.08
EXPECTED_SCENES = (1, 2, 9)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the source/0.9/1.1 review sheet for the targeted Klein 9B v2 tests."
    )
    parser.add_argument("manifest_090", type=Path)
    parser.add_argument("manifest_110", type=Path)
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / filename), size=size)


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    contained = ImageOps.contain(image.convert("RGB"), size, Image.Resampling.LANCZOS)
    tile = Image.new("RGB", size, (18, 18, 20))
    tile.paste(contained, ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2))
    return tile


def load_faces(analyzer, path: Path):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def load_manifest(path: Path, expected_strength: float) -> dict:
    manifest = json.loads(path.resolve().read_text(encoding="utf-8-sig"))
    if manifest.get("method") != "FLUX.2 Klein Base 9B LoRA-only text-to-image; source scenes shown only for comparison":
        raise RuntimeError(f"Unexpected method in {path}")
    for key in ("source_scene_conditioning", "reference_conditioning", "identity_pass", "face_swap", "restoration"):
        if manifest.get(key) is not False:
            raise RuntimeError(f"{key} must be false in {path}")
    if abs(float(manifest["lora_strength"]) - expected_strength) > 1e-6:
        raise RuntimeError(f"Expected strength {expected_strength:.1f} in {path}")
    scenes = manifest.get("scenes", [])
    if tuple(int(scene["scene"]) for scene in scenes) != EXPECTED_SCENES:
        raise RuntimeError(f"Expected scenes {EXPECTED_SCENES} in {path}")
    return manifest


def reference_centroid(analyzer) -> tuple[np.ndarray, list[str]]:
    paths = sorted(VALIDATION_ROOT.glob("*.jpg"))
    if len(paths) != 6:
        raise RuntimeError(f"Expected six held-out genuine references, found {len(paths)}")
    embeddings = []
    for path in paths:
        faces = load_faces(analyzer, path)
        if not faces:
            raise RuntimeError(f"No face detected in held-out reference: {path}")
        face = max(faces, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
        embeddings.append(np.asarray(face.normed_embedding, dtype=np.float32))
    centroid = np.mean(np.stack(embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)
    return centroid, [str(path) for path in paths]


def evaluate(analyzer, centroid: np.ndarray, path: Path) -> dict:
    faces = load_faces(analyzer, path)
    if not faces:
        return {
            "status": "rejected",
            "detected_face_count": 0,
            "main_identity_similarity": -1.0,
            "maximum_secondary_identity_similarity": -1.0,
            "failures": ["no_detected_face"],
        }
    report = evaluate_identity_scope(
        [np.asarray(face.normed_embedding, dtype=np.float32) for face in faces],
        [face.bbox for face in faces],
        [float(face.det_score) for face in faces],
        centroid,
        NEAR_CENTROID_MINIMUM,
    ).as_dict()
    return report


def failure_label(report: dict) -> str:
    failures = report.get("failures", [])
    if "identity_leaked_to_secondary_face" in failures:
        return "FAIL: Mitch leaked to bystander"
    if "secondary_face_too_similar_to_main" in failures:
        return "FAIL: bystander resembles Mitch"
    if "main_identity_below_threshold" in failures:
        return "FAIL: main identity below near"
    if failures:
        return "FAIL: " + str(failures[0]).replace("_", " ")
    return "PASS: identity/leakage diagnostic"


def main() -> None:
    args = parse_args()
    manifest_090 = load_manifest(args.manifest_090, 0.9)
    manifest_110 = load_manifest(args.manifest_110, 1.1)
    if manifest_090["lora"] != manifest_110["lora"]:
        raise RuntimeError("The two manifests must use the same LoRA checkpoint.")

    from insightface.app import FaceAnalysis

    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(Path.home() / ".insightface"),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    centroid, reference_paths = reference_centroid(analyzer)

    by_scene_090 = {int(scene["scene"]): scene for scene in manifest_090["scenes"]}
    by_scene_110 = {int(scene["scene"]): scene for scene in manifest_110["scenes"]}
    rows = []
    for scene_number in EXPECTED_SCENES:
        left = by_scene_090[scene_number]
        right = by_scene_110[scene_number]
        if Path(left["source"]).resolve() != Path(right["source"]).resolve():
            raise RuntimeError(f"Source mismatch for scene {scene_number}")
        eval_090 = evaluate(analyzer, centroid, Path(left["selected_output"]))
        eval_110 = evaluate(analyzer, centroid, Path(right["selected_output"]))
        rows.append(
            {
                "scene": scene_number,
                "label": left["label"],
                "source": left["source"],
                "strength_090": {**left, "identity_diagnostic": eval_090},
                "strength_110": {**right, "identity_diagnostic": eval_110},
            }
        )

    tile_w, tile_h = 300, 438
    gap, margin, header_h = 18, 24, 76
    label_h = 88
    canvas_w = margin * 2 + tile_w * 3 + gap * 2
    canvas_h = header_h + margin + len(rows) * (label_h + tile_h + gap) - gap + margin
    canvas = Image.new("RGB", (canvas_w, canvas_h), (12, 13, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 12), "FLUX.2 KLEIN BASE 9B — AI-TOOLKIT RANK-32 LORA STRENGTH CHECK", font=font(20, True), fill=(239, 240, 244))
    draw.text((margin, 42), "Source pixels are comparison targets only · no reference conditioning or identity pass", font=font(15), fill=(177, 185, 201))

    for index, row in enumerate(rows):
        y = header_h + margin + index * (label_h + tile_h + gap)
        draw.text((margin, y), f"{row['scene']:02d}  {row['label']}", font=font(23, True), fill=(245, 245, 247))
        source_path = Path(row["source"])
        variants = [
            ("SOURCE", source_path, None, (255, 216, 125)),
            ("LORA 0.90", Path(row["strength_090"]["selected_output"]), row["strength_090"], (151, 198, 255)),
            ("LORA 1.10", Path(row["strength_110"]["selected_output"]), row["strength_110"], (190, 151, 255)),
        ]
        for col, (label, path, variant, color) in enumerate(variants):
            x = margin + col * (tile_w + gap)
            draw.text((x, y + 34), label, font=font(17, True), fill=color)
            if variant is not None:
                report = variant["identity_diagnostic"]
                score = float(report["main_identity_similarity"])
                secondary = float(report["maximum_secondary_identity_similarity"])
                detail = f"main {score:.3f} · secondary {secondary:.3f} · {float(variant['seconds']):.0f}s"
                draw.text((x, y + 57), detail, font=font(13), fill=(191, 197, 211))
            with Image.open(path) as image:
                canvas.paste(fit(image, (tile_w, tile_h)), (x, y + label_h))
            if variant is not None:
                report = variant["identity_diagnostic"]
                status_color = (120, 220, 155) if not report.get("failures") else (255, 126, 126)
                draw.rectangle((x, y + label_h + tile_h - 27, x + tile_w, y + label_h + tile_h), fill=(10, 11, 14))
                draw.text((x + 7, y + label_h + tile_h - 23), failure_label(report), font=font(12, True), fill=status_color)

    output_dir = args.manifest_090.resolve().parent.parent / "strength-comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = output_dir / "source-vs-step1200-strengths-0.90-1.10.png"
    preview_path = output_dir / "source-vs-step1200-strengths-0.90-1.10-preview.jpg"
    evaluation_path = output_dir / "evaluation.json"
    canvas.save(sheet_path, format="PNG", compress_level=6)
    preview = canvas.copy()
    preview.thumbnail((1000, 1600), Image.Resampling.LANCZOS)
    preview.save(preview_path, format="JPEG", quality=84, optimize=True, progressive=True)
    evaluation = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "lora": manifest_090["lora"],
        "method": manifest_090["method"],
        "source_scene_conditioning": False,
        "reference_conditioning": False,
        "identity_pass": False,
        "held_out_genuine_identity_references": reference_paths,
        "near_centroid_minimum": NEAR_CENTROID_MINIMUM,
        "manifest_090": str(args.manifest_090.resolve()),
        "manifest_110": str(args.manifest_110.resolve()),
        "contact_sheet": str(sheet_path),
        "contact_sheet_preview": str(preview_path),
        "scenes": rows,
        "manual_full_size_and_thumbnail_review_required": True,
        "published": False,
    }
    evaluation_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    print(f"SHEET={sheet_path}")
    print(f"PREVIEW={preview_path}")
    print(f"EVALUATION={evaluation_path}")


if __name__ == "__main__":
    main()
