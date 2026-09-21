# Calibrated semantic expression controls — feasibility gate

Status: initial calibration and sole close-only refinement rejected on house;
no native final RGB, production change or cross-photo success.

Previous goal turn made progress: motion-only remapping retained raw texture on canyon,
but whole absolute-expression transfer at2x opened the house mouth and moved gaze. That
fixed recipe is rejected. This test changes the conditioning mechanism, not its strength:
use only the author's explicit smile, brow and lip-opening controls on the generated
raw's own expression. No driving photograph enters LivePortrait M/F/W/G.

## Primary evidence and compatibility

Read installed author `src/gradio_pipeline.py` update_delta_new_smile,
update_delta_new_eyebrow, update_delta_new_lip_variation_three and their calling path;
read `app.py` slider ranges. Current upstream sources confirm the same formulas:
https://github.com/KlingAIResearch/LivePortrait/blob/main/src/gradio_pipeline.py
https://github.com/KlingAIResearch/LivePortrait/blob/main/app.py
https://huggingface.co/KlingTeam/LivePortrait

Local source remains pinned to9b294b3d0536135442ea73cb01e6cb3ca7029dd3; the same five
already-installed, hash-verified human checkpoints and float32 runtime are used. Crop512,
network256, decoder512, no stitching/lip-normalization/scalar-retargeting. No downloads,
dependency changes or invented Comfy nodes. No203landmark model is required by these
explicit controls. New small control functions will be compared numerically with the
author's methods extracted from the reviewed source, without importing the whole Gradio app.

## Mechanism and limits

The native generated raw supplies appearance F, canonical identity/pose/scale/translation M,
and starting expression. Only three author-defined expression offsets are applied. Original
scene pixels go to the installed CPU face-landmark detector, supplying geometric expression
targets, never a new face appearance volume or copied pixels. Genuine validation photos
are used only for face-similarity checks, not for expression optimization.

Measure each control's local response on the raw: six finite-difference probes (smile+/-0.15,
brow+/-5, lip-opening+/-5), a zero decode, then one predicted edit. They are calibration
measurements, not aesthetic candidates selected by a grid. Use a bounded least-squares
solve targeting source-relative mouth corners/closure, brows and eye aperture, while
penalizing changed gaze/nose/jaw proportions. Correct for zero-decoder landmark bias by
targeting zero_features + source_features - raw_features. Since brow is piecewise linear,
solve each sign branch algebraically and select by predicted residual, not more renders.
Limits: smile[-0.3,0.6], eyebrow[-15,15], lip-opening[-20,20], within author GUI ranges.

Use the same policy for every photo; never select coefficients by photo name. The author
controls are coupled, not guarantees of independent facial motion. A linear calibration
may be insufficient; record predicted versus measured response and reject unsupported
claims. These controls do not inherently remove pigment/creases or guarantee attractiveness.

As in `upgrade-expression-flow-evaluation-2026-09-03.md`, zero and controlled decodes supply
2D DIS motion only. The final native RGB is a single remap of the raw. Background/hair exact,
no decoder RGB, no pasteback, no sharpening/restoration. The same cycle/Jacobian/motion
guards remain in force. The motion-only combination and calibration are our hypothesis,
not an author-endorsed quality guarantee or identity lock.

## Bounded acceptance

Run house first (the failure case), not the easier canyon. Inspect both GPUs/queues; retain
RTX3090 lock and existing verified-owned-cache/headroom checks. Seven mapping tests plus
semantic-control formula/solver tests precede inference. Complete one calibration and one
candidate. At most one controlled policy refinement, not a coefficient/seed/model sweep.

Inspect native image, face and thumbnail: clearly stronger/source-faithful eye/brow/smile,
closed lips/no teeth, no puffy cheeks, same head/gaze, retained texture and no seam. Compare
at least two genuine references (all six available; exclude any third-source overlap).
Metrics support but never replace visual acceptance. If useful, freeze the algorithm and
cross-check canyon and a genuine third. Full goal still additionally requires skin/freckle,
hair, Low/High separation, Phone ON/Turbo OFF, one coherent upstream recipe and actual
production integration plus end-to-end verification. A component pass is not completion.

## First calibration result and sole refinement

House calibration selected smile-0.15518, eyebrow+2.74386, lip-opening+14.18059.
Predicted weighted residual1.726 versus unchanged2.272, but actual4.973: the decoded lip
gap increased to0.0584. Cycle consistency passed, but native inverse Jacobian0.108
rejected the map before final RGB. Analysis-only crop visually confirms parted lips.
The local derivative near a nearly closed mouth extrapolates poorly beyond the probes.

Sole refinement: constrain the author mouth-opening parameter to[-20,0] (close-only),
leaving smile/brow ranges, probes, targets and weights unchanged. Add an explicit actual
response guard before remapping: reject if weighted target error worsens or decoder lip
gap exceeds0.035. This is not proof of beauty; it only prevents an obviously wrong
calibration prediction from masquerading as a useful edit. No further control/ridge grid.

Close-only selected smile-0.108952, eyebrow+3.561633 and lip-opening approximately0.
It predicted residual2.092, but measured2.555 versus unchanged2.272; the actual-response
guard rejects before remapping. The decoded crop has nearly the same tense appearance.
These generic, coupled controls plus a local linear fit do not reproduce the requested
expression, and geometric motion alone cannot remove the existing dark creases/pigment.
No more semantic-slider/ridge/strength refinements. Preserve both house folders under
`work/upgrade-source-faithful-20260903/semantic-expression-house*`. Six semantic CPU tests
and seven motion-map tests pass, but that is not a visual quality success.
