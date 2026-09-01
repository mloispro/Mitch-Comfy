# FLUX.2 Klein Base 9B identity LoRA — AI-Toolkit / RTX 3090

> **Historical non-selected V1 training record — not current instructions.** Its LoRA weights were removed; current primary generation uses the protected Klein 9B V3 step-1600 adapter. See `docs/STATUS.md`.

## Locked objective

Train an independent `m1tch_person` identity LoRA against the undistilled
`black-forest-labs/FLUX.2-klein-base-9B` model. The distilled
`flux-2-klein-9b-fp8.safetensors` inference checkpoint is not a training base and is excluded.
No RTX 4070 fallback is permitted.

## Primary-source basis

- [Black Forest Labs' training guide](https://docs.bfl.ai/flux_2/flux2_klein_training)
  identifies Base as the undistilled fine-tuning variant, Klein 9B Base as the maximum-quality
  choice, and an RTX 3090/4090 with 22 GB VRAM plus 64 GB RAM as the minimum 9B setup.
- [Black Forest Labs' worked AI-Toolkit example](https://docs.bfl.ai/flux_2/flux2_klein_training_example)
  gives AdamW8bit, weighted/balanced timestep sampling, quantization, a `1e-4` baseline, and
  800–1200 steps for a 10–15-image character LoRA.
- [The official Base 9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
  supplies the gated, non-commercial Base weights used here.
- [AI-Toolkit PR #837](https://github.com/ostris/ai-toolkit/pull/837) documents a BF16 residual
  overflow in AI-Toolkit's Klein Base 9B reimplementation that can silently train a degenerate
  adapter while reporting plausible loss. Its five-site ±30000 residual clamp is applied and
  hash-locked before training.

## Dataset lock

- Manifest SHA-256: `D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003`
- Training: 13 genuine, unedited camera photographs with 13 matching TXT captions.
- Evaluation: all six genuine validation photographs remain held out.
- Every caption begins with `m1tch_person`.
- Smoke and production use separate clean copies containing only the 26 image/TXT files. Existing
  `_latent_cache`, `_t_e_cache`, and `.aitk_size.json` artifacts are excluded.

## Locked training settings

| Setting | Value |
|---|---|
| Architecture | `flux2_klein_9b` |
| Transformer | FLUX.2 Klein Base 9B snapshot `32773329...` |
| Text encoder | Qwen3-8B snapshot `b968826d...` |
| VAE | AI-Toolkit FLUX.2 VAE snapshot `3f679cf2...` |
| GPU | Physical GPU 0, RTX 3090 only |
| Network | Linear LoRA rank/alpha 16/16, transformer only |
| Updates | 1200 maximum; checkpoint every 100; retain all 12 |
| Resolution | 768 and 1024 aspect-ratio buckets |
| Batch | 1; gradient accumulation 1; seed 42 |
| Optimizer | AdamW8bit, `8e-5`, constant, weight decay `1e-4`, max grad norm 1.0 |
| Objective | Flow match, weighted timesteps, balanced content/style, MSE |
| Precision | BF16 training/save; qfloat8 transformer and text encoder |
| Memory | Gradient checkpointing; disk-cached latents/text; unload text encoder; no layer offload |
| Disabled | TE training, dropout, token shuffle, flips, EMA, production-time sampling |

Rank 16 and `8e-5` deliberately reduce overfitting risk on 13 identity images while staying inside
the official character range. The terminal 1200-step adapter is not automatically considered best;
the retained checkpoints must be ranked on held-out identity and manually reviewed.

## Acceptance sequence

1. Full local SHA-256 verification of every Base, Qwen, and VAE weight file.
2. Forty-update smoke on the isolated RTX 3090.
3. Smoke log must prove 112 targeted transformer LoRA modules, both resolution sets, finite loss,
   zero OOMs, and a loadable finite safetensors adapter.
4. A Base 9B smoke image must be nonblack and nonblank, specifically guarding against the known
   residual-overflow failure.
5. Production starts only after the smoke record passes. Existing outputs are never overwritten or
   silently resumed.
6. Rank checkpoints with fixed prompts/seeds and all six genuine held-outs. Multiperson tests must
   contain exactly one Mitch; manual full-size and thumbnail review remains authoritative.

Historical entry point after restoring the archived V1 files to their original `scripts` and `config`
locations as described in `checkpoints/legacy-scripts/README.md`:

```powershell
.\scripts\run-flux2-klein9b-identity-v1-3090.ps1 -Phase Validate
.\scripts\run-flux2-klein9b-identity-v1-3090.ps1 -Phase Smoke
.\scripts\run-flux2-klein9b-identity-v1-3090.ps1 -Phase Train
```
