from __future__ import annotations

import io

import numpy as np
import torch
from PIL import Image, ImageFilter


PHONE_FINISH_SEED = 9472103
LUMA_SIGMA = 0.65
CHROMA_SIGMA = 0.18
JPEG_QUALITY = 95


def phone_finish_frame(frame: torch.Tensor, seed: int = PHONE_FINISH_SEED) -> torch.Tensor:
    """Apply the validated subtle phone finish to one HWC float image."""

    pixels = frame.detach().cpu().numpy()
    rgb = np.clip(pixels[..., :3] * 255.0, 0, 255).astype(np.uint8)
    source = Image.fromarray(rgb, mode="RGB")
    sharpened = source.filter(ImageFilter.UnsharpMask(radius=0.55, percent=12, threshold=4))
    working = np.asarray(sharpened, dtype=np.float32)

    rng = np.random.default_rng(seed)
    luminance = (
        0.2126 * working[..., 0]
        + 0.7152 * working[..., 1]
        + 0.0722 * working[..., 2]
    ) / 255.0
    shadow_weight = 0.72 + 0.42 * (1.0 - luminance)
    luma = rng.normal(0.0, LUMA_SIGMA, luminance.shape) * shadow_weight
    chroma_blue = rng.normal(0.0, CHROMA_SIGMA, luminance.shape)
    chroma_red = rng.normal(0.0, CHROMA_SIGMA, luminance.shape)
    noise = np.stack(
        (
            luma + 0.80 * chroma_red,
            luma - 0.40 * chroma_red - 0.40 * chroma_blue,
            luma + 0.80 * chroma_blue,
        ),
        axis=-1,
    )
    finished = Image.fromarray(
        np.clip(working + noise, 0.0, 255.0).astype(np.uint8), mode="RGB"
    )

    encoded = io.BytesIO()
    finished.save(
        encoded,
        format="JPEG",
        quality=JPEG_QUALITY,
        subsampling=2,
        optimize=True,
    )
    encoded.seek(0)
    with Image.open(encoded) as decoded:
        result = np.asarray(decoded.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(result.copy())


class WholeFramePhoneFinish:
    """A fixed, CPU-only, non-generative finish validated for the Krea2 photo route."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",)}}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("finished_image",)
    FUNCTION = "finish"
    CATEGORY = "image/finishing"
    DESCRIPTION = (
        "Applies one fixed whole-frame phone response: very light global sharpening, "
        "fine luminance/chroma sensor texture, and a single quality-95 JPEG round trip. "
        "It uses no masks, detection, generation, relighting, or selective face processing."
    )

    def finish(self, image):
        frames = [
            phone_finish_frame(frame, seed=PHONE_FINISH_SEED + index)
            for index, frame in enumerate(image)
        ]
        return (torch.stack(frames, dim=0),)
