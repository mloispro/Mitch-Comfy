#!/usr/bin/env python3
"""Build the curated FLUX.2 Klein identity dataset from Mitch's real media.

The source folder is never modified. Stills are copied byte-for-byte and the
five selected video frames are extracted deterministically at fixed times.
Generated/retouched headshots and ambiguous multi-person images are excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"C:\projects\AI-Tools\Mitch photos")
DEFAULT_OUTPUT = ROOT / "datasets" / "flux2-klein-identity-v2"
TRIGGER = "M1TCHX9"


TRAIN_STILLS = [
    (
        "01_body_mirror_mint",
        "20231119_205833.jpg",
        "session_20231119_restroom",
        "[trigger], adult man, three-quarter-length mirror selfie, pale mint long-sleeve shirt and dark jeans, standing relaxed in a brightly lit restroom, phone visible in one hand.",
    ),
    (
        "02_closeup_tan_indoor",
        "20240619_001913.jpg",
        "session_20240619_restroom",
        "[trigger], adult man, close head-and-shoulders selfie at a slight three-quarter angle, small closed-mouth smile, tan crew-neck T-shirt, tiled indoor restroom background.",
    ),
    (
        "03_body_mirror_white_sleeveless",
        "20250922_152616.jpg",
        "session_20250922_hotel",
        "[trigger], adult man, full-body mirror selfie, white sleeveless shirt and light blue shorts, standing relaxed in a hotel bathroom, phone visible in one hand.",
    ),
    (
        "04_navy_front_smile",
        "20260316_200010.jpg",
        "session_20260316_navy",
        "[trigger], adult man, close front-facing cellphone selfie with a subtle closed-mouth smile, dark navy crew-neck shirt, warm indoor light and an open closet behind him.",
    ),
    (
        "05_navy_three_quarter_neutral",
        "20260316_200025.jpg",
        "session_20260316_navy",
        "[trigger], adult man, close three-quarter-view cellphone selfie with a calm neutral expression, dark navy crew-neck shirt, warm indoor light and an open closet behind him.",
    ),
    (
        "06_navy_upper_body",
        "20260316_200052.jpg",
        "session_20260316_navy",
        "[trigger], adult man, upper-body cellphone selfie with relaxed posture and a small smile, dark navy crew-neck shirt, warm apartment light and an open closet behind him.",
    ),
    (
        "07_window_bare_shoulders_smile",
        "20260508_122959.jpg",
        "session_20260508_window",
        "[trigger], adult man, close head-and-shoulders selfie with bare shoulders, slight three-quarter angle and a small natural smile, soft window light in an apartment.",
    ),
    (
        "08_sweater_front_neutral",
        "20260508_123126.jpg",
        "session_20260508_sweater",
        "[trigger], adult man, front-facing chest-up cellphone selfie with a neutral expression, burgundy crew-neck sweater, warm apartment lighting.",
    ),
    (
        "09_sweater_right_profile",
        "20260508_123154.jpg",
        "session_20260508_sweater",
        "[trigger], adult man, close right three-quarter to near-profile cellphone selfie with a relaxed small smile, burgundy crew-neck sweater, warm apartment lighting.",
    ),
    (
        "10_sweater_left_profile",
        "20260508_123156.jpg",
        "session_20260508_sweater",
        "[trigger], adult man, close left three-quarter to near-profile cellphone selfie with a calm closed-mouth expression, burgundy crew-neck sweater, warm apartment lighting.",
    ),
    (
        "11_full_body_orange_mirror",
        "20260822_140934.jpg",
        "session_20260822_bedroom",
        "[trigger], adult man, full-body mirror selfie standing barefoot, orange crew-neck T-shirt and black shorts, phone held at chest height, ordinary bedroom background.",
    ),
]


TRAIN_VIDEO_FRAMES = [
    (
        "12_kitchen_smile_three_quarter",
        "identity-source-20260805.mp4",
        12.0,
        "session_20260805_kitchen_video",
        "[trigger], adult man, upper-body cellphone video frame with bare shoulders, smiling at a three-quarter angle in a warmly lit kitchen.",
    ),
    (
        "13_kitchen_opposite_angle_neutral",
        "identity-source-20260805.mp4",
        28.0,
        "session_20260805_kitchen_video",
        "[trigger], adult man, upper-body cellphone video frame with bare shoulders, neutral expression at the opposite three-quarter angle in a warmly lit kitchen.",
    ),
    (
        "14_outdoor_left_three_quarter",
        "20260812_112431.mp4",
        12.0,
        "session_20260812_outdoor_video",
        "[trigger], adult man, seated upper-body cellphone video frame at a left three-quarter angle, black crew-neck T-shirt, daylight beside a brick building.",
    ),
    (
        "15_outdoor_right_three_quarter",
        "20260812_112431.mp4",
        16.0,
        "session_20260812_outdoor_video",
        "[trigger], adult man, seated upper-body cellphone video frame at a right three-quarter angle, black crew-neck T-shirt, daylight beside a brick building.",
    ),
    (
        "16_outdoor_front_smile",
        "20260812_112431.mp4",
        33.5,
        "session_20260812_outdoor_video",
        "[trigger], adult man, seated upper-body front-facing cellphone video frame with a natural smile, black crew-neck T-shirt, daylight beside a brick building.",
    ),
]


VALIDATION_STILLS = [
    ("val_01_balcony_front", "20260815_165446.jpg", "session_20260815_balcony"),
    ("val_02_balcony_angle", "20260815_165449.jpg", "session_20260815_balcony"),
    ("val_03_car", "20260818_173106.jpg", "session_20260818_car"),
    ("val_04_laundry", "20260818_213243.jpg", "session_20260818_laundry"),
    ("val_05_event", "IMG_2961(1).jpg", "session_event_white_shirt"),
    ("val_06_surf_full_body", "20240923_130835.jpg", "session_20240923_surf"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_frame(source: Path, timestamp: float, destination: Path) -> None:
    capture = cv2.VideoCapture(str(source))
    capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"Could not decode {source.name} at {timestamp:.2f}s")
    if not cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 97]):
        raise RuntimeError(f"Could not write {destination}")


def prepare_output(output: Path, force: bool) -> None:
    resolved = output.resolve()
    datasets_root = (ROOT / "datasets").resolve()
    if not resolved.is_relative_to(datasets_root) or resolved == datasets_root:
        raise RuntimeError(f"Refusing to rebuild outside a named dataset directory: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        if not force:
            raise RuntimeError(f"Dataset already exists; pass --force to rebuild: {resolved}")
        shutil.rmtree(resolved)
    (resolved / "train").mkdir(parents=True, exist_ok=True)
    (resolved / "validation").mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    prepare_output(output_dir, args.force)
    train_dir = output_dir / "train"
    validation_dir = output_dir / "validation"
    records: list[dict] = []

    for stem, source_name, session, caption in TRAIN_STILLS:
        source = source_dir / source_name
        destination = train_dir / f"{stem}{source.suffix.lower()}"
        caption = caption.replace("[trigger]", TRIGGER)
        shutil.copy2(source, destination)
        (train_dir / f"{stem}.txt").write_text(caption + "\n", encoding="utf-8")
        records.append(
            {
                "split": "train",
                "id": stem,
                "kind": "still",
                "session": session,
                "source": str(source),
                "source_sha256": sha256(source),
                "dataset_file": str(destination),
                "dataset_sha256": sha256(destination),
                "caption": caption,
            }
        )

    for stem, source_name, timestamp, session, caption in TRAIN_VIDEO_FRAMES:
        source = source_dir / source_name
        destination = train_dir / f"{stem}.jpg"
        caption = caption.replace("[trigger]", TRIGGER)
        extract_frame(source, timestamp, destination)
        (train_dir / f"{stem}.txt").write_text(caption + "\n", encoding="utf-8")
        records.append(
            {
                "split": "train",
                "id": stem,
                "kind": "video_frame",
                "session": session,
                "source": str(source),
                "source_sha256": sha256(source),
                "timestamp_seconds": timestamp,
                "dataset_file": str(destination),
                "dataset_sha256": sha256(destination),
                "caption": caption,
            }
        )

    for stem, source_name, session in VALIDATION_STILLS:
        source = source_dir / source_name
        destination = validation_dir / f"{stem}{source.suffix.lower()}"
        shutil.copy2(source, destination)
        records.append(
            {
                "split": "validation",
                "id": stem,
                "kind": "still",
                "session": session,
                "source": str(source),
                "source_sha256": sha256(source),
                "dataset_file": str(destination),
                "dataset_sha256": sha256(destination),
            }
        )

    train_hashes = {record["dataset_sha256"] for record in records if record["split"] == "train"}
    validation_hashes = {
        record["dataset_sha256"] for record in records if record["split"] == "validation"
    }
    overlap = sorted(train_hashes & validation_hashes)
    if overlap:
        raise RuntimeError(f"Training/validation SHA-256 overlap: {overlap}")

    train_count = len(TRAIN_STILLS) + len(TRAIN_VIDEO_FRAMES)
    validation_count = len(VALIDATION_STILLS)
    manifest = {
        "schema_version": 1,
        "dataset": "flux2-klein-identity-v2",
        "trigger_word": TRIGGER,
        "source_policy": "User-owned real media only; generated, retouched, ambiguous multi-person, low-resolution legacy headshots, and redundant burst frames excluded.",
        "pixel_policy": "Selected stills are byte-identical copies. Video frames are deterministic JPEG extractions. No generative editing, face restoration, alignment, skin processing, or enhancement.",
        "split_policy": "Validation photos are excluded from training by file hash. Validation deliberately covers current close views, different environments, an event photo, and a difficult full-body photo.",
        "train_image_count": train_count,
        "validation_image_count": validation_count,
        "records": records,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "# FLUX.2 Klein identity dataset v2\n\n"
        f"Trigger: `{TRIGGER}`\n\n"
        f"- `train/`: {train_count} curated real images with matching AI-Toolkit captions.\n"
        f"- `validation/`: {validation_count} real images never supplied to training.\n"
        "- `manifest.json`: provenance, hashes, sessions, video timestamps, and captions.\n\n"
        "The source folder is never modified. Rebuild with "
        "`python scripts/build-flux2-identity-dataset.py --force`.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"output": str(output_dir), "train": train_count, "validation": validation_count},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
