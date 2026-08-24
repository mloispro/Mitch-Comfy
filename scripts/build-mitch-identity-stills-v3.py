#!/usr/bin/env python3
"""Build Mitch's still-photo-only identity LoRA dataset for AI Toolkit.

The source directory is read-only from this script's perspective. Training and
validation images are byte-identical copies of reviewed JPG/PNG camera stills.
Video frames, generated/retouched images, and redundant burst photos are never
included.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"C:\projects\AI-Tools\Mitch photos")
DEFAULT_OUTPUT = ROOT / "datasets" / "mitch-identity-stills-v3"
TRIGGER = "m1tch_person"
ALLOWED_STILL_SUFFIXES = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class Photo:
    stem: str
    source_name: str
    session: str
    caption: str | None = None
    role: str = "training"
    rationale: str = ""
    identity_similarity: float | None = None


TRAINING = (
    Photo(
        "01_body_mirror_mint",
        "20231119_205833.jpg",
        "20231119_restroom_mirror",
        f"{TRIGGER}, an adult man, three-quarter-length mirror cellphone photo, relaxed pose and slight closed-mouth smile, pale mint long-sleeve shirt and dark jeans, bright ordinary restroom lighting, phone visible in one hand",
        rationale="Strong genuine still with useful three-quarter body proportions and different clothing.",
        identity_similarity=0.80,
    ),
    Photo(
        "02_closeup_tan_indoor",
        "20240619_001913.jpg",
        "20240619_restroom_closeup",
        f"{TRIGGER}, an adult man, close head-and-shoulders cellphone photo at a slight three-quarter angle, natural small smile, tan crew-neck shirt, ordinary indoor restroom lighting",
        rationale="Sharp natural close view from an independent session with visible skin texture.",
        identity_similarity=0.80,
    ),
    Photo(
        "03_beach_daylight",
        "20240919_095137.jpg",
        "20240919_beach",
        f"{TRIGGER}, an adult man, chest-up outdoor cellphone photo, facing the camera with a relaxed expression, dark shirt with sunglasses resting on his head, bright beach daylight and water in the background",
        rationale="New independent outdoor still with natural texture and useful lighting diversity.",
        identity_similarity=0.76,
    ),
    Photo(
        "04_navy_front_neutral",
        "20260316_200014.jpg",
        "20260316_navy_indoor",
        f"{TRIGGER}, an adult man, close front-facing cellphone photo with a calm neutral expression, dark navy crew-neck shirt, warm apartment lighting",
        rationale="Best neutral frontal view from the March burst.",
        identity_similarity=0.78,
    ),
    Photo(
        "05_navy_three_quarter_neutral",
        "20260316_200025.jpg",
        "20260316_navy_indoor",
        f"{TRIGGER}, an adult man, close cellphone photo at a three-quarter angle with a relaxed neutral expression, dark navy crew-neck shirt, warm apartment lighting",
        rationale="Useful facial geometry from one three-quarter direction.",
        identity_similarity=0.80,
    ),
    Photo(
        "06_window_bare_shoulders_neutral",
        "20260508_122948.jpg",
        "20260508_window_daylight",
        f"{TRIGGER}, an adult man, close head-and-shoulders cellphone photo at a three-quarter angle, neutral closed-mouth expression and bare shoulders, soft daylight from a nearby window",
        rationale="One high-resolution natural-skin reference; all similar frames from this burst are excluded.",
        identity_similarity=0.77,
    ),
    Photo(
        "07_sweater_front_neutral",
        "20260508_123126.jpg",
        "20260508_sweater_indoor",
        f"{TRIGGER}, an adult man, front-facing chest-up cellphone photo with a calm neutral expression, burgundy crew-neck sweater, warm apartment lighting",
        rationale="High-resolution frontal anchor with a neutral expression.",
        identity_similarity=0.83,
    ),
    Photo(
        "08_sweater_near_profile",
        "20260508_123154.jpg",
        "20260508_sweater_indoor",
        f"{TRIGGER}, an adult man, close cellphone photo at a strong three-quarter to near-profile angle, relaxed small smile, burgundy crew-neck sweater, warm apartment lighting",
        rationale="High-resolution near-profile geometry from one direction.",
        identity_similarity=0.84,
    ),
    Photo(
        "09_sweater_opposite_near_profile",
        "20260508_123156.jpg",
        "20260508_sweater_indoor",
        f"{TRIGGER}, an adult man, close cellphone photo at the opposite strong three-quarter to near-profile angle, calm closed-mouth expression, burgundy crew-neck sweater, warm apartment lighting",
        rationale="High-resolution near-profile geometry from the opposite direction.",
        identity_similarity=0.88,
    ),
    Photo(
        "10_balcony_front_smile",
        "20260815_165446.jpg",
        "20260815_balcony_daylight",
        f"{TRIGGER}, an adult man, front-facing head-and-shoulders cellphone photo with a natural small smile, plain white crew-neck shirt, soft outdoor daylight on a balcony",
        rationale="Current-appearance frontal anchor and strongest audited identity match.",
        identity_similarity=0.94,
    ),
    Photo(
        "11_balcony_three_quarter_neutral",
        "20260815_165506.jpg",
        "20260815_balcony_daylight",
        f"{TRIGGER}, an adult man, head-and-shoulders cellphone photo at a three-quarter angle with a calm neutral expression, plain white crew-neck shirt, soft outdoor daylight on a balcony",
        rationale="Current-appearance angle variation without adding the whole balcony burst.",
        identity_similarity=0.82,
    ),
    Photo(
        "12_laundry_orange_shirt",
        "20260818_213243.jpg",
        "20260818_laundry_room",
        f"{TRIGGER}, an adult man, chest-up cellphone photo at a slight three-quarter angle with a natural animated expression, orange crew-neck shirt, ordinary indoor laundry-room lighting",
        rationale="Current independent indoor session with different expression, clothing, and background.",
        identity_similarity=0.86,
    ),
    Photo(
        "13_full_body_orange_mirror",
        "20260822_140934.jpg",
        "20260822_bedroom_mirror",
        f"{TRIGGER}, an adult man, full-body mirror cellphone photo standing barefoot, orange crew-neck shirt and black shorts, phone held at chest height, ordinary bedroom background",
        rationale="Best current full-body still for proportions and non-headshot framing.",
        identity_similarity=0.76,
    ),
)


VALIDATION = (
    Photo(
        "val_01_surf_full_body",
        "20240923_130835.jpg",
        "20240923_surf",
        role="hard_validation",
        rationale="Independent difficult full-body view with a small face; intentionally not trained.",
        identity_similarity=0.67,
    ),
    Photo(
        "val_02_body_mirror_sleeveless",
        "20250922_152616.jpg",
        "20250922_hotel_mirror",
        role="validation",
        rationale="Independent body-framing and clothing holdout.",
    ),
    Photo(
        "val_03_navy_upper_body",
        "20260316_200052.jpg",
        "20260316_navy_indoor",
        role="same_session_validation",
        rationale="Held-out wider framing from a represented session.",
    ),
    Photo(
        "val_04_window_small_smile",
        "20260508_122959.jpg",
        "20260508_window_daylight",
        role="same_session_validation",
        rationale="Held-out expression from the window session.",
    ),
    Photo(
        "val_05_balcony_opposite_angle",
        "20260815_165449.jpg",
        "20260815_balcony_daylight",
        role="same_session_validation",
        rationale="Held-out current opposite-angle smile.",
        identity_similarity=0.92,
    ),
    Photo(
        "val_06_car_daylight",
        "20260818_173106.jpg",
        "20260818_car",
        role="validation",
        rationale="Independent current car-lighting holdout and strong identity reference.",
        identity_similarity=0.91,
    ),
)


EXCLUDED = {
    "video_sources": {
        "20260812_112431.mp4",
        "identity-source-20260805.mp4",
    },
    "redundant_burst_frames": {
        "20260316_200010.jpg",
        "20260316_200020.jpg",
        "20260316_200031.jpg",
        "20260316_200041.jpg",
        "20260316_200046.jpg",
        "20260316_200102.jpg",
        "20260508_122941.jpg",
        "20260508_122944.jpg",
        "20260508_123005.jpg",
        "20260508_123009.jpg",
        "20260508_123132.jpg",
        "20260508_123133.jpg",
        "20260508_123137.jpg",
        "20260508_123139.jpg",
        "20260508_123144.jpg",
        "20260508_123200.jpg",
        "20260508_123206.jpg",
        "20260815_165425.jpg",
    },
    "poor_lighting_or_distortion": {
        "20260719_170802.jpg",
        "20260719_170821.jpg",
        "20260726_010444.jpg",
        "20260726_010444(1).jpg",
        "20260814_014313.jpg",
        "20260814_014359.jpg",
        "IMG_2961(1).jpg",
    },
    "old_low_resolution_or_current_identity_mismatch": {
        "Me-3.png",
        "Mitch (1).PNG",
        "Mitch head 3.jpg",
        "Mitch head 6.png",
        "Mitch head.jpg",
        "WIN_20231101_11_35_03_Pro.png",
        "WIN_20231101_11_35_06_Pro.png",
        "WIN_20231101_11_35_40_Pro.png",
    },
    "retouched_or_synthetic": {
        "Mitch-headshot-2024-large.jpg",
        "Mitch.safetensors.png",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_info(path: Path) -> dict[str, int | str]:
    with Image.open(path) as image:
        return {
            "width": image.width,
            "height": image.height,
            "format": image.format or path.suffix.lstrip(".").upper(),
        }


def prepare_output(output: Path, force: bool) -> None:
    resolved = output.resolve()
    datasets_root = (ROOT / "datasets").resolve()
    if not resolved.is_relative_to(datasets_root) or resolved == datasets_root:
        raise RuntimeError(f"Refusing to rebuild outside a named dataset directory: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        if not force:
            raise RuntimeError(f"Dataset already exists; pass --force to rebuild: {resolved}")
        shutil.rmtree(resolved)
    (resolved / "dataset").mkdir(parents=True, exist_ok=True)
    (resolved / "validation").mkdir(parents=True, exist_ok=True)
    (resolved / "review").mkdir(parents=True, exist_ok=True)


def validate_inventory(source_dir: Path) -> dict[str, str]:
    selected = {photo.source_name for photo in TRAINING + VALIDATION}
    excluded = {name for names in EXCLUDED.values() for name in names}
    overlap = selected & excluded
    if overlap:
        raise RuntimeError(f"Files are both selected and excluded: {sorted(overlap)}")

    source_media = {
        path.name
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_STILL_SUFFIXES | {".mp4"}
    }
    missing = (selected | excluded) - source_media
    if missing:
        raise FileNotFoundError(f"Reviewed source files are missing: {sorted(missing)}")
    unreviewed = source_media - selected - excluded
    if unreviewed:
        raise RuntimeError(
            "New or unreviewed media found. Review and classify it before rebuilding: "
            + ", ".join(sorted(unreviewed))
        )

    return {
        name: category
        for category, names in EXCLUDED.items()
        for name in sorted(names)
    }


def copy_photo(photo: Photo, source_dir: Path, destination_dir: Path, split: str) -> dict:
    source = source_dir / photo.source_name
    if source.suffix.lower() not in ALLOWED_STILL_SUFFIXES:
        raise RuntimeError(f"Non-still source cannot enter the dataset: {source}")
    destination = destination_dir / f"{photo.stem}{source.suffix.lower()}"
    shutil.copy2(source, destination)
    if sha256(source) != sha256(destination):
        raise RuntimeError(f"Byte-copy verification failed for {source.name}")

    if split == "train":
        if not photo.caption or not photo.caption.startswith(TRIGGER):
            raise RuntimeError(f"Missing trigger-first caption for {photo.stem}")
        (destination_dir / f"{photo.stem}.txt").write_text(
            photo.caption + "\n", encoding="utf-8"
        )

    return {
        "split": split,
        "id": photo.stem,
        "kind": "camera_still",
        "role": photo.role,
        "session": photo.session,
        "source": str(source),
        "source_sha256": sha256(source),
        "dataset_file": str(destination),
        "dataset_sha256": sha256(destination),
        "caption": photo.caption if split == "train" else None,
        "selection_rationale": photo.rationale,
        "identity_similarity_diagnostic": photo.identity_similarity,
        **image_info(destination),
    }


def make_contact_sheet(records: list[dict], destination: Path, title: str) -> None:
    thumb_width, thumb_height = 320, 300
    label_height = 58
    columns = 4
    rows = (len(records) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_width, 56 + rows * (thumb_height + label_height)), "#17191d")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    small_font = ImageFont.load_default(size=14)
    draw.text((16, 14), title, fill="#f4f4f5", font=font)

    for index, record in enumerate(records):
        row, column = divmod(index, columns)
        x = column * thumb_width
        y = 56 + row * (thumb_height + label_height)
        with Image.open(record["dataset_file"]) as source:
            preview = ImageOps.exif_transpose(source).convert("RGB")
            preview.thumbnail((thumb_width - 16, thumb_height - 16), Image.Resampling.LANCZOS)
            px = x + (thumb_width - preview.width) // 2
            py = y + (thumb_height - preview.height) // 2
            sheet.paste(preview, (px, py))
        draw.text((x + 8, y + thumb_height + 4), record["id"], fill="#f4f4f5", font=small_font)
        draw.text(
            (x + 8, y + thumb_height + 25),
            f'{record["width"]}x{record["height"]}  {record["session"]}',
            fill="#a1a1aa",
            font=small_font,
        )
    sheet.save(destination, quality=92, optimize=True)


def write_readme(output_dir: Path, records: list[dict], exclusions: dict[str, str]) -> None:
    train_records = [record for record in records if record["split"] == "train"]
    validation_records = [record for record in records if record["split"] == "validation"]
    session_counts = Counter(record["session"] for record in train_records)
    lines = [
        "# Mitch identity stills v3",
        "",
        "AI Toolkit-ready, still-photo-only identity LoRA dataset.",
        "",
        f"- Trigger token: `{TRIGGER}`",
        f"- Training folder: `{output_dir / 'dataset'}`",
        f"- Training images/captions: {len(train_records)} matched pairs",
        f"- Held-out validation images: {len(validation_records)}",
        "- Pixel policy: byte-identical copies only; no cropping, enhancement, face restoration, alignment, filtering, or generative edits",
        "- Source policy: genuine user-owned JPG/PNG stills only; no extracted video frames",
        "",
        "## AI Toolkit use",
        "",
        f"Point one AI Toolkit dataset entry at `{output_dir / 'dataset'}` and use `txt` as the caption extension. Every caption starts with `{TRIGGER}`. Keep `shuffle_tokens` disabled so the identity token remains first. Do not point the trainer at `validation/` or `review/`.",
        "",
        "The image/caption set is model-agnostic. Choose the base model, rank, optimizer, resolution buckets, and training steps in the model-specific AI Toolkit job rather than copying settings from an incompatible prior run.",
        "",
        "## Balance",
        "",
    ]
    for session, count in sorted(session_counts.items()):
        lines.append(f"- `{session}`: {count}")
    lines.extend(
        [
            "",
            "No setup contributes more than three training images. Validation includes three independent-session holdouts and three same-session pose/framing holdouts.",
            "",
            "## Explicit exclusions",
            "",
        ]
    )
    exclusion_counts = Counter(exclusions.values())
    for category, count in sorted(exclusion_counts.items()):
        lines.append(f"- `{category}`: {count}")
    lines.extend(
        [
            "",
            "See `manifest.json` for source paths, exact SHA-256 hashes, dimensions, captions, review rationale, and every excluded filename.",
            "",
            "Rebuild deterministically from the reviewed source folder with:",
            "",
            "```powershell",
            "python scripts/build-mitch-identity-stills-v3.py --force",
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(source_dir)

    exclusions = validate_inventory(source_dir)
    prepare_output(output_dir, args.force)
    train_dir = output_dir / "dataset"
    validation_dir = output_dir / "validation"

    records = [copy_photo(photo, source_dir, train_dir, "train") for photo in TRAINING]
    records.extend(
        copy_photo(photo, source_dir, validation_dir, "validation") for photo in VALIDATION
    )

    train_hashes = {record["dataset_sha256"] for record in records if record["split"] == "train"}
    validation_hashes = {
        record["dataset_sha256"] for record in records if record["split"] == "validation"
    }
    if len(train_hashes) != len(TRAINING):
        raise RuntimeError("Exact duplicate content exists inside the training split")
    if len(validation_hashes) != len(VALIDATION):
        raise RuntimeError("Exact duplicate content exists inside the validation split")
    if overlap := train_hashes & validation_hashes:
        raise RuntimeError(f"Training/validation hash overlap: {sorted(overlap)}")

    train_records = [record for record in records if record["split"] == "train"]
    validation_records = [record for record in records if record["split"] == "validation"]
    make_contact_sheet(
        train_records,
        output_dir / "review" / "training-contact-sheet.jpg",
        f"Mitch identity stills v3 - training ({len(train_records)})",
    )
    make_contact_sheet(
        validation_records,
        output_dir / "review" / "validation-contact-sheet.jpg",
        f"Mitch identity stills v3 - held-out validation ({len(validation_records)})",
    )

    manifest = {
        "schema_version": 1,
        "dataset": "mitch-identity-stills-v3",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "trigger_word": TRIGGER,
        "ai_toolkit_training_folder": str(train_dir),
        "caption_extension": "txt",
        "training_image_count": len(train_records),
        "validation_image_count": len(validation_records),
        "training_session_counts": dict(
            sorted(Counter(record["session"] for record in train_records).items())
        ),
        "source_policy": "Genuine user-owned JPG/PNG camera stills only. All MP4 sources and extracted video frames are excluded.",
        "pixel_policy": "Every selected dataset image is a byte-identical source copy. No crop, resize, enhancement, filtering, face restoration, alignment, or generative editing.",
        "caption_policy": f"Natural-language TXT sidecars with the stable identity trigger {TRIGGER} first. Variable pose, expression, framing, clothing, lighting, and scene are captioned rather than baked into the identity token.",
        "selection_policy": "Manual full-resolution visual review plus CPU face-similarity diagnostics; current identity coverage, facial geometry, expression, framing, clothing, lighting, and source-session diversity favored over raw image count.",
        "identity_similarity_note": "Optional diagnostic cosine scores are from the local InsightFace audit against a four-photo current-identity centroid. They are screening evidence, not a guarantee of generated likeness.",
        "records": records,
        "exclusions": [
            {"source": str(source_dir / name), "source_name": name, "reason": reason}
            for name, reason in sorted(exclusions.items())
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(output_dir, records, exclusions)

    print(
        json.dumps(
            {
                "output": str(output_dir),
                "training_folder": str(train_dir),
                "trigger": TRIGGER,
                "training_images": len(train_records),
                "validation_images": len(validation_records),
                "excluded_media": len(exclusions),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
