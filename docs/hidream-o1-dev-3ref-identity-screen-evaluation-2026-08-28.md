# HiDream-O1 Dev native three-reference identity screen

> **Historical record — not current instructions.** This experiment was rejected and its runnable files are archived. See `docs/STATUS.md`.

Date: 2026-08-28
Worker: local RTX 4070 (`http://127.0.0.1:8189`)
Privacy: all photographs, generation, and evaluation stayed local.

## Outcome

Stronger genuine reference photos improved HiDream-O1 Dev identity retention. The best candidate,
seed `8675603`, reached `0.8101` similarity to the held-out identity centroid, compared with
`0.7447` for the earlier two-reference baseline. Its minimum held-out similarity (`0.5693`) also
cleared the genuine-photo pairwise floor (`0.5533`).

This is a successful identity-mechanism result, not an approved final dating photo. The winner is
still framed too close and has visibly smoother skin and hair than the genuine photographs.

## Why identity conditioning is real here

The three `LoadImage` outputs enter the core `HiDreamO1ReferenceImages` node as
`images.image_1`, `images.image_2`, and `images.image_3`. That node adds the raw reference images to
the positive and negative conditioning used by the sampler. It is HiDream-O1's documented native
multi-reference subject-driven personalization path, not generic img2img, a style reference, or a
face swap. No LoRA, mask, restoration, upscaler, SDXL/Z-Image pass, or hosted service is present.

Primary implementation sources:

- <https://github.com/HiDream-ai/HiDream-O1-Image/blob/main/README.md>
- <https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_hidream_o1.py>

## References

All three are byte-identical genuine camera stills from `mitch-identity-stills-v3/dataset`.

| Slot | Dataset still | Detected face width | Purpose |
|---|---|---:|---|
| 1 | `07_sweater_front_neutral.jpg` | 914 px | high-detail frontal anchor |
| 2 | `09_sweater_opposite_near_profile.jpg` | 1,092 px | opposite-angle geometry |
| 3 | `12_laundry_orange_shirt.jpg` | 332 px | newer independent-session angle |

The previously considered full-body mirror still was rejected as an identity input because its
detected face was only 89 pixels wide. Validation used five genuine photographs that were not fed
to this workflow.

## Locked recipe

- Official Dev FP8 checkpoint SHA-256:
  `7CBF53A475E0A13F92F2EC08BCFFDB9B9DE4305EF3B6F35CDD784D09DCD8D0CC`
- Canvas: `1728x2304`
- Steps: `28`
- CFG: `1.0`
- Model noise scale: `7.6`
- Scheduler: `normal`
- Sampler: LCM (`s_noise=1.0`, `s_noise_end=1.0`, `noise_clip_std=2.5`)
- Seeds: `8675601` through `8675604`
- Scene prompt frozen from the earlier Dev baseline except for naming three references.

## Identity results

InsightFace AntelopeV2 scores are local diagnostics, not proof by themselves.

| Rank | Candidate | Centroid | Mean | Minimum | Visual decision |
|---:|---|---:|---:|---:|---|
| 1 | new 3-ref, seed `8675603` | **0.8101** | **0.6960** | **0.5693** | keep as best identity proof; single subject |
| 2 | new 3-ref, seed `8675602` | 0.7685 | 0.6603 | 0.5639 | reject; duplicated Mitch |
| 3 | new 3-ref, seed `8675601` | 0.7641 | 0.6565 | 0.5512 | valid single subject; too close and smooth |
| 4 | old 2-ref, seed `8675601` | 0.7447 | 0.6398 | 0.5305 | prior baseline |
| 5 | new 3-ref, seed `8675604` | 0.6664 | 0.5726 | 0.4952 | reject; duplicate, phone, and text |

The same-seed causal comparison is the old baseline versus new seed `8675601`. Changing the
reference set raised centroid similarity by `0.0194`, mean similarity by `0.0167`, and minimum
similarity by `0.0207`. The seed screen then found the stronger `8675603` result.

## Visual and texture review

- Seed `8675603` has one clear main subject, plausible current age, recognizable facial geometry,
  intact hairline, distinct background diners, and no obvious cutout halo.
- It still behaves like a close selfie instead of the requested waist-up friend-taken photograph.
- Its micro-luma variation is `4.176`, better than the old baseline's `3.402` but below the selected
  genuine references (`5.574` to `6.749`).
- Its normalized Laplacian variance is `163.121`, better than the old baseline's `97.5` but well
  below the selected genuine references (`434.213` to `774.351`). This agrees with the visible
  waxy/smooth rendering.
- Seed `8675602` generated two foreground versions of Mitch.
- Seed `8675604` generated a partial second Mitch, a phone displaying Mitch, and unwanted text.

## Decision

Use the three-reference set for future HiDream-O1 Dev identity experiments. Preserve seed
`8675603` as the best identity proof. Do not call this identity locked or publish it as a final
dating image. The next controlled experiment should keep the three references and model recipe
fixed while changing only composition pressure to obtain a true waist-up, single-subject frame;
texture refinement should wait until the composition is correct because a second model pass can
damage the identity gain.

## Artifacts

- Archived workflow: `checkpoints/legacy-workflows/experiments/HiDream-O1 Dev Native 3-Reference Dating Identity - Seed Screen.json`
- Archived runner: `checkpoints/legacy-scripts/hidream-o1/run-hidream-o1-dev-3ref-seed-screen.ps1`
- Generation manifest: `output/hidream-o1-reference-dating-3ref-v1/generation-manifest.json`
- Experiment lock: `output/hidream-o1-reference-dating-3ref-v1/experiment-lock.json`
- Best identity proof: `output/hidream-o1-reference-dating-3ref-v1/best-identity-proof-seed-8675603.png`
- Held-out identity report: `output/hidream-o1-reference-dating-3ref-v1/evaluation/identity.json`
- Texture contact sheet: `output/hidream-o1-reference-dating-3ref-v1/evaluation/face-texture-contact-sheet.png`
