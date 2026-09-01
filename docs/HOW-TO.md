# Mitch Comfy maintenance and operating guide

For canonical current status, read `docs/STATUS.md`. Dated evaluation reports record the decision at their date
and are not operating instructions unless STATUS links them as current.

## Before generating

1. Check the RTX 3090 and RTX 4070 workers and queues.
2. Do not stop, restart, or repurpose a worker with running or pending work.
3. Refresh the ComfyUI Workflows sidebar after workflow files move.
4. Reopen an already-open graph after its JSON or custom node changes.
5. Use only genuine photographs for identity-sensitive evaluation.

The normal RTX 3090 worker is `http://127.0.0.1:8188`.

## Choose the correct workflow

### New photograph: Klein 9B Identity Studio

Open `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1`.

- Choose `GROUP — front only (one Mitch)` whenever anyone besides Mitch appears.
- Choose a matching `SOLO` angle for a one-person portrait.
- Choose `FULL BODY` for head-to-feet or body-proportion scenes.
- Describe the complete photograph, including setting, clothing, pose, camera, and lighting.
- Queue on the RTX 3090.

Locked recipe: Klein Base 9B, V3 step-1600 LoRA at `0.90`, genuine native references, `832×1216`,
50 Euler steps, CFG `4.0`, and `Flux2Scheduler`. This is whole-frame generation with no source-scene latent,
face swap, restoration, sharpening, or second identity pass.

Detailed contract: `docs/flux2-klein9b-mitch-identity-studio-v1.md`.

### Source-matched group: Klein 9B Group Scene Studio

Open `Mitch/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1`.

1. Load a genuine source group photograph.
2. Put `target_x` and `target_y` near the person who should become Mitch.
3. Describe the complete group photograph.
4. Keep `head_scale` at `0.92` unless a measured source-specific adjustment is necessary.
5. Inspect the face-free guide before trusting the generated image.

The intended source face must have blank internal eye/nose/mouth edges in the guide. Reject a run if the wrong
person was selected, Mitch appears more than once, the head scale is wrong, or the frame looks composited.

Detailed contract: `docs/flux2-klein9b-mitch-group-scene-studio-v1.md`.

### Existing one-person image: Upgrade Photo Detail & Realism

Open `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1`.

1. Load an image containing exactly one detectable face.
2. Describe only the material/background detail to improve.
3. Use seed `8675416` first.
4. If visual review fails, use seed `8675412` as the single controlled retry with every other setting unchanged.
5. Review the generated image and saved face-interior-free guide at full size and thumbnail.

This workflow re-renders the whole frame. It is not pixel-preserving retouching and does not use latent img2img,
face swap, masks, restoration, sharpening, upscaling, or a second model pass.

Detailed contract: `docs/flux2-klein9b-upgrade-photo-detail-realism-v1.md`.

### Validated dating templates: FLUX.2 Dev

Open `Mitch/production/FLUX.2 Dev LoRA - 9 Dating Scenes v1`.

- Choose one of the nine `mitch-workbench-dating-*` scene images or provide a controlled scene reference.
- Picture 1 supplies composition, pose, clothing category, props, location, lighting, and crop—not identity.
- The protected Dev V2 step-1000 LoRA supplies Mitch’s identity.
- Keep the active workflow default at LoRA `1.1`, 28 Euler steps, guidance `4.0`, unless running a documented A/B.
- In group scenes, verify every secondary face and confirm there is exactly one Mitch.

Detailed contract: `docs/flux2-dev-mitch-scene-studio.md`.

## Utility workflows

`Dataset gen - QWEN 2511 - 3-photo` creates controlled multi-angle dataset images with Qwen Image Edit 2511.
Generated images are not genuine identity truth and must not enter held-out identity evaluation.

`Train Generated Dataset - AI Toolkit` submits and monitors the fixed generated-dataset training job. A completed
job is not automatically approved or published for production; it still requires the normal held-out and visual gates.

## Review checklist

At full size and thumbnail, inspect:

- recognizable identity and current apparent age;
- hairline, forehead, hair material, eyes, mouth, jaw, and ears;
- body/head proportion, anatomy, hands, and feet;
- exactly one Mitch and distinct bystanders;
- scene geometry, depth, materials, lighting, and camera consistency;
- halos, pasted-head boundaries, selective sharpness, fake bokeh, noise, or smoothing.

Automated similarity can reject or rank a candidate. It cannot certify identity or visual quality.

## Hidden rollbacks and failed experiments

Normal-use workflows live only in `workflows/production`. Exact legacy graphs are under
`checkpoints/legacy-workflows` and do not appear in ComfyUI.

Retired launchers/configs under `checkpoints/legacy-scripts` retain their original path assumptions. Do not run
them in place. Restore an archived experiment only for a deliberate regression investigation, and copy all of its
documented dependencies back to their original locations first.

The accepted One Reference rollback can also be restored from its tag:

```powershell
git restore --source flux2-one-reference-v1.0.0 -- "workflows/production/FLUX.2 One Reference Photo.json" "custom_nodes/ComfyUI-AIToolkit-Training/one_reference_photo.py" "custom_nodes/ComfyUI-AIToolkit-Training/__init__.py"
```

Restart ComfyUI after restoring Python files. Do not overwrite the archived copy.

## Verification and check-in

Run:

```powershell
.\scripts\verify.ps1
.\scripts\verify-flux2-klein9b-mitch-identity-studio-v1.ps1
.\scripts\verify-flux2-klein9b-group-scene-studio-v1.ps1
.\scripts\verify-flux2-klein9b-upgrade-photo-detail-realism-v1.ps1
git diff --check
git status --short
```

The specialized verifiers are read-only by default. The Group and Upgrade verifiers also accept `-Smoke`, which
queues a generation. Never use `-Smoke` while either GPU has running or pending work.

For a normal repository checkpoint:

```powershell
.\scripts\checkpoint.ps1 -Message "Describe the verified change"
```

Git history is not an off-computer backup. Models, LoRAs, datasets, genuine reference photographs, and generated
outputs require a separate private backup.
