# Upgrade High: source contours plus synthetic self-reference

Status: **rejected as a stronger-High route after the pilot and sole prompt-only
diagnostic; closed 2026-09-04.** No production changes. Previous goal turn was
progress: the Dev pilot and sole refinement showed clearer skin but failed eye,
cheek and original-pose fidelity. Do not repeat Dev strength/reference grids.

## Research gate and distinct hypothesis

Inventory found the already-installed RefControl Canny adapter. Its earlier GROUP
pilot is rejected: main similarity0.445 versus current Group0.619, changed hands,
small77px face and a differently framed genuine identity portrait. This is not
proof of readiness for Upgrade. No undocumented identity/phone adapter stack.
Other tasks' research and assets are read-only; their GPU work is preserved.

Different test: a close, same-framing edit where Picture1 is the ORIGINAL source's
full Canny contours, INCLUDING eyelids, mouth, nose, hairline and head outline.
Picture2 is the audited detailed, PhoneON Klein raw from that same photograph.
The latter is explicitly a GENERATED self-reference, not a genuine identity
photograph. Its identity originates in the preceding genuine-trained Klein LoRA
and genuine portrait conditioning; the second stage attempts to preserve that
appearance through an adapter TRAINED for reference identity + Canny fusion.
All likeness EVALUATION uses six real held-outs, never a generated reference.

This is not generic Canny fed to an untrained image slot: the matching Base9B
adapter and the author-trained order provide the proposed conditioning mechanism.
It may retain the raw's unflattering skin, over-copy the synthetic source's
geometry, or lose genuine likeness. The author's claim predicts reference
consistency, not Mitch identity or beauty; those require actual review.

## Primary evidence inspected

