# Superseded Qwen Easy Identity + Build checkpoint

> **Historical record — not current instructions.** Terms such as “production,” “current,” “selected,” or “recommended” below describe the decision on 2026-08-20. See `docs/STATUS.md` for current state.

Archived workflow: `checkpoints/workflows/Qwen Easy Identity + Build - unsafe-body-v3.json`

This checkpoint is retained for restoration only. The strong whole-frame body edit was rejected after review because it changed gaze and limb placement, invented or stretched legs, altered clothing, and sometimes produced detached-looking hands. It is no longer shown under Production.

Current archive SHA256: `D7E433FB7F350E990357A09D086ED4CD93433BC1FBEC3A8CC0E0284DCCA119F8`

Preserved workflow hashes:

- `Qwen + ReActor Single-Person Scene Match.json`: `2C04D28733A02ACC62B6BFA812516F2C8DCC37FD6DBDC36DC43E7023DB234072`
- `Qwen 2512 + ReActor - 9 Dating Photos.json`: `35EC491F5C8F29B60BE4E1D2B7495D090C40EA6F6503F09D79D419797808F9C7`
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

External models used at validation time were installed under `C:\projects\AI-Tools\ComfyUI` and excluded from Git.
The Qwen 2512 and Samsung LoRAs listed below were removed on 2026-09-01; the 2511 Lightning LoRA remains installed:

- `models\diffusion_models\qwen_image_2512_fp8_e4m3fn.safetensors`
- `models\diffusion_models\qwen_image_edit_2511_fp8mixed.safetensors`
- `models\loras\Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors`
- `models\loras\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`
- `models\loras\samsung_qwen2512.safetensors`
- `models\text_encoders\qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `models\vae\qwen_image_vae.safetensors`
- `models\insightface\inswapper_128.onnx`
