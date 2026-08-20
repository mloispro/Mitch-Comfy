from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps

import folder_paths
import nodes as comfy_nodes
import comfy.model_management
from comfy_extras.nodes_canny import Canny
from comfy_extras.nodes_model_advanced import ModelSamplingAuraFlow
from comfy_extras.nodes_model_patch import ModelPatchLoader, ZImageFunControlnet


WIDTH = 832
HEIGHT = 1216
STEPS = 25
CFG = 4.0
SHIFT = 3.0
LORA_STRENGTH = 0.9
CONTROL_STRENGTH = 0.7
MODEL_NAME = "z_image_bf16.safetensors"
TEXT_ENCODER_NAME = "qwen_3_4b_fp8_mixed.safetensors"
VAE_NAME = "ae.safetensors"
CONTROL_NAME = "Z-Image-Fun-Controlnet-Union-2.1-lite.safetensors"
TRIGGER = "zimg_person"

NEGATIVE_PROMPT = (
    "low resolution, blurry, soft focus, CGI, illustration, painting, plastic skin, waxy skin, "
    "overprocessed face, beauty filter, deformed anatomy, bad hands, extra fingers, missing fingers, "
    "extra limbs, duplicate main subject, two identical men, cloned face, malformed cat, distorted golf club, "
    "text, caption, watermark, logo, screenshot, interface, playback controls, white border, blank margin, "
    "picture frame, letterboxing"
)


@dataclass(frozen=True)
class Scene:
    key: str
    label: str
    seed: int
    prompt: str
    reference_file: str = ""
    crop: tuple[int, int, int, int] | None = None


