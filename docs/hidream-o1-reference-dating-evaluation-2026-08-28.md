# HiDream-O1 native-reference dating-photo evaluation

> **Historical record — not current instructions.** This experiment was rejected and its runnable files are archived. See `docs/STATUS.md`.

Status: completed experiment. Native identity conditioning passed; the generated
photo is **not approved for dating-profile use** because realism and composition
failed visual review.

## Research gate

- Model family: `HiDream-O1-Image-Dev`, not the older text-only HiDream-I1.
- Official checkpoint: Comfy-Org's repackaged
  `hidream_o1_image_dev_fp8_scaled.safetensors` (28-step Dev recipe).
- Conditioning mechanism: two genuine photographs flow from separate `LoadImage`
  nodes into the core `HiDreamO1ReferenceImages` node. That node appends the raw
  images to both positive and negative conditioning as `reference_latents`; the
  unified pixel-level transformer consumes those image tokens during generation.
- Conditioning class: native multi-reference subject-driven personalization.
  It is not style-only conditioning, generic img2img, a prompt-only identity
  description, face embedding, face swap, mask, inpaint, output composite, or
  character LoRA.
- Why identity preservation is a supported prediction: the authors state that
  HiDream-O1 was trained with subject-reference samples and demonstrate
  subject-driven personalization for preserving a subject across new scenes.
  Their official inference path requires two or more references for this mode.
- Reference order: image 1 is the near-front genuine photograph and image 2 is a
  genuine complementary angle of the same man. The official same-subject example
  supplies multiple views in a simple ordered list; no interchangeable role labels
  or special face/body slot semantics are documented for this mode.
- Exact Dev recipe: 28 steps, CFG 1.0, empty negative prompt, model noise scale 7.6,
  `normal` scheduler, and the official LCM sampler settings `1.0 / 1.0 / 2.5`.
- Resolution caveat: HiDream-O1 was trained near 4 MP. The first 832x1248 run is
  intentionally an approximately 1 MP project smoke test. One controlled rerun at
  the trained 1728x2304 portrait resolution is allowed before rejecting the
  mechanism for a low-resolution miss.
- Hardware: the RTX 3090 is actively training and must remain untouched. All setup
  and inference use only the idle RTX 4070 worker on port 8189.

## Prompting basis

The official prompt agent recommends a single natural English paragraph of roughly
80-220 words. It places the subject and intent first, then makes composition,
action, location, style, and camera details explicit. The local prompt follows that
structure and states that both references show the same person before describing a
new restaurant-patio dating photograph. The negative conditioning stays empty, as
required by the official Dev workflow; visible failure exclusions are written as
plain photographic requirements at the end of the positive prompt.

## Primary sources

- https://github.com/HiDream-ai/HiDream-O1-Image
- https://github.com/HiDream-ai/HiDream-O1-Image/blob/main/README.md
- https://github.com/HiDream-ai/HiDream-O1-Image/blob/main/prompt_agent.py
- https://arxiv.org/abs/2605.11061
- https://docs.comfy.org/tutorials/image/hidream/hidream-o1
- https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_hidream_o1_dev.json

## Acceptance checks

1. One untouched whole-frame result at approximately 1 MP on the RTX 4070.
2. Full-size and thumbnail review of face, hair, apparent age, body proportion,
   whole-frame integration, crowd diversity, depth, sharpness, noise, and halos.
3. Local InsightFace comparison against at least two genuine photographs. Scores
   are diagnostics only; visual identity review remains authoritative.
4. At most one controlled refinement. The planned change is resolution only,
   from 832x1248 to the trained 1728x2304 portrait size, with model, references,
   prompt, order, seed, steps, CFG, scheduler, and sampler frozen.

## Results

### Reproducibility and safety

- Official FP8 checkpoint: 8,067,535,296 bytes, SHA-256
  `7CBF53A475E0A13F92F2EC08BCFFDB9B9DE4305EF3B6F35CDD784D09DCD8D0CC`.
- Reference 1 SHA-256:
  `63F149C16C80C82BC77CD222A612C019920895530FD2C3A0765E78FDBA6E53EB`.
