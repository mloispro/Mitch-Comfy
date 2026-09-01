# FLUX.2 Klein 9B – Upgrade Photo Detail & Realism v1

This production workflow re-renders an existing one-person Mitch photograph as a more realistic and materially detailed whole-frame phone photo while preserving the source pose and layout.

Open `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1` in the standard RTX 3090 ComfyUI instance at `http://127.0.0.1:8188`.

## Use

1. Load the exact source photo.
2. Describe only source-specific material detail in `detail_instructions`. Good examples are layered canyon rock, irregular vegetation, believable river banks, painted siding seams, bark ridges, fabric fibers, or natural skin and hair transitions.
3. Queue seed `8675416` first. If the result fails identity or visual review, the only controlled retry is seed `8675412` with every other setting unchanged.
4. Inspect the result and the automatically saved structure guide at full size and thumbnail.

The source must contain exactly one detectable face. The node deliberately rejects zero-face and multi-face inputs; use the Group Scene Studio for groups.

## Locked mechanism

Reference order is part of the lock:

1. source photo at `1.00 MP`: scene, pose, expression, clothing, lighting layout, composition;
2. automatically generated face-interior-free Canny guide at `0.50 MP`: geometry only;
3. protected genuine frontal Mitch photograph at `0.50 MP`: identity and facial geometry;
4. protected isolated genuine hair crop at `0.10 MP`: hair material only.

All four reference latents enter both the positive and empty-negative conditioning in that order. The model is FLUX.2 Klein Base 9B dynamically loaded as `fp8_e4m3fn`, with the protected V3 step-1600 LoRA at `0.90`, Qwen 3 8B FP8, FLUX.2 VAE, 50 Euler steps, CFG `4.0`, and `Flux2Scheduler`.

The output keeps source dimensions when they are at or below `1.70 MP`; larger inputs are downscaled with the aspect ratio preserved and dimensions rounded to multiples of 16. This bound preserves the tested 1680×1008 and 1024×1024 cases on the RTX 3090.

This is not img2img latent initialization. It does not use face swap, masks, restoration, sharpening, upscaling, film grain, compositing, or a second model pass.

## Saved evidence

Each run creates a timestamped directory below `ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/` containing:

- the raw generated photo;
- the face-interior-free structure guide;
- `prompt-api.json` with the exact submitted ComfyUI prompt graph;
- `workflow-snapshot.json` when the run comes from the ComfyUI UI;
- `report.json` with the decoded source-pixel hash, protected model/reference hashes, exact prompt, reference order and encoded sizes, output dimensions, seed, settings, runtime, GPU, and manual-review checklist.

The approved anchor for this workflow is `output/klein9b-existing-photo2-restage-4070/candidate-klein9b-iphone-structure-v4-seed-8675416.png`. The locked 3090 reproductions and validation reports remain under `output/klein9b-realism-locked-v1/`.
