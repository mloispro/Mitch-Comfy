from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import cv2
import folder_paths
import node_helpers
import nodes as comfy_nodes
import numpy as np
import torch
from comfy_extras.nodes_custom_sampler import (
    CFGGuider,
    KSamplerSelect,
    RandomNoise,
    SamplerCustomAdvanced,
)
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler
from kornia.filters import canny
from PIL import Image, ImageDraw

from . import one_reference_photo as baseline
from .flux2_klein9b_mitch_identity_studio import (
    CLIP_NAME,
    GUIDANCE,
    HEIGHT,
    LORA_NAME,
    LORA_SHA256,
    LORA_STRENGTH,
    MODEL_NAME,
    STEPS,
    VAE_NAME,
    WIDTH,
    _assert_rtx3090,
    _verify_sha256,
)


IDENTITY_REFERENCE = "mitch-klein9b-ref-training04-front-neutral.jpg"
IDENTITY_REFERENCE_SHA256 = "31870369467B7A8FC19199D7877F56257FED2B0F28B08AA183006BCD3112DDAB"
SCENE_REFERENCE_PIXELS = 250_000
IDENTITY_REFERENCE_PIXELS = 1_000_000
DEFAULT_HEAD_SCALE = 0.92
DEFAULT_TARGET_X = 0.50
DEFAULT_TARGET_Y = 0.44
DEFAULT_CANNY_LOW = 0.20
DEFAULT_CANNY_HIGH = 0.60
OUTPUT_ROOT = "flux2-klein9b-mitch-group-scene-studio-v1"
PROMPTING_STRATEGY = "bfl-flux2-face-free-layout-native-identity-v1"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _identity_reference_path() -> Path:
    path = Path(folder_paths.get_input_directory()) / IDENTITY_REFERENCE
    if not path.is_file():
        raise RuntimeError(f"Missing protected genuine identity reference: {path}")
    _verify_sha256(path, IDENTITY_REFERENCE_SHA256, "Group Studio genuine identity reference")
    return path


def _lora_path() -> Path:
    path = folder_paths.get_full_path("loras", LORA_NAME)
    if not path:
        raise RuntimeError(f"Missing protected Klein 9B step-1600 LoRA: {LORA_NAME}")
    resolved = Path(path)
    _verify_sha256(resolved, LORA_SHA256, "Klein 9B step-1600 LoRA")
    return resolved


def _select_face(faces, width: int, height: int, target_x: float, target_y: float):
    if not faces:
        raise RuntimeError("No face was detected in the source group photograph.")
    target_px = float(target_x) * width
    target_py = float(target_y) * height

    def distance(face) -> float:
        x1, y1, x2, y2 = (float(value) for value in face.bbox)
        center_x = (x1 + x2) * 0.5
        center_y = (y1 + y2) * 0.5
        return ((center_x - target_px) / width) ** 2 + ((center_y - target_py) / height) ** 2

    return min(faces, key=distance)


