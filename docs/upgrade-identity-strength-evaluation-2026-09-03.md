# Upgrade High: identity-strength diagnostic

Status: strength and angle-reference diagnostics completed; neither solves the
requested High appearance, not production. The preceding goal turn was progress: the
registered-variant blend failed its frozen house validation, demonstrating that
it cannot supply an expression missing from the stronger native render. This is
not another blend, mask, smoothing or negative-wording sweep.

## Inventory and hypothesis

Only the selected Klein9B V3 rank32 DOP step1600 identity LoRA remains installed.
The earlier checkpoints were removed in the recorded September1 cleanup, with
evaluations/configurations preserved. V6 is shelved; no V6 weights are installed.
No removed checkpoint will be reconstructed, downloaded or trained by this test.

The actual V3 dataset has13 genuine camera photographs and descriptive captions,
including calm/neutral/small-smile expressions. Its transformer-only rank32
character training uses the undistilled Klein Base9B and DOP against class `man`.
The records do not prove that it is overfit or that it alone causes the frown.

Existing Upgrade experiment manifests show four-reference High tests at identity
strength0.9 only. The earlier0.35 test was a source-only second pass, while1.2
used a three-reference layout without the genuine portrait. Those tests do not
isolate identity strength in this four-reference High recipe.

**Hypothesis, not fact:** reducing the learned identity patch may permit the
model to follow the source's relaxed eyes/brows/smile more closely, while the
genuine portrait and remaining character LoRA retain enough likeness. Conversely,
it may only lose identity or retain the same expression; either result is useful
to stop treating LoRA strength as an untested explanation.

## Research gate and unchanged conditioning

