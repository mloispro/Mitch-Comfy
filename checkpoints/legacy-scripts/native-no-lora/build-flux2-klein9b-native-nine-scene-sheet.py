from __future__ import annotations

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


def load_faces(analyzer, path: Path):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def build_reference_centroid(analyzer) -> tuple[np.ndarray, list[str]]:
    reference_paths = sorted(VALIDATION_ROOT.glob("*.jpg"))
    if len(reference_paths) != 6:
        raise RuntimeError(
            f"Expected exactly six held-out genuine references, found {len(reference_paths)}"
        )
    embeddings = []
    for path in reference_paths:
        faces = load_faces(analyzer, path)
        if not faces:
            raise RuntimeError(f"No face detected in held-out reference: {path}")
        face = max(
            faces,
            key=lambda item: float(
                (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
            ),
        )
        embeddings.append(np.asarray(face.normed_embedding, dtype=np.float32))
    centroid = np.mean(np.stack(embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)
    return centroid, [str(path) for path in reference_paths]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: build-flux2-klein9b-native-nine-scene-sheet.py MANIFEST.json")
    manifest_path = Path(sys.argv[1]).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    scenes = manifest.get("scenes", [])
    if len(scenes) != 9:
        raise RuntimeError(f"Expected nine scenes in manifest, found {len(scenes)}")
    if manifest.get("source_scene_conditioning") is not False:
        raise RuntimeError("The comparison must explicitly record that source pixels were not conditioned.")

    from insightface.app import FaceAnalysis

    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(Path.home() / ".insightface"),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    centroid, reference_paths = build_reference_centroid(analyzer)

    evaluated = []
    for scene in scenes:
        source_path = Path(scene["source"])
        output_path = Path(scene["selected_output"])
        if not source_path.is_file() or not output_path.is_file():
            raise FileNotFoundError(f"Missing comparison pair: {source_path} / {output_path}")
        faces = load_faces(analyzer, output_path)
        if faces:
            identity = evaluate_identity_scope(
                [np.asarray(face.normed_embedding, dtype=np.float32) for face in faces],
                [face.bbox for face in faces],
                [float(face.det_score) for face in faces],
                centroid,
                0.75,
            ).as_dict()
        else:
            identity = {
                "main_identity_similarity": -1.0,
                "maximum_secondary_identity_similarity": -1.0,
                "maximum_secondary_pair_similarity": -1.0,
                "detected_face_count": 0,
                "status": "no_face",
            }
        evaluated.append(
            {
                **scene,
                "identity_similarity": float(identity["main_identity_similarity"]),
                "maximum_secondary_identity_similarity": float(
                    identity["maximum_secondary_identity_similarity"]
                ),
                "maximum_secondary_pair_similarity": float(
                    identity["maximum_secondary_pair_similarity"]
                ),
                "detected_faces": int(identity["detected_face_count"]),
                "identity_diagnostic": identity,
            }
        )

    tile_w, tile_h = 282, 412
    cell_w, cell_h = tile_w * 2 + 28, tile_h + 98
    margin, gap, header_h = 26, 20, 58
    canvas = Image.new(
        "RGB",
        (
            margin * 2 + cell_w * 3 + gap * 2,
            header_h + margin * 2 + cell_h * 3 + gap * 2,
        ),
        (12, 13, 16),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (margin, 15),
        "KLEIN 9B NATIVE 4-REFERENCE — source scenes shown as targets, not supplied as input",
        font=font(21, bold=True),
        fill=(232, 234, 240),
    )
    title_font = font(23, bold=True)
    small_font = font(16)
    label_font = font(18, bold=True)
    for index, row in enumerate(evaluated):
        col, grid_row = index % 3, index // 3
        x = margin + col * (cell_w + gap)
        y = header_h + margin + grid_row * (cell_h + gap)
        source_path = Path(row["source"])
        output_path = Path(row["selected_output"])
        with Image.open(source_path) as source, Image.open(output_path) as output:
            canvas.paste(fit(source, (tile_w, tile_h)), (x, y + 64))
            canvas.paste(fit(output, (tile_w, tile_h)), (x + tile_w + 8, y + 64))
        draw.text(
            (x, y),
            f"{int(row['scene']):02d}  {row['label']}",
            font=title_font,
            fill=(245, 245, 247),
        )
        secondary = row["maximum_secondary_identity_similarity"]
        suffix = f" · secondary {secondary:.3f}" if secondary >= 0 else ""
        score = row["identity_similarity"]
        score_text = "no face detected" if score < 0 else f"identity {score:.3f}{suffix}"
        draw.text((x, y + 32), score_text, font=small_font, fill=(173, 207, 255))
        draw.text((x + 6, y + 68), "SOURCE", font=label_font, fill=(255, 216, 125))
        draw.text(
            (x + tile_w + 14, y + 68),
            "KLEIN 9B 4-REF",
            font=label_font,
            fill=(117, 218, 196),
        )

    sheet_path = manifest_path.parent / "source-vs-flux2-klein9b-native-4ref.png"
    canvas.save(sheet_path, format="PNG", compress_level=6)
    evaluation = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "method": manifest["method"],
        "source_scene_conditioning": False,
        "held_out_genuine_identity_references": reference_paths,
        "contact_sheet": str(sheet_path),
        "scenes": evaluated,
    }
    evaluation_path = manifest_path.parent / "evaluation.json"
    evaluation_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    print(f"SHEET={sheet_path}")
    print(f"EVALUATION={evaluation_path}")


if __name__ == "__main__":
    main()
