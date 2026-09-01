# Z-Image Base Identity LoRA v1 — Training and Evaluation

> **Historical rejected training record — not current instructions.** All Z-Image identity LoRA weights were removed on 2026-09-01; workflow, evaluation, config, and script evidence remains archived. See `docs/STATUS.md`.

## Outcome

The RTX 3090 smoke and production runs completed successfully, but the trained adapter was rejected during held-out identity evaluation. No checkpoint passed all three fixed-seed finalist runs, so the strength sweep, exact nine-scene recreation, and publication phases were intentionally not run.

The workflow, evaluation, configs, and scripts remain preserved for provenance. The unpublished final adapter,
all numbered LoRA checkpoints, and the obsolete backup copy were deleted during the 2026-09-01 LoRA cleanup.
AI-Toolkit optimizer state and cached dataset latents were outside that weight-only cleanup and may still exist.

## Training validation

- Base: cached `Tongyi-MAI/Z-Image` Base snapshot; no Turbo assistant adapter.
- Device: physical GPU 0, NVIDIA GeForce RTX 3090.
- Dataset: fresh run-local copy containing 13 genuine image/caption pairs; held-out images excluded.
- Smoke: 40 updates, both 768 and 1024 bucket families, 240 LoRA modules, finite BF16 adapter, zero OOMs.
- Production: 2,000 updates, 20 numbered checkpoints plus a separate final adapter, zero OOMs.
- Final and numbered step-2000 SHA-256: `E4DAD3EFBE02C411DBCEE87C11092213093DEE4BE503D82E8BEADEAB96DDFB33`.
- The RTX 4070 worker was not selected or stopped. The RTX 3090 ComfyUI worker was restored after training.

## Benchmark result

Coarse screening selected steps 1800 and 2000 as the numerical leaders. The required adjacent checkpoints produced a finalist set of 1700, 1800, 1900, and 2000. Each was tested at strength 0.9 with seed bases 22000, 32000, and 42000.

| Step | Mean core median | Passing fixed-seed runs |
|---:|---:|---:|
| 1700 | 0.6058 | 0/3 |
| 1800 | 0.5580 | 0/3 |
| 1900 | 0.6142 | 0/3 |
| 2000 | 0.6403 | 0/3 |

The best single numerical run was step 2000, strength 0.9, seed base 42000, with a core median of 0.7224. It was still rejected because the near-profile scene drifted from Mitch's identity and the multiperson scene leaked identity to a secondary face.

Across the finalist set, frontal images were materially stronger than the down-left near-profile scene. Visual inspection confirmed that the rooftop composition pointed down-left, but the subject did not retain Mitch's identity. Some group runs also produced a secondary face classified as Mitch. These are hard failures under the locked acceptance criteria.

## Gate decision

- Strength sweep: not run.
- Original nine-scene recreation: not run.
- Publication to `aitk/m1tch-zimage-base-identity-v1.safetensors`: not allowed.
- Existing LoRAs: unchanged.

At the time, the proposed follow-up was a new version trained with more genuine current-appearance side and
near-profile photographs from independent sessions and lighting conditions. That proposal was not promoted;
current identity work uses the selected Klein 9B V3 adapter instead.
