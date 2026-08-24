from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply a restrained, deterministic whole-frame phone-camera finish. "
            "No region masks, generative edits, relighting, or selective sharpening are used."
        )
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=9472103)
    parser.add_argument("--luma-sigma", type=float, default=0.65)
    parser.add_argument("--chroma-sigma", type=float, default=0.18)
    parser.add_argument("--jpeg-quality", type=int, default=95)
    return parser.parse_args()


def apply_phone_finish(
    image: Image.Image,
    *,
    seed: int,
    luma_sigma: float,
    chroma_sigma: float,
) -> Image.Image:
    source = image.convert("RGB")

    # A tiny whole-frame edge response resembles ordinary phone processing while
    # remaining below the level that creates a selectively sharpened subject.
    sharpened = source.filter(ImageFilter.UnsharpMask(radius=0.55, percent=12, threshold=4))
    pixels = np.asarray(sharpened, dtype=np.float32)

    rng = np.random.default_rng(seed)
    luminance = (
        0.2126 * pixels[..., 0]
        + 0.7152 * pixels[..., 1]
        + 0.0722 * pixels[..., 2]
    ) / 255.0
    shadow_weight = 0.72 + 0.42 * (1.0 - luminance)

    luma = rng.normal(0.0, luma_sigma, luminance.shape) * shadow_weight
    chroma_blue = rng.normal(0.0, chroma_sigma, luminance.shape)
    chroma_red = rng.normal(0.0, chroma_sigma, luminance.shape)
    noise = np.stack(
        (
            luma + 0.80 * chroma_red,
            luma - 0.40 * chroma_red - 0.40 * chroma_blue,
            luma + 0.80 * chroma_blue,
        ),
        axis=-1,
    )

    finished = np.clip(pixels + noise, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(finished, mode="RGB")


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if not input_path.is_file():
        raise RuntimeError(f"Input image does not exist: {input_path}")
    if output_path.suffix.lower() not in {".jpg", ".jpeg"}:
        raise RuntimeError("The phone-finish output must be a JPEG file.")
    if not 85 <= args.jpeg_quality <= 100:
        raise RuntimeError("--jpeg-quality must be between 85 and 100.")

    with Image.open(input_path) as source:
        source_rgb = source.convert("RGB")
        finished = apply_phone_finish(
            source_rgb,
            seed=args.seed,
            luma_sigma=args.luma_sigma,
            chroma_sigma=args.chroma_sigma,
        )

    # Encode once with ordinary high-quality 4:2:0 chroma response, matching the
    # kind of subtle compression a phone/social-photo pipeline normally introduces.
    encoded = io.BytesIO()
    finished.save(
        encoded,
        format="JPEG",
        quality=args.jpeg_quality,
        subsampling=2,
        optimize=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(encoded.getvalue())

    with Image.open(output_path) as decoded:
        decoded_pixels = np.asarray(decoded.convert("RGB"), dtype=np.int16)
    source_pixels = np.asarray(source_rgb, dtype=np.int16)
    delta = np.abs(decoded_pixels - source_pixels)
    report = {
        "input": str(input_path),
        "output": str(output_path),
        "dimensions": list(source_rgb.size),
        "seed": args.seed,
        "luma_sigma": args.luma_sigma,
        "chroma_sigma": args.chroma_sigma,
        "jpeg_quality": args.jpeg_quality,
        "whole_frame_only": True,
        "mean_absolute_pixel_delta": round(float(delta.mean()), 4),
        "p95_absolute_pixel_delta": round(float(np.percentile(delta, 95)), 4),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
