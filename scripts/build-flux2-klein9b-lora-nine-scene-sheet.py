from __future__ import annotations

import json
import hashlib
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


LEGACY_VALIDATION_ROOT = REPO_ROOT / "datasets" / "mitch-identity-stills-v3" / "validation"
MANUAL_SCENE_GATES = {
    1: ["exactly four adults", "exactly one Mitch", "foreground seated Mitch matches source composition", "no duplicated face or missing limb"],
    2: ["exactly five visible adult faces including left-edge partial", "exactly one central Mitch", "all bystanders distinct", "coherent hands and arms"],
    3: ["one person", "two complete arms supporting the Ragdoll cat", "coherent hands and cat paws", "head looks down toward image-right with no eye contact"],
    4: ["one person", "two complete arms and both hands holding the tabby", "coherent cat anatomy", "head looks down toward image-right"],
    5: ["one person", "entire body from head through both shoes", "two complete arms and hands", "one club in right hand and white glove on left"],
    6: ["one person", "complete railing hand", "waist-up source-like framing", "consistent face shape and apparent age"],
    7: ["one person", "two complete extended arms", "both hands rest on boat rails", "coherent seated body proportions"],
    8: ["one person", "right hand supports chin", "both arms and hands coherent", "source-like restaurant framing"],
    9: ["one person", "two complete arms and both hands on railing", "head and eyes point down-left toward image-left", "no direct eye contact", "never turns toward image-right"],
}
EXPECTED_FACE_COUNTS = {1: 4, 2: 5, **{scene: 1 for scene in range(3, 10)}}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    contained = ImageOps.contain(image.convert("RGB"), size, Image.Resampling.LANCZOS)
    tile = Image.new("RGB", size, (18, 18, 20))
    tile.paste(contained, ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2))
    return tile


