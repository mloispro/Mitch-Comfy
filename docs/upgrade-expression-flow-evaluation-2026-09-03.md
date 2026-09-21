# Expression-motion-only feasibility

Status: pilot and sole refinement completed; fixed stronger recipe rejected on house.
No production change, third-photo inference or complete High acceptance.

The user explicitly prefers a stronger beauty edit while remaining recognizable. Prior native
Klein changes did not consistently recover the source smile/eyes. The original LivePortrait
decoded-face pasteback was rejected for texture loss and remains rejected. This experiment
does not use its decoded RGB as final pixels, blend a generated face into another face, or
add restoration/sharpening. It tests a different, unproven use: a motion estimator.

## Evidence and exact mechanism

Author source pinned at `9b294b3d0536135442ea73cb01e6cb3ca7029dd3`, five existing human weights
at HF revision `82a4fa6735ca58432b6ce39301b4b9ee066dea47`, hash-verified before inference.
Existing F/M/W/G/S runtime and 256-input/512-decoder crop are described in
`upgrade-liveportrait-evaluation-2026-09-03.md`. No new weights, nodes, dependencies, services
or base model are introduced. This is a standalone experiment, not a fabricated Comfy graph.
Original Upgrade renders already use the compatible Klein9B identity LoRA and phone adapter;
they remain phone-on, Turbo-off. The Upgrade RTX3090 lock remains in force.

The original scene supplies expression only through M. The generated raw is the edit target:
its F appearance features, M canonical shape, pose, scale and translation remain in both
reconstructions. Copy only the author's absolute `exp` subset (pipeline lines 367-373), not
the driving canonical keypoints or head pose. Use the same no-stitching setting in both
reconstructions, matching the earlier exact-zero control. No lip normalization, scalar
eye/lip retargeting, or extra landmark models. Absolute expression can leak identity;
retaining appearance/canonical points is a preservation mechanism, not an identity lock.

Author primary source:
https://github.com/KlingAIResearch/LivePortrait/blob/main/assets/docs/changelog/2024-08-19.md
and `src/live_portrait_pipeline.py` in that repository.

Compute OpenCV DIS inverse optical flow from expression reconstruction to zero reconstruction,
plus its forward counterpart for consistency diagnostics. Both have the same appearance
source. Convert this 2D displacement through the known crop affine into the native frame.
Feather displacement inside the face oval and exclude semantic hair. Remap the original
full-resolution raw exactly once. No decoded or driving-photo RGB enters the output.
Do not treat LivePortrait's 3D feature sampling grid as physical RGB motion or average its
depth planes. Do not add decoded-image differences to raw (which could ghost features).

OpenCV primary sources:
https://docs.opencv.org/4.13.0/de/d4f/classcv_1_1DISOpticalFlow.html
https://docs.opencv.org/4.13.0/da/d54/group__imgproc__transform.html

The combination of these mechanisms is our hypothesis, not an author-endorsed pipeline.
Its limits include imperfect correspondence, occlusion, expression/identity entanglement,
and inability to create newly visible surfaces or remove existing pigment/creases by motion.

## Bounded test and acceptance

CPU synthetic tests first: zero remap exact; input immutable; known translation recovered;
crop affine rotates/scales vectors correctly; positive map Jacobian; folded/oversized fields
rejected; background/hair exact. One canyon pilot, full absolute expression strength 1.0.
At most one controlled strength refinement. No parameter grid.
Only proceed to house and a genuine third source if the pilot is useful visually.

Before inference inspect both queues/GPUs; never interrupt work. Cached Comfy weights may
be released only after the latest owned terminal job and both idle queues are verified.
The script itself rechecks RTX3090 queue, physical mapping and idle memory/utilization.
An unrelated job began on4070 during preparation, so the cache-release attempt aborted
before making any change. The alternative is to retain all cached models: allow inference
only with the exact known owned terminal3090 history ID, utilization <=10%, empty3090 queue,
and at least8GiB free. The earlier author-core test peaked at1.20GB. Both preflight checks
record this provenance; no server unload, restart, other-card inference or interruption.

