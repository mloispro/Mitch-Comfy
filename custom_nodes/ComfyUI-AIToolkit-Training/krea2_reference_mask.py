from __future__ import annotations

import threading
from typing import Iterable

import numpy as np
import torch


_ANALYZER = None
_ANALYZER_LOCK = threading.Lock()


def _get_face_analyzer():
    """Load the existing local AntelopeV2 detector on CPU, once per worker."""

    global _ANALYZER
    if _ANALYZER is not None:
        return _ANALYZER
    with _ANALYZER_LOCK:
        if _ANALYZER is None:
            from insightface.app import FaceAnalysis

            analyzer = FaceAnalysis(
                name="antelopev2",
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection"],
            )
            analyzer.prepare(ctx_id=-1, det_size=(640, 640), det_thresh=0.35)
            _ANALYZER = analyzer
    return _ANALYZER


def _largest_face(faces: Iterable):
    faces = list(faces)
    if not faces:
        raise RuntimeError(
            "No face was detected in the identity reference. Use a clear genuine photo "
            "with visible eyes, forehead, cheeks, and jaw."
        )
    return max(
        faces,
        key=lambda face: float(
            max(0.0, face.bbox[2] - face.bbox[0])
            * max(0.0, face.bbox[3] - face.bbox[1])
        ),
    )


def internal_face_oval(
    image_height: int,
    image_width: int,
    bbox,
    width_scale: float = 0.82,
    height_scale: float = 0.86,
    vertical_offset: float = 0.02,
) -> torch.Tensor:
    """Return a binary internal-face ellipse in reference-image pixel space."""

    x0, y0, x1, y1 = [float(value) for value in bbox]
    box_width = max(2.0, x1 - x0)
    box_height = max(2.0, y1 - y0)
    center_x = (x0 + x1) * 0.5
    center_y = (y0 + y1) * 0.5 + box_height * float(vertical_offset)
    radius_x = max(1.0, box_width * float(width_scale) * 0.5)
    radius_y = max(1.0, box_height * float(height_scale) * 0.5)

    ys = torch.arange(image_height, dtype=torch.float32).view(-1, 1)
    xs = torch.arange(image_width, dtype=torch.float32).view(1, -1)
    distance = ((xs - center_x) / radius_x) ** 2 + ((ys - center_y) / radius_y) ** 2
    return (distance <= 1.0).to(dtype=torch.float32)


class Krea2ReferenceFaceAttentionMask:
    """Boost identity tokens inside the reference face without masking output pixels."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "width_scale": (
                    "FLOAT",
                    {"default": 0.82, "min": 0.50, "max": 1.00, "step": 0.01},
                ),
                "height_scale": (
                    "FLOAT",
                    {"default": 0.86, "min": 0.50, "max": 1.00, "step": 0.01},
                ),
                "vertical_offset": (
                    "FLOAT",
                    {"default": 0.02, "min": -0.20, "max": 0.20, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("reference_attention_mask",)
    FUNCTION = "build"
    CATEGORY = "image/conditioning/Krea2"
    DESCRIPTION = (
        "Detects the largest face in a reference image and returns an internal-face oval for "
        "Krea2EditModelPatch.ref_boost_mask. This changes reference attention only; it never "
        "masks, composites, or edits output pixels."
    )

    def build(self, image, width_scale, height_scale, vertical_offset):
        analyzer = _get_face_analyzer()
        masks = []
        for frame in image:
            rgb = frame.detach().cpu().numpy()
            bgr = np.ascontiguousarray(
                np.clip(rgb[..., :3] * 255.0, 0, 255).astype(np.uint8)[..., ::-1]
            )
            face = _largest_face(analyzer.get(bgr))
            masks.append(
                internal_face_oval(
                    int(frame.shape[0]),
                    int(frame.shape[1]),
                    face.bbox,
                    width_scale=float(width_scale),
                    height_scale=float(height_scale),
                    vertical_offset=float(vertical_offset),
                )
            )
        return (torch.stack(masks, dim=0),)