SCENES = (
    Scene(
        "01-night-out-a",
        "Night Out — warm lounge",
        910462781,
        f"{TRIGGER}, highly realistic candid smartphone photograph of one handsome adult man seated centrally on "
        "a curved cognac leather banquette in an upscale amber-lit cocktail lounge, wearing a perfectly fitted "
        "dark navy suit and open-collar white shirt, relaxed confident posture, one arm along the seat, three "
        "distinct adult friends leaning in around him, two women and one man, everyone social and natural, drinks "
        "in hand, warm concealed lighting across a textured orange wall, full-body vertical composition, believable "
        "skin texture, mild phone-camera grain, spontaneous nightlife snapshot, the central man is the only person "
        "matching {TRIGGER}",
    ),
    Scene(
        "02-night-out-b",
        "Night Out — alternate group",
        1846503927,
        f"{TRIGGER}, photorealistic casual nightlife group photo, one handsome adult man centered on a caramel leather "
        "lounge sofa wearing a dark tailored suit and pale shirt, relaxed legs apart and hands naturally placed, one "
        "Black woman in an elegant black evening dress seated on his left, one Black woman in a warm brown cocktail "
        "dress and one clearly distinct Black male friend on his right, four clearly different people, no cropped "
        "partial people at either edge, champagne glasses "
        "and a low table in foreground, glowing amber wall and indirect strip lights, direct phone flash mixed with "
        "warm room light, vertical candid social photo, natural faces and hands, only the central man matches {TRIGGER}",
    ),
    Scene(
        "03-cat-ragdoll",
        "Cat Lover — Ragdoll",
        2837451096,
        f"{TRIGGER}, realistic indoor smartphone portrait of the same adult man standing in a modern neutral living "
        "room, black zip hoodie, smiling gently while cradling a large fluffy white-and-gray Ragdoll cat horizontally "
        "in both arms, affectionate eye contact with the cat, white curtains and beige sofa behind him, soft evening "
        "room light, natural skin and fabric texture, candid unposed vertical photo",
        "reference-grid.jpg",
        (630, 8, 902, 369),
    ),
    Scene(
        "04-cat-tabby",
        "Cat Lover — tabby",
        396128507,
        f"{TRIGGER}, authentic vertical phone photo of the same adult man in a loose black hoodie looking down tenderly "
        "at a plump gray-and-white tabby cat held securely against his chest, both hands visible and anatomically "
        "correct, quiet modern apartment with cream sofa and pale curtains, soft diffuse interior light, shallow depth "
        "of field, natural candid expression, lifelike fur and skin texture",
        "reference-grid.jpg",
        (9, 463, 281, 823),
    ),
    Scene(
        "05-golfer",
        "Golfer",
        1519374208,
        f"{TRIGGER}, realistic full-body vertical lifestyle photograph of the same adult man walking toward the camera "
        "on a manicured tropical golf course, fitted plain black T-shirt, charcoal tailored golf trousers, white golf "
        "glove, carrying one iron casually at his side, relaxed confident stride, vivid green fairway, palm trees and "
        "dense tropical landscaping, bright clear daylight, natural proportions, editorial smartphone realism",
        "reference-grid.jpg",
        (320, 463, 592, 823),
    ),
    Scene(
        "06-amalfi-balcony",
        "Amalfi balcony",
        2471059683,
        f"{TRIGGER}, premium but believable travel portrait of the same adult man standing at a balcony overlook above "
        "Positano on the Amalfi Coast, relaxed short-sleeve white linen resort shirt open at the collar, warm friendly "
        "smile, one hand resting near the railing, colorful cliffside houses, domed church and blue Mediterranean sea "
        "behind him, golden late-afternoon sunlight, natural skin texture, vertical 35mm travel photography",
        "reference-travel.jpg",
        (580, 338, 1050, 960),
    ),
    Scene(
        "07-lake-boat",
        "Italian lake boat",
        328470519,
        f"{TRIGGER}, photorealistic vertical vacation photograph of the same adult man sitting casually on the bow of "
        "a small luxury motorboat on Lake Como, crisp white linen shirt with sleeves rolled and collar open, tailored "
        "white shorts, dark sunglasses, hands resting on the boat rails, turquoise water, elegant villas and steep "
        "green mountains behind him, bright soft summer daylight, realistic reflections and anatomy, candid travel "
        "photo filling the entire canvas edge-to-edge with no border or blank margin",
        "reference-travel.jpg",
        (1067, 338, 1536, 960),
    ),
    Scene(
        "08-restaurant",
        "Elegant restaurant",
        4702981162,
        f"{TRIGGER}, sophisticated realistic evening portrait of the same adult man seated at a white-tablecloth table "
        "in an elegant intimate restaurant, tailored light-gray double-breasted suit over a black shirt, elbow on table "
        "and fingers resting thoughtfully near his chin, warm shaded table lamp illuminating his face, glowing arched "
        "doorway and indoor palm behind him, subtle jewelry, cinematic low light but authentic phone-camera texture, "
        "vertical composition, natural hand and facial anatomy",
        "reference-travel.jpg",
        (1554, 338, 2025, 960),
    ),
    Scene(
        "09-city-balcony-night",
        "City balcony at night",
        590174263,
        f"{TRIGGER}, highly realistic vertical nighttime phone photograph of the same adult man leaning back against a "
        "glass high-rise balcony railing, both arms extended naturally along the rail, fitted black short-sleeve button "
        "shirt open at the upper chest, dark trousers and understated wristwatch, head turned slightly down and to the "
        "side with a calm expression, vast sparkling city skyline far below, direct camera flash on the subject, deep "
        "teal-black sky, tasteful film grain, candid social-media nightlife portrait, correct hands and body proportions",
    ),
)


def _aitk_loras() -> list[str]:
    names = folder_paths.get_filename_list("loras")
    preferred = [name for name in names if name.replace("\\", "/").casefold().startswith("aitk/")]
    return preferred or [name for name in names if "zimage" in name.casefold() or "z_image" in name.casefold()]


def _require_model(folder_name: str, filename: str) -> None:
    if folder_paths.get_full_path(folder_name, filename) is None:
        raise RuntimeError(
            f"Required Z-Image file is missing: {filename}. The one-time model setup must finish before generating."
        )


