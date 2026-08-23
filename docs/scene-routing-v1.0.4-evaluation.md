# Easy Social Photos v1.0.4 scene-routing evaluation

## Goal

Reduce obvious background-generation tells without adding controls to the two-node social-photo workflow or
weakening the accepted 4B identity LoRA path. The motivating failures were a headrest visually fused behind the
subject, repeated cool-colored crowd clothing/faces, and ambiguous traffic orientation.

## Shipped design

The node infers scene contexts from the ordinary prompt and selected moment. It composes only the relevant rules
for car interiors, traffic, crowds, background extras, requested groups, reflections, action, held objects, and
signage. Simple scenes stay on the direct Base 4B + identity LoRA path.

Prompts containing background crowds, requested groups, reflections, or combined crowd/traffic use an automatic
complex route:

1. FLUX.2 Klein 9B KV FP8 creates a four-step scene layout using one automatically selected genuine reference for
   approximate body proportions.
2. The largest layout face is detected locally and strongly pixelated/blurred with a feathered head mask so its
   wrong identity cannot dominate the final pass.
3. The layout is reduced to `384×576` structural evidence.
4. FLUX.2 Klein Base 4B re-renders the entire `896×1344` photograph with the trained identity LoRA, the selected
   genuine full reference, and its derived face crop.
5. The existing identity gate ranks/retries before optional deterministic phone-lens optics.

This is not a face swap, masked pixel composite, SDXL refiner, or local VLM approval gate.

## Controlled results on RTX 3090

| Test | Route | Time | Identity score | Result |
| --- | --- | ---: | ---: | --- |
| Car/headrest regression | direct 4B | 36.0 s | 0.8406 | Headrest offset from head with seatback/supports readable; one pass |
| Dense street before routing | direct 4B | 36.8 s | 0.8316 | Rejected: front-facing row, repeated cool shirts/faces |
| 9B scene-only proof | native 9B KV | 21.8 s | 0.5302 | Scene improved; rejected identity |
| Full-resolution 9B anchor + 4B identity | two stage | about 64 s | 0.9038 | Rejected: visible head graft/halo |
| Low-resolution identity-erased anchor experiment | two stage | about 64 s | 0.9105 | Accepted architecture: integrated head and preserved scene structure |
| Final integrated dense street | automatic complex | 59.2 s | 0.8946 | One identity pass; varied extras and coherent parked traffic |

The final output report records the route, inferred contexts, model stages, anchor identity-removal bounds, seeds,
timings, reference analysis, identity threshold/status, and phone-optics metrics.

## Rejected approaches

- Prompt rules alone improved the car but did not make the 4B model reliable on dense crowds.
- Qwen3-VL 4B falsely accepted the known car defect at about `85/100` and hallucinated evidence.
- Qwen3.5 4B also falsely accepted it at `92/100` after about 44 seconds. It was more latency, not a trustworthy gate.
- A full-resolution 9B layout reference copied pixels too literally and produced a composited-looking head after identity correction.
- The native 9B output had much better scene logic but unacceptable identity drift without the 4B LoRA pass.
- An SDXL refiner cannot reason about which headrest, vehicle direction, or repeated person is wrong and adds another
  model family, so it remains excluded.

## Limits

No local metric proves that a generated scene is real. The identity score is a drift filter, not visual proof, and
the scene router prevents or reduces known failure modes rather than certifying every background. Final review by
the subject remains authoritative. v1.0.3 is unchanged and remains the exact rollback baseline.
