# Source-faithful Upgrade: paused implementation plan

**Paused by user on 2026-09-04; resume only when requested.** The unfinished
High implementation and rejected PixelSmile probe are in
[Experiments](../workflows/experiments/Upgrade%20High%20-%20PAUSED%202026-09-04/README.md),
with frozen code, settings, evidence and a handoff. This is preservation, not
completion or production acceptance. No generation or reminder was scheduled.

Status: incomplete. The prior PixelSmile download blocker is resolved by Mitch's explicit
"download whatever you want" approval. See the current research note and STATUS for the isolated
genuine-source pilot. Earlier completed experiments below are historical,
not a claim that a live generation is running. The full three-photo result is still required.
The PixelSmile 0.5 pilot and sole score-0 neutral control are now complete and
visually rejected: likeness 0.328812 / 0.365971 versus genuine source 0.797263,
altered eye/nose geometry, lost smile, and soft face. No further expression/seed
sweep, production promotion or three-photo expansion. This rejects the tested
local configuration; author BF16/bicubic parity is not established. Download
permission is not a blocker. No generation remains queued from this experiment.

Latest character-LoRA preference, 2026-09-04: **no new character LoRA training**.
Prefer a workflow without a character LoRA; retain the existing one only if comparative evidence
shows it is needed for the best recognizable, realistic result. Do not assume it is necessary.
This applies to the entire image lineage, not only the last edit stage: an upstream character-LoRA
render followed by a LoRA-free editor is not an end-to-end character-LoRA-free workflow.

The saved house/canyon/third `source_only` manifests all retain character LoRA strength 0.9.
Their label describes image-reference count, not removal of the character LoRA. They therefore
do not settle the user's preference. A search of this effort's experiment manifests found no
explicit `identity_strength: 0` test; this is not an exhaustive claim about every historical
project experiment. Before retaining or removing the character LoRA, verify actual graph
connections and source provenance and compare against genuine photographs on all three cases.

PixelSmile is a general expression adapter, not a Mitch character LoRA and not new identity
training. This preference does not itself approve downloading it, changing dependencies, or
removing the current production LoRA. The existing LoRA is permitted as a fallback, not mandated.
No new training job or production change follows from this clarification alone.

Latest explicit preference,2026-09-03: **"Stronger beauty edit, still recognizably me."** High should
prioritize a clear beauty improvement over near-byte-identical facial appearance. A modest likeness
tradeoff is acceptable; the requested diagnostic target around0.70, recognizable identity and visual
quality still matter. A small embedding drop alone is not a sufficient reason to reject a visually good
candidate. Keep no-teeth smile, pupil focus, head direction/forehead, coherent texture and realistic scene.
Low remains the conservative option. This preference does not authorize hosted uploads or purchases.

## Completion requirements

- Off/Low/High must have clear semantics and visibly useful separation. High should produce a recognizably
  same-person best-day result, not merely darken eyebrows. Low must remain a useful restrained treatment.
- Preserve source head direction, pupil focus, appealing expression and natural closed-lip smile; no invented
  teeth, enlarged forehead, inflated cheeks, or generic replacement face.
- Clearer skin with reduced freckles/dots and fine lines, real pores and groomed stubble, natural hair with
  slight highlights, subtly flattering eyes/brows and facial definition; no waxy skin or cosmetic patches.
- Keep composition, body, scene integration and recognizable detailed background. Phone defaults on;
  phone off gives believable softer background separation. Turbo remains off for this workflow.
- Use one coherent recipe on the canyon and house cases, then verify a third genuine photograph. No
  per-photo hardcoded face coordinates or cherry-picked scoring references. Show labeled side-by-sides.
- Evaluate at native size and thumbnail, score against multiple genuine photographs with source exclusion,
  and report score limits honestly. A score is not proof of attractiveness or identity lock.
- Integrate the accepted recipe into the actual public workflow, with legacy-value migration, accurate
  reporting, updated tests/baselines/docs, and end-to-end live-node verification. Until evidence proves all
  of this, leave the goal active.

## Mechanism diagnosis and first ablation

The current source face enters native edit latents, alongside a face-free Canny guide, a separate frontal
identity photo and an isolated hair reference. Identity also enters through the protected trained Base9B
LoRA. Low then applies an unconditional, image-axis lift to both mouth corners and cheek brightening.
These are separate potential causes of expression/fullness drift and need isolated tests.

First ablate only the separate identity portrait. Retain source (1 MP), guide (0.5 MP), hair (0.1 MP), the
identity LoRA at 0.9, smartphone LoRA at 0.25, 50 steps, CFG4, Euler and seed8675412. Remove that portrait's
prompt role, renumber the hair reference, and keep the character trigger. Raw comparison precedes polish.
This tests a reference-conditioning hypothesis, not another stronger-beauty paragraph. If identity fails,
make at most one controlled strength refinement before deciding whether this mechanism works.

## Research gate