def _reference_tensor(scene: Scene) -> torch.Tensor:
    if not scene.reference_file or scene.crop is None:
        raise RuntimeError(f"Scene {scene.key} has no reference crop")
    source = Path(__file__).parent / "assets" / "social_pack" / scene.reference_file
    with Image.open(source) as opened:
        image = opened.convert("RGB").crop(scene.crop)
        image = ImageOps.fit(image, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
        array = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(array).unsqueeze(0)


class AIToolkitGenerateNinePhotos:
    """Generate the fixed nine-photo social pack from one completed Z-Image LoRA."""

    @classmethod
    def INPUT_TYPES(cls):
        choices = _aitk_loras()
        if not choices:
            choices = ["No completed AI-Toolkit Z-Image LoRA found"]
        return {"required": {"lora_name": (choices,)}, "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("nine_photos", "output_folder")
    FUNCTION = "generate"
    CATEGORY = "image/generation/AI-Toolkit"
    OUTPUT_NODE = True

    def generate(self, lora_name: str, prompt: Any = None, extra_pnginfo: Any = None):
        available = _aitk_loras()
        if lora_name not in available:
            raise RuntimeError("Select a completed AI-Toolkit Z-Image LoRA from the LoRA menu.")
        _require_model("diffusion_models", MODEL_NAME)
        _require_model("text_encoders", TEXT_ENCODER_NAME)
        _require_model("vae", VAE_NAME)
        _require_model("model_patches", CONTROL_NAME)

        base_model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, "default")[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(base_model, lora_name, LORA_STRENGTH)[0]
        model = ModelSamplingAuraFlow().patch_aura(model, SHIFT)[0]
        clip = comfy_nodes.CLIPLoader().load_clip(TEXT_ENCODER_NAME, "lumina2", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]
        model_patch = ModelPatchLoader().load_model_patch(CONTROL_NAME)[0]
        negative = comfy_nodes.CLIPTextEncode().encode(clip, NEGATIVE_PROMPT)[0]

        images: list[torch.Tensor] = []
        ui_images: list[dict[str, Any]] = []
        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_folder = f"zimg-social-pack/{run_stamp}"

        for scene in SCENES:
            scene_model = model
            if scene.reference_file:
                reference = _reference_tensor(scene)
                control = Canny.detect_edge(reference, 0.25, 0.65)[0]
                scene_model = ZImageFunControlnet().diffsynth_controlnet(
                    model, model_patch, vae, image=control, strength=CONTROL_STRENGTH
                )[0]

            positive = comfy_nodes.CLIPTextEncode().encode(clip, scene.prompt)[0]
            latent = {
                "samples": torch.zeros(
                    [1, 16, HEIGHT // 8, WIDTH // 8],
                    device=comfy.model_management.intermediate_device(),
                    dtype=comfy.model_management.intermediate_dtype(),
                ),
                "downscale_ratio_spacial": 8,
            }
            sampled = comfy_nodes.common_ksampler(
                scene_model,
                scene.seed,
                STEPS,
                CFG,
                "res_multistep",
                "simple",
                positive,
                negative,
                latent,
                denoise=1.0,
            )[0]
            image = comfy_nodes.VAEDecode().decode(vae, sampled)[0]
            images.append(image)
            saved = comfy_nodes.SaveImage().save_images(
                image,
                f"{output_folder}/{scene.key}",
                prompt=prompt,
                extra_pnginfo={
                    **(extra_pnginfo or {}),
                    "social_pack_scene": {"key": scene.key, "label": scene.label, "prompt": scene.prompt},
                },
            )
            ui_images.extend(saved["ui"]["images"])

        batch = torch.cat(images, dim=0)
        status = f"Generated and saved {len(SCENES)} photos to ComfyUI/output/{output_folder}"
        return {"ui": {"images": ui_images, "text": (status,)}, "result": (batch, output_folder)}
