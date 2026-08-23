from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SceneCrop:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


_FRAMING = {
    "Head and shoulders": {
        "target_face_fraction": 0.28,
        "no_crop_face_fraction": 0.22,
        "min_height_fraction": 0.34,
        "max_height_fraction": 0.55,
        "face_center_fraction": 0.38,
    },
    "Waist-up": {
        "target_face_fraction": 0.16,
        "no_crop_face_fraction": 0.13,
        "min_height_fraction": 0.50,
        "max_height_fraction": 0.75,
        "face_center_fraction": 0.30,
    },
    "Prompt decides": {
        "target_face_fraction": 0.12,
        "no_crop_face_fraction": 0.10,
        "min_height_fraction": 0.65,
        "max_height_fraction": 1.0,
        "face_center_fraction": 0.34,
    },
}


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def face_aware_scene_crop(
    image_width: int,
    image_height: int,
    face_bbox: tuple[float, float, float, float] | list[float],
    framing: str,
    output_width: int,
    output_height: int,
) -> SceneCrop:
    """Return a deterministic crop that promotes the layout subject without losing context."""
    if min(image_width, image_height, output_width, output_height) <= 0:
        raise ValueError("Image and output dimensions must be positive.")
    if len(face_bbox) != 4:
        raise ValueError("face_bbox must contain left, top, right, and bottom.")

    if framing == "Full body":
        return SceneCrop(0, 0, image_width, image_height)

    settings = _FRAMING.get(framing, _FRAMING["Prompt decides"])
    x1, y1, x2, y2 = [float(value) for value in face_bbox]
    face_width = max(1.0, x2 - x1)
    face_height = max(1.0, y2 - y1)
    face_center_x = (x1 + x2) * 0.5
    face_center_y = (y1 + y2) * 0.5

    if face_height / image_height >= settings["no_crop_face_fraction"]:
        return SceneCrop(0, 0, image_width, image_height)

    minimum_height = image_height * settings["min_height_fraction"]
    maximum_height = image_height * settings["max_height_fraction"]
    desired_height = face_height / settings["target_face_fraction"]
    crop_height = int(round(max(minimum_height, min(desired_height, maximum_height))))
    crop_height = _clamp(crop_height, 1, image_height)

    output_aspect = output_width / output_height
    crop_width = int(round(crop_height * output_aspect))
    if crop_width > image_width:
        crop_width = image_width
        crop_height = min(image_height, int(round(crop_width / output_aspect)))

    desired_top = int(
        round(face_center_y - crop_height * settings["face_center_fraction"])
    )
    top = _clamp(desired_top, 0, image_height - crop_height)

    # Keep the face close to center while leaving a small amount of look room for
    # a three-quarter pose. The scene model decides which side gets that space.
    horizontal_bias = (face_width * 0.12) if face_center_x < image_width * 0.5 else -(face_width * 0.12)
    desired_left = int(round(face_center_x + horizontal_bias - crop_width * 0.5))
    left = _clamp(desired_left, 0, image_width - crop_width)
    return SceneCrop(left, top, left + crop_width, top + crop_height)
