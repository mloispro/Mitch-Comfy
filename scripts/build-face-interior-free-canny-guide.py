#!/usr/bin/env python3
"""Build a Canny layout guide while removing one face's internal feature edges.

The outer detected-face boundary is deliberately retained so the guide still
constrains head position and scale. Only an inset ellipse covering the eyes,
nose, and mouth is cleared to avoid imposing the source person's identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from kornia.filters import canny
from PIL import Image, ImageDraw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-input-sha256", required=True)
    parser.add_argument("--face-bbox", nargs=4, type=float, required=True, metavar=("X1", "Y1", "X2", "Y2"))
    parser.add_argument("--low-threshold", type=float, default=0.20)
    parser.add_argument("--high-threshold", type=float, default=0.60)
    parser.add_argument("--x-inset", type=float, default=0.12)
    parser.add_argument("--top-inset", type=float, default=0.16)
    parser.add_argument("--bottom-inset", type=float, default=0.12)
    parser.add_argument("--head-region", nargs=4, type=float, metavar=("X1", "Y1", "X2", "Y2"))
    parser.add_argument("--head-scale", type=float, default=1.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    args = parse_args()
    actual_hash = sha256(args.input)
    if actual_hash != args.expected_input_sha256.upper():
        raise SystemExit(f"input hash mismatch: {actual_hash}")
    if not 0.0 < args.low_threshold < args.high_threshold < 1.0:
        raise SystemExit("thresholds must satisfy 0 < low < high < 1")

    source = Image.open(args.input).convert("RGB")
    source_tensor = torch.from_numpy(__import__("numpy").array(source)).float().div(255.0)
    source_tensor = source_tensor.permute(2, 0, 1).unsqueeze(0)
    edges = canny(source_tensor, args.low_threshold, args.high_threshold)[1]
    edge_array = edges[0, 0].mul(255.0).round().clamp(0, 255).byte().numpy()
    guide = Image.fromarray(edge_array, mode="L").convert("RGB")

    x1, y1, x2, y2 = args.face_bbox
    transformed_region = None
    if args.head_region:
        if not 0.5 <= args.head_scale <= 1.0:
            raise SystemExit("head-scale must be between 0.5 and 1.0")
        rx1, ry1, rx2, ry2 = (round(value) for value in args.head_region)
        region_width = rx2 - rx1
        region_height = ry2 - ry1
        if region_width <= 0 or region_height <= 0:
            raise SystemExit("head-region must have positive width and height")
        crop = guide.crop((rx1, ry1, rx2, ry2))
        scaled_size = (
            max(1, round(region_width * args.head_scale)),
            max(1, round(region_height * args.head_scale)),
        )
        crop = crop.resize(scaled_size, resample=Image.Resampling.NEAREST)
        paste_x = round((rx1 + rx2 - scaled_size[0]) / 2)
        paste_y = round((ry1 + ry2 - scaled_size[1]) / 2)
        ImageDraw.Draw(guide).rectangle((rx1, ry1, rx2, ry2), fill=(0, 0, 0))
        guide.paste(crop, (paste_x, paste_y))
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        half_width = (x2 - x1) * args.head_scale / 2
        half_height = (y2 - y1) * args.head_scale / 2
        x1, y1, x2, y2 = (
            center_x - half_width,
            center_y - half_height,
            center_x + half_width,
            center_y + half_height,
        )
        transformed_region = [rx1, ry1, rx2, ry2]

    width = x2 - x1
    height = y2 - y1
    interior = (
        round(x1 + width * args.x_inset),
        round(y1 + height * args.top_inset),
        round(x2 - width * args.x_inset),
        round(y2 - height * args.bottom_inset),
    )
    ImageDraw.Draw(guide).ellipse(interior, fill=(0, 0, 0))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    guide.save(args.output, format="PNG", compress_level=9)

    print(json.dumps({
        "input": str(args.input.resolve()),
        "input_sha256": actual_hash,
        "output": str(args.output.resolve()),
        "output_sha256": sha256(args.output),
        "size": [source.width, source.height],
        "low_threshold": args.low_threshold,
        "high_threshold": args.high_threshold,
        "face_bbox": list(args.face_bbox),
        "transformed_head_region": transformed_region,
        "head_scale": args.head_scale,
        "transformed_face_bbox": [x1, y1, x2, y2],
        "cleared_interior_ellipse": list(interior),
    }, indent=2))


if __name__ == "__main__":
    main()
