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
from .flux2_klein9b_appearance_polish import (
    APPEARANCE_POLISH_LABEL_OFF,
    APPEARANCE_POLISH_LABEL_ON,
)
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
from .flux2_klein9b_smartphone_style import (
    SMARTPHONE_STYLE_LORA_NAME,
    SMARTPHONE_STYLE_LORA_STRENGTH,
    apply_smartphone_style_trigger,
    smartphone_style_report,
    verify_smartphone_style_lora,
)
from .flux2_klein9b_turbo import (
    TURBO_LORA_NAME,
    TURBO_LORA_STRENGTH,
    TURBO_MODE_LABEL_OFF,
    TURBO_MODE_LABEL_ON,
    sampling_settings,
    turbo_mode_report,
    verify_turbo_lora,
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
PROMPTING_STRATEGY = "bfl-flux2-concise-face-free-layout-native-identity-v2"
DEFAULT_SCENE_PROMPT = (
    "Create one photorealistic vertical phone-flash group photograph matching Picture 1. Four adults sit closely "
    "on the rust-orange booth, with a partial fifth person at the extreme image-right edge. The central seated man "
    "is m1tch_person from Picture 2, wearing a fitted dark navy suit and crisp white open-collar shirt. Match his real "
    "balanced head width, moderately broad forehead and upper cheeks, straight jaw sides, rounded chin, facial-feature "
    "spacing, hairline, apparent age, and natural skin. Give him a calm pleasant expression: his lips rest gently "
    "together, their corners rise only slightly, his jaw and cheeks remain relaxed, and his eyes engage softly with "
    "the camera. Both complete forearms extend down and his separate hands rest on his thighs. Keep every surrounding "
    "person distinct and unrelated. Preserve the copper wall, amber perimeter light, booth, low table, ordinary "
    "smartphone perspective, direct flash, and seamless natural detail."
)
GROUP_IDENTITY_SAFE_POLISH = (
    "Keep the same recognizable current-age face and expression. Improve only photographic presentation with natural "
    "pores, tidy faint stubble, healthy but authentic skin color, and clean natural eye catchlights. Do not change the "
    "head shape, facial geometry, feature spacing, apparent age, or expression supplied by Picture 2."
)


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


def compose_group_prompt(scene_prompt: str, appearance_polish: bool = False) -> str:
    scene = " ".join(scene_prompt.strip().split())
    if not scene:
        raise ValueError("Describe the complete group photograph before queuing.")
    contract = (
        "Picture 1 is a Canny edge map derived from the source photograph and supplies its camera framing, person "
        "positions, seated body poses, outer head sizes, arm positions, booth geometry, table placement, and spatial "
        "layout. The selected source person's internal eye, nose, and mouth edges were intentionally removed so "
        "Picture 1 does not supply his identity. Picture 2 is a genuine photograph of m1tch_person and exclusively "
        "supplies the selected man's identity and internal facial geometry."
    )
    parts = [contract, scene]
    if appearance_polish:
        parts.append(GROUP_IDENTITY_SAFE_POLISH)
    return " ".join(parts)


class Flux2Klein9BMitchGroupSceneStudioV1:
    """Approved reusable group-scene workflow with face-free structural conditioning."""

    def _prepare_sampling_model(self, model, *, steps, guidance):
        """Per-invocation extension seam; the original production path is a no-op."""
        return model, None

    def _generation_output_root(self):
        return OUTPUT_ROOT

    def _finalize_sampling_report(self, report, sampling_metadata):
        """Original production reports are unchanged; adapters override locally."""
        return report

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_scene": ("IMAGE",),
                "scene_prompt": (
                    "STRING",
                    {
                        "default": DEFAULT_SCENE_PROMPT,
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
                "appearance_polish": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": APPEARANCE_POLISH_LABEL_ON,
                        "label_off": APPEARANCE_POLISH_LABEL_OFF,
                    },
                ),
                "fast_turbo": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": TURBO_MODE_LABEL_ON,
                        "label_off": TURBO_MODE_LABEL_OFF,
                    },
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
    def VALIDATE_INPUTS(
        cls,
        source_scene,
        scene_prompt,
        target_x,
        target_y,
        head_scale,
        appearance_polish,
        fast_turbo,
        seed,
    ):
        try:
            compose_group_prompt(scene_prompt, appearance_polish)
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

    def generate(
        self,
        source_scene,
        scene_prompt,
        target_x,
        target_y,
        head_scale,
        appearance_polish,
        fast_turbo,
        seed,
    ):
        validation = self.VALIDATE_INPUTS(
            source_scene,
            scene_prompt,
            target_x,
            target_y,
            head_scale,
            appearance_polish,
            fast_turbo,
            seed,
        )
        if validation is not True:
            raise RuntimeError(validation)

        gpu = _assert_rtx3090()
        baseline._require_model("diffusion_models", MODEL_NAME)
        baseline._require_model("text_encoders", CLIP_NAME)
        baseline._require_model("vae", VAE_NAME)
        lora_path = _lora_path()
        smartphone_style_path = verify_smartphone_style_lora()
        turbo_path = verify_turbo_lora() if fast_turbo else None
        steps, guidance = sampling_settings(fast_turbo, STEPS, GUIDANCE)
        identity_path = _identity_reference_path()
        effective_prompt = apply_smartphone_style_trigger(
            compose_group_prompt(scene_prompt, appearance_polish)
        )
        layout_guide, guide_report = build_face_free_layout(
            source_scene, target_x, target_y, head_scale
        )
        started = time.perf_counter()

        model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
        if fast_turbo:
            model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
                model, TURBO_LORA_NAME, TURBO_LORA_STRENGTH
            )[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, LORA_NAME, LORA_STRENGTH
        )[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, SMARTPHONE_STYLE_LORA_NAME, SMARTPHONE_STYLE_LORA_STRENGTH
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

        model, sampling_metadata = self._prepare_sampling_model(
            model, steps=steps, guidance=guidance
        )
        guider = CFGGuider.execute(model, positive, negative, guidance)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        sigmas = Flux2Scheduler.execute(steps, WIDTH, HEIGHT)[0]
        noise = RandomNoise.execute(int(seed))[0]
        latent_image = EmptyFlux2LatentImage.execute(WIDTH, HEIGHT, 1)[0]
        sampled = SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent_image
        )[0]
        photo = comfy_nodes.VAEDecode().decode(vae, sampled)[0]

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"{self._generation_output_root()}/{run_stamp}"
        lora_load_order = []
        if fast_turbo:
            lora_load_order.append(
                {
                    "name": TURBO_LORA_NAME,
                    "strength": TURBO_LORA_STRENGTH,
                    "role": "8-step acceleration",
                }
            )
        lora_load_order.extend(
            [
                {"name": LORA_NAME, "strength": LORA_STRENGTH, "role": "identity"},
                {
                    "name": SMARTPHONE_STYLE_LORA_NAME,
                    "strength": SMARTPHONE_STYLE_LORA_STRENGTH,
                    "role": "whole-frame smartphone realism",
                },
            ]
        )
        report = {
            "schema_version": 1,
            "purpose": "flux2_klein9b_mitch_group_scene_studio_v1",
            "approval_basis": (
                "Mitch visually approved the locked lounge result on 2026-08-31; the concise identity-first prompt "
                "with Smartphone Snapshot v13 was revalidated on 2026-09-01"
            ),
            "gpu": gpu,
            "model": MODEL_NAME,
            "text_encoder": CLIP_NAME,
            "vae": VAE_NAME,
            "lora": LORA_NAME,
            "lora_path": str(lora_path),
            "lora_sha256": LORA_SHA256,
            "lora_strength": LORA_STRENGTH,
            "trigger": "m1tch_person",
            "turbo_mode": turbo_mode_report(fast_turbo, turbo_path, 1 if fast_turbo else None),
            "smartphone_style": {
                **smartphone_style_report(),
                "path": smartphone_style_path,
                "load_order": 3 if fast_turbo else 2,
            },
            "lora_load_order": lora_load_order,
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
            "appearance_polish": bool(appearance_polish),
            "fast_turbo": bool(fast_turbo),
            "scene_prompt": scene_prompt.strip(),
            "effective_prompt": effective_prompt,
            "width": WIDTH,
            "height": HEIGHT,
            "steps": steps,
            "guidance": guidance,
            "sampler": "euler",
            "scheduler": "Flux2Scheduler",
            "seed": int(seed),
            "seconds": round(time.perf_counter() - started, 3),
            "manual_review_required": [
                "identity at full size and thumbnail",
                "internal eye, nose, mouth, cheek, and jaw relationships against genuine references",
                "exactly one Mitch",
                "selected target face and head scale",
                "complete limbs, coherent hands, and body proportions",
                "whole-frame integration and scene fidelity",
            ],
        }
        report = self._finalize_sampling_report(report, sampling_metadata)
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
