# Source upper-lid curvature: bounded component investigation

Status: **closed as a standalone stronger-High solution after frozen house/canyon
tests; experimental solver retained, not production or full-goal completion.** The previous goal
turn made progress by completing and rejecting RefControl High and its sole
diagnostic; that closed route is not reopened here.

## Evidence and distinct change

Production `flux2_klein9b_attractiveness.py` limits upper-lid displacement, averages
overlapping kernels, then attenuates the edit and protects a complete inferred
iris disk. The saved `eye-guard-diagnostic.json` shows that disk intersects desired
upper-lid targets in all six tested eyes. Existing source-contour TPS also fixes
the inferred iris disk. The later cosmetic contour test replaced that disk with
pupil-core protection, but requested a fixed1.035x eye width/outer-corner lift and
initially a squint; it did not restore the source's upper-lid curve.

Inventory correction: `experimental_upgrade_eye_expression.py` already tried a
Gaussian pupil-core upper-lid repair on canyon; the active plan records its
maximum0.32/1.20px requests, likeness0.746670 and insufficient visible change.
Do not call this the first pupil-core repair or a newly discovered identity
mechanism. The present experiment replaces that averaged Gaussian field with a
controlled TPS and records achieved positions on clean common-polish baselines.
It is an additional measured solver check of a known limitation.

This is a constrained solver correction for that observed failure, not another
beauty prompt, width/squint sweep or reopening of the closed full-expression TPS.
Use source upper-lid height in normalized fixed eye-corner coordinates; keep eye
width, corner positions/angle and lower-lid controls fixed. Candidate pixels are
remapped; source supplies landmarks only. Pupil core, brows, lips, nose, hair and
face boundary are hard protected. Full inferred iris-disk pixels are not protected:
existing iris-edge texture can stretch; this cannot reconstruct unseen iris detail.

Frozen request: source curvature90%, maximum10% of eye width. Continuous local
thin-plate-spline inverse map, fixed pupil-core/boundary controls, minimum inverse
Jacobian.25 and maximum3. A bounded safety line search may retain at least60% of
the requested field, otherwise reject. Record actual mapped control positions as
well as separate rendered-image landmark redetection. Requested shifts alone are
not proof the edit happened or that it improves attractiveness.

[MediaPipe Iris documentation](https://chuoling.github.io/mediapipe/solutions/iris.html)
describes approximate eye/iris landmarks and explicitly does not infer actual
gaze or identity. Pixel invariants, source-relative pupil geometry and visual
review therefore remain separate. Existing SciPy RBFInterpolator and OpenCV are
used locally; no models, dependencies or image services are installed/contacted.

## Isolation and acceptance

Start from the house's audited native PhoneON Klein BASE RAW, not the failed
RefControl output or an accumulation of failed beauty edits. Both branches get
identical common polish with the previously diagnosed forced corner lift and
cheek highlight disabled in this process only. High alone gets the new lid map;
both receive the existing source-pupil correction last. No other High tone,
skin, brow or mouth modification is mixed into this comparison.

Inspect the native full frame, equal-scale face crops and thumbnail; score against
six genuine held-outs. Require demonstrably reduced source-curvature error and a
visibly more appealing eye without stretched/odd iris edges or changed pupil focus.
No new teeth, face-outline, head, hairline, body or background change is permitted
from this component. Exact unselected pixels and fixed-feature pixels are tested.
At most one controlled refinement, then a component decision. Even success here
does not solve skin, expression, one general native policy or production integration;
those and a fresh three-photo end-to-end validation remain full-goal requirements.

## Frozen results

Eight CPU tests pass (four source-lid tests, four imported source-expression
safety tests). Exactly the same90% curve recipe ran on house and canyon; there
was no strength refinement, generation, new model or GPU action.

| Case | Revised Low likeness | Finished eye candidate | Closed-lip ratio | Horizontal source-pupil diagnostic | Source-pose delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| House | .770816 | .774792 | .002933 | .026743 (above .02) | 3.636633 degrees |
| Canyon | .753381 | .755315 | .003648 | .014588 | 3.096737 degrees |

Identity uses the same six genuine held-outs. These are diagnostics, not beauty
ratings. The component does not repair pre-existing source-pose drift. Historical
failed native candidates from the supplied audits were NOT reused: the runner's
explicit `candidate_input_key=BASE RAW` records the actual input, while their old
failure lists remain labeled historical. Low and High share exactly the same raw
and common polish; only the new lid map differs before the same final gaze stage.

Measured map geometry:

- House near/far upper-lid target errors .8612 -> .0899px / .6628 -> .2189px;
  maximum achieved control movement1.2939/.8237px. Full safety fraction1;
  minimum inverse Jacobian.7603, maximum1.7982.
- Canyon errors .0848 -> .0263px /1.1294 -> .1173px; maximum achieved movement
  .1818/1.6864px. Full safety fraction1; minimum Jacobian.3982, maximum1.3592.
- Rendered landmark redetection is saved separately; it broadly improves the
  larger curve discrepancies, but the tiny near-eye canyon error does not improve.
- Outside each lid-edit mask and outside the complete polish/lid/gaze union,
  independent image-difference checks report exactly0/255 error.

Native full images, equal-scale face crops and thumbnails were reviewed for both.
The eyes change slightly; no new teeth, face-cutout edge, body/background damage,
hairline displacement or new cheek fullness is introduced by the map. Existing
skin marks, frown/brow impression, hair appearance and weaker source smile remain.
The improvement is insufficient at thumbnail and is NOT a stronger High pass.
House pupil alignment still needs review; its flag is not waived. No third-photo
repeat, production update or end-to-end acceptance was claimed.

Saved outputs:

- `work/upgrade-source-faithful-20260903/source-lid-curve-house/high-source-gaze.png`,
  SHA `E27AC7E0E31527A65EAC9BE41853728664EAE46E8D500D8A0632EF423FEF2EF4`.
- `work/upgrade-source-faithful-20260903/source-lid-curve-canyon/high-source-gaze.png`,
  SHA `800472BD04455233B5877B036171D069FC6A0721027B6979655283FE9B8E87BA`.

## Why further lid-strength tuning is not the next action

House eye-frame measurements show source/current near-eye width relative to
interocular distance .5190/.5070, far-eye .3399/.3682. Source/current corner angles
relative to the eye line are .131/.019 degrees and -2.096/-2.087 degrees. These
2D diagnostics include the existing head-angle difference; they do not establish
ideal anatomy. Large arbitrary eye-frame changes are not supported by this evidence.

The saved upper-orbit diagnostic samples the same normalized skin band above each
lid, excluding dilated eyes and brows. Sample-mask overlays were inspected and
no candidate pixels were edited. In house, source/current dark-band95th percentiles
are .1182/.0874 and .1064/.0480; in canyon .0437/.0482 and .0551/.0514. Thus a
universal claim that excess upper-lid crease contrast causes the problem is NOT
supported. Do not blindly add orbital smoothing or treat this as physical lighting
measurement. Results and masks: `upper-orbit-diagnostic/audit.json` and its two JPGs.

The earlier Gaussian and present TPS source-lid routes are now both explicitly
closed as stronger-High solutions. Do not repeat another pupil-guard/curve sweep.
Next useful investigation is actual iris/sclera/brow photometric definition,
with measured source/current differences before choosing a bounded edit; do not
assume another gain increase will solve the full appearance objective. Skin,
smile/cheeks, a coherent native policy and final three-photo production verification
remain required. All six protected production hashes stayed unchanged.
