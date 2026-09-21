# High expression and cheek investigation — 2026-09-03

## Status

Both generation experiments are complete and rejected as production solutions. The active Off/Low/High
implementation and defaults remain unchanged. Stronger attractiveness/expression is **not resolved**.
Mitch reported that High is too similar to Low, the cheeks look fuller than his real face, and the
source smile is preferable. The existing High is a small deterministic retouch of the same generated
face as Low; it cannot be presented as a material generation-level expression correction.

## Observations and rejected micro-edit

The canyon raw generation already differs from the source expression. Its mouth corners are more
uniformly lifted. Source-relative landmark measurements suggest asymmetry, not a larger smile, is
the useful target. Face-width estimates do not establish substantial anatomical widening; expression
and shading can make cheek fullness look different without a larger outline.

An offline half-strength mouth-column remap moved existing generated pixels toward the source's
relative lip-corner positions. No source pixels were copied. Measured corner error fell from 0.061876
to 0.039984 (35.38%), but the visible change remained too small to answer Mitch's request. This is
not enabled in production. Evidence: `work/flux2-klein9b-attractiveness-20260903/canyon-smile-half-v1/`.

The experiment retained identical eye, brow and nose pixels relative to the pre-expression High.
Whole-face landmark redetection nevertheless changed the apparent gaze diagnostic to 0.024016.
The replay utility records this redetection confound separately: accepted pre-expression High must
still pass the 0.02 gaze check, and the expression step must preserve the protected pixels exactly.
It saves failed candidates and their validation errors instead of discarding their evidence.

## Single-variable generation test

Prompt ID: `6efa5e06-402a-4f61-8d0b-fbee5230e5e6` on local RTX 3090, port 8188.
Runner: `scripts/run-upgrade-expression-test.ps1` (one-shot; do not rerun to poll).
Manifest: `work/flux2-klein9b-attractiveness-20260903/generation-high-v1/experiment.json`.

Only one detail-instruction paragraph was added: preserve the source's restrained asymmetric
closed-lip smile and naturally lean cheek planes. The paragraph is saved verbatim in the manifest.
The seed (8675412), native 1024-square output, 50 steps, CFG 4, Euler, Base 9B fp8 model, identity
LoRA at 0.90, Smartphone Snapshot v1.3 at 0.25, references and their order remain unchanged.
Phone style is on and Turbo is off. Appearance is off during generation so raw output can be
compared and the accepted Low/High treatments replayed separately. No experimental mouth remap
or cheek-tonal adjustment is mixed into this test.

The existing conditioning path is preserved: Picture 1 is the source edit/composition image,
Picture 2 the face-free structural guide, Picture 3 the protected genuine identity reference, and
Picture 4 the isolated hair reference, each encoded to native reference latents. Explicit identity
conditioning also includes the existing trained identity LoRA. The source's identity influence is
not isolated; native edit conditioning is not a guaranteed identity lock. The textual instruction
is an expression target, not a new identity mechanism.

