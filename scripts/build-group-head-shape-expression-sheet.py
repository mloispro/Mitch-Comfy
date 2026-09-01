from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def faces_for(analyzer, path: Path):
    with Image.open(path) as opened:
        rgb = np.asarray(ImageOps.exif_transpose(opened).convert("RGB"), dtype=np.uint8)
    return analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def largest_face(faces):
    if not faces:
        raise RuntimeError("No face detected")
    return max(faces, key=lambda face: float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])))


def identity_face(faces, centroid: np.ndarray):
    if not faces:
        raise RuntimeError("No face detected")
    return max(
        faces,
        key=lambda face: float(np.dot(np.asarray(face.normed_embedding, dtype=np.float32), centroid)),
    )


def normalized_face_crop(image: Image.Image, bbox, size: tuple[int, int]) -> Image.Image:
    x1, y1, x2, y2 = (float(value) for value in bbox)
    center_x = (x1 + x2) * 0.5
    center_y = (y1 + y2) * 0.5
    side = max(x2 - x1, y2 - y1) * 2.05
    left = max(int(center_x - side * 0.5), 0)
    top = max(int(center_y - side * 0.54), 0)
    right = min(int(center_x + side * 0.5), image.width)
    bottom = min(int(center_y + side * 0.46), image.height)
    crop = image.crop((left, top, right, bottom)).convert("RGB")
    return ImageOps.fit(crop, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a normalized genuine-reference vs group-candidate face sheet.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "work" / "group-lounge-prompt-research-20260831" / "09-head-shape-expression-finalists.png",
    )
    args = parser.parse_args()

    items = [
        {
            "label": "GENUINE NEUTRAL",
            "subtitle": "identity/head anchor",
            "path": Path(r"C:\projects\AI-Tools\ComfyUI\input\mitch-klein9b-ref-front-neutral-v2.jpg"),
            "kind": "reference",
        },
        {
            "label": "GENUINE SMALL SMILE",
            "subtitle": "expression reference",
            "path": Path(r"C:\projects\AI-Tools\ComfyUI\input\mitch-klein9b-ref-front-small-smile-v1.jpg"),
            "kind": "reference",
        },
        {
            "label": "1.00 MP FULL PHOTO",
            "subtitle": "identity 0.5928",
            "path": REPO_ROOT / "work" / "group-lounge-prompt-research-20260831" / "06-canny-concise-neutral-id100-head-shape-slight-smile.png",
            "kind": "candidate",
        },
        {
            "label": "FULL-PHOTO WINNER",
            "subtitle": "identity 0.6096 · face W/H 0.741",
            "path": REPO_ROOT / "work" / "group-lounge-prompt-research-20260831" / "08-canny-concise-neutral-id100-gentle-lips-winner.png",
            "kind": "candidate",
        },
        {
            "label": "FACE-CROP FINALIST",
            "subtitle": "identity 0.5954 · face W/H 0.735",
            "path": REPO_ROOT / "work" / "group-lounge-prompt-research-20260831" / "09-canny-facecrop-id100-gentle-lips-head-shape-finalist.png",
            "kind": "candidate",
        },
    ]
    for item in items:
        if not item["path"].is_file():
            raise FileNotFoundError(item["path"])

    from insightface.app import FaceAnalysis

    analyzer = FaceAnalysis(
        name="antelopev2",
        root=str(Path.home() / ".insightface"),
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
    )
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))

    reference_embeddings = []
    reference_faces = []
    for item in items[:2]:
        face = largest_face(faces_for(analyzer, item["path"]))
        reference_faces.append(face)
        reference_embeddings.append(np.asarray(face.normed_embedding, dtype=np.float32))
    centroid = np.mean(np.stack(reference_embeddings), axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)

    tile = (330, 330)
    canvas = Image.new("RGB", (1120, 960), (11, 12, 15))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "MITCH HEAD SHAPE + EXPRESSION", font=font(30, True), fill=(242, 243, 247))
    draw.text(
        (36, 65),
        "Normalized face crops — compare forehead/cheek width, jaw taper, chin, and mouth corners",
        font=font(17),
        fill=(174, 182, 198),
    )

    positions = [(210, 145), (580, 145), (25, 585), (395, 585), (765, 585)]
    report_items = []
    for index, (item, position) in enumerate(zip(items, positions, strict=True)):
        faces = faces_for(analyzer, item["path"])
        face = reference_faces[index] if index < 2 else identity_face(faces, centroid)
        bbox = [round(float(value), 2) for value in face.bbox]
        with Image.open(item["path"]) as opened:
            crop = normalized_face_crop(ImageOps.exif_transpose(opened).convert("RGB"), bbox, tile)
        x, y = position
        canvas.paste(crop, (x, y))
        border = (245, 210, 120) if item["kind"] == "reference" else (177, 142, 255)
        draw.rectangle((x - 2, y - 2, x + tile[0] + 1, y + tile[1] + 1), outline=border, width=3)
        draw.text((x, y - 49), item["label"], font=font(18, True), fill=border)
        draw.text((x, y - 24), item["subtitle"], font=font(14), fill=(205, 208, 216))
        report_items.append(
            {
                "label": item["label"],
                "kind": item["kind"],
                "path": str(item["path"]),
                "sha256": sha256(item["path"]),
                "selected_face_bbox": bbox,
                "selection": "largest face" if index < 2 else "highest similarity to two-photo genuine centroid",
            }
        )

    draw.text((36, 515), "CONTROLLED PROGRESSION", font=font(22, True), fill=(232, 234, 240))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, format="PNG", compress_level=6)
    report_path = args.output.with_suffix(".json")
    report_path.write_text(
        json.dumps(
            {
                "sheet": str(args.output),
                "method": "AntelopeV2 face detection; two-reference centroid selects Mitch in group outputs; identical normalized crop geometry",
                "manual_review_required": True,
                "items": report_items,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"SHEET={args.output}")
    print(f"REPORT={report_path}")


if __name__ == "__main__":
    main()
