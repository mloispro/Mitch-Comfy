# LoRA cleanup — 2026-09-01

## Decision

Only validated production dependencies and the proven Krea2 rollback pair remain installed. Failed
workflow JSON, evaluation reports, generated evidence, training configs, logs, and dataset records were
preserved so rejected approaches remain documented and are not rediscovered as untested ideas.

## Installed keepers

The surviving files under `C:\projects\AI-Tools\ComfyUI\models\loras` are:

- `m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors`
- `flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors`
- `aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors`
- `aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors`
- `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`
- `qwen-image-edit-2511-multiple-angles-lora.safetensors`
- `krea2_identity_edit_v1_2.safetensors`
- `krea-smartphone-photo-slider.safetensors`

The first six support active or still-validated workflows. The final two preserve the validated
no-character-LoRA Krea2 fallback.

## Removed weights

The cleanup removed only LoRA/adaptor weight files:

- 112 rejected, superseded, or duplicate files from ComfyUI's live LoRA directory: 15.477 GiB.
- 50 completed-run copies from AI-Toolkit output: 5.801 GiB.
- 156 duplicate or rejected training weights from `Mitch-Comfy\work`: 17.728 GiB.
- 1 obsolete Z-Image LoRA backup copy: 0.079 GiB.

Total: 319 files and 39.085 GiB of logical file size.

Removed families include FLUX.2 Dev v1, non-selected Dev v2 checkpoints, Klein 4B v2, redundant
Klein 4B v1/v3 checkpoints, Klein 9B v1/v2/v4/v5, non-selected Klein 9B v3 checkpoints, Z-Image
identity runs, rejected Krea2 character/ReID/realism/style experiments, Qwen 2512 adapters, USO,
and the rejected `mtch35` adapter.

AI-Toolkit optimizer states were not included in this cleanup. Cached image latents with a
`.safetensors` extension were also left untouched because they are not LoRAs.

Retired experiment launchers, builders, templates, and lock files were moved out of the live
`scripts`, `config`, and `templates` trees into `checkpoints/legacy-scripts`. Their matching failed
workflow JSON and evaluation reports remain preserved, while the helpers required by the four
selected custom LoRAs remain in their original live locations.
