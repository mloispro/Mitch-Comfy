# Krea2 Smartphone LoRA Evaluation

> **Historical evaluation for an archived fallback.** The smartphone LoRA remains installed only with the retained Krea2 no-character rollback; it is not part of current primary generation. See `docs/STATUS.md`.

## Decision

The Elusarca smartphone-photography LoRA is compatible with the proven Krea2 Identity Edit v1.2
pipeline at low strength, but it does not materially correct Krea2's excessive background defocus.
Retain `0.35` as an optional realism control; do not promote the LoRA as the solution to deep-focus
city-background realism.

## Controlled mechanism

The genuine identity photograph continues to enter through both training-matched Identity Edit
paths:

1. VAE appearance tokens through `Krea2EditModelPatch`.
2. Image-aware Qwen3-VL instruction conditioning through `Krea2EditGroundedEncode`.

The smartphone adapter is a model LoRA placed before the Identity Edit adapter. It supplies camera
appearance only and never receives the reference photograph. Therefore it cannot provide or improve
identity by itself.

## Test

All three images used the same genuine reference, prompt, seed `9472103`, `832x1248` resolution,
12 steps, CFG `1`, Euler/simple sampling, Identity Edit strength `1`, `ref_boost=6`, and 768-pixel
grounding. The only variable was smartphone LoRA strength.

| Variant | Four-reference centroid | Result |
| --- | ---: | --- |
| Baseline | 0.7218 | Identity near-match; excessive background defocus |
| Smartphone 0.35 | 0.7225 | Identity retained; photographic change too subtle |
| Smartphone 0.50 | 0.7203 | Identity retained; more scene change but depth problem remains |

The scores are local InsightFace AntelopeV2 diagnostics against four genuine held-out photographs.
They are useful for rejecting drift but do not prove identity or overall photographic quality.

A later valid Gokay Realism comparison added more environmental structure but reduced centroid
similarity to `0.7130` at strength `0.35` and `0.7073` at `0.50`. Smartphone `0.35` therefore
remains the selected low-risk realism control. See `docs/krea2-gokay-realism-evaluation.md`.

## Preserved artifacts

- `output/krea2-smartphone-ab/baseline-seed-9472103.png`
- `output/krea2-smartphone-ab/smartphone-0p35-seed-9472103.png`
- `output/krea2-smartphone-ab/smartphone-0p50-seed-9472103.png`
- `work/identity-evals/krea2-smartphone-ab-seed-9472103.json`

## Reproduction

Download and verify the exact adapter:

```powershell
.\scripts\download-krea2-smartphone-lora.ps1
```

Run the selected setting on the isolated RTX 4070 worker:

```powershell
.\scripts\smoke-krea2-identity-edit.ps1 -SmartphoneLoraStrength 0.35
```

## Source

- https://huggingface.co/reverentelusarca/elusarcas-krea2-smartphone-photography-lora