[BFL's Klein training guide](https://docs.bfl.ai/flux_2/flux2_klein_training)
documents Base-model character LoRA training and50-step/CFG4 inference. The local
training config is `config/flux2-klein9b-identity-v3-r32-dop-3090.yaml`, with the
continued selected checkpoint already hash-locked by the established runner.
[ComfyUI's author-maintained LoraLoaderModelOnly](https://github.com/Comfy-Org/ComfyUI/blob/master/nodes.py)
and the installed `ComfyUI/nodes.py:756` pass `strength_model` into the model patch
with no text-encoder LoRA. They support the controlled change, not a prediction
of attractiveness or a promise that0.6 preserves identity.

The existing graph remains the shipped Base9B edit template adaptation:

1. Source image ->1MP bicubic scale -> VAE -> reference latent1: edit-source,
   composition, pose/expression; its identity influence is not isolated.
2. Face-interior-free edge guide ->0.5MP nearest-exact -> VAE -> reference2:
   structural composition, not identity.
3. Genuine frontal identity portrait ->0.5MP nearest-exact -> VAE -> reference3:
   native identity image alongside the genuine-trained character LoRA.
4. Genuine isolated hair crop ->0.1MP bicubic -> VAE -> reference4: material,
   not a substitute identity signal.

All four reference latents enter both CFG branches. Identity is not supplied only
through a prompt/style reference/face swap. The same Base9B BF16 file loadedfp8,
Qwen3-8B encoder, full Flux2 VAE, SmartphoneSnapshot v13 LoRA0.25,50Euler/CFG4,
seed8675416 and1680x1008 house output remain fixed. Keeping that previous full-size
baseline avoids changing resolution at the same time; this is1.69MP rather than
a1MP speed benchmark. The phone adapter stays active and Turbo stays off.

The nonempty negative branch is the previously documented experimental local CFG
test, not BFL-endorsed negative prompting. Neither text branch changes here.

## One controlled test and stopping condition

Use the saved `compact-native-high-negative-house` graph as the0.9 control.
Change only node2 `strength_model` to0.6, plus the save prefix. The existing runner
must freshly check both GPUs/queues, all required live nodes/model names, five
weight hashes and reference hashes. RTX3090/8188 remains locked. An idle cache may
be freed only after verifying our terminal job is the latest and both queues empty.

No postprocess, registered blend, additional identity reference, new model,
training, download, install, service restart or production edit is part of this
diagnostic. Compare the raw result with both the0.9 control and original source,
not only Low. Use all six independent genuine scoring references and inspect full
size/thumbnail for likeness, attractive eye/brow/smile changes, cheek fullness,
forehead/hairline, head direction/gaze, teeth, background detail and whole-frame
realism. Preserve the old numeric diagnostics without making them the sole beauty
verdict. If0.6 does not materially improve expression at acceptable likeness,
stop this strength hypothesis rather than starting a strength grid.

## Submission evidence

Both queues were empty and the latest completed3090 job was our house control
`3e30ed4f-7448-4bb0-b332-e3aff50d1443`. Its idle model cache was released; a fresh
hardware check showed3090 at1148MiB/utilization0 and4070 at237MiB/utilization0.
The existing runner freshly verified the live nodes/models and five weight hashes.
Job `4dceb1de-5d9c-4616-b702-85144b0f352a` was submitted once, queue number36,
with no node errors. It is not a new checkpoint or retraining run.

Exact submitted-graph comparison passes: only `2.strength_model` and
`27.filename_prefix` differ. References, verified model hashes, seed, steps, CFG,
phone strength, both prompt texts and all other node inputs are identical.
Control manifest SHA256:
`D90422510E24CC94178FE894AD4D9D069EA1DDF091A857CF1251C1627ED1FFA4`.
Test manifest SHA256:
`A0B2CD5C45D51CE81104944D91F86870D5AD8034B3F7E322649B2E3FFE9A1655`.
Executed-PNG verification and appearance review remain pending at submission.

## Separate reference inventory, not a change to this test

Training and held-out contact sheets were visually reviewed while this job ran.
The archive's genuine-photo discovery records contain two training images with
potentially useful three-quarter geometry, beyond the previously tried frontal
calm reference07. Current dataset bytes were checked against the camera-still
training manifest and the saved discovery hash before reusing those pose numbers:

- Train08 `08_sweater_near_profile.jpg`: yaw+29.8678, pitch-4.6493, roll+7.6971;
  SHA256 `4d46086b4ef5f0f913ccb4786165c6e6589677edbc039e00c55e23dd971486fb`.
- Train09 `09_sweater_opposite_near_profile.jpg`: yaw-35.5572, pitch-1.0780,
  roll-12.4014; SHA256 `4b98feb4d7929bd89f75402b85d1d86be690d67c48212c1f4740419f9374ca6b`.

These are cached pose diagnostics, not new-generation scores, and are not an
attractiveness ranking. Neither image replaces reference3 in the current strength
test. Any later angle-matched reference experiment must remain separately labeled,
preserve the four input roles, and not confuse training-photo pose screening with
the independent six-photo likeness evaluation.

## Strength result: not the expression fix

Job4dceb1de completed in501.095seconds. Its executed PNG graph matches the saved
manifest; no postprocessing was applied. Native candidate SHA256:
`44b06657e8add5b05493d28efd87ad2f1d0d812d1af9de9ac5621af27eac6d3d`.
Six-reference likeness falls from0.741355 at0.9 to0.704957 at0.6. Source-pose error
slightly improves2.198845 ->1.862539degrees, while normalized source mouth-corner
error does not improve (0.014931 ->0.015571). Lips remain closed0.006727, but raw
eye-coordinate error worsens0.044975 ->0.073723. It still fails the original
raw-baseline likeness-drop diagnostic; that is not the sole rejection basis.

Full-size, face and thumbnail review, including a direct0.9-versus0.6 sheet, finds
essentially the same tense brow/smile and soft background. It changes likeness
more than the intended expression. **Do not promote0.6 or run a strength grid.**
This does not prove the LoRA has no expression influence, only that this isolated
one-third strength reduction is not an adequate remedy. Files are preserved under
`identity-s060-native-high-house/evaluation/` and `control-comparison/`.

## Next independent ablation: angle-matched genuine portrait

Use the0.9 house control, not the rejected0.6 variant. Replace only reference3's
frontal portrait with the verified full, unedited train08 photograph. Its saved
yaw+29.87/roll+7.70 are close to the house source+33.74/+6.16, unlike a frontal
identity anchor. This changes reference content (including angle and expression),
not an isolated pose variable. Full-size inspection shows a small smile, inner-
brow creasing and a thin visible tooth line; it is **not** a flawless beauty
target or a closed-lip guarantee. Source1 and the unchanged prompts must still
govern gaze/expression/closed lips, and any copied teeth are a hard rejection.

[BFL's multi-reference editing guide](https://docs.bfl.ai/guides/prompting_editing_multi_reference)
supports up to four Klein references with explicit roles and character-consistent
variations. Together with the same genuine-trained character LoRA, this supports
the existing conditioning mechanism, not a promise that matching reference angle
will improve likeness or attractiveness. All source->VAE->reference roles above,
both CFG branches, model hashes, text, strengths, seed,50Euler/CFG4 and dimensions
remain unchanged. No new nodes or weights are introduced. The image is staged as
a byte-identical local copy; no upload, synthetic identity or validation-photo
conditioning is used. Validate the exact graph difference120.image plus save27.

Evaluate the raw whole-frame output against the0.9 control, actual Low and source
at full size/thumbnail and with the same six held-outs. Stop if the angle-reference
change fails the requested expression/likeness/pose/teeth/background checks; do
not use it as license to sweep the entire photo library.

The byte-identical reference is staged at
`ComfyUI/input/mitch-upgrade-angle-genuine-4d46086b.jpg`; its hash was checked both
before and after copying without overwriting another file. With both queues empty
and the latest terminal3090 job verified as our strength test, its cache was freed
and memory rechecked at1147MiB/utilization0 (4070:237MiB/utilization0).
Angle-reference job `359b70af-a7a5-4c9f-8ea9-5bd484082b59`, queue number37, was
submitted once after the same live-node/model/hash checks. Manifest SHA256:
`72AB8C10FEDD912422AFA39D6E0407A030C121548A958D71D2E418320020AC5F`.
The exact submitted-graph audit passes: only `120.image` and the save prefix
change from the0.9 control. Ordered roles/scales/methods and all other settings
match. Generation and final visual acceptance were still pending at submission.

## Angle-reference result: likeness improvement, not the requested expression

Job359b70af completed in502.583seconds. Executed PNG/manifest verification passes,
with no postprocessing and the same six genuine held-outs. Candidate SHA256:
`6e4329f0d4cbd1a68118de63e8cf728c9d9712dd77b25bd86916e102b8f7894e`.
Likeness improves0.741355 ->0.765444; source-pose error is2.050815degrees and
source face-center displacement is[+0.001656,-0.004864] of frame dimensions.
Lips are closed0.003790, with no visible copied teeth. Raw eye-coordinate error
is0.044408 and source mouth-corner error0.024390 (worse than the front-reference
control's0.014931). The native evaluator's numeric failure list is empty, but it
does not test all visual requirements or prove an identity lock.

Native-size, face and thumbnail inspection of the result and direct reference A/B
still finds the tense inner-brow/forehead appearance and an insufficient change
in the intended eyes/smile. Skin speckles remain; the whole background is still
soft rather than the required detailed phone-on environment. Hair is coherent
but does not restore the requested whole-frame/source-expression result.

**Decision:** preserve this as evidence that a pose-near identity reference can
improve this case's similarity score, not as a successful High or a general
reference-selection policy. No further identity-reference library sweep, polish,
blend, additional-photo generation or promotion follows from this result.
Both tested levers changed likeness more than the desired expression. They do not
establish which remaining mechanism is responsible; do not claim the dataset or
LoRA has been proven overfit. The full three-photo goal and actual workflow
integration remain incomplete. All production node/UI/workflow/model bytes remain
unchanged, with phone on/Turbo off. This goal turn made progress through two
controlled native evaluations; it was not a blocked/wait-only turn.
