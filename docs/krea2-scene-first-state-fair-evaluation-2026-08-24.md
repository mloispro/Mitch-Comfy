# Krea2 scene-first state-fair evaluation — 2026-08-24

> **Historical record — not current instructions.** This route was rejected. See `docs/STATUS.md` for current state.

## Objective

Test the final proposed role for Krea2 in complex scenes: generate the crowd and environment first,
then use the training-matched two-image Krea2 Identity Edit layout (scene first, genuine identity
photo second) to restage Mitch as the existing foreground host.

## Scene plates

- Generator: FLUX.2 Klein 9B KV FP8
- Worker: RTX 3090
- Resolution: `896x1344`
- Sampler: Euler, four native distilled steps
- Seeds: `8675401`, `8675402`, `8675403`, `8675404`
- Total four-plate runtime: `30.25` seconds
- Selected plate: seed `8675401`

The selected plate had the best coherent fair layout, one Ferris wheel, a compatible foreground
host, deep crowd detail, and naturally varied red, green, yellow, blue, patterned, black, and white
clothing. Other candidates had duplicate Ferris wheels, an intrusive foreground foot, or a selfie
arm.

## Krea2 identity edit

- Model: Krea2 Turbo FP8
- Identity adapter: Krea2 Identity Edit v1.2
- Reference order: state-fair scene first, genuine Mitch photograph second
- Smartphone LoRA: `0.35`
- Resolution: `832x1248`
- Sampler: 12 Euler/simple steps, CFG `1`
- Seed: `9472103`
- Grounding: `512`
- Scene reference boost: `1`
- Identity reference attention: automatic internal-face mask
- Whole-frame phone finish: enabled

Edit prompt used for both identity runs:

```text
Use the first image as the complete state-fair scene and the second image only as the identity reference. Restage the exact same man from the second image as the central foreground man already walking toward the camera in the first image. Preserve his exact recognizable facial identity, face shape, forehead lines, eye shape and spacing, nose, mouth, ears, short light-brown hairstyle, hairline, apparent age, natural skin texture, and lean build. Keep the host's existing full-body scale, walking position, camera angle, perspective, and natural integration; dress him in a plain fitted navy crew-neck T-shirt, dark casual pants, and ordinary dark sneakers. Preserve the first image's state-fair layout, Ferris wheel, stalls, umbrellas, pavement, railings, daylight, crowd density, every surrounding person's independent clothing colors, depth order, overlaps, motion, shadows, and phone-camera texture. The subject must share the same exposure, sharpness, noise, depth, and edge softness as nearby fairgoers. Do not simplify, recolor, blur, regenerate, duplicate, or coordinate the background crowd. No flash, portrait blur, beauty filter, cinematic grade, face swap, collage, pasted head or body boundary, halo, selective sharpening, legible text, logo, or watermark. Make the result look like the same ordinary phone photograph captured in one moment, with only the central foreground man's identity and clothing naturally restaged.
```

### Baseline masked identity boost 6

- Worker: RTX 4070
- Approximate runtime: 100 seconds
- Four-reference centroid similarity: `0.5606`
- Status: `identity_drift`

The fair layout, crowd colors, depth, and most plate detail survived. The subject had no obvious
head-mask halo, but retained too much of the plate host and did not meet Mitch identity acceptance.

### Single controlled retry: masked identity boost 12

- Worker: RTX 3090
- Approximate runtime: 73 seconds
- Four-reference centroid similarity: `0.5583`
- Status: `identity_drift`

Doubling only the masked identity-face attention did not improve identity and slightly regressed the
score. All other variables were held fixed.

## Verdict

Reject Krea2 two-image host replacement as the complex-crowd identity route. Scene-first generation
solved the background diversity and detail problem, but Krea2 did not overcome the existing host's
identity. Do not spend additional time on prompt length, negative conditioning, resolution,
sharpening, or higher identity boost for this mechanism.

Keep the accepted single-reference Krea2 Face Attention workflow for solo and lightly populated
photographs. For state fairs, clubs, lounges, and dense streets, retain the strong Klein 9B scene
plate and test a FLUX.2 Klein Base 4B plus Mitch identity-LoRA subject regeneration route instead.

## Artifacts

- Selected plate: `output/scene-first-state-fair-plate-seed-8675401.png`
- Boost-6 result: `output/scene-first-state-fair-krea2-identity-20260824.png`
- Boost-12 result: `output/scene-first-state-fair-krea2-identity-boost12-20260824.png`
- Boost-6 identity report: `work/identity-evals/scene-first-state-fair-krea2-20260824.json`
- Boost-12 identity report: `work/identity-evals/scene-first-state-fair-krea2-boost12-20260824.json`
- Reusable plate runner: `scripts/run-klein9b-scene-plates.ps1`
