# Krea2 Mitch busy-sidewalk experiment — rejected

> **Historical rejected plan — do not execute it.** The character LoRA and live launchers were removed on
> 2026-09-01. See `docs/STATUS.md` for current workflows and installed weights.

## Intended mechanism

The graph tested a one-pass Krea2 Turbo generation in which a locally trained Mitch character LoRA would create
the person, body, lighting, sidewalk, and pedestrians together. It deliberately avoided face swap, masks,
restoration, relighting, sharpening, and compositing. That mechanism was worth testing because earlier masked
host-replacement routes produced oversized heads and obvious subject/background boundaries.

## What happened

The LoRA provenance was valid: Krea2 Turbo-adapter base, 22 genuine Mitch photographs, trigger `m1tch_person`,
rank/alpha 32, and a completed 500-step run. Controlled one-pass tests at strengths `0.85` and `1.00` produced
coherent, naturally integrated photographs, but the person was plainly not Mitch. Held-out centroid similarity
was only `0.2323` and `0.2632`. Stacking the same LoRA into scene-first Identity Edit also failed to remove the
composited appearance.

The experiment was therefore rejected. The character LoRA and publication launcher were deleted; strength
sweeps, prompt expansion, or higher undocumented strengths are not justified.

## Preserved evidence

- Archived graph: `archive/krea2-workflows/Krea 2 Mitch - Busy Sidewalk (Unavailable Personal LoRA).json`
- Evaluation: `docs/krea2-character-lora-state-fair-evaluation-2026-08-24.md`
- Archived runner: `checkpoints/legacy-scripts/krea2-character-lora/smoke-krea2-character-lora.ps1`

The retained Krea2 Identity Edit and smartphone LoRAs support only the archived no-character fallback. Current
identity-sensitive generation uses the protected Klein 9B V3 workflow family.
