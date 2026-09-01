# No-character-LoRA street-corner evaluation — 2026-08-24

> **Historical evaluation for an archived fallback.** “Best” below means best tested on 2026-08-24, not the current primary route. See `docs/STATUS.md`.

## Outcome

Native FLUX.2 was rejected for Mitch identity in this test. The best no-character-LoRA candidate tested on
2026-08-24 used Krea2 Identity Edit v1.2 as the whole-frame generator and scored `0.7459` against five held-out
genuine photographs (`strong_match`). It is now an archived fallback. It has a coherent body and street scene
with no face swap, output mask, crop, inpaint, or compositing. Mitch's visual approval remains the final gate.

The tested candidate is `output/no-character-lora-street-corner-v1/winner.png`.

## Why FLUX.2 was rejected

The earlier native Dev result scored `0.6865`, but Mitch correctly rejected it visually: the generated face did not have his eye, mouth, and jaw structure. The expanded audit then tested the remaining high-confidence changes without a character LoRA:

| FLUX.2 test | Centroid similarity | Decision |
| --- | ---: | --- |
| Klein 9B, improved four genuine references, `0.40 MP` each | 0.6275 | Identity still wrong |
| Same run, official `1.0 MP` reference scale | 0.6104 | More reference pixels regressed identity |
| Klein 9B native single genuine reference | 0.5439 | Identity drift |
| Dev native single genuine reference, 20 steps/guidance 4 | 0.5511 | Larger model did not solve identity |
| Klein 9B PuLID v2, maintainer's 512-square preprocessing/strength 1.3 | 0.4371 | Hard identity failure |
| Klein 9B native from a previously approved synthetic identity anchor | 0.5964 | Coherent street, wrong face |

More steps, reference resolution, prompt emphasis, and model size are therefore not the missing control. Native `ReferenceLatent` is useful semantic editing conditioning, but it did not function as a reliable face-identity lock for Mitch. PuLID is the only released FLUX.2 adapter found with an actual face embedding and an exact Klein 9B trained width; its author-exact run failed more strongly. Other searched FLUX.2 adapters were rejected before installation because they supplied generic SigLIP/style tokens, untrained runtime projections, or no author-linked trained checkpoint.

## Winning mechanism

One genuine photograph enters Krea2 Identity Edit through both of its trained paths:

1. VAE appearance tokens in `Krea2EditModelPatch`.
2. Image-aware Qwen3-VL instruction encoding in `Krea2EditGroundedEncode`.

An internal oval restricts the extra reference attention to the face. It exists only in reference-token space and never masks or composites output pixels. The model generates the face, body, clothing, crowd, cars, and street together in one pass.

Locked settings:

- Krea2 Turbo FP8
- Identity Edit v1.2 strength `1.0`
- masked reference boost `6`
- grounding `512`
- camera-appearance LoRA `0.35` (not a character LoRA)
- `832×1248`, 12 Euler/simple steps, CFG `1`
- seed `9472103`
- deterministic whole-frame phone finish

The controlled refinement changed only the genuine identity reference. The alternate reference regressed from `0.7459` to `0.6600` and looked less like Mitch, so the original locked photograph remains selected.

## Reproducible artifacts

- Archived ComfyUI workflow: `checkpoints/legacy-workflows/production/Krea 2 No Character LoRA Street Corner v1.json`
- Archived runner: `checkpoints/legacy-scripts/krea2-no-character-lora/run-no-character-lora-street-corner.ps1`
- Archived decision and hashes: `checkpoints/legacy-scripts/krea2-no-character-lora/no-character-lora-street-corner-v1.lock.json`
- Winner evaluation: `work/flux2-no-lora-reference-audit/krea2-locked-no-character-lora-street-corner.json`
- Rejected refinement evaluation: `work/flux2-no-lora-reference-audit/krea2-best-ref-no-character-lora-street-corner.json`

All reference photographs and evaluation stayed local.