- [Author model card](https://huggingface.co/thedeoxen/refcontrol-FLUX.2-klein-9B-reference-canny-lora):
  trained on Base9B, control first/reference second, best with similar framing;
  primarily human training, identity/style transfer plus structural contours.
- [Author repository](https://github.com/thedeoxen/refcontrol).
- Pinned author workflow revision `be1fed28213ee9a176198b5d077727198e3cb4f4`, local
  SHA C71149905458FB3CE936317C6BD1D49B90104C9FF56238EBF47E192F2E26ED17.
  It actually uses20Euler/CFG5, adapter1, two1Mi-pixel nearest-exact references,
  fullFlux2VAE and empty latent dimensions from the resized control. The card's
  approximate50/4 is different; start from the concrete minimal example.
- [Author-used Canny preprocessor](https://github.com/Fannovel16/comfyui_controlnet_aux):
  CannyDetector and resize_image_with_pad source inspected. The node is NOT
  installed/live. The model author explicitly permits precomputed Canny images.
  Reproduce its CPU OpenCV preprocessing with installed dependencies: shorter
  edge512, area downsample/cubic upscale, edge padding to64, Canny100/200,
  remove padding, replicate grayscale toRGB. No node installation or update.

The original author's example filenames also identify generated image inputs;
this does not turn them into genuine identity evidence. Our synthetic-reference
status and six-genuine evaluation remain explicit.

## Frozen pilot

House original source -> CPU full Canny -> LoadImage -> nearest-exact1Mi-pixel ->
fullVAE -> firstReferenceLatent in BOTH positive and empty-negative branches.
Verified PhoneON raw -> LoadImage -> same resize -> fullVAE -> secondReferenceLatent
in BOTH branches. Base9B BF16 asset loaded FP8 (existing proven local adaptation,
NOT byte-identical to author's separate prequantized file), protected Qwen3 TE,
full VAE, RefControl only1.0,20Euler,CFG5, seed8675416. No Turbo. No character or
phone LoRA in this second stage. Phone appearance is inherited via Picture2.
No photo RGB masks/compositing, inpainting, restoration, sharpening or smoothing.

Use the existing flattened author graph, hash-pinned; replace only scene-specific
text, the two input filenames, seed and output prefix. The reusable text requests
source eye/smile/head contours, recognizable reference identity, lean cheeks,
rested clear skin with fine pores/stubble, natural highlighted hair and detailed
phone-camera background. No case-specific face correction or extra reference.

Review the actual Canny image BEFORE generation; if it has lost critical facial
contours, do not queue an ungrounded control test. Verify all live nodes/model
choices and fresh base/TE/VAE/adapter hashes. Locked3090/8188 only; check both GPUs
and queues, normal memory management only from the exact saved owned terminal
cache. Do not free/restart either card.

Acceptance: visibly stronger/flattering than Low, recognizable Mitch, closed
lips, source pupils/head/forehead/hairline and lean facial proportions, real skin/
hair/body/background at native size and thumbnail. Score against six genuine
photos. Original-source pose is the desired target; raw-pose differences remain
diagnostics because that raw already drifted. Do not call a score or a contour
match a beauty pass. At most one controlled refinement, then reject or advance
ONE coherent recipe to canyon and the held-out third before production/end-to-end.

## Pilot execution record

Prepared `refcontrol-high-house-inputs/source-full-canny.png`,853x512,
SHA `1E6AE5D9392BA95C4BCE148BAE8A28A5F7D0579678202AD2A425E8623EE9C53E`.
Pre-generation visual review against the original confirmed that both eyelids,
pupils, brow contours, nose, mouth/lip corners, visible jaw outline and hairline
remain legible. No face-interior clearing or RGB source replacement occurred.

Five RefControl graph/preprocessing tests and seven reused Dev/worker-ownership
tests passed. Both queue snapshots showed idle3090 and busy4070; the latter was
left alone. All four installed model hashes and required live nodes were verified.
Submitted exactly one job, `24370b9c-60bd-4062-a142-12cedfeeb5b7`, queue45, using
normal memory management from the verified owned terminal Dev0.8 cache. No free,
restart, extra adapter, model download or production change.

Completed in156.435 seconds. Native1312x784 PNG SHA
`C640C30EF711F3E556BC04DFC43AE6FA1350872A3536D9156D64AE73465A5A1B`.
The exact embedded graph and reference hashes passed provenance checks, but
likeness collapsed to0.244817 versus raw0.779115 / Low0.738950. Mouth opening
was0.127323 with plainly visible teeth; source-pose delta5.5711 degrees. Native,
individual face crops and thumbnail all reviewed: generic different-looking man,
squinting smile, conspicuous teeth, changed beard, somewhat rendered skin/hair.
Body and detailed siding/branches stayed broadly coherent without a cutout halo,
but this is clearly NOT a stronger recognizable High. No gaze/polish rescue.

Sole controlled refinement, declared before generation: replace ONLY positive
prompt text with the model card's literal `refcontrol` example. All model hashes,
adapter1, Canny, raw reference, seed,20steps,CFG5 and graph links stay identical.
This is a mechanism diagnostic: can the trained reference/contour path retain
the face without a long beauty prompt overriding it? It is NOT automatic High
acceptance even if resemblance improves. No strength, reference-order, resolution,
negative-prompt or extra-adapter grid after this refinement.

## Sole diagnostic result and decision — 2026-09-04

Trigger-only prompt `e2a95c64-f012-4a9d-8705-a9b3f55532b0`, queue46,
completed in150.345 seconds. Native1312x784 PNG SHA
`5AED65B3E6679D0B6F3E7AA45A0EA9A34C1B67D34C4294562A3C159D11E6B2B9`.
Fresh model hashes and queue checks passed. Saved graph comparison confirmed
ONLY node5 positive text and node37 output destination changed. The negative
branch, ordered references,20steps,CFG5,adapter1 and seed were identical.

Six-genuine likeness recovered to0.764295 (raw0.779115, actual Low0.738950);
closed-lip ratio0.000025, source-pose delta3.486877 degrees, raw-pose delta0.449699,
source-relative eye delta0.044277. Native PNG graph/reference hashes verified.
The source-pose flag is borderline and NOT the reason to reject this as High.
The actual full-size, face and thumbnail review showed the raw's tense brow,
heavier lids and dotted/coarse skin remained; the desired source eye shape and
more flattering expression did not return. The background remained readable and
coherent, body/clothing stable, no obvious face-cutout halo, but hair is still
somewhat stringy and the face is not a visibly stronger attractive alternative.

Interpretation: the original beauty prompt, as a whole, caused the huge likeness
loss in this controlled pair. This does not isolate prompt length from semantics
and does not prove every RefControl configuration fails. The author's minimal
trigger preserves the generated reference reasonably here, but does not achieve
the requested fine facial changes. Do not add another prompt/strength/CFG grid or
claim that a likeness score alone validates High. No gaze, skin polish or RGB
composite was applied to rescue either candidate.

Artifacts under `work/upgrade-source-faithful-20260903/`:

- `refcontrol-high-house-inputs`: original-source audit and exact CPU Canny.
- `refcontrol-native-high-house`: failed beauty-prompt manifest/submission/evaluation.
- `refcontrol-native-high-house-trigger`: sole diagnostic manifest/submission/evaluation.

Six RefControl unit tests and seven reused Dev/worker tests pass; these prove
plumbing, not beauty. The six protected production code/UI/workflow hashes remain
unchanged. End snapshot: both queues empty,3090/4070 utilization0; no explicit
free or worker restart. No accepted candidate advanced to canyon/third, and no
production/end-to-end success is claimed. The broader three-picture stronger-High
goal remains incomplete. This turn made bounded diagnostic progress, not a new
external-state block; do not rediscover/retry this closed route next turn.