def _face_free_layout_from_bbox(
    image: torch.Tensor,
    bbox,
    head_scale: float,
    canny_low: float = DEFAULT_CANNY_LOW,
    canny_high: float = DEFAULT_CANNY_HIGH,
) -> tuple[torch.Tensor, dict]:
    """Create the approved structural guide from a known source-face bounding box."""
    if image.ndim != 4 or image.shape[0] < 1 or image.shape[-1] < 3:
        raise ValueError("source_scene must be a ComfyUI IMAGE tensor")
    if not 0.75 <= float(head_scale) <= 1.0:
        raise ValueError("head_scale must be between 0.75 and 1.00")
    if not 0.01 <= float(canny_low) < float(canny_high) <= 0.99:
        raise ValueError("Canny thresholds must satisfy 0.01 <= low < high <= 0.99")

    source = image[:1, :, :, :3].detach().float().cpu()
    height, width = (int(source.shape[1]), int(source.shape[2]))
    edges = canny(source.movedim(-1, 1), float(canny_low), float(canny_high))[1]
    edge_array = edges[0, 0].mul(255.0).round().clamp(0, 255).byte().numpy()
    guide = Image.fromarray(edge_array, mode="L").convert("RGB")

    original_bbox = [float(value) for value in bbox]
    x1, y1, x2, y2 = original_bbox
    face_width = max(x2 - x1, 1.0)
    face_height = max(y2 - y1, 1.0)
    region = (
        max(0, round(x1 - 0.16 * face_width)),
        max(0, round(y1 - 0.35 * face_height)),
        min(width, round(x2 + 0.16 * face_width)),
        min(height, round(y2 + 0.04 * face_height)),
    )
    rx1, ry1, rx2, ry2 = region
    region_width = max(rx2 - rx1, 1)
    region_height = max(ry2 - ry1, 1)
    scaled_size = (
        max(1, round(region_width * float(head_scale))),
        max(1, round(region_height * float(head_scale))),
    )
    crop = guide.crop(region).resize(scaled_size, resample=Image.Resampling.NEAREST)
    paste_x = round((rx1 + rx2 - scaled_size[0]) / 2)
    paste_y = round((ry1 + ry2 - scaled_size[1]) / 2)
    ImageDraw.Draw(guide).rectangle(region, fill=(0, 0, 0))
    guide.paste(crop, (paste_x, paste_y))

    center_x = (x1 + x2) * 0.5
    center_y = (y1 + y2) * 0.5
    transformed_width = face_width * float(head_scale)
    transformed_height = face_height * float(head_scale)
    transformed_bbox = (
        center_x - transformed_width * 0.5,
        center_y - transformed_height * 0.5,
        center_x + transformed_width * 0.5,
        center_y + transformed_height * 0.5,
    )
    tx1, ty1, tx2, ty2 = transformed_bbox
    interior = (
        round(tx1 + transformed_width * 0.12),
        round(ty1 + transformed_height * 0.16),
        round(tx2 - transformed_width * 0.12),
        round(ty2 - transformed_height * 0.12),
    )
    ImageDraw.Draw(guide).ellipse(interior, fill=(0, 0, 0))

    guide_array = np.asarray(guide, dtype=np.float32) / 255.0
    guide_tensor = torch.from_numpy(guide_array.copy()).unsqueeze(0)
    report = {
        "source_size": [width, height],
        "selected_face_bbox": [round(value, 2) for value in original_bbox],
        "head_region": list(region),
        "head_scale": round(float(head_scale), 4),
        "transformed_face_bbox": [round(value, 2) for value in transformed_bbox],
        "cleared_interior_ellipse": list(interior),
        "canny_low": round(float(canny_low), 4),
        "canny_high": round(float(canny_high), 4),
    }
    return guide_tensor, report


def build_face_free_layout(
    source_scene: torch.Tensor,
    target_x: float,
    target_y: float,
    head_scale: float,
) -> tuple[torch.Tensor, dict]:
    source = source_scene[:1, :, :, :3].detach().float().cpu()
    height, width = (int(source.shape[1]), int(source.shape[2]))
    rgb = np.clip(source[0].numpy() * 255.0, 0, 255).astype(np.uint8)
    faces = baseline._face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    selected = _select_face(faces, width, height, target_x, target_y)
    guide, report = _face_free_layout_from_bbox(source, selected.bbox, head_scale)
    report.update(
        {
            "detected_face_count": len(faces),
            "target_position": [round(float(target_x), 4), round(float(target_y), 4)],
            "selection_method": "face center nearest target_position",
            "all_detected_face_bboxes": [
                [round(float(value), 2) for value in face.bbox] for face in faces
            ],
        }
    )
    return guide, report