def face_crop(image: Image.Image, bbox, size: tuple[int, int]) -> Image.Image:
    if bbox is None:
        tile = Image.new("RGB", size, (27, 28, 33))
        draw = ImageDraw.Draw(tile)
        draw.text((12, size[1] // 2 - 8), "NO FACE", font=font(15, True), fill=(255, 135, 135))
        return tile
    x1, y1, x2, y2 = (float(value) for value in bbox)
    center_x, center_y = (x1 + x2) * 0.5, (y1 + y2) * 0.5
    side = max(x2 - x1, y2 - y1) * 2.0
    left = max(int(center_x - side * 0.5), 0)
    top = max(int(center_y - side * 0.52), 0)
    right = min(int(center_x + side * 0.5), image.width)
    bottom = min(int(center_y + side * 0.48), image.height)
    return fit(image.crop((left, top, right, bottom)), size)


def load_faces(analyzer, path: Path):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image for face analysis: {path}")
    return analyzer.get(image)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def resolve_reference_paths(manifest: dict) -> list[Path]:
    declared = manifest.get("held_out_genuine_identity_references")
    if declared is None:
        reference_paths = sorted(LEGACY_VALIDATION_ROOT.glob("*.jpg"))
        if len(reference_paths) != 6:
            raise RuntimeError(
                f"Expected six legacy held-out genuine references, found {len(reference_paths)}"
            )
        return reference_paths
    if not isinstance(declared, list) or len(declared) < 2:
        raise RuntimeError("Manifest must declare at least two held-out genuine references.")
    reference_paths: list[Path] = []
    for item in declared:
        if isinstance(item, str):
            path = Path(item).resolve()
            expected_hash = None
        elif isinstance(item, dict) and item.get("path"):
            path = Path(str(item["path"])).resolve()
            expected_hash = str(item.get("sha256", "")).upper() or None
        else:
            raise RuntimeError(f"Invalid held-out reference record: {item!r}")
        if not path.is_file():
            raise FileNotFoundError(f"Held-out reference is missing: {path}")
        if expected_hash is not None and sha256(path) != expected_hash:
            raise RuntimeError(f"Held-out reference hash changed: {path}")
        reference_paths.append(path)
    if len(set(reference_paths)) != len(reference_paths):
        raise RuntimeError("Manifest contains duplicate held-out reference paths.")
    return reference_paths


def build_reference_centroid(
    analyzer, manifest: dict
) -> tuple[np.ndarray, list[np.ndarray], list[str], dict[str, float]]:
    reference_paths = resolve_reference_paths(manifest)
    embeddings = []
    for path in reference_paths:
        faces = load_faces(analyzer, path)
        if not faces:
            raise RuntimeError(f"No face detected in held-out reference: {path}")
        face = max(faces, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
        embedding = np.asarray(face.normed_embedding, dtype=np.float32)
        embedding /= max(float(np.linalg.norm(embedding)), 1e-8)
        embeddings.append(embedding)
    centroid = np.mean(np.stack(embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)
    pairwise = [
        float(np.dot(embeddings[left], embeddings[right]))
        for left in range(len(embeddings))
        for right in range(left + 1, len(embeddings))
    ]
    pairwise_floor = float(min(pairwise))
    pairwise_mean = float(np.mean(pairwise))
    calibration = {
        "reference_pairwise_floor": pairwise_floor,
        "reference_pairwise_mean": pairwise_mean,
        "near_centroid_minimum": pairwise_floor - 0.08,
        "strong_centroid_minimum": pairwise_floor - 0.02,
        "near_mean_reference_minimum": pairwise_floor - 0.13,
        "strong_mean_reference_minimum": pairwise_floor - 0.05,
    }
    return centroid, embeddings, [str(path) for path in reference_paths], calibration


def identity_status(centroid_score: float, mean_score: float, calibration: dict[str, float]) -> str:
    if (
        centroid_score >= calibration["strong_centroid_minimum"]
        and mean_score >= calibration["strong_mean_reference_minimum"]
    ):
        return "strong"
    if (
        centroid_score >= calibration["near_centroid_minimum"]
        and mean_score >= calibration["near_mean_reference_minimum"]
    ):
        return "near"
    return "drift"


def intended_main_face_index(faces, image_size: tuple[int, int], scene_number: int) -> tuple[int, str]:
    """Select the prompted subject by scene role, never by identity similarity."""
    if not faces:
        raise ValueError("At least one face is required")
    if scene_number in (1, 2):
        width, height = image_size
        anchor_x, anchor_y = {
            1: (0.50, 0.44),  # foreground man seated diagonally on the sofa
            2: (0.50, 0.40),  # central seated man leaning toward the camera
        }[scene_number]
        scored = []
        for index, face in enumerate(faces):
            x1, y1, x2, y2 = (float(value) for value in face.bbox)
            center_x = ((x1 + x2) * 0.5) / width
            center_y = ((y1 + y2) * 0.5) / height
            area = max((x2 - x1) * (y2 - y1), 0.0) / max(width * height, 1)
            distance = (center_x - anchor_x) ** 2 + (center_y - anchor_y) ** 2
            scored.append((distance - 0.05 * area, index))
        return min(scored)[1], "prompted_center_foreground_anchor"
    areas = [
        float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]))
        for face in faces
    ]
    return int(np.argmax(np.asarray(areas))), "largest_face_single_subject_scene"


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit(
            "Usage: build-flux2-klein9b-lora-nine-scene-sheet.py MANIFEST.json [NEW_OUTPUT_DIRECTORY]"
        )
    manifest_path = Path(sys.argv[1]).resolve()
    if len(sys.argv) == 3:
        output_root = Path(sys.argv[2]).resolve()
        if output_root.exists():
            raise FileExistsError(f"Refusing to overwrite an existing evaluation directory: {output_root}")
        output_root.mkdir(parents=True)
    else:
        output_root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    scenes = manifest.get("scenes", [])
    scene_numbers = [int(scene["scene"]) for scene in scenes]
    declared_subset = manifest.get("evaluation_scene_numbers")
    if len(scenes) == 9:
        if sorted(scene_numbers) != list(range(1, 10)) or len(set(scene_numbers)) != 9:
            raise RuntimeError(f"A complete review must contain scenes 1-9 exactly once; found {scene_numbers}")
        evaluation_scope = "complete_nine_scene_review"
    else:
        if not isinstance(declared_subset, list) or not declared_subset:
            raise RuntimeError(
                f"Expected nine scenes, found {len(scenes)} without an explicit evaluation_scene_numbers subset"
            )
        declared_numbers = [int(value) for value in declared_subset]
        if scene_numbers != declared_numbers:
            raise RuntimeError(
                f"Manifest scenes {scene_numbers} do not exactly match declared subset {declared_numbers}"
            )
        if len(set(scene_numbers)) != len(scene_numbers) or any(value not in EXPECTED_FACE_COUNTS for value in scene_numbers):
            raise RuntimeError(f"Invalid or duplicate scene number in explicit subset: {scene_numbers}")
        evaluation_scope = "explicit_scene_subset"
    if manifest.get("source_scene_conditioning") is not False:
        raise RuntimeError("Source scene pixels must not be conditioning.")
    reference_conditioning = manifest.get("reference_conditioning")
    if reference_conditioning not in (False, True):
        raise RuntimeError("Manifest must explicitly declare reference_conditioning true or false.")

    from insightface.app import FaceAnalysis

    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(Path.home() / ".insightface"),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    centroid, reference_embeddings, reference_paths, calibration = build_reference_centroid(
        analyzer, manifest
    )

    evaluated = []
    for scene in scenes:
        scene_number = int(scene["scene"])
        expected_face_count = EXPECTED_FACE_COUNTS[scene_number]
        source_path = Path(scene.get("source") or scene.get("source_comparison", ""))
        output_path = Path(scene["selected_output"])
        if not source_path.is_file() or not output_path.is_file():
            raise FileNotFoundError(f"Missing comparison pair: {source_path} / {output_path}")
        with Image.open(output_path) as output_image:
            image_size = output_image.size
        faces = load_faces(analyzer, output_path)
        if faces:
            main_index, selection_method = intended_main_face_index(
                faces, image_size, scene_number
            )
            identity = evaluate_identity_scope(
                [np.asarray(face.normed_embedding, dtype=np.float32) for face in faces],
                [face.bbox for face in faces],
                [float(face.det_score) for face in faces],
                centroid,
                calibration["near_centroid_minimum"],
                preferred_main_index=main_index,
            ).as_dict()
            main_score = float(identity["main_identity_similarity"])
            main_embedding = np.asarray(faces[main_index].normed_embedding, dtype=np.float32)
            main_embedding /= max(float(np.linalg.norm(main_embedding)), 1e-8)
            per_reference = [float(np.dot(main_embedding, item)) for item in reference_embeddings]
            mean_score = float(np.mean(per_reference))
            if (
                mean_score < calibration["near_mean_reference_minimum"]
                and "main_identity_mean_below_threshold" not in identity["failures"]
            ):
                identity["failures"].append("main_identity_mean_below_threshold")
                identity["status"] = "rejected"
        else:
            main_score = -1.0
            mean_score = -1.0
            per_reference = []
            selection_method = "none"
            identity = {
                "main_identity_similarity": -1.0,
                "maximum_secondary_identity_similarity": -1.0,
                "maximum_secondary_pair_similarity": -1.0,
                "detected_face_count": 0,
                "status": "no_face",
                "failures": ["no_detected_face"],
                "faces": [],
            }
        face_count_passed = len(faces) == expected_face_count
        if not face_count_passed:
            identity["failures"].append("unexpected_scene_face_count")
            identity["status"] = "rejected"
        normalized_scene = {**scene, "source": str(source_path)}
        evaluated.append(
            {
                **normalized_scene,
                "manual_scene_gates": MANUAL_SCENE_GATES[scene_number],
                "identity_similarity": main_score,
                "identity_mean_reference_similarity": mean_score,
                "identity_per_reference_similarity": per_reference,
                "identity_status": identity_status(main_score, mean_score, calibration)
                if main_score >= 0
                else "no face",
                "intended_main_selection_method": selection_method,
                "maximum_secondary_identity_similarity": float(identity["maximum_secondary_identity_similarity"]),
                "maximum_secondary_pair_similarity": float(identity["maximum_secondary_pair_similarity"]),
                "detected_faces": int(identity["detected_face_count"]),
                "expected_faces": expected_face_count,
                "face_count_passed": face_count_passed,
                "identity_diagnostic": identity,
            }
        )

    tile_w, tile_h = 282, 412
    cell_w, cell_h = tile_w * 2 + 28, tile_h + 100
    margin, gap, header_h = 26, 20, 66
    grid_rows = (len(evaluated) + 2) // 3
    canvas = Image.new(
        "RGB",
        (margin * 2 + cell_w * 3 + gap * 2, header_h + margin * 2 + cell_h * grid_rows + gap * (grid_rows - 1)),
        (12, 13, 16),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (margin, 14),
        "FLUX.2 KLEIN BASE 9B + AI-TOOLKIT LORA" + (" + NATIVE REFS" if reference_conditioning else "") + " — sources are visual targets",
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
        with Image.open(row["source"]) as source, Image.open(row["selected_output"]) as output:
            canvas.paste(fit(source, (tile_w, tile_h)), (x, y + 66))
            canvas.paste(fit(output, (tile_w, tile_h)), (x + tile_w + 8, y + 66))
        draw.text((x, y), f"{int(row['scene']):02d}  {row['label']}", font=title_font, fill=(245, 245, 247))
        score = row["identity_similarity"]
        secondary = row["maximum_secondary_identity_similarity"]
        score_text = "no face detected" if score < 0 else f"identity {score:.3f} {row['identity_status']}"
        if secondary >= 0:
            score_text += f" · secondary {secondary:.3f}"
        score_text += f" · faces {int(row['detected_faces'])}/{int(row['expected_faces'])}"
        score_text += f" · {float(row['seconds']):.0f}s"
        score_fill = (173, 207, 255) if row["face_count_passed"] else (255, 135, 135)
        draw.text((x, y + 33), score_text, font=small_font, fill=score_fill)
        draw.text((x + 6, y + 70), "SOURCE", font=label_font, fill=(255, 216, 125))
        candidate_label = "9B + LORA + REFS" if reference_conditioning else "9B + LORA"
        draw.text((x + tile_w + 14, y + 70), candidate_label, font=label_font, fill=(180, 141, 255))

    sheet_path = output_root / "source-vs-flux2-klein9b-lora.png"
    canvas.save(sheet_path, format="PNG", compress_level=6)
    preview = canvas.copy()
    preview.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    preview_path = output_root / "source-vs-flux2-klein9b-lora-preview.jpg"
    preview.save(preview_path, format="JPEG", quality=78, optimize=True, progressive=True)

    crop_tile = (238, 238)
    crop_cell_w, crop_cell_h = crop_tile[0] * 2 + 16, crop_tile[1] + 84
    crop_canvas = Image.new(
        "RGB",
        (margin * 2 + crop_cell_w * 3 + gap * 2, header_h + margin * 2 + crop_cell_h * grid_rows + gap * (grid_rows - 1)),
        (12, 13, 16),
    )
    crop_draw = ImageDraw.Draw(crop_canvas)
    crop_title = "INTENDED MITCH — SOURCE VS KLEIN 9B LORA" + (" + NATIVE REFS" if reference_conditioning else "") + " FACE GEOMETRY"
    crop_draw.text((margin, 14), crop_title, font=font(21, True), fill=(232, 234, 240))
    for index, row in enumerate(evaluated):
        col, grid_row = index % 3, index // 3
        x = margin + col * (crop_cell_w + gap)
        y = header_h + margin + grid_row * (crop_cell_h + gap)
        source_path = Path(row["source"])
        output_path = Path(row["selected_output"])
        with Image.open(source_path) as source_image:
            source_rgb = source_image.convert("RGB")
            source_size = source_rgb.size
        source_faces = load_faces(analyzer, source_path)
        source_bbox = None
        if source_faces:
            source_main, _ = intended_main_face_index(source_faces, source_size, int(row["scene"]))
            source_bbox = source_faces[source_main].bbox
        output_faces_report = row["identity_diagnostic"].get("faces", [])
        output_main = next((face for face in output_faces_report if face.get("role") == "main"), None)
        output_bbox = output_main.get("bbox") if output_main else None
        with Image.open(source_path) as source_image, Image.open(output_path) as output_image:
            crop_canvas.paste(face_crop(source_image.convert("RGB"), source_bbox, crop_tile), (x, y + 76))
            crop_canvas.paste(face_crop(output_image.convert("RGB"), output_bbox, crop_tile), (x + crop_tile[0] + 8, y + 76))
        crop_draw.text((x, y), f"{int(row['scene']):02d}  {row['label']}", font=font(20, True), fill=(245, 245, 247))
        crop_draw.text((x, y + 30), f"identity {float(row['identity_similarity']):.3f} · mean {float(row['identity_mean_reference_similarity']):.3f} · {row['identity_status']}", font=font(13), fill=(173, 207, 255))
        crop_draw.text((x + 5, y + 55), "SOURCE TARGET", font=font(13, True), fill=(255, 216, 125))
        crop_candidate_label = "KLEIN 9B + LORA + REFS" if reference_conditioning else "KLEIN 9B + LORA"
        crop_draw.text((x + crop_tile[0] + 13, y + 55), crop_candidate_label, font=font(13, True), fill=(180, 141, 255))

    face_sheet_path = output_root / "source-vs-flux2-klein9b-lora-face-crops.png"
    face_preview_path = output_root / "source-vs-flux2-klein9b-lora-face-crops-preview.jpg"
    crop_canvas.save(face_sheet_path, format="PNG", compress_level=6)
    crop_preview = crop_canvas.copy()
    crop_preview.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    crop_preview.save(face_preview_path, format="JPEG", quality=84, optimize=True, progressive=True)
    evaluation = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "method": manifest["method"],
        "lora": manifest["lora"],
        "lora_strength": manifest["lora_strength"],
        "evaluation_scope": evaluation_scope,
        "evaluated_scene_numbers": scene_numbers,
        "source_scene_conditioning": False,
        "reference_conditioning": reference_conditioning,
        "held_out_genuine_identity_references": reference_paths,
        "calibration": calibration,
        "contact_sheet": str(sheet_path),
        "contact_sheet_preview": str(preview_path),
        "face_geometry_contact_sheet": str(face_sheet_path),
        "face_geometry_contact_sheet_preview": str(face_preview_path),
        "scenes": evaluated,
        "expected_face_counts": EXPECTED_FACE_COUNTS,
        "automatic_face_count_failures": [
            int(row["scene"]) for row in evaluated if not row["face_count_passed"]
        ],
        "manual_scene_gates": MANUAL_SCENE_GATES,
        "manual_full_size_and_thumbnail_review_required": True,
    }
    evaluation_path = output_root / "evaluation.json"
    evaluation_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    print(f"SHEET={sheet_path}")
    print(f"PREVIEW={preview_path}")
    print(f"FACE_SHEET={face_sheet_path}")
    print(f"FACE_PREVIEW={face_preview_path}")
    print(f"EVALUATION={evaluation_path}")


if __name__ == "__main__":
    main()
