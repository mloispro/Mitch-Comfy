# FLUX.2 Klein 9B Mitch Group Scene Studio v1

> Historical internal-engine contract. The duplicate public v1 sheet was removed on 2026-09-03. Use
> `Mitch/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets`.

## Locked decision

Mitch visually approved the lounge result preserved as
`work/group-lounge-prompt-research-20260831/18-approved-locked-group-scene.png` on 2026-08-31.
The retained internal engine is exposed only through the public v1.1 visual-preset workflow.

The approved result uses FLUX.2 Klein Base 9B, the protected V3 step-1600 LoRA at `0.90`, the accepted
Smartphone Snapshot Photo Reality v13 style LoRA second at `0.25` with the `casual snapshot` trigger, a genuine
front-neutral training photograph at `1.00 MP`, a `0.25 MP` face-free Canny scene guide, `0.92` target
head scale, `832×1216`, 50 Euler steps, CFG `4.0`, and seed `8675412` on the RTX 3090.

## Why the workflow preserves identity

The source photograph supplies composition through a structural edge guide. The selected source face's internal eye,
nose, and mouth edges are removed before conditioning, while the guide retains approximate outer-head scale and
placement. A separate genuine Mitch photograph and the step-1600 Mitch LoRA supply identity and internal facial
geometry. The prompt states those roles concisely before describing the scene and expression.

This concise division of responsibility is evidence-based. Adding detailed instructions for exact forehead, temple,
cheekbone, jaw, chin, and face-ratio measurements displaced the reference's internal geometry and made the face more
generic even though the detected outline became narrower. The workflow no longer uses that verbose skull lock.

The approved frame passed the held-out six-photo AntelopeV2 gate at `0.5946`. Maximum bystander-to-Mitch
similarity was `0.1956`, with no identity-leakage failure. Automated similarity remains a rejection and
ranking aid; full-size human review is required for each new scene.

## Use

1. Load a source group photograph in the workflow.
2. Put `target_x` and `target_y` near the face that should become Mitch. Coordinates are normalized: left
   and top are `0`; right and bottom are `1`.
3. Describe the complete group photograph, including Mitch's position and clothing.
4. Keep `head_scale` at the approved `0.92` unless the generated head is visibly out of proportion.
5. Leave `Visible flattering enhancement` off for the validated identity-first default. Its optional on-state is a
   short rendering-only treatment that does not request younger age, altered expression, or changed bone structure.
6. Leave Fast Turbo off for the validated 50-step quality result. The 8-step option is implemented for deliberate
   speed experiments, but it did not meet the conservative identity-retention gate for this concise Group recipe.
7. Queue on the RTX 3090 and inspect both the generated photo and the face-free layout-guide preview.

The optional Group enhancement changes only the positive prompt. It retains the face-free layout, genuine identity
reference, LoRAs, head scale, sampler, resolution, and bystander-separation contract. Its short clause permits natural
pores, tidy faint stubble, healthy authentic skin color, and clean catchlights while explicitly preserving current
age, expression, facial geometry, and feature spacing. It does not add a face pass or post-processing stage.

For a new scene, the guide preview must show the correct target face with blank internal features. Reject
the run if the wrong face was selected, Mitch appears more than once, anatomy is incoherent, or the face
looks composited.

## Locked assets

- Model: `flux-2-klein-base-9b-bf16.safetensors`
- Text encoder: `qwen_3_8b_fp8mixed.safetensors`
- VAE: `flux2-vae.safetensors`
- LoRA: `m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors`
- LoRA SHA-256: `D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC`
- Smartphone style: `smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors` at `0.25`, loaded after the identity LoRA
- Smartphone-style SHA-256: `1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90`
- Smartphone-style trigger: `casual snapshot` (prepended automatically)
- Optional Turbo: `flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors` at `1.0`, loaded before identity and smartphone realism
- Turbo SHA-256: `A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600`
- Quality default: 50 Euler steps / CFG `4.0`; optional Turbo: 8 Euler steps / CFG `1.0`
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

The 2026-09-01 Smartphone Snapshot v13 rollout smoke also passed on the RTX 4070. Main identity improved from
`0.5603` to `0.5626` on the established six-photo group gate, maximum bystander identity similarity fell from
`0.1938` to `0.1499`, all four faces remained distinct, and full-size review found no Canny conflict or hair-edge halo.
The exact graph and evidence are under
`output/smartphone-snapshot-klein9b-production-rollout-4070/20260901-210410`.

Full-size review of that rollout subsequently found the central head too broad. A first Group-only correction added a
detailed exact-skull prompt. It narrowed the detected face, but visual identity became more generic and six-photo
likeness fell to `0.5465`. This disproved the assumption that matching only the outline ratio would fix identity.

The final controlled diagnostic restored the concise prompt embedded in the original approved PNG while retaining
Smartphone Snapshot v13 at `0.25` and holding the Canny guide, genuine identity reference, step-1600 LoRA, reference
order, resolution, sampler, steps, CFG, and seed fixed. It completed on the RTX 3090 in `285.52` seconds. Six-photo
main identity rose to `0.6007`, exceeding the original approved frame's `0.5946`; four faces were detected, maximum
bystander identity similarity was `0.2732`, maximum bystander-to-main similarity was `0.4371`, and maximum bystander
pair similarity was `0.4805`. All remained below their gates and there were no failures. Skin diagnostics remained
close to the approved frame without an oversharpening regression. The raw result, exact graph report, and evaluation
evidence are under `output/group-identity-correction-3090/20260901-220033`.

After the node was reloaded, the production workflow itself completed the same identity-first 50-step quality path on
the RTX 3090 in `264.939` seconds. Its six-photo main identity score was `0.5958`, maximum bystander identity was
`0.3026`, maximum bystander-to-main similarity was `0.3595`, and maximum bystander-pair similarity was `0.3007`.
All four faces were distinct and every gate passed. The production photo, face-free guide, exact report, diagnostic
candidate, and consolidated results are preserved under
`output/group-identity-correction-3090/20260901-220033`.

The exact current-prompt Turbo check completed in `42.21` seconds. It still detected four distinct faces and passed
all configured leakage limits, but selected-main identity fell from the reloaded Production quality result's `0.5958`
to `0.5672`, a `0.0286` drop beyond the `0.02` promotion allowance. Full-size review also favored the quality face.
Fast Turbo therefore remains available but off by default in Group Scene Studio. The Turbo image, native report,
graph, and identity-scope comparison are under `work/flux2-klein9b-turbo-rollout/rollout-20260901-v2`.
