from __future__ import annotations

import cv2
import numpy as np
import torch


PHONE_FINISH_SEED = 20260823


def apply_natural_phone_finish(image: torch.Tensor) -> tuple[torch.Tensor, dict]:
    """Unify scene/subject rendering into a restrained ordinary-phone response."""
    source = np.clip(image.detach().float().cpu().numpy(), 0.0, 1.0)
    output = []
    for batch_index, frame in enumerate(source):
        rgb = np.clip(frame * 255.0, 0, 255).astype(np.uint8)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] *= 0.94
        subdued = cv2.cvtColor(
            np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB
        ).astype(np.float32)
        subdued = 127.5 + (subdued - 127.5) * 0.97
        softened = cv2.GaussianBlur(subdued, (0, 0), sigmaX=0.42, sigmaY=0.42)
        rng = np.random.default_rng(PHONE_FINISH_SEED + batch_index)
        luminance_noise = rng.normal(0.0, 0.55, softened.shape[:2]).astype(np.float32)
        softened += luminance_noise[:, :, None]
        softened = np.clip(softened, 0, 255).astype(np.uint8)
        success, encoded = cv2.imencode(
            ".jpg", cv2.cvtColor(softened, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95]
        )
        if success:
            softened = cv2.cvtColor(cv2.imdecode(encoded, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        output.append(softened.astype(np.float32) / 255.0)
    tensor = torch.from_numpy(np.stack(output)).to(dtype=image.dtype)
    return tensor, {
        "applied": True,
        "method": "restrained_phone_sensor_and_compression_finish",
        "saturation_scale": 0.94,
        "contrast_scale": 0.97,
        "optical_softening_sigma": 0.42,
        "luminance_noise_sigma_8bit": 0.55,
        "jpeg_quality": 95,
        "extra_model_passes": 0,
    }
