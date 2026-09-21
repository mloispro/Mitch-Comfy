# Solo Cocktail comparison — use the completed Speed handoff

The source comparison is complete. For the accepted closed-lip, slight image-left
gaze Cocktail case, use **Mitch/production-speed → Individual - Cocktail - Tested
Recipe - RTX 3090** at [ComfyUI](http://127.0.0.1:8188/), with its saved seed
315982047 and default settings. That ordinary-Run handoff already passed; no new
image or production change was needed to finish this comparison.

The [public result](../work/9b-readiness-resume-20260907/public-cocktail-parity/ROOT-RESULT.md)
failed mouth/gaze review despite passing likeness diagnostics. The accepted
[Speed result](../work/production-speed-rollout/RESULTS.md) passed the existing
full-size/thumbnail and genuine-reference requirements for its exact recipe.
This comparison does not transfer that acceptance to other seeds or scenes.

## Exact differences and shared inputs

[Machine-readable comparison](../work/solo-cocktail-comparison-20260921/comparison.json)
and its [read-only audit](../work/solo-cocktail-comparison-20260921/compare.py)
record the full prompts, reference hashes, source hashes and executed graph checks.
The audit script/data and this report are also preserved in the verified local
`local/solo-cocktail-comparison-20260921/evidence.zip`; its sibling `verification.json`
records SHA256 read-back checks. The accepted and failed image files remain in place.

| Setting | Failed public execution | Accepted Speed execution |
| --- | --- | --- |
| Genuine references in order | Front 448×592; left-facing portrait 448×592 | Same front 448×592; body 512×512; angle09 432×576 |
| Reference roles in text | Both photos anchor identity, adult age and body proportions | Pictures 1/3 anchor face/hair; Picture 2 requests body proportions only |
| Effective positive prompt | 481 words: reference contract, general appearance block, scene, bare-neck reminder, general finish | 331 words: three-reference contract, identical scene, explicit hand/framing and mouth/gaze directions, shorter appearance block, scene-specific finish |
| Diffusion loading | Native loader `default`; historical run-correlated log reports BF16 without manual cast | Explicit `fp8_e4m3fn`; Speed guard enforces it |
| Seed in compared runs | 315982047 | 315982047 |
| Models and LoRAs | Same Base9B checkpoint, Qwen FP8mixed and full VAE; Turbo 1 → identity V3 step1600 .90 → Phone v13 .25 | Same files, strengths and order |
| Sampling/output | Euler, Flux2Scheduler, 8 steps, CFG 1, 832×1216, empty initial latent | Same |
| Conditioning | Genuine photos resized Lanczos, VAE encoded, appended as native reference latents to both CFG branches; empty negative text | Same mechanism with the different reference bundle |

Both recipes request appearance enhancement and closed lips. This is not an
appearance-on versus appearance-off comparison. The scene paragraph is identical;
the surrounding prompt differs. Textual body-only roles do not enforce hard
identity isolation. Public reference dimensions above follow Comfy LoadImage's
EXIF orientation before the engine's aspect-preserving resize; raw JPEG dimensions
would incorrectly suggest landscape inputs.

The compared public test deliberately used the same seed as Speed. The original
public workflow's saved default seed is 8675411, so its unchanged defaults are not
the exact failed test either. Neither seed inherits another recipe's acceptance.

## What the fresh checks establish

- Seven public engine/prompt/preset/resize source files still match their historical
  execution pins. Current Cocktail preset fields match the failed run, and composing
  its effective prompt now reproduces the saved engine report exactly. The gallery's
  later St. Barts changes did not repair or alter Cocktail.
- The current Speed workflow hash matches package provenance. Packaged API, completed
  history and native PNG graph agree exactly; both compared PNG hashes still match
  their original receipts. Five recipe-reference entries were freshly hashed
  (four distinct genuine photographs, with the front photo shared).
- All 31 Speed execution nodes and their scalar dropdown choices are available on
  the current 3090/8188 API. This is a read-only exposure check; no model was loaded
  and no new image was generated. Historical successful Run evidence remains the
  runtime/visual acceptance evidence.

## Decision and remaining uncertainty

No preset-resolution defect was demonstrated. The wrapper resolves the requested
Cocktail scene/profile and forwards it to the engine as designed. Three groups of
variables changed together: reference bundle, surrounding prompt and diffusion
precision. The saved observations cannot identify which caused the mouth/gaze
difference, and the shorter prompt is not proven causally better.

Use the existing accepted workflow for this bounded case. Do not copy its full
prompt into the public card: it refers to Picture 3, while the named public preset
forces the two-photo front/left profile. Changing the profile dropdown with that
named preset does not recreate the three-reference recipe. Do not globally disable
appearance or replace all scene profiles based on this one comparison.

If original-card parity becomes a required feature, the smallest clean diagnostic
would isolate the diffusion-loading policy while holding the public prompt,
references/order/resize, seed and sampling fixed. It would require a separately
recorded controlled experiment and the same mouth/gaze/likeness/anatomy review;
an FP8 improvement is unproven. Do not loosen the existing Speed guard to perform it.
No such experiment or new workflow is prepared or queued by this report.

The immediate Cocktail handoff is complete. Broader Upgrade source coverage remains
the next separate development candidate; stronger High and general Group remain
unresolved. All existing controls, photos and models stay preserved.
