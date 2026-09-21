# Upgrade High: identity conditioning across sampling time

Status: rejected after the sole timing refinement and matched final-finish review; not production. The preceding goal turn
made progress by completing and rejecting the sole phone-repeat refinement.
It did not establish a working High; the full three-photo objective remains.

## Evidence and distinction from closed routes

Constant identity-strength reductions were already tried, including a
single-reference second pass0.9 ->0.35 and a four-reference native edit0.9 ->0.6.
Neither fixed expression/realism. Do not repeat those constant-strength grids.
The most recent detailed-raw edit retains likeness but adds creases/speckles;
removing the second phone adapter did not fix it.

Different hypothesis: use the existing genuine-trained identity LoRA while the
coarse face is formed, then allow the unchanged base model and native reference
conditioning to finish without the identity weight patch. This tests WHEN the
identity patch is applied, not a stronger text prompt, repeated phone tweak or
another RGB polish. It could lose likeness or retain the same expression; the
hypothesis is not a promise that late steps separate identity and skin cleanly.

Primary evidence inspected:

- [ComfyUI author's scheduling explanation](https://blog.comfy.org/p/masking-and-scheduling-lora-and-model-weights)
  and its [minimal scheduling example](https://raw.githubusercontent.com/Kosinkadink/ComfyUI/workflows/lorahookscheduling.json):
  weight timing can affect composition versus styling; not proof of beauty or identity retention.
- [Base9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
  supports the undistilled native edit model,50steps/CFG4.
- [BFL training guide](https://docs.bfl.ai/flux_2/flux2_klein_training) and the existing
  V3 training config establish the genuine-photo-trained character LoRA mechanism.
- Installed `comfy_extras/nodes_custom_sampler.py`, `comfy/samplers.py`,
  `comfy/model_sampling.py`, `comfy/k_diffusion/sampling.py` and `nodes_flux.py`
  were traced for residual-latent output, zero-noise continuation and the actual
  shifted Flux2 sigma schedule. No guessed custom node or downloaded implementation.

The hook node's lower-level dynamic patcher raises an unsupported error, BUT
`CFGGuider.inner_set_conds` automatically selects a non-dynamic delegate when
hooks are attached. Thus hooks are not proven unusable: the concern is a memory-
implementation change. Avoid that extra variable with existing native split-
sigma samplers and static model clones. Do not restart workers or change fast flags.

## Exact mechanism and validation gate

Reuse the already-audited `native-expression-reference-house-phone-inherited`
graph and four reference roles. Picture1 is the detailed raw, Picture2 the exact
original expression crop, Picture3 a genuine identity portrait, Picture4 genuine
hair material. Each LoadImage -> scale -> full Flux2 VAE -> ReferenceLatent chain
enters both CFG branches and BOTH sampling segments unchanged. Identity is supplied
by genuine-trained V3 in the early segment, not only generic img2img or a prompt.
Later native-reference identity retention is a prediction to be measured against
six genuine held-outs, not an identity lock.

Keep protected9B/Qwen3/fullVAE/V3 weights, original1680x1008 dimensions, seed8675416,
Euler/CFG4 and50TOTAL steps. PhoneON is inherited from the original base; second-
pass phone strength stays0 in both segments. TurboOFF. No new reference photos,
new model/dependency, masks, face swap, postprocess, extra noise or intermediate
VAE encode/decode. These dimensions retain the previous1.69MP comparator; they
are not a claimed1MP speed benchmark.

Split the original sigma vector at step35 into35+15 intervals, sharing the exact
boundary sigma. FIRST sampler output0 (still-noisy latent) goes to SECOND sampler
with DisableNoise, the remaining sigma vector and the same reference/text/CFG.
Do NOT use its denoised preview/output1 or reset the schedule. Flux flow exports
latent/(1-sigma); the next zero-noise import multiplies by(1-sigma), restoring
the trajectory. Euler has no multistep solver history to carry across the split.

First run a constant0.9/0.9 split control and compare with the actual uninterrupted
0.9 output. Require negligible pixel difference and no meaningful visual change
before interpreting the experiment. CPU graph guards and actual installed Euler/
flow math tests precede generation. This control proves implementation fidelity,
not image quality. Then change ONLY late identity strength0.9 ->0.0, plus the save
prefix. The early35-step latent can be reused only if live execution reports cache
reuse; never claim a speedup or exact cache hit from intent alone.

If the scheduled result visibly improves High without losing recognizable likeness,
closed lips, source head/gaze, natural hair/skin or background detail, apply the
same recipe to canyon and the third genuine image. At most one boundary refinement
after the first scheduled result; no strength/timing grid. Reject and diagnose if
the effect is still merely different, not better. Production is untouched until
one coherent recipe passes all requested photos and end-to-end verification.

Locked RTX3090/8188 only; check both GPUs/queues, node/model visibility and protected
hashes before submission. Reuse only an explicitly verified latest owned terminal
cache. Never free another worker or interrupt unrelated jobs.

## Preflight and constant-strength control

PowerShell graph tests pass: exact output0/noise/sigma wiring, shared conditioning,
unchanged phone strength, constant-strength control metadata, invalid parameter
rejection and rejection of stateful/non-Euler samplers. Four CPU tests using the
actual installed schedule, CONST noise conversion and Euler function also pass.
The actual shifted sigma at step35 is0.67460555; do not describe it as sigma0.3
or assume that70% of step count means70% of the flow's noise range.

Control job `884126c1-2967-460f-a14b-81b982e11fd1` was submitted once on8188,
queue number40, no node errors. Five protected model hashes and all required
live schemas passed. It keeps identity0.9 in BOTH segments and inherits the same
PhoneON raw with second-pass phone strength0. The runner saved the complete
manifest under `work/upgrade-source-faithful-20260903/identity-schedule-house-control/`.
No result or beauty acceptance was claimed while that job was running.

## Control result and explicit comparison-scope correction

Control completed successfully in498.56seconds. Native output SHA256:
`ce7a795edc0baee878d44ea5d35a85035a64cb04443d2f6c4d7ce6da147bc82a`.
Six-reference likeness0.75728518 versus uninterrupted0.75923485; source pose
error3.80733degrees and closed-lip ratio0.00206784. Those retain the existing
beauty/source-pose failures. Face review finds the same coarse skin/tense expression.

The first comparison invocation rejected a Windows path-separator spelling
difference for the SAME source file. Path canonicalization was corrected while
also freshly verifying every reference SHA; no inputs or image thresholds changed.
All non-schedule graph inputs and five model records match. The numeric control
then FAILS its originally declared tight thresholds: full-frame MAE0.27984497,
SSIM0.99891388; face MAE0.20952688, SSIM0.99883293. PSNR52.58dB; maximum per-channel
pixel difference26. The saved `mechanics-audit.json` remains failed and unmodified.
Do not relabel the split as pixel-identical or claim the cause is proven. The
CPU toy test establishes the intended math, not numerical equivalence of the GPU
model across two sampling invocations.

Explicit protocol correction before the first scheduled test: use this actual
SPLIT control, not the uninterrupted image, as the matched comparator for changing
late identity strength. That isolates the scheduling change within the same
two-segment implementation despite its measured small difference from unsplit.
This does NOT waive any beauty/identity/source-pose requirement, promote the
split control, or turn its failed equivalence check into a pass. Both original
and actual Low remain visible; the scheduled image must be genuinely better,
not merely different. Shared first35-step cache use must be checked from history.

## Scheduled result and sole timing refinement

Job `29957d55-f1c2-4f05-8f08-c2bc064b7ddb` completed in150.42seconds. History
explicitly reports node25 (first35 sampler) cached, along with its unchanged
model/reference/text inputs. Graph comparison proves ONLY node31 identity0.9 ->0
and node27 output prefix changed from the matched split control. This saves
time for this controlled experiment; it does not make a fresh full workflow
three times faster. Output SHA256:
`f6f4f87336b3b827265eb6937c7c2e48609f1ca079a8a9e52475ea0024264e95`.

Likeness0.75616664 versus matched control0.75728518; closed lips0.00294436;
source pose error3.60753250degrees; source eye-coordinate error0.06062442.
Six genuine held-outs were scored, and native/face/thumbnail images reviewed.
Coarse speckles/forehead creases and tense expression remain; the background
is detailed and the face stays recognizable, but this is not a better High.
Source-pose evaluation remains failed. No production change.

One timing refinement only: move the switch from step35 to step15, keeping
early identity0.9 and late0, both texts, four references, phone0 inherited,
total50Euler/CFG4/seed/dimensions unchanged. The35-step test leaves likeness
almost unchanged but cannot remove the already-established appearance; the
earlier switch tests a substantially longer native-edit finishing interval.
This may lose likeness, which must be assessed visually plus genuine-reference
diagnostics rather than accepted just because appearance changes. No later
timing/strength grid. CPU continuation math is also tested at step15 before
submission. Its first segment differs, so the earlier35-step latent cannot be
reused or truncated; expect a complete50-step run, not another150-second run.

## Final result: timing did not solve the appearance problem

Early15 job `e90553ca-ef51-4163-ab29-222701fbd2ba` succeeded in500.057seconds.
SHA256 `dd693ee86e753bd924a861dc0c084ecad9586f6622febf261fb15e5f50878c80`.
Structural JSON comparison (ignoring dictionary ordering) proves that only
node30 split35 ->15 and node27 filename changed from early35; all model and
reference records match. Native likeness0.75083804, closed-lip ratio0.00147774,
original-source pose error3.75050545degrees. The face remains recognizable, but
the coarse freckles/creases and tense expression are still worse than the source.

Replayed the SAME existing common polish and source-gaze correction on control,
early35 and early15. No extra retouch layer or High geometry; the experimental
common policy disables forced mouth-corner lift and cheek highlight equally for
Low and each candidate. Production was not changed. All three revised Low files
are byte-identical SHA256 E37C521F3F4EC68E550081D397D685867C76C59A646B9FE3877A793426C812E0.

| Finished result | Genuine-reference likeness | Source pose error | Horizontal gaze error |
| --- | ---: | ---: | ---: |
| Matched split control |0.765516|3.72478 degrees|0.008966|
| Early35 |0.751480|3.70115 degrees|0.017354|
| Early15 |0.740402|3.69910 degrees|0.020858|

All mouths remained closed; pixels outside the established polish/gaze mask were
unchanged. Early15 marginally misses the existing horizontal-gaze tolerance and
identity-drop diagnostic, but those are NOT the primary reason for rejection.
Full-size, face and thumbnail review still shows older/coarser skin, speckles,
a pinched/frowning brow and no compelling smile improvement. Detailed background
survives. The finish does not rescue this mechanism. No additional timing/strength
grid or three-photo repetition; keep these failed artifacts for reference.
