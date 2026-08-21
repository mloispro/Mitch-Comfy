# Superseded Qwen Easy Identity + Build checkpoint

Archived workflow: `checkpoints/workflows/Qwen Easy Identity + Build - unsafe-body-v3.json`

This checkpoint is retained for restoration only. The strong whole-frame body edit was rejected after review because it changed gaze and limb placement, invented or stretched legs, altered clothing, and sometimes produced detached-looking hands. It is no longer shown under Production.

Workflow SHA256: `DA92834337B6E64E2BDD88CB898DB931D2AC7E0B7999BF9DCF9DE19979AF02DF`

Preserved workflow hashes:

- `Qwen + ReActor Single-Person Scene Match.json`: `BAB42CD251644175AD170C4D8748A86614E83F4EEBED14A54633FCBE538CC54A`
- `Qwen 2512 + ReActor - 9 Dating Photos.json`: `C01EA3931C51E3E70F395EE918CA58E49B4783C6F323D59DE9F5D47BBC443003`
- `ReActor Multi-Person Identity Finish - Sharper Face.json`: `E8E3A3B387C84BAA944298D73A6B3BC180ECF2F3B72CF608B430FA994A3BDB2D`

Validated defaults:

- Approved scene mode: on (`CREATE NEW PHOTOS = false`)
- Qwen Edit 2511 full-head lock: on for solo scenes
- Strong silhouette body correction: on for golfer, Amalfi, lake boat, and night city
- Three-genuine-photo ReActor finish: on
- Samsung camera LoRA: off in exact-scene mode
- Face detail: `0.32`

The `_00004_` final output set was run to completion on 2026-08-20 with no prompt validation errors or missing-node warnings. Visual checks confirmed a single intended identity in both group scenes, no added people in the final set, angle-appropriate full heads, and a visibly slimmer golfer/lake build than the original templates.

Solo genuine-reference face-similarity scores from the `_00003_` run were: Ragdoll 67.43%, Tabby 57.45%, Golfer 87.11%, Amalfi 87.35%, Lake Boat 85.86%, Restaurant 87.71%, and Night City 70.72%. The installed similarity node always scores the first detected face, so its lounge group values do not measure the selected central man and are excluded.

External models are installed under `C:\projects\AI-Tools\ComfyUI` and intentionally excluded from Git:

- `models\diffusion_models\qwen_image_2512_fp8_e4m3fn.safetensors`
- `models\diffusion_models\qwen_image_edit_2511_fp8mixed.safetensors`
- `models\loras\Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors`
- `models\loras\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`
- `models\loras\samsung_qwen2512.safetensors`
- `models\text_encoders\qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `models\vae\qwen_image_vae.safetensors`
- `models\insightface\inswapper_128.onnx`
