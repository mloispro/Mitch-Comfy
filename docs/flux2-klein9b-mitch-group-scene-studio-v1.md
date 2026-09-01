# FLUX.2 Klein 9B Mitch Group Scene Studio v1

## Locked decision

Mitch visually approved the lounge result preserved as
`work/group-lounge-prompt-research-20260831/18-approved-locked-group-scene.png` on 2026-08-31.
The production workflow is
`workflows/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.json`.

The approved result uses FLUX.2 Klein Base 9B, the protected V3 step-1600 LoRA at `0.90`, a genuine
front-neutral training photograph at `1.00 MP`, a `0.25 MP` face-free Canny scene guide, `0.92` target
head scale, `832×1216`, 50 Euler steps, CFG `4.0`, and seed `8675412` on the RTX 3090.

## Why the workflow preserves identity

The source photograph supplies composition through a structural edge guide. The selected source face's
internal eye, nose, and mouth edges are removed before conditioning, while its outer head position is
retained and scaled. A separate genuine Mitch photograph and the step-1600 Mitch LoRA supply identity.
This prevents the source person's face from competing with Mitch's native identity conditioning.

The approved frame passed the held-out six-photo AntelopeV2 gate at `0.5946`. Maximum bystander-to-Mitch
similarity was `0.1956`, with no identity-leakage failure. Automated similarity remains a rejection and
ranking aid; full-size human review is required for each new scene.

## Use

1. Load a source group photograph in the workflow.
2. Put `target_x` and `target_y` near the face that should become Mitch. Coordinates are normalized: left
   and top are `0`; right and bottom are `1`.
3. Describe the complete group photograph, including Mitch's position and clothing.
4. Keep `head_scale` at the approved `0.92` unless the generated head is visibly out of proportion.
5. Queue on the RTX 3090 and inspect both the generated photo and the face-free layout-guide preview.

For a new scene, the guide preview must show the correct target face with blank internal features. Reject
the run if the wrong face was selected, Mitch appears more than once, anatomy is incoherent, or the face
looks composited.

## Locked assets

- Model: `flux-2-klein-base-9b-bf16.safetensors`
- Text encoder: `qwen_3_8b_fp8mixed.safetensors`
- VAE: `flux2-vae.safetensors`
- LoRA: `m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors`
- LoRA SHA-256: `D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC`
- Identity reference: `mitch-klein9b-ref-training04-front-neutral.jpg`
- Identity-reference SHA-256: `31870369467B7A8FC19199D7877F56257FED2B0F28B08AA183006BCD3112DDAB`

No face swap, identity pass, restoration, sharpening, or hosted service is part of this workflow.

## Production verification

The final production node loaded through the live ComfyUI API and completed an `832×1216` generation on the RTX
3090 in `263.4` seconds. The tightened default-prompt smoke is preserved under
`work/group-scene-studio-v1/final-production-smoke.png` with its generated face-free guide and report.

The smoke detected four faces. Main identity similarity was `0.5793`; maximum bystander-to-Mitch similarity was
`0.2371`; maximum bystander-to-main similarity was `0.3097`; maximum bystander-pair similarity was `0.2881`.
There were no automated failures. Its central-to-neighbor median face-height ratio was approximately `1.20`, and
its corresponding face-width ratio was approximately `1.10`, correcting the earlier visually oversized head.