- Reference 2 SHA-256:
  `FEB62E762B990FB9979D730D9BA0A8D08C0CB81832DB6EAB308FE760C4A98B4D`.
- The runner verified both GPU states and all three ComfyUI queues before every
  generation. Both test prompts ran only on the RTX 4070 worker at port 8189;
  the RTX 3090 training worker was not queued or interrupted.
- A final no-generation preflight passed against the live RTX 4070 worker after
  the reusable workflow was updated to its tested resolution.

### Required approximately 1 MP smoke test

- Prompt ID: `1b07dcb1-375b-4690-a8e5-ef0cb784f3d5`.
- Settings: 832x1248, seed 8675601, 28 steps, CFG 1.0, normal scheduler,
  official LCM sampler and noise-scale settings.
- Runtime: 28.286 seconds.
- Output SHA-256:
  `9553ABCE9A177CB46985FCCCE95C99E8CB163E77F49ADCD53C5B5232A819E6A8`.
- Result: complete failure. The output is a featureless beige/mushy field with
  no detectable person or scene. This agrees with the core-node warning that
  HiDream-O1 regresses severely away from its roughly 4 MP training regime.

### One controlled refinement: trained portrait resolution

- Prompt ID: `f483d8f3-d5cb-4608-8cb4-93c692ad4c67`.
- Only changed variable: 832x1248 to 1728x2304. Model, two references and order,
  prompt, seed, 28 steps, CFG, scheduler, sampler, and noise scale were frozen.
- Runtime: 88.656 seconds.
- Output SHA-256:
  `99F5E2430E527AC3EA136AB7BA3D238CC1655C93DF5D91B5EA8F7290593AE49B`.
- Result: coherent vertical restaurant/courtyard image with a recognizable main
  subject, believable depth, varied background diners, and no cutout halo.

### Identity evidence

Local InsightFace AntelopeV2 comparison used five held-out genuine photographs,
not either source image. The candidate scored 0.7447 against the held-out
centroid and 0.6398 mean similarity, yielding the calibrated diagnostic
`strong_match`. Its weakest individual score was 0.5305, slightly below the
0.5533 floor between the genuine validation views, so this is strong aggregate
evidence rather than an identity lock. Thumbnail and full-size visual review
agree that the result is recognizably Mitch, although some facial geometry is
simplified and overly polished.

### Visual dating-photo review

- **Composition failed:** despite an explicit waist-up, slightly off-center,
  three-quarter request, the result is a centered close selfie. The detected
  face is about 622x924 pixels within the 1728x2304 frame and dominates the
  image; there is almost no body or dating-context action.
- **Skin and hair failed realism:** forehead lines are unnaturally carved while
  pores, stubble, and hair strands are smoothed into painted surfaces. The local
  normalized face diagnostic measured micro-luma variation of 3.402 versus
  6.041 and 4.132 in the real inputs. Normalized Laplacian variance was 97.5
  versus 624.7 and 280.4. These numbers are only flags, but the contact sheet and
  exact-pixel crops show the same obvious smoothing.
- **Scene partially passed:** depth, clothing, diners, tables, and subject
  integration are coherent. However, the apartment-courtyard geometry and
  lighting borrow heavily from reference 1 instead of creating the requested
  neighborhood restaurant, indicating scene leakage from the identity source.
- **Thumbnail partially passed:** the subject remains clear and recognizable at
  dating-app size, but the oversized head and synthetic polish remain visible.
- **No corrective post-processing was applied.** A face restorer, face swap,
  selective sharpening, SDXL/Z-Image refinement, or mask could obscure the
  mechanism verdict and risk changing identity.

## Verdict

HiDream-O1 Dev's native two-reference mechanism **does preserve identity well
enough to justify further research**, and it can run locally on the 12 GB RTX
4070 at its trained portrait size. The tested recipe **does not produce an
approved dating-profile photograph**: its low-resolution path fails completely,
and its trained-resolution result is too close, too smooth, and too influenced by
the reference background. The reusable graph therefore defaults to 1728x2304
and is explicitly labeled as a tested native-reference baseline, not a final
photo recipe. No additional generation was hidden after the single controlled
refinement.
