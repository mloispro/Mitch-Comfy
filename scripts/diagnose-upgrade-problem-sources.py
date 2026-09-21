"""CPU-only source diagnostics for the user canyon clipboard and synthetic house.

No generation, queue/network access, model downloads, image edits or uploads.
Creates derived comparison sheets and a diagnostic report; source bytes unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path
from runpy import run_path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "work/upgrade-high-20260907/problem-source-diagnostics"
utility = run_path(str(ROOT / "scripts/evaluate-upgrade-beautygrpo.py"))
sha, read = utility["sha"], utility["read"]
SOURCES = {
    "USER CANYON SOURCE": {
        "path": Path("C:/Users/Mitch/AppData/Local/Temp/codex-clipboard-5411229e-4e9c-47ee-996a-78a8ebef887d.png"),
        "sha256": "e12c0c3d417e8174f0b82d4e44b7f41d237a4c5ef85beaa8a64d84476efe6aa9",
        "provenance": "unknown; possibly synthetic; not a genuine validation reference",
        "genuine_validation_anchor": False,
    },
    "SYNTHETIC HOUSE SOURCE": {
        "path": Path("C:/projects/AI-Tools/ComfyUI/input/mitch-photo2-source-aef87048.png"),
        "sha256": "aef8704873c40c92ec365c091ea142998e72b3d80d22b45f55275309165ba5b4",
        "provenance": "synthetic edit target; not a genuine validation reference",
        "genuine_validation_anchor": False,
    },
}


def main():
    if DESTINATION.exists():
        raise ValueError("Preserve the existing diagnostic directory.")
    photos, source_metadata = {}, {}
    for label, item in SOURCES.items():
        path = item["path"].resolve(strict=True)
        if sha(path) != item["sha256"]:
            raise ValueError("Pinned source changed: " + str(path))
        with Image.open(path) as image:
            oriented = ImageOps.exif_transpose(image)
            source_metadata[label] = {**item, "path": str(path), "bytes": path.stat().st_size,
                "stored_size": list(image.size), "exif_oriented_size": list(oriented.size),
                "aspect_ratio": oriented.width / oriented.height, "format": image.format,
                "exif_orientation": image.getexif().get(274), "metadata_keys": sorted(image.info),
                "embedded_comfy_prompt_present": "prompt" in image.info}
        photos[label] = read(path)
    references = []
    for name, expected in utility["REFERENCE_PINS"].items():
        path = utility["REFERENCE_DIRECTORY"] / name
        if sha(path) != expected:
            raise ValueError("Pinned genuine reference changed: " + name)
        if expected in {item["sha256"] for item in SOURCES.values()}:
            raise ValueError("A problem source unexpectedly overlaps a genuine scoring anchor.")
        references.append(path)
    if len(references) != 6:
        raise ValueError("Require all six independent genuine references.")
    root = Path.home() / ".insightface"
    if not all((root / "models/antelopev2" / name).is_file() for name in
               ("scrfd_10g_bnkps.onnx", "glintr100.onnx", "1k3d68.onnx")):
        raise ValueError("Installed CPU scoring weights missing; no downloads.")
    from insightface.app import FaceAnalysis

    sys.path.insert(0, str(ROOT / "custom_nodes/ComfyUI-AIToolkit-Training"))
    import flux2_klein9b_source_gaze_lock as gaze
    from experimental_upgrade_smile_balance import measure_smile

    cv2.setNumThreads(4)
    analyzer = FaceAnalysis(name="antelopev2", root=str(root), providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition", "landmark_3d_68"])
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))

    def face(rgb):
        detected = analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if len(detected) != 1:
            raise ValueError("Require exactly one detected face for unambiguous source/reference scoring.")
        return detected[0]

    vectors = [face(read(path)).normed_embedding for path in references]
    centroid = np.mean(vectors, axis=0)
    centroid /= np.linalg.norm(centroid)
    results, detections = {}, {}
    for label, rgb in photos.items():
        detected = face(rgb)
        detections[label] = detected
        points, method = gaze._detect_refined_landmarks(rgb)
        smile = measure_smile(points)
        results[label] = {"identity_centroid": float(detected.normed_embedding @ centroid),
            "per_reference_similarity": [{"reference": path.name, "similarity": float(detected.normed_embedding @ vector)}
                                         for path, vector in zip(references, vectors)],
            "pose": detected.pose.tolist(), "pose_order": "pitch_yaw_roll", "face_bbox": detected.bbox.tolist(),
            "eye_coordinates": [gaze._eye_measurement(points, eye)["coordinate"].tolist() for eye in gaze._EYES],
            "mouth_opening_ratio": float(smile["opening_ratio"]), "smile_lift": float(smile["smile_lift"]),
            "landmark_method": method}
    for item in SOURCES.values():
        if sha(item["path"]) != item["sha256"]:
            raise ValueError("Source changed during read-only diagnostics.")
    report = {"status": "source_only_diagnostics_not_generation_or_acceptance", "sources": source_metadata,
        "references": [{"path": str(path), "sha256": sha(path), "genuine": True} for path in references],
        "results": results, "scoring_execution_provider": "CPUExecutionProvider", "source_bytes_unchanged": True,
        "generation_submitted": False, "uploaded": False,
        "limitation": "Sources are edit targets, not genuine identity anchors. Six-reference centroid similarity is a diagnostic, not a probability or guarantee of retouch preservation/improvement. Different reference sets make these scores not directly comparable to leave-one-out five-reference genuine-source scores. Display crops/resizes are derived sheets only; original sources remain unchanged."}
    DESTINATION.mkdir(parents=True)
    for crop, filename, height in ((False, "source-thumbnails.jpg", 360), (True, "source-faces.jpg", 512)):
        panels = []
        for label, rgb in photos.items():
            image = Image.fromarray(rgb)
            if crop:
                box = detections[label].bbox
                pad = float(box[2] - box[0]) * .15
                left, top, right, bottom = np.rint(box + [-pad, -pad, pad, pad]).astype(int)
                image = image.crop((max(0, left), max(0, top), min(image.width, right), min(image.height, bottom)))
            image = image.resize((round(image.width * height / image.height), height), Image.Resampling.LANCZOS)
            panels.append((label, image))
        sheet = Image.new("RGB", (sum(image.width for _, image in panels), height + 36), (20, 20, 20))
        draw = ImageDraw.Draw(sheet)
        offset = 0
        for label, image in panels:
            sheet.paste(image, (offset, 36))
            draw.text((offset + 6, 9), label, fill="white")
            offset += image.width
        sheet.save(DESTINATION / filename, quality=97)
    (DESTINATION / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
