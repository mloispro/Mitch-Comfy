# FLUX.2 Easy Social Photos realism candidate — 2026-08-22

## Goal

Keep the accepted private identity LoRA while removing the visibly over-detailed, separately rendered
face/head seen in the city-sidewalk result. Frozen v1 remains unchanged under
`flux2-one-reference-v1.0.0`.

## Selected profile

- Model: FLUX.2 Klein Base 4B FP8
- Identity LoRA: `m1tch-flux2-klein-4b-identity-v1-best.safetensors`
- LoRA strength: `0.4`
- Guidance: `2.0`
- Sampler/steps: Euler, 20
- Model identity inputs: primary full photo plus automatic 2.4x face crop
- Reference resolution: 0.25 MP per derived input
- Additional uploaded photos: same-person validation and output-centroid scoring only
- Retry: one extra seed only below `0.75`; retain the higher identity score

The prompt presets append one camera-coherence instruction covering face, hair, neck, body, clothing,
lighting, edge softness, and camera texture. Phone and professional styles use the same compact workflow.

## Controlled A/B evidence

All city tests held the genuine reference, base scene request, seed `8675310`, 768x1024 output, Euler
sampler, and 20 steps constant. Candidate variants after the prompt-isolation test also held the selected
camera-coherence suffix constant.

| Variant | Identity score | Seconds | Result |
| --- | ---: | ---: | --- |
| Reported artificial face/head: 2.0x crop, 1.00 MP, LoRA 0.6, guidance 4.0 | 0.8704 | 47.582 | Rejected visually |
| Full photo only, 0.64 MP, LoRA 0.4, guidance 3.0 | 0.7825 | 26.711 | Natural but too much identity loss |
| Face crop only, 0.40 MP, LoRA 0.4, guidance 3.0 | 0.7585 | 26.869 | Natural but too much identity loss |
| Full + 2.4x crop, 0.25 MP, LoRA 0.4, guidance 3.0 | 0.8921 | 27.368 | Strong balance |
| Full + 2.4x crop, 0.25 MP, LoRA 0.4, guidance 2.5 | 0.9054 | 25.503 | Better |
| **Selected: full + 2.4x crop, 0.25 MP, LoRA 0.4, guidance 2.0** | **0.9112** | **25.329** | Best balance |

## Held-out workflow checks

| Case | References | Identity score | Seconds |
| --- | ---: | ---: | ---: |
| Professional waist-up window portrait | 1 | 0.8834 | 28.222 |
| Smartphone full-body lakeside action | 4 | 0.7511 against four-photo centroid | 25.881 |

Raising the retry threshold to `0.80` caused the action case to generate a second candidate scoring `0.7483`,
worse than the first, and increased total time to `51.565` seconds. The cutoff therefore remains `0.75`.
Automated identity scores are drift diagnostics; the subject's visual judgment remains the acceptance test.