Primary-source basis: the [Base 9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
and [BFL image-editing guidance](https://docs.bfl.ai/flux_2/flux2_image_editing) support native reference
editing and explicit edit descriptions, but do not guarantee exact expression or identity preservation.
The experiment tests that uncertainty rather than assuming text will fix it.

## Acceptance

Inspect full frame, face crop and thumbnail against the source and previous Low/High. Look for a
visible but believable change, restrained closed lips, less rounded-looking cheeks, retained gaze,
head angle, forehead/hairline, skin/hair realism, and coherent background detail. Compare identity
with six genuine held-out photographs, not the edited source. Scores are diagnostics, not an
attractiveness measure or identity lock. Reject a stronger look that meaningfully sacrifices likeness,
expression fidelity or whole-image realism. No production/default change until this review passes.

## First generation result

Completed in 435 seconds. Raw output:
`C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260903-144859-764011\photo_00001_.png`.
Replay and comparisons: `work/flux2-klein9b-attractiveness-20260903/generation-high-v1/polish/`.

| Diagnostic | Previous raw/High | New raw/High |
| --- | ---: | ---: |
| Raw identity centroid | 0.751794 | 0.773237 |
| High identity centroid | 0.724661 | 0.744635 |
| High weakest genuine reference | 0.515342 | 0.525063 |
| High mean source-relative lip-corner error | 0.061876 | 0.059543 |

The weakest High similarity still falls below the 0.553346 genuine pairwise floor. High's estimated
pose changed by approximately -0.34/+0.48/+0.48 degrees (pitch/yaw/roll) from previous High. The
small identity-score improvement did not translate into a convincing visual expression improvement:
the face remains close to Low, with the same more uniformly lifted smile. **Rejected as an adequate
solution to Mitch's complaint**, not promoted.

The executed effective prompt was checked: removing exactly the added paragraph yields the baseline
effective prompt byte-for-byte. Model, encoder, VAE, identity LoRA and reference hashes, strengths,
encoded reference sizes, source decoded-pixel hash, seed, dimensions, CFG, steps, sampler and smartphone
LoRA metadata match. The prose description of Picture 1 in the report differs because of earlier
report-hardening, not because the reference order or latent encoding changed.

## One controlled refinement

Prompt ID: `2683882b-1320-4685-a97b-424de94909b4`. Manifest:
`work/flux2-klein9b-attractiveness-20260903/generation-high-v2/experiment.json`.
Only the added paragraph was replaced. It more explicitly assigns the lip curve and relaxed smiling
eye expression to Picture 1, with lean lower cheeks and rested presentation. All other settings remain
fixed. This is the single permitted generation-prompt refinement before deciding whether this mechanism
answers the request. The small mouth-remap prototype remains offline-only in
`scripts/experimental_upgrade_smile_balance.py`; it is not loaded by the production custom node.

## Second generation result and decision

Completed in 417 seconds. Raw output:
`C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260903-145712-921623\photo_00001_.png`.
Replay and comparisons: `work/flux2-klein9b-attractiveness-20260903/generation-high-v2/polish/`.

The second candidate is visibly a little different, but not a clear improvement. The source's relaxed
asymmetry still is not reproduced. The lip-corner diagnostic improved to 0.043150, but High identity
centroid fell to 0.710118 (raw 0.735161), and its weakest genuine reference was 0.513662. The normalized
gaze-redetection check was 0.029461, above the retained 0.02 gate. That check is a diagnostic rather than
proof of actual pupil motion, but the candidate does not pass it. No threshold was loosened to accept
the result. The replay saved images and `validation_errors` before returning exit code 1.

Full-frame and crop inspection found recognizable scene structure, similar pose and continuous head/hair
boundaries, but neither a convincing source-smile match nor enough improved appearance to justify the
likeness tradeoff. Both images retain a small dark/open-looking lip seam rather than clearly achieving
the requested softly closed source mouth. **Do not promote either prompt or the mouth-remap prototype.**

The finding is narrower than “the model cannot do this”: small retouch changes and these two appended
prompt instructions did not reliably solve this case. Existing High deliberately protects lips/head
outline and therefore cannot correct the raw expression/cheek drift. The next useful investigation is
the source-expression versus fixed-identity-reference influence, not another small sharpening/contrast
increase. That conditioning balance has not been isolated by these tests.

The local Klein Qwen3 tokenizer was inspected for a possible 512-token cutoff. Its configured
`min_length=512`, `max_length=99999999` and `pad_to_max_length=False` do not indicate such a tokenizer
cutoff; do not claim the extra instructions were simply truncated based on prompt length.

Validation: 135 existing project unit tests and five offline-remap safety tests pass. Low remains
SHA256 `D970934CE4CF0B640A4BD24ABD7DA3BFA16A67F23842CBC81B14B4323793977B`; active High remains
`5FE7A4F3A9FC799AD2D0AB606D2C075D081DE6C4042EDEDF1145EF65B75920AB`. No production implementation,
model, default or workflow JSON change was made during this expression investigation. Earlier uncommitted
Off/Low/High work is preserved. Defaults: Low, phone on, Turbo off.