def compose_group_prompt(scene_prompt: str) -> str:
    scene = " ".join(scene_prompt.strip().split())
    if not scene:
        raise ValueError("Describe the complete group photograph before queuing.")
    contract = (
        "Picture 1 is a face-free edge layout derived from the source group photograph. It supplies camera framing, "
        "person positions, body poses, outer head sizes, objects, and scene geometry. The selected source person's "
        "internal eye, nose, and mouth edges are absent, so Picture 1 supplies no identity for that person. Picture 2 "
        "is a genuine photograph of m1tch_person and exclusively supplies the selected man's identity and internal "
        "facial geometry."
    )
    identity = (
        "Render the selected man as m1tch_person with his balanced head width, moderately broad forehead and upper "
        "cheeks, straight jaw sides, rounded chin, natural feature spacing, hairline, apparent age, and skin. Give him "
        "a calm pleasant expression with lips resting gently together, mouth corners raised only slightly, relaxed jaw "
        "and cheeks, and eyes softly engaged with the camera. Every other person is unrelated and visually distinct; "
        "the photograph contains exactly one Mitch."
    )
    finish = (
        "Create one coherent photorealistic whole-frame phone photograph with natural detail, complete limbs, coherent "
        "hands, believable body proportions, and seamless integration. The final image is uncaptioned and unbranded."
    )
    return " ".join((contract, scene, identity, finish))


