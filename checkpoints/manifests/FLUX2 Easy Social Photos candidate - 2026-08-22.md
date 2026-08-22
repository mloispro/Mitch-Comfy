# FLUX.2 Easy Social Photos candidate

## Purpose

This candidate adds a small preset UI and accepts one to four genuine photos without changing the accepted
`flux2-one-reference-v1.0.0` workflow or identity core. Put the clearest face photo first. Optional photos are
checked locally for same-person consistency and form a multi-photo embedding centroid used to rank the result
and decide whether one retry is needed.

Only the first photo's full image and automatic 2x face crop enter the FLUX.2 transformer. Controlled local
tests showed that passing every supplied photo as a model latent made both identity and speed substantially
worse. Extra photos therefore improve validation/ranking while the proven v1 generation path stays intact.

The UI exposes only:

- primary face photo plus zero to three optional genuine photos;
- plain-language scene prompt;
- smartphone, professional, or prompt-decides style;
- head-and-shoulders, waist-up, full-body, or prompt-decides framing;
- camera-facing, candid/looking-away, action, or prompt-decides moment.

Workflow: `workflows/experiments/FLUX.2 Easy Social Photos - 1-4 References.json`

## Accepted-core controls

| Case | Identity score | Time | Result |
| --- | ---: | ---: | --- |
| One upload through candidate, presets disabled | 0.8993 | 48.2 s | Exact frozen v1 route reproduced |
| Four uploads, validated action prompt | 0.8233 | 46.5 s | Difficult angle reproduced; extras used for centroid |
| Four uploads, professional preset | 0.8879 | 46.5 s | Correct eye contact, wardrobe, framing, and restrained realism |
| Four uploads, phone preset | 0.8896 | 46.7 s | Strong phone realism/identity; initial candid wording did not force gaze |
| Four uploads, final candid/no-eye-contact preset | 0.7908 | 49.2 s | Correct three-quarter gaze with expected harder-angle score |
| Four uploads, compact action preset | 0.7822 | 49.1 s | Correct looking-away action and realistic scene |

The final preset code includes the explicit no-eye-contact candid wording. The workflow remains a candidate
until Mitch visually accepts its outputs; v1 remains the production fallback.

## Rejected designs

| Rejected route | Identity score | Time | Reason rejected |
| --- | ---: | ---: | --- |
| Four full reference latents | 0.7344 | 164.1 s | Lower identity, two attempts, more than 3x v1 latency |
| Two full sources plus primary face crop | 0.7285 | 124.6 s | Lower identity, two attempts, more than 2x v1 latency |
| Long-form preset wording | 0.7604 | 49.3 s | Over-steered the action prompt despite normal speed |

FLUX.2 Klein officially supports up to four model references, but support is not evidence that more latents
help this identity-LoRA workflow. The measured local result determined the final design.

- Official overview: https://docs.bfl.ai/flux_2/flux2_overview
- Official inference repository: https://github.com/black-forest-labs/flux2