Map acceptance: forward/back consistency p95 <=1.5 decoder pixels, no more than3% active
pixels above3pixels; inverse Jacobian >=0.25; maximum displacement <=12% native face width;
exact zero-motion output and exact pixels outside active face/hair protection. These are
engineering guards, not perceptual quality claims. Abort unsafe maps; no silent clamp.

Review native image, face crop and thumbnail for actual stronger/source-faithful appeal,
closed lips/no new teeth, gaze/head direction, puffy cheeks, forehead/hairline, texture and
seams. Score against six genuine held-out photos (exclude third source when applicable).
Likeness is diagnostic, not a sole .70 cutoff after the user's preference. Report all scores
and failures. No production promotion from a numerical or component-only pass.

## Initial pilot and sole refinement decision

Full expression1.0 completed in11.11s. Native remap maximum2.43px, minimum inverse
Jacobian0.802, cycle p950.164px. Background/exterior and semantic hair are exact;
zero-control is exact. Likeness0.73643 versus raw0.75179 and actual Low0.74614.
Closed-mouth diagnostic0.00518, source pose error2.697degrees. Native/full/face/thumbnail
review found retained texture and no obvious seam, but still too little expression/beauty
separation. Freckles and frown creases remain; movement alone cannot remove them.

Because the pilot is underpowered, the sole refinement will double the expression delta
to2.0 (the author's driving-multiplier concept), keeping every other setting fixed.
This extrapolates rather than exactly reproduces source expression; inspect for exaggerated
smile/eyes and puffiness. A lower-strength test would move farther from the user's request
and is not performed. Do not sweep further strengths if2.0 is not useful.

## Refinement and cross-photo result

Canyon2.0 took10.67s, peak allocated1.12GiB. Likeness0.68842 (raw0.75179, Low0.74614),
all six genuine references0.47543/0.57626/0.63099/0.63601/0.61134/0.63336.
Closed-mouth ratio0.000374; source-pose error2.463degrees; full source-relative eye
coordinate error0.04803. Maximum displacement7.39px, inverse Jacobian minimum0.472,
cycle p950.444px. Semantic hair, exterior and zero control remain exact. Output SHA256:
`3582309a6c9b06cceeb5a173b9439d7eb0379410d16b477813b1da8d249f5ded`.

Native, face and thumbnail review: the smile becomes more closed/asymmetric and the
eye expression shifts modestly toward the source. No obvious face boundary or decoder
texture replacement. It is not a full beauty pass: freckles, frown lines, skin tone and
some source/expression differences remain. The0.69 diagnostic alone is not the rejection
reason given the user's explicit willingness to trade some likeness for a stronger edit.

The same2.0 recipe on house fails before remapping raw RGB. Cycle p95 is13.454pixels,
17.68% of active pixels exceed3pixels, maximum27.236pixels. Visual inspection of the
analysis-only decoder crop shows an open mouth, shifted pupils and altered brow expression,
despite the driving source being closed-lip. These introduce unmatched/disoccluded surfaces
that cannot safely be obtained by remapping existing pixels. The map guard correctly aborts.
No house `expression-flow.png` exists; do not show its decoder crop as a delivered result.

The cause is upstream, not just a poor skin compositor: absolute learned expression transfer
and its extrapolation are not faithful enough on this image. Optical flow cannot repair a
wrong expression or create new occluded content. This is consistent with the author's
documented image-driving limitations. Do not bypass the consistency guard, silently clamp,
choose a different strength per named photo, add texture restoration, or claim a cross-photo
success based on the canyon-only result. No third-source inference is warranted for this
failed fixed recipe. A weaker house control would be a diagnosis, not a stronger-High fix.

Artifacts under `work/upgrade-source-faithful-20260903/`:
- `expression-flow-canyon/`: strength1.0, complete diagnostics and comparisons.
- `expression-flow-canyon-200/`: sole2.0 refinement, complete comparisons.
- `expression-flow-house-200/`: unsafe-flow rejection and analysis-only reconstructions.

Implementation remains evaluation-only in `scripts/experimental_upgrade_expression_flow.py`
and `scripts/test-upgrade-expression-flow.py`; seven synthetic CPU unit tests pass in
`scripts/test_upgrade_expression_flow.py`. No production module imports these files.
The active4070 job was never interrupted; cached3090 models were never unloaded.