class Flux2Klein9BMitchGroupSceneStudioV1:
    """Approved reusable group-scene workflow with face-free structural conditioning."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_scene": ("IMAGE",),
                "scene_prompt": (
                    "STRING",
                    {
                        "default": (
                            "A photorealistic vertical phone-flash group photograph. Replace the person nearest the "
                            "target position with Mitch, seated naturally among distinct unrelated friends. Preserve "
                            "the source camera framing, people count, body poses, furniture, objects, and setting. "
                            "Mitch wears a fitted dark navy suit and crisp white open-collar shirt."
                        ),
                        "multiline": True,
                    },
                ),
                "target_x": (
                    "FLOAT",
                    {"default": DEFAULT_TARGET_X, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "target_y": (
                    "FLOAT",
                    {"default": DEFAULT_TARGET_Y, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "head_scale": (
                    "FLOAT",
                    {"default": DEFAULT_HEAD_SCALE, "min": 0.75, "max": 1.0, "step": 0.01},
                ),
                "seed": (
                    "INT",
                    {
                        "default": 8675412,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, source_scene, scene_prompt, target_x, target_y, head_scale, seed):
        try:
            compose_group_prompt(scene_prompt)
            if not 0.0 <= float(target_x) <= 1.0 or not 0.0 <= float(target_y) <= 1.0:
                return "target_x and target_y must be between 0 and 1"
            if not 0.75 <= float(head_scale) <= 1.0:
                return "head_scale must be between 0.75 and 1.00"
        except ValueError as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("photo", "layout_guide", "effective_prompt", "output_folder", "report_json")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity"
    OUTPUT_NODE = True

    def generate(self, source_scene, scene_prompt, target_x, target_y, head_scale, seed):
        validation = self.VALIDATE_INPUTS(
            source_scene, scene_prompt, target_x, target_y, head_scale, seed
        )
        if validation is not True:
            raise RuntimeError(validation)

        gpu = _assert_rtx3090()
        baseline._require_model("diffusion_models", MODEL_NAME)
        baseline._require_model("text_encoders", CLIP_NAME)
        baseline._require_model("vae", VAE_NAME)
        lora_path = _lora_path()
        identity_path = _identity_reference_path()
        effective_prompt = compose_group_prompt(scene_prompt)
        layout_guide, guide_report = build_face_free_layout(
            source_scene, target_x, target_y, head_scale
        )
        started = time.perf_counter()

        model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, LORA_NAME, LORA_STRENGTH
        )[0]
        clip = comfy_nodes.CLIPLoader().load_clip(CLIP_NAME, "flux2", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]

        positive = comfy_nodes.CLIPTextEncode().encode(clip, effective_prompt)[0]
        negative = comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
        scene_resized = baseline._resize_reference(layout_guide, SCENE_REFERENCE_PIXELS)
        scene_latent = comfy_nodes.VAEEncode().encode(vae, scene_resized)[0]["samples"]
        values = {"reference_latents": [scene_latent]}
        positive = node_helpers.conditioning_set_values(positive, values, append=True)
        negative = node_helpers.conditioning_set_values(negative, values, append=True)

        identity_image = comfy_nodes.LoadImage().load_image(IDENTITY_REFERENCE)[0][:1, :, :, :3]
        identity_resized = baseline._resize_reference(
            identity_image, IDENTITY_REFERENCE_PIXELS
        )
        identity_latent = comfy_nodes.VAEEncode().encode(vae, identity_resized)[0]["samples"]
        values = {"reference_latents": [identity_latent]}
        positive = node_helpers.conditioning_set_values(positive, values, append=True)
        negative = node_helpers.conditioning_set_values(negative, values, append=True)

        guider = CFGGuider.execute(model, positive, negative, GUIDANCE)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        sigmas = Flux2Scheduler.execute(STEPS, WIDTH, HEIGHT)[0]
        noise = RandomNoise.execute(int(seed))[0]
        latent_image = EmptyFlux2LatentImage.execute(WIDTH, HEIGHT, 1)[0]
        sampled = SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent_image
        )[0]
        photo = comfy_nodes.VAEDecode().decode(vae, sampled)[0]

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"{OUTPUT_ROOT}/{run_stamp}"
        report = {
            "schema_version": 1,
            "purpose": "flux2_klein9b_mitch_group_scene_studio_v1",
            "approval_basis": "Mitch visually approved the locked lounge result on 2026-08-31",
            "gpu": gpu,
            "model": MODEL_NAME,
            "text_encoder": CLIP_NAME,
            "vae": VAE_NAME,
            "lora": LORA_NAME,
            "lora_path": str(lora_path),
            "lora_sha256": LORA_SHA256,
            "lora_strength": LORA_STRENGTH,
            "trigger": "m1tch_person",
            "identity_reference": IDENTITY_REFERENCE,
            "identity_reference_path": str(identity_path),
            "identity_reference_sha256": IDENTITY_REFERENCE_SHA256,
            "reference_order": "Picture 1 face-free scene layout; Picture 2 Mitch identity",
            "scene_reference_megapixels": 0.25,
            "identity_reference_megapixels": 1.0,
            "guide": guide_report,
            "identity_mechanism": "step-1600 identity LoRA plus genuine native identity reference",
            "source_identity_removed_from_layout": True,
            "face_swap": False,
            "identity_pass": False,
            "restoration": False,
            "sharpening": False,
            "prompting_strategy": PROMPTING_STRATEGY,
            "scene_prompt": scene_prompt.strip(),
            "effective_prompt": effective_prompt,
            "width": WIDTH,
            "height": HEIGHT,
            "steps": STEPS,
            "guidance": GUIDANCE,
            "sampler": "euler",
            "scheduler": "Flux2Scheduler",
            "seed": int(seed),
            "seconds": round(time.perf_counter() - started, 3),
            "manual_review_required": [
                "identity at full size and thumbnail",
                "exactly one Mitch",
                "selected target face and head scale",
                "complete limbs, coherent hands, and body proportions",
                "whole-frame integration and scene fidelity",
            ],
        }
        saved = comfy_nodes.SaveImage().save_images(
            photo,
            f"{output_folder}/photo",
            extra_pnginfo={"flux2_klein9b_mitch_group_scene_studio_v1": report},
        )
        comfy_nodes.SaveImage().save_images(
            layout_guide,
            f"{output_folder}/layout-guide",
            extra_pnginfo={"flux2_klein9b_mitch_group_scene_studio_v1": report},
        )
        report_json = json.dumps(report, indent=2)
        report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")

        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (f"Saved Group Scene Studio result to ComfyUI/output/{output_folder}",),
            },
            "result": (photo, layout_guide, effective_prompt, output_folder, report_json),
        }
