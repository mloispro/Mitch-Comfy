from __future__ import annotations

import json
import shutil
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


COMFY_INPUT = Path(r"C:\projects\AI-Tools\ComfyUI\input")
VALIDATION_ROOT = REPO_ROOT / "datasets" / "mitch-identity-stills-v3" / "validation"
SCENE_ONE_ROOT = (
    REPO_ROOT
    / "work"
    / "flux2-dev-nine-scenes-3090"
    / "smoke-group-a-dev-s1000-3090-strength110"
    / "selected"
)
BATCH_ROOT = (
    REPO_ROOT
    / "work"
    / "flux2-dev-nine-scenes-3090"
    / "dev-s1000-3090-nine-scenes-strength110"
    / "selected"
)
DESTINATION = (
    REPO_ROOT
    / "work"
    / "flux2-dev-nine-scenes-3090"
    / "final-dev-s1000-strength110"
)
SCENES = [
    (1, "night out A", "mitch-workbench-dating-01-night-out-a.png", "01-night-out-a.png"),
    (2, "night out B", "mitch-workbench-dating-02-night-out-b.png", "02-night-out-b.png"),
    (3, "Ragdoll cat", "mitch-workbench-dating-03-cat-ragdoll.png", "03-ragdoll-cat.png"),
    (4, "tabby cat", "mitch-workbench-dating-04-cat-tabby.png", "04-tabby-cat.png"),
    (5, "golfer", "mitch-workbench-dating-05-golfer-safe.png", "05-golfer.png"),
    (6, "Amalfi", "mitch-workbench-dating-06-amalfi.png", "06-amalfi.png"),
    (7, "lake boat", "mitch-workbench-dating-07-lake-boat.png", "07-lake-boat.png"),
    (8, "restaurant", "mitch-workbench-dating-08-restaurant.png", "08-restaurant.png"),
    (9, "night rooftop", "mitch-workbench-dating-09-night-city.png", "09-night-rooftop.png"),
]
MANUAL_NOTES = {
    1: "Four people retained; Mitch is only the foreground sofa subject; lounge geometry and clothing match.",
    2: "Central Mitch and four foreground friends retained; extra small background face detected; no visible Mitch duplication.",
    3: "Large Ragdoll orientation, two-hand cradle, black zip hoodie, downward gaze, curtains and sofa match.",
    4: "Smaller tabby cradle, black pullover hoodie, bowed head, bright apartment and sofa match.",
    5: "Full-body walk, club at image-left, glove at image-right, both feet, palms and fairway match.",
    6: "Close Amalfi crop, white linen shirt, railing hand and watch, Positano left and sea right match.",
    7: "Centered boat seat, sunglasses, white linen outfit, both rail hands, villas and mountains match.",
    8: "Gray double-breasted blazer, chin-on-hand pose, lamp, arched mirror light and crop match.",
    9: "Both hands remain on the glass railing; head and eyes look down toward image-left with no eye contact.",
}


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
    if len(reference_paths) < 2:
        raise RuntimeError("At least two held-out genuine identity photos are required.")
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
    from insightface.app import FaceAnalysis

    selected_root = DESTINATION / "selected"
    selected_root.mkdir(parents=True, exist_ok=True)
    source_and_outputs = []
    for number, label, source_name, output_name in SCENES:
        source_path = COMFY_INPUT / source_name
        candidate_root = SCENE_ONE_ROOT if number == 1 else BATCH_ROOT
        generated_path = candidate_root / output_name
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        if not generated_path.is_file():
            raise FileNotFoundError(generated_path)
        selected_path = selected_root / output_name
        shutil.copy2(generated_path, selected_path)
        source_and_outputs.append((number, label, source_path, selected_path))

    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(Path.home() / ".insightface"),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    centroid, reference_paths = build_reference_centroid(analyzer)

    rows = []
    for number, label, source_path, output_path in source_and_outputs:
        faces = load_faces(analyzer, output_path)
        identity = evaluate_identity_scope(
            [np.asarray(face.normed_embedding, dtype=np.float32) for face in faces],
            [face.bbox for face in faces],
            [float(face.det_score) for face in faces],
            centroid,
            0.75,
        ).as_dict()
        maximum_secondary = float(identity["maximum_secondary_identity_similarity"])
        maximum_pair = float(identity["maximum_secondary_pair_similarity"])
        leakage_passed = maximum_secondary < 0.42 and maximum_pair < 0.72
        rows.append(
            {
                "scene": number,
                "label": label,
                "source": str(source_path),
                "selected_output": str(output_path),
                "manual_scene_match": "passed",
                "manual_scene_notes": MANUAL_NOTES[number],
                "identity_similarity": float(identity["main_identity_similarity"]),
                "identity_status": (
                    "passed" if float(identity["main_identity_similarity"]) >= 0.75 else "below_threshold"
                ),
                "detected_faces": int(identity["detected_face_count"]),
                "maximum_secondary_identity_similarity": maximum_secondary,
                "maximum_secondary_pair_similarity": maximum_pair,
                "identity_leakage_status": "passed" if leakage_passed else "rejected",
                "identity_diagnostic": identity,
            }
        )

    tile_w, tile_h = 282, 412
    cell_w, cell_h = tile_w * 2 + 28, tile_h + 98
    margin, gap = 26, 20
    canvas = Image.new(
        "RGB",
        (margin * 2 + cell_w * 3 + gap * 2, margin * 2 + cell_h * 3 + gap * 2),
        (12, 13, 16),
    )
    draw = ImageDraw.Draw(canvas)
    title_font = font(23, bold=True)
    small_font = font(16)
    label_font = font(18, bold=True)
    for index, (row, item) in enumerate(zip(rows, source_and_outputs)):
        _, _, source_path, output_path = item
        col, grid_row = index % 3, index // 3
        x = margin + col * (cell_w + gap)
        y = margin + grid_row * (cell_h + gap)
        with Image.open(source_path) as source, Image.open(output_path) as output:
            canvas.paste(fit(source, (tile_w, tile_h)), (x, y + 64))
            canvas.paste(fit(output, (tile_w, tile_h)), (x + tile_w + 8, y + 64))
        draw.text((x, y), f"{row['scene']:02d}  {row['label']}", font=title_font, fill=(245, 245, 247))
        secondary = row["maximum_secondary_identity_similarity"]
        suffix = f" · secondary {secondary:.3f}" if secondary >= 0 else ""
        draw.text(
            (x, y + 32),
            f"identity {row['identity_similarity']:.3f}{suffix}",
            font=small_font,
            fill=(173, 207, 255),
        )
        draw.text((x + 6, y + 68), "SOURCE", font=label_font, fill=(255, 216, 125))
        draw.text(
            (x + tile_w + 14, y + 68),
            "DEV + DEV LoRA",
            font=label_font,
            fill=(170, 145, 255),
        )

    sheet_path = DESTINATION / "source-vs-flux2-dev-lora-3090.png"
    canvas.save(sheet_path, format="PNG", compress_level=6)
    verification = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "FLUX.2 Dev native single-scene reference restaging plus trained Dev identity LoRA",
        "gpu": "NVIDIA GeForce RTX 3090",
        "base_model": "flux2_dev_fp8mixed.safetensors",
        "text_encoder": "mistral_3_small_flux2_fp4_mixed.safetensors",
        "vae": "flux2-vae.safetensors",
        "lora": r"flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors",
        "lora_sha256": "7c0c4f1726189c51e19c8392c12fe3e03a26bd084fffb8d84b907c966a77cc3e",
        "trigger": "m1tch_person",
        "settings": {"lora_strength": 1.1, "sampler": "euler", "steps": 28, "guidance": 4.0},
        "conditioning": "Picture 1 is a native FLUX.2 Dev reference latent for scene, pose, clothing, props and lighting; the Dev LoRA supplies identity.",
        "face_swap": False,
        "mask": False,
        "restoration": False,
        "held_out_genuine_identity_references": reference_paths,
        "identity_threshold": 0.75,
        "secondary_identity_leakage_limit": 0.42,
        "contact_sheet": str(sheet_path),
        "scenes": rows,
    }
    verification_path = DESTINATION / "verification.json"
    verification_path.write_text(json.dumps(verification, indent=2), encoding="utf-8")
    print(f"SHEET={sheet_path}")
    print(f"VERIFICATION={verification_path}")
    print(f"SELECTED={selected_root}")


if __name__ == "__main__":
    main()
