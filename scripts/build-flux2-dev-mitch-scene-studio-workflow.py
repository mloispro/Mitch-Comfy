from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "checkpoints" / "legacy-workflows" / "production" / "FLUX.2 Dev Mitch Scene Studio v1.json"


def build() -> dict:
    return {
        "id": "f84647d1-a688-49da-880b-5736ea97d3e0",
        "revision": 0,
        "last_node_id": 3,
        "last_link_id": 1,
        "nodes": [
            {
                "id": 1,
                "type": "MarkdownNote",
                "pos": [-750, -20],
                "size": [610, 760],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [],
                "outputs": [],
                "title": "MITCH SCENE STUDIO — QUICK GUIDE",
                "properties": {"Node name for S&R": "MarkdownNote", "cnr_id": "comfy-core"},
                "widgets_values": [
                    "# FLUX.2 Dev Mitch Scene Studio\n\n"
                    "## Fastest route\n"
                    "1. Leave **PROMPT ONLY** selected.\n"
                    "2. Choose a scene preset.\n"
                    "3. Choose gaze/action and click **Run**.\n\n"
                    "## Restage any scene image\n"
                    "1. Select **SCENE IMAGE** mode.\n"
                    "2. Upload/select the scene under **scene_reference**.\n"
                    "3. Pick the closest preset or use **Custom**.\n"
                    "4. The image supplies composition, pose, props, lighting and crop. The step-1000 LoRA supplies Mitch's identity.\n\n"
                    "## Proven defaults\n"
                    "- FLUX.2 Dev FP8 mixed\n"
                    "- Prompt-only: Mitch v2 step 1000, strength 1.0\n"
                    "- Uploaded scene already containing a man: strength 1.1 tested\n"
                    "- Euler, 28 steps, guidance 4.0\n"
                    "- No face swap, mask, restoration or hosted API\n\n"
                    "## Honest limits\n"
                    "Portrait and waist-up identity are strongest. Full-body faces are less exact. Group scenes require checking that Mitch does not leak into friends. A scene image containing another person can compete with identity, so the generated prompt explicitly treats it as composition—not identity."
                ],
                "color": "#2f4f4f",
                "bgcolor": "#17363b",
            },
            {
                "id": 2,
                "type": "Flux2DevMitchSceneStudio",
                "pos": [-70, -20],
                "size": [650, 760],
                "flags": {},
                "order": 1,
                "mode": 0,
                "inputs": [
                    {"name": "scene_mode", "type": "COMBO", "widget": {"name": "scene_mode"}, "link": None},
                    {"name": "scene_reference", "type": "COMBO", "widget": {"name": "scene_reference"}, "link": None},
                    {"name": "scene_preset", "type": "COMBO", "widget": {"name": "scene_preset"}, "link": None},
                    {"name": "custom_scene_prompt", "type": "STRING", "widget": {"name": "custom_scene_prompt"}, "link": None},
                    {"name": "camera_style", "type": "COMBO", "widget": {"name": "camera_style"}, "link": None},
                    {"name": "framing", "type": "COMBO", "widget": {"name": "framing"}, "link": None},
                    {"name": "moment", "type": "COMBO", "widget": {"name": "moment"}, "link": None},
                    {"name": "canvas", "type": "COMBO", "widget": {"name": "canvas"}, "link": None},
                    {"name": "lora_strength", "type": "FLOAT", "widget": {"name": "lora_strength"}, "link": None},
                    {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": None},
                    {"name": "guidance", "type": "FLOAT", "widget": {"name": "guidance"}, "link": None},
                    {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": None},
                ],
                "outputs": [
                    {"name": "photo", "type": "IMAGE", "links": [1], "slot_index": 0},
                    {"name": "effective_prompt", "type": "STRING", "links": None, "slot_index": 1},
                    {"name": "output_folder", "type": "STRING", "links": None, "slot_index": 2},
                    {"name": "report_json", "type": "STRING", "links": None, "slot_index": 3},
                ],
                "title": "CREATE — PROMPT LIBRARY OR UPLOADED SCENE",
                "properties": {
                    "Node name for S&R": "Flux2DevMitchSceneStudio",
                    "cnr_id": "ComfyUI-AIToolkit-Training",
                },
                "widgets_values": [
                    "PROMPT ONLY — create a new scene",
                    "No scene image (prompt-only)",
                    "Golden-hour rooftop — linen shirt",
                    "",
                    "Dating app — natural smartphone",
                    "Waist-up",
                    "Candid — looking away",
                    "Portrait — 832 × 1248",
                    1.0,
                    28,
                    4.0,
                    8675310,
                    "fixed",
                ],
                "color": "#174d52",
                "bgcolor": "#20666d",
            },
            {
                "id": 3,
                "type": "PreviewImage",
                "pos": [650, -20],
                "size": [560, 760],
                "flags": {},
                "order": 2,
                "mode": 0,
                "inputs": [{"name": "images", "type": "IMAGE", "link": 1}],
                "outputs": [],
                "title": "RESULT — REVIEW AT FULL SIZE AND THUMBNAIL",
                "properties": {"Node name for S&R": "PreviewImage", "cnr_id": "comfy-core"},
                "widgets_values": [],
            },
        ],
        "links": [[1, 2, 0, 3, 0, "IMAGE"]],
        "groups": [
            {
                "id": 1,
                "title": "FLUX.2 DEV — MITCH IDENTITY SCENE STUDIO v1",
                "bounding": [-790, -80, 2040, 860],
                "color": "#3f789e",
                "font_size": 30,
                "flags": {},
            }
        ],
        "config": {},
        "extra": {"ds": {"scale": 0.78, "offset": [780, 120]}},
        "version": 0.4,
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(OUTPUT.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