- Inspected the installed author template `image_flux2_klein_image_edit_9b_base.json`, single-reference
  subgraph `7b34ab90-36f9-45ba-a665-71d418f0df18`: LoadImage -> scale -> VAEEncode -> ReferenceLatent on
  positive and negative conditioning; CFGGuider/Euler/Flux2Scheduler -> empty Flux2 latent -> decode.
  Its example uses20steps/CFG5 and a small decoder. Keep our verified50/CFG4/fullVAE instead to isolate
  the reference change; no VAE or sampler change is needed for this experiment.
- [Official model repository](https://github.com/black-forest-labs/flux2) documents native single- and
  multi-reference editing for Base9B. [Single-reference editing guidance](https://docs.bfl.ai/guides/prompting_editing_single_reference)
  supports precise edits and retained context, not guaranteed identity locking.
- [BFL training guide](https://docs.bfl.ai/flux_2/flux2_klein_training) supports character LoRAs on Base.
  Local config `config/flux2-klein9b-identity-v3-r32-dop-3090.yaml` and selected step1600 provenance
  establish an actual genuine-photo-trained identity mechanism, not style-reference-only identity.
- Existing hashes, exact Base9B/Qwen3-8B/full Flux2 VAE compatibility and live node/model availability
  are validated before queuing. Same3090 lock, no external photo transfer, no Turbo or new model.
- Prediction: removing a competing face may improve source expression; the identity LoRA should retain
  likeness. Both parts are unproven in this reduced-reference configuration and must be measured.

## Work log

- Reduced-reference canyon run submitted as `aa896fc4-bdc8-490b-a1e9-86989f7c4660`, port8188, after both
  cards/queues and protected model hashes were checked. Reproducible graph/manifest under
  `work/upgrade-source-faithful-20260903/no-identity-canyon/`. Status must be read from live history.
- CPU ablation removed only the legacy corner lift, preserving the production file bytes. Canyon High
  centroid0.724661 ->0.742639; house0.727175 ->0.756096. The mouth looks less forced, not fully source-matched.
- Single refinement additionally removed cheek brightening. Canyon High0.742472, house0.757390; small
  visual benefit, not a solution to stronger High. Both variants still exceed the old whole-face
  gaze-redetection threshold. No threshold has been relaxed or result promoted. Need distinguish true
  pupil motion from whole-face landmark redetection sensitivity before final validation.
- Third genuine photo selected: `val_03_navy_upper_body.jpg`, SHA256
  `fef084d60982754250ab76a7320d71228c96255b2d5244b7461f77b67ce929cf`. Prepared full-frame816x1088 source
  under `work/upgrade-source-faithful-20260903/third-source/`, with provenance. Exclude this photograph
  from its own score set via `--exclude-reference`; preparation alone is not third-photo validation.
- Reduced-reference0.9 failed identity: raw0.555502 and High0.538354, despite improving normalized
  source-mouth error from0.061876 to0.036268. Fixed-alignment scoring confirmed the identity loss.
  The one allowed strength refinement is1.2, prompt `22ebdb80-413b-46f6-9f6e-222a6daf3643`.
- Source diagnostics: canyon0.358505, house0.657355, third genuine0.825853 (excluding itself).
  These are likeness diagnostics, not attractiveness ratings. Copying the canyon source face is
  not an identity-preserving solution. Preserve expression geometry separately from facial appearance.

## Next native expression-conditioning experiment

If the reduced-reference refinement fails, restore all four references and identity strength0.9.
The current guide omits mouth and eye geometry. Add only source lip/eyelid/brow/iris contours to
that same guide and clarify its role. Keep guide resolution, sampler, seed, models and other prompts
unchanged. Use the installed official MediaPipe contour connections, not guessed landmarks.
[MediaPipe source](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/python/solutions/face_mesh_connections.py)
defines those groups. No nose, jaw, source skin pixels or shaded face enters this added signal.

This remains the author-template native reference mechanism, not a trained expression adapter or
ControlNet. BFL's native-edit support is evidence of compatibility, not proof that sparse expression
control works. Identity prediction still rests on the genuine trained LoRA and protected portrait.
Acceptance requires a visible smile/eyelid fidelity improvement, genuine-reference identity near
the four-reference baseline, unchanged pose/forehead/composition, coherent whole-frame detail and
no face seam. One controlled refinement maximum, then decide on the mechanism before further work.
This is preparation only; passing it would still not establish the requested High/Low distinction.

The reduced-reference1.2 result is also rejected: raw0.657540, Low0.652149, High0.618957;
source-mouth error0.055365. Both ablations remain saved. The four-reference expression-guide
test is submitted as `6854ab0f-8130-494a-8863-0dd3f7c81fc6`, port8188,50steps/CFG4,phone on.

Prepared, not queued: an experimental generation-level High replaces only the identity-presentation
paragraph with an explicit same-person best-day edit. It leaves the scene, guide, hair, gaze and
background instructions intact. This differs from the rejected appended-paragraph experiments:
the existing current-age/skin instruction is replaced rather than paired with a conflicting edit.
This is a hypothesis, not a claimed explanation or improvement. Only test if expression-guide review
supports proceeding; then score and visually compare the native result before considering integration.

Expression-guide test completed and is rejected, not promoted: good likeness but visibly open lips
and teeth, increased source-expression error. The guide is not a reliable expression constraint.
No geometric-guide refinement will be mixed into the next test. The prebuilt house guide and
guide-plus-High prompts remain unqueued experimental artifacts.

Next test: the explicit generation-level High identity-presentation role, with the established original
face-free guide and all four original references, models, strengths,50steps/CFG4 and seed. Only that
role changes. Native High is evaluated with common polish (no forced smile/cheek brightening), NOT
the old additional High eye warp; comparisons must use the actual previous Low generation, not label
two finishing stages of one High generation as separate Low/High outputs. PNG-embedded graph metadata
must match the saved High experiment before the replay accepts `--native-high-manifest`.

## Subsequent completed tests — still not a solution

- Native High role substitution, original four references: prompt `21ff4e70-ac60-41a5-ad03-b72cbb0223c0`.
  Raw identity0.774371, common-finish High0.779211, but visible teeth, changed hair styling, source-mouth
  error0.080175 and opening0.086791. Rejected visually despite strong identity and passing selected
  finishing checks. No further prompt-strength refinement queued. PNG metadata has verified LoadImage
  `is_changed` cache hashes in addition to the submitted graph; replay validates those hashes before
  comparing the remaining graph exactly.
- Broad crease-band CPU retouch at1.0 looked overly smooth and reduced canyon identity to0.698664.
  One strength refinement0.65 yielded canyon0.722258 and house0.733925. It visibly softens forehead
  creases but does not solve smile/cheek expression, and the current prototype still fails the expanded
  eye/brow/nose pixel guard near rectangular-versus-elliptical dilation corners. Do not promote it.
  Existing pre-retouch High also fails the retained whole-face gaze redetection gate in these replays.
- A separate upper-lid experiment relaxed only the outer-iris occlusion guard and removed extra warp
  blending, then re-applied source-relative gaze. Canyon identity0.746670 and final horizontal gaze
  error0.010578, but visible change remains too small. Actual requested upper-lid curvature changes
  were only0.32px and1.20px at their maxima: the conservative guard was not the whole explanation.
  Current fixed-eye-pixel/old-redetection tests are not appropriate evidence of success for a deliberate
  eye-expression change; they remain failures, not silently waived. This prototype is not promoted.
- All native generations are terminal, and no house/third native candidate has been queued. House
  High prompt and third816x1088 prepared settings/guide are saved, not validation results. Third genuine
  source remains excluded from its own scores. Production files/defaults remain unchanged.

## Next bounded mechanism review

Inspect the official local LivePortrait image-driven expression controls as a separate experiment,
not a replacement identity generator. The accepted raw render would provide appearance/identity;
the source would provide expression coefficients only, with original pose/scale/translation retained.
First require a zero-expression reconstruction control to test loss of face detail/likeness and seams
before transferring expression. This additional face-decoder stage is justified for evaluation only
by the observed failure of native prompt/reference controls; the project prefers native whole-image
generation and will reject the stage if its reconstruction already degrades the good render.
Official sources: https://github.com/KlingAIResearch/LivePortrait and https://arxiv.org/abs/2407.03168.
No model weights or runtime dependency changes have yet been approved by the research gate; inspect
exact paths, author implementation, image-driven regional controls, resolution and dependency compatibility
first. Never install the upstream requirements over the production ComfyUI environment.

## Completed zero-motion control and next isolated native edit

The official LivePortrait zero-motion control completed successfully in float32 on the idle3090,
with verified author weights and no dependency changes. Raw likeness0.751794, zero-motion0.754952,
stitched-zero0.757601; background outside the author mask is pixel-identical. Nevertheless, native-size
review shows obvious loss of pore, stubble, eye and hair detail in both reconstructions. Reject this
mechanism for the requested high-quality still-image result; no expression transfer is authorized by
this research gate. Artifacts: `work/upgrade-source-faithful-20260903/liveportrait-zero-canyon/`.

Next bounded test separates the already-good identity/detail render from the requested High edit.
Use the accepted raw render as the SINGLE native edit-source, plus the existing genuine-photo-trained
identity LoRA0.9 and smartphone0.25. This is not a genuine scoring reference: evaluation still uses
the six genuine photos. Do not use the previous four competing reference roles for this second pass.
LoadImage -> scale1MP -> fullVAEEncode -> ReferenceLatent positive AND negative -> Base9B native
editing on an empty Flux2 latent. No mask, img2img initialization, face swap, restoration or sharpening.
Keep50Euler/CFG4, seed8675412, established dtype/model hashes and locked3090. Only High would incur
the second pass if it succeeds; Off/Low retain the established first pass. The
[Base9B author model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) explicitly
supports native editing and character fine-tuning, but not guaranteed identity retention. Prediction:
the already-correct face appearance provides a better edit starting point than rebuilding identity and
expression simultaneously. This is unproven; reject if it alters head pose, smile, cheeks, hairline,
background or fine detail. Require visible improvement and centroid>=0.70 without a large likeness drop.
One controlled refinement maximum before a mechanism decision. This is experimental, not production.

Single-source High second pass0.9 completed as `5b23508d-3659-4b68-b79e-cee87e6763c8` in236.69s.
Likeness0.746493 vs raw0.751794, pose delta0.323degrees, mouth opening0.017773; however, it does
not visibly relax the frown/eye expression and leaves or accentuates skin speckles. Not accepted.
The one controlled refinement lowers ONLY the second-pass identity LoRA from0.9 to0.35. The already
verified raw render stays the edit-source and the genuine trained identity mechanism remains present;
all other prompt/model/reference/seed/settings stay fixed. Hypothesis: repeated strong identity
conditioning may be resisting the cosmetic edit. This is not proven and the refinement must retain
genuine-reference likeness>=0.70, expression/pose and detail. No further strength/prompt sweep afterward.

The0.35 refinement completed as `607f85d2-bef2-429d-9fa7-7c3a9794728b`: likeness0.574501,
pose delta1.09degrees, mouth opening0.004460. Visually over-dark brows, stronger skin creases/spots,
and identity loss. Reject both strength variants. No further full-frame second-pass strength sweep.

### Focused editing gate

New bounded mechanism: allocate the native1MP editing canvas to a face-context crop rather than the
whole scene, retaining the verified character LoRA0.9 and smartphone0.25. The crop is an edit target,
not a genuine identity reference. Use the already-reviewed author Base9B native editing graph, same
50Euler/CFG4 and seed, fullVAE and verified models. No new model, denoising-mask node or face swap.
Source crops are deterministic, preserve aspect, use1.4x detected face extent and include local
lighting/context. Genuine-photo scoring remains independent. First review the raw edited crop;
only a visibly successful crop may proceed to an exact-background compositing feasibility test.
This is eligible because full-frame native edits failed to focus the treatment and altered background
appearance. Acceptance: clear attractive improvement, recognizable identity near requested0.70,
retained head/iris direction, small closed-lip smile, realistic pores and coherent lighting. A crop pass
alone is not a full-photo success: final face boundary/forehead/texture integration would still need testing.

Primary-source review: [CropAndStitch author](https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch)
documents allocating sampling context/resolution and preserving unmasked original pixels, but its shipped
Flux1 inpainting model is NOT assumed compatible with Klein. We are using basic deterministic cropping
and the existing verified native Klein graph, not installing or guessing that Flux1 workflow. The crop
is neither an identity mechanism nor an excuse to accept seams. [BFL positive-framing guidance](https://docs.bfl.ai/guides/prompting_guide_t2i_negative)
also favors describing the desired appearance instead of listing unwanted traits. The focused-edit prompt
uses that form, with the user's now-explicit stronger-beauty priority. This is a new bounded composite
design, not a causal claim that either cropping or phrasing alone caused previous failures.

Focused crop0.9/phone0.25 completed as `d3bc129e-ac04-4f5a-acde-3e821a35bb48` in238.09s. With
the same neutral25% detection padding for every crop and genuine reference, raw likeness0.761436,
candidate0.688037, pose delta1.68degrees, mouth opening0.000915. Padding was needed because the
detector missed the tightly framed source crop at both640 and1024; no detector-confidence or likeness
threshold was lowered. Eye/expression changes are more visible, but the skin/stubble are harsh and
forehead creases still too strong. Not approved; no full-frame composite created.

The single focused-edit refinement removes ONLY the repeated smartphone adapter from the crop pass
(0.25 ->0). The base remains the unchanged PHONE-ON raw photo; final defaults are not changed.
The idea that repeated style conditioning contributes to rough texture is a hypothesis, not a finding:
the earlier first-pass phone A/B actually smoothed facial microtexture. Keep the same crop, positive
prompt (including snapshot wording), seed, identity0.9,50steps/CFG4 and all model files. Record crop-stage
phone adapter off separately from upstream phone style on. This tests whether stage separation helps;
no further focused prompt/strength sweep after the result. A crop cannot establish full-frame quality.

The no-repeat-phone crop completed as `b4699c5b-aa0f-4112-b24b-7ed4dbb9b4c6` in237.887s:
likeness0.691342, pose delta1.39degrees, mouth opening0.000019 and source-mouth error0.037599.
The eyes/mouth changed, but harsh pore/stubble rendering and strong frown creases remain. No useful
skin-quality improvement from removing the repeated adapter; reject both crop variants. Do not composite
or promote them. This ablation does not justify changing the final phone-on default. No more crop sweeps.

### Next original-workflow reference test

Return to the established whole-frame FOUR-reference workflow, avoiding extra render stages. The
protected original identity portrait visibly has a furrowed brow and parted mouth, matching recurring
output problems. Test whether a calmer genuine reference reduces this competing-expression signal;
this is a hypothesis, not proof that the portrait alone caused it. Replace ONLY reference3 with
`datasets/mitch-identity-stills-v3/dataset/07_sweater_front_neutral.jpg`, SHA256
`0e9f30d584646b3455674fa88e03c3c8b5a534d0fcbc2083088032ecb35da93a`.
Its dataset manifest identifies it as a genuine camera still, a frontal neutral anchor from2026-05-08.
Inspection of the full-frame viewing preview confirms closed lips, calmer expression and real fine skin
texture. It is not one of the six scoring photos. The byte-identical original, not the downsized viewing
preview, is the proposed reference. No synthetic identity image or held-out evaluation leak is introduced.

All original roles/order remain: source/edit/pose; face-free composition guide; genuine identity portrait;
isolated genuine hair. Identity also remains in the trained Base9B LoRA0.9. Keep the exact original
baseline prompt, reference3 resolution0.5MP/method, all other references,50Euler/CFG4, seed8675412,
phone0.25 and Turbo off. Primary support remains the reviewed BFL native multi-reference author graph
and documented Base9B LoRA compatibility. Exact model hashes and live nodes are revalidated before
submission. This test diagnoses the upstream expression source; it does NOT by itself establish
off/low/high separation. Inspect the raw whole-frame result before adding polish or calling it a fix.

Calmer-reference test completed as `ea29a07f-aa2c-4dcd-8359-e3b2b35509c0` in413.131s:
likeness0.753268 versus baseline0.751794, pose delta0.673degrees, closed mouth0.002215,
source-mouth error0.058553. No material flattering-expression improvement: brow tension and speckles
remain. This is not an accepted High solution; original production reference is unchanged.
Next bounded mechanism and evidence gate: `upgrade-qwen-high-evaluation-2026-09-03.md`.

### Selective local crease repair after native-model failures

Both Qwen native edits failed recognizability/skin realism, documented separately. Do not keep sweeping
Qwen prompts. The next CPU-only prototype tests a different operation than rejected broad frequency
smoothing: detect elongated dark forehead ridges, repair only those selected narrow crease pixels with
local interpolation, and leave non-selected skin/features/background exact. No generic face reconstruction,
new model, identity signal, source-pixel transplant or geometry change. The observed failure is persistent
deep creases/frown tension; broad smoothing damaged skin realism. Local selection has a measurable
acceptance test: selected forehead area<=22%, protected eyes/brows/nose/mouth/hair/background exact,
retained natural skin under full-size review, and visible High/Low difference with genuine-reference
likeness retained. This cannot by itself prove an improved smile/eye anatomy or finish the broader goal.
Use the previously evaluated no-forced-smile/no-cheek-lift baseline only in the isolated replay; production
is not changed. One initial test and at most one controlled refinement; preserve failures.

Initial selective repair: `crease-repair-canyon`, strength0.75. Nineteen components selected7.96% of
eligible forehead;1974 pixels changed, all guarded feature pixels exact. High likeness0.743790 versus
pre-repair0.742472. Full-size review still shows no sufficiently obvious High improvement; this does
not solve eyes or smile. Existing pre-repair High also trips the replay's0.02 redetected-gaze gate
(0.034046); the repair itself has exact eye pixels and must not be blamed for or used to waive that gate.
Not promoted. No stronger crease-only sweep: it does not address the central expression requirement.

### Next: coupled source-expression geometry (CPU only)

Code/landmark review explains a concrete limit: current High fixes eye corners, requests only0.035–0.320px
upper-lid shifts for one canyon eye and0.228–1.196px for the other, then multiplies them by0.72 and further
attenuates them. It never changes the smile. Earlier isolated half-strength mouth and lid prototypes were
too small; native reconstructions changed identity/texture. Test a coupled, bounded expression deformation
of the candidate's own pixels using source-relative eye contour and closed-mouth corner coordinates.
Source geometry is expression guidance only, never genuine identity data or copied pixels. Keep iris/pupil,
nose, hairline and outer head fixed; preserve closed lips as a unit. This is not face swapping or an identity
mechanism. Require positive deformation Jacobian/no fold, protected-pixel checks, full-size/thumbnail review,
genuine-photo identity diagnostic and visibly more source-like flattering eyes/smile. One controlled prototype
and at most one refinement; no blind parameter sweep. No production change until verified on all3 photos.

Initial `source-contour-expression-canyon` at0.85 kept likeness0.714929 and reduced the source-mouth
coordinate error42.5%, but produced a visible mouth-corner crease artifact. Eye field max3.172px,
positive minimum inverse Jacobian0.495, iris/pupil and other explicit guards exact. Reject as-is.

The single solver refinement uses the same requested eye/corner shifts, but interpolates the entire lip
contour and neighboring skin smoothly with fixed nose/boundary anchors. A first implementation was
blocked before saving by a negative mouth Jacobian(-0.322). Corrected the overly short3px transition
to fixed nose/outline pixels: use a displacement-scaled26.76px transition and a deterministic no-fold
line search that rejects if less than60% of the field can safely remain. Also explicitly protected the
eroded head oval in the eye stage. These are safety fixes, not a strength/prompt sweep.

Completed refined `source-contour-expression-tps-canyon`: eye Jacobian0.495, mouth0.820, full1.0
displacement retained after safety check. Mouth field max8.546px; no corner crease artifact in full-size
and mouth-crop review. Likeness0.691167 (fixed raw alignment0.703289) versus no-smile/cheek Low0.753497.
This modest loss is within the user's qualitative stronger-beauty tradeoff for visual review, not an
automatic identity pass. Mouth opening0.006134, pose close. Redetected source-mouth error improvement
is only1.1%, despite visibly altered smile; don't claim a measured source-expression lock.
Old High redetected-gaze gate still fails0.034046 and remains unwaived; the added geometry has exact
iris/pupil pixels but changes eye boundary geometry, so source-relative gaze needs fresh validation.
Same frozen0.85 recipe is now being replayed on house, not promoted. Third-photo/end-to-end validation
and proper reporting/test coverage are still required.

House replay with the same geometry: likeness0.761663, eye Jacobian0.554, protected pixels exact.
Its near-neutral source smile score0.010676 is below the existing closed-smile threshold0.012, so the
mouth operation correctly reports skipped rather than claiming an edited smile. Full-size review retains
the house/background and recognizable face; the visible High difference is modest. No parameter changed
for this photo. Do not call either result an accepted attractiveness fix without visual assessment.

Gaze ordering correction: for this new eye-contour geometry, run the existing iris-only source-gaze lock
last, after the expression edit. Its target is the source's horizontal iris coordinate in the **final
pixel-identical eyelid geometry**, not a return to Low's old eye boundaries. Keep the old Low-delta
diagnostic visible; it is not meaningful as the target of an intentional eye-shape change. New check
remains max per-eye normalized horizontal source error<=0.02 and exact pixels outside the final iris mask.
This changes the comparison reference, not the numerical0.02 threshold; it does not establish vertical
gaze or subjective appearance by itself. Final iris pixels can move to match source focus, so only the
preceding geometry stage claims exact iris/pupil pixels, not the whole finished High pipeline.

`source-contour-final-gaze-canyon`: likeness0.694568 (fixed alignment0.705017), max per-eye horizontal
source error0.018509, mean0.011770,862 iris-region pixels selected, outside-pixel error0. Mouth remains
closed0.002698; source-mouth landmark error is not improved overall, so no expression-lock claim.
`source-contour-final-gaze-house`: likeness0.761173, max horizontal source error0.009441, mean0.006051,
617 iris-region pixels selected, outside-pixel error0. Both CPU runs finish with no replay validation errors.
Four synthetic-geometry unit safety tests pass. Subjective attractiveness remains under review; a
non-blocking user question accompanies the source/actual-Low/candidate-High canyon comparison.

Third genuine source baseline is now running as `f7e3ff0b-35fb-451c-a999-203ca9110cfa`, original four-reference
Klein50Euler/CFG4, seed8675412, phone0.25, Turbo off. Preparation/settings are not a result. Staged guide
`mitch-upgrade-third-facefree-guide.png` SHA25655773963690bda707f03bd14fbd237ca68382d7570995a75d8678e56deb56763.
An initial sandbox read-denial occurred before submission; the authorized local retry verified model
hashes and submitted once. Always exclude original `val_03_navy_upper_body.jpg` from third-photo scoring.

Third baseline completed in387.653s. The same0.85 geometry/final-gaze recipe yields likeness0.769151
against five independent genuine references and maximum horizontal gaze error0.013162. Nevertheless,
**reject the three-photo candidate as a production fix**: full-size/thumbnail review shows the baseline
already recenters/straightens the head, enlarges the face and opens the original closed lips. High remains
too subtle and does not repair those failures. Source mouth opening0.005749, raw0.061452, final0.066153.
The earlier replay incorrectly accepted the mouth because it compared against an already-open generated
baseline. A new model-independent closed-lip check always enforces<=0.035, retains visual teeth review,
and has four passing regression tests. Corrected replay `source-contour-third-source-audited` exits1;
the old audit/images remain preserved, not overwritten. No production bytes changed.

Source pose audit quantifies the third baseline error: yaw8.7996->-1.8906degrees and roll8.9291->2.3174;
maximum angular delta10.6902degrees. Raw bbox center also moves left about64pixels. Native and CPU
evaluators now report source pose separately and reject >3degree drift even if a polish matches its raw.
See the Qwen evaluation document for the final0.35 source-retention diagnostic: visible stronger edit,
but0.636 likeness and unresolved gaze/skin tradeoffs. Its exact comparison is presented to Mitch; it is
not an accepted replacement. No queued job remains and production is unchanged.

## Third-source fidelity isolation after failed four-reference baseline

Previous goal turn made progress: measured the genuine third-source failure, fixed the mouth/source-pose
acceptance gap, and completed the bounded Qwen retention diagnostic. The stronger High's exact appearance
awaits Mitch's judgment, but independent source-pose work can continue without relaxing likeness gates.

The third input is independently documented genuine (`third-source/provenance.json`), with0.825853
similarity against the other five genuine photos. Its four-reference prompt nevertheless says the source
is **not identity** and another portrait exclusively supplies identity/current age. The raw output adopts
a more frontal, parted-lip presentation. This is evidence of a conflicting role, not proof of causality.
The earlier no-portrait canyon failure used a source with0.358505 similarity, so it does not establish
that a genuine already-correct face needs replacement. Never infer genuineness from an embedding score.

Test the author's minimal SINGLE native edit reference on the genuine third source: source -> bicubic1MP
-> fullFlux2VAE -> ReferenceLatent positive AND negative. Keep the actual genuine-photo-trained protected
Base9B identity LoRA0.9 and phone0.25,50Euler/CFG4, seed8675412,816x1088, same model files/dtype. No
additional face/edge/hair reference, no extra image stage or latent-denoise manipulation. Explicit source
role now includes its own identity as well as pose/expression. This is a reference-layout/role test, not a
claim that any single removed component alone caused the drift. Source pixels remain native reference
conditioning, not composited/copied facial pixels. Identity support is the trained character LoRA plus
BFL's native edit mechanism, not a generic style input.

Re-read installed author single-reference template `image_flux2_klein_image_edit_9b_base.json` nodes AND
links (`7b34ab90-36f9-45ba-a665-71d418f0df18`). [BFL Base9B card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
documents native editing and supports50steps/CFG4; [BFL training guide](https://docs.bfl.ai/flux_2/flux2_klein_training)
supports genuine character-LoRA conditioning. Prompt is saved as `third-source-preserve-prompt.txt`.
Protected hashes/live nodes/both GPUs/queues checked before submission; locked3090 only. The model and
reference topology were previously run successfully here; no downloads, installs or hosted services.

Acceptance: source pose<=3degrees, closed lips<=0.035 plus visual no-teeth review, preserved head placement,
hairline and body/scene geometry at native size/thumbnail, no worse than modest genuine-reference likeness
loss from the source. Score only the other five genuine photos. This tests structural fidelity, not High
attractiveness, and cannot by itself complete the three-photo workflow. At most one controlled refinement;
no photo-specific hardcoded mask or coordinates, and no automatic production input-routing change.

Third source-only native edit completed as `f2bfb77e-3c17-4219-a438-83eec7ba0179` in216.473s. Likeness
0.825638 versus genuine source0.825853 and old four-reference raw0.777842. Source pose error0.154degrees
versus old10.690; face center differs by0.355% frame width/0.188% height; closed-lip ratio0.003597.
Source mouth-coordinate error0.006953 versus old0.038814. Native-size review shows the original tilt,
expression, placement, hairline, clothing and recognizable room retained, with realistic detail. This is
useful positive evidence for source-faithful native editing of an already-correct face, not High approval.

The generic evaluator initially flagged the10.734degree change FROM THE WRONG OLD RAW, while source
error was only0.154degrees. Add an explicit source-fidelity role: verify the single native reference hash
matches the actual source, retain old-raw pose delta as diagnostic, and keep the exact3degree SOURCE
pose threshold. Default High-edit mode still requires both raw and source pose. The corrected
`source-fidelity-evaluation` preserves the original failed audit, and does not relax the source criterion.

Final source-gaze finish on this third base: likeness0.822698, maximum horizontal error0.006796,
581 selected iris-region pixels, all outside pixels exact. Two-dimensional target errors0.168px/0.327px,
down from0.390px/0.936px. No Low skin retouch or High applied in this check. Evaluation role is explicitly
source-fidelity, not High. The reviewed comparison uses each image's own face bounds, because a box tied
to the failed baseline clipped the source/corrected faces; original full-frame geometry remains visible
in the thumbnail/full-image comparisons. Successful base/gaze evidence does not establish stronger High,
input-mode/routing integration, freckle/hair cosmetic treatment or three-photo production acceptance.

## Stronger High: complete finish evaluated on all three

The user explicitly chooses a stronger beauty edit while remaining recognizably himself. The fixed
Qwen0.35 recipe has now been run on house and the corrected third base, followed by an isolated CPU
common-polish/final-gaze test on all three. This addresses the earlier omission of freckle/hair cleanup
from native candidate comparisons. Forced mouth lifting and cheek highlighting are disabled only in
this experiment; no old High geometry is layered over the native edit. Production remains unchanged.

Finished genuine-reference likeness: canyon0.653306, house0.732281, third0.783743. Matched revised Low:
0.753381/0.770816/0.824368. All lips stay closed and the gaze finish improves both eyes'2D diagnostics;
outside combined polish/gaze masks pixels are exact to native candidates. Selected dark-dot contrast
falls60–71%. Native failure flags remain visible, not erased by successful finishing checks.

Full-size/face review still does not justify promotion: canyon offers a stronger look but loses likeness;
house's expression remains close to Low; third has some added cheek fullness. The complete finish is
better evidence than the unpolished candidates, not a claim that the requested universal High is fixed.
Detailed measurements and limitations are in `upgrade-qwen-high-evaluation-2026-09-03.md`.

## Remaining house expression/pose: source-preserving base test

The newer Qwen genuine-reference High helps identity: canyon complete finish0.696216, house0.761413
(native house0.772997). Yet the house still inherits much of its base's tense brow and source-pose
error: base3.672880degrees, native High3.589449, finished High3.792002. Its original source has a
more flattering eye/brow/expression presentation. Another cosmetic-strength sweep does not isolate
why that source presentation was replaced before High. No production change has been made.

Inventory check found no prior source-only original-house test. Crucially, `no-identity-canyon`
used THREE image references (source, edge guide, hair), and retained the instruction that Picture1
supplies composition/expression **not identity**. It does not test the actual author-minimal single
source layout that already repaired the third genuine photo. Do not conflate those experiments.

Bounded next test: original house source ->1MP bicubic Flux2VAE encoding -> single ReferenceLatent
on both CFG branches, plus the same protected genuine-photo-trained Klein Base9B identity LoRA0.9
and compatible phone LoRA0.25. Native50Euler/CFG4, seed8675416, Turbo off; no extra identity, edge,
hair, mask, restoration or lighting stage. The identity mechanism is the genuine character LoRA
plus native editing, not an unverified assumption that any image input locks identity. The source
is a depicted identity/edit target; its genuineness is not inferred from its0.657 similarity.

[BFL's Base9B card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) and
[training guide](https://docs.bfl.ai/flux_2/flux2_klein_training) were rechecked. Reuse the previously
inspected author single-reference template and existing `run-upgrade-reference-ablation.ps1`
source_only path, already verified by the successful third-source run. A reusable source-preserving
prompt is saved as `work/upgrade-source-faithful-20260903/source-preserve-upgrade-prompt.txt`; it is
not a production prompt change. It deliberately avoids photo-specific face coordinates or identity
claims based on a score. Check live nodes, exact model hashes and both GPU queues before submission.

Evaluate native source pose, pupil focus, closed lips, face placement/forehead, whole-frame realism,
background detail and six independent genuine scoring references before any High finish. Compare
against original source AND accepted old raw; source-fidelity evaluation targets the source pose,
not the already-drifted base. At most one controlled refinement, and no automatic input-routing rule
or universal-recipe claim before evidence on the requested photos.

House source-only base completed as `7acf1f42-9b35-41d8-9e86-d6e5f44b179b` in325.903s.
Its verified native evaluation is `house-source-native-preserve/evaluation/audit.json`.
Source pose error improves3.672880 ->0.911003degrees; source mouth-coordinate error improves
0.027753 ->0.007384. Lips remain closed (0.002063). Identity is0.691008 versus source0.657355
and old raw0.779115: the source-relative gain is useful but the absolute0.70 diagnostic fails.
Full-size/face review shows substantially better retention of the source's eye shape, mouth,
hairline and head direction, with the same scene. Some brow furrowing and dark skin speckles
remain; phone-on alone does not restore detail in an already blurred source background.
This is a base-fidelity result, not an approved High or a claim that all criteria pass.

Next bounded composition test: apply the already frozen two-reference Qwen stronger High
(genuine training portrait as Picture2,20Euler/CFG4/denoise0.35,whole-frame) to this exact
verified new base. Keep its existing prompt and parameters. The changed upstream base is
the experimental variable; do not tune High again or mistake this for an isolated LoRA test.
Use the native upstream audit/hash for provenance and compare against the original source,
new base and matched revised Low. Native editing identity mechanism and author evidence
remain those documented in `upgrade-qwen-high-evaluation-2026-09-03.md`. The final Qwen
stage inherits phone appearance; it does not actively load the Klein smartphone adapter.

The fixed High-on-new-house-base test completed as `da8eae96-bf44-423d-8b8e-5f4068ee0a24`
in197.523s. Native likeness0.694595; common-polish/final-gaze likeness0.688376 versus
matched revised Low0.683992. Finished source pose error2.536129degrees, closed lips0.003432,
maximum horizontal gaze error0.0184;2D gaze errors improve to0.399/0.721px. Finish-exterior
pixels are exact to its native Qwen candidate. Native and final absolute0.70 likeness failures
are retained. Full-size/face/thumbnail review shows much better source-feature retention than
the old-base High, but the difference between new Low/High remains relatively modest.
Projected outline widths change-0.300/+0.384/+0.945% versus the new raw; this is not a proof
against all perceived cheek fullness. The comparison was shown to Mitch for aesthetic feedback.

To test whether the source-preserving base is usable beyond house/third, run ONE original-canyon
single-source test with the exact same reusable source-preserve prompt and verified author-minimal
Klein graph. Keep canyon's baseline seed8675412,50steps/CFG4,identity0.9,phone0.25,1024square.
This is not the earlier three-reference no-identity test nor an edit of an already-generated raw.
The genuine-trained character LoRA still supplies identity conditioning. Source identity0.358505
means retained source appearance may compete with a recognizable Mitch result; that is a risk to
measure, not a reason to claim source genuineness or to relax the0.70 diagnostic. Score six genuine
held-out photos, review source direction/expression/whole-frame detail before considering any High.
No automatic score-based routing or production change is authorized by this experiment alone.

Canyon single-source test `30038a6b-791e-4c4d-a55b-af29b4833b93` completed in 237.119 seconds.
The first preflight was denied while reading a protected VAE file, before any submission; the same
runner then completed its hash checks with approved filesystem access. There was only one generation.
Native likeness is 0.688457 versus old raw 0.751794; source-pose error is 4.604616 degrees, closed-lip
ratio 0.001647. Source mouth-coordinate error improves 0.054632 -> 0.039160, but pose and absolute
likeness diagnostics fail. Full-size and thumbnail review also shows the soft background retained,
unlike the accepted detailed canyon base. Preserve this failed run without applying High. This rules
out universal replacement of the detailed four-reference base with this single-source recipe.
