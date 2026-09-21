# Stronger eye/brow definition — bounded component test

Status: experimental, not production. Previous goal turn made progress by closing
source-lid geometry after measured house/canyon tests and rejecting blanket upper-
orbit smoothing from actual sampled-region evidence. Those routes stay closed.

## Measured failure and limits

`eye-definition-diagnostic/audit.json` under the existing upgrade work directory
compares source with the audited revised-Low pre-gaze image. Fixed inferred iris,
limbal, sclera and brow regions were used; pupils and bright iris catchlights are
excluded from iris-contrast statistics. Sample-mask panels were visually inspected.

Source/current iris normalized10th-to90th percentile contrast:

- House:1.576/.668 and1.397/.834.
- Canyon:1.015/.386 and1.897/.613.

Source/current brow positive local dark-response means:

- House:.0476/.0168 and.0405/.0099.
- Canyon:.0343/.0191 and.0206/.0088.

Both pairs have weaker rendered iris and brow contrast. Sclera brightness and
iris saturation do NOT show a consistent same-direction deficit. The canyon
source has a strong colour cast and is not a genuine identity reference. Do not
copy its hue, brighten every sclera, invent catchlights or infer ideal anatomy.
These are image diagnostics, not physical lighting or attractiveness ratings.

## Frozen experiment

CPU-only, same native PhoneON raw and revised common polish as the preceding
audits. Reproduce saved revised Low byte-for-byte by replaying the existing source
gaze correction on its hash-verified pre-gaze pixels. Then change only existing
iris/brow luminance contrast AFTER gaze correction. No geometry/second gaze warp.

- Iris contrast about its own median: requested gain2, bounded luma change.08.
- Existing brow positive local dark contrast: requested gain2.5, bounded change.075.
- Smooth application within existing feature boundaries. No new eyebrow shape,
  eyeliner, limbal ring, source colour or texture.
- Pupil core, sclera, existing bright catchlights and semantic hair remain exact.
  Gamut-safe RGB scaling retains per-pixel colour ratios before8-bit rounding.
- All other skin, mouth, nose, head outline, body and background pixels stay exact.

This stronger treatment must visibly improve eye definition without painted brows,
harsh irises or a changed perceived gaze. Score against all six genuine held-outs,
measure fixed-landmark contrast before/after, re-detect final pupil coordinates,
inspect native images/equal-scale face crops/thumbnails. Do not mistake a contrast
gain or exact-pixel check for a complete High solution. At most one overall-strength
refinement to.65 after the initial test; no hue/whitening/sharpening grid.

Even a successful eye component leaves source smile/cheeks, clear natural skin,
one coherent native policy and full third-photo/production end-to-end validation
outstanding. No production/default change or GPU generation is part of this test.

## Frozen house/canyon results

Both runs completed at strength 1.0. The runner reproduced each audited revised
Low byte-for-byte before applying eye/brow photometry. All six genuine held-out
photographs were used for likeness diagnostics. These two scene sources are not
being used as genuine identity anchors. Paths below are relative to
`work/upgrade-source-faithful-20260903/`.

| Test folder | Revised Low likeness | Eye-definition likeness | Largest horizontal gaze change from Low |
| --- | ---: | ---: | ---: |
| `eye-definition-house` | .770816 | .756578 | .006950 eye widths |
| `eye-definition-canyon` | .753381 | .740804 | .009591 eye widths |

House fixed-landmark iris contrast increases .570 -> .983 and .788 -> 1.367;
brow dark response increases .01582 -> .02786 and .01060 -> .01913. Thus the
experimental operation genuinely changes its intended photometric signal.
Canyon iris contrast increases .386 -> .743 and .506 -> .895; brow dark response
increases .01877 -> .03040 and .00898 -> .01594. These are not measurements of
attractiveness, and no production setting has been changed.

Final redetected horizontal source errors are .02462/.02575 for house and
.00481/.02753 for canyon. Both have an eye above the existing .02 diagnostic
bound. No pupil core was moved or repainted by this stage; whole-face landmark
redetection also responds to photometry. This does not establish perfect perceived
gaze. The pre-existing Low gaze correction and its errors are saved separately.

Native-size images, equal-height face crops and whole-frame thumbnails were
visually reviewed for both photos. Eyes and individual brow marks are more
defined, but the difference is small at normal viewing size. The frown/smile,
cheek fullness, visible spots and coarse skin remain inherited from Low. Darker
existing brow marks are not newly restored natural brow hairs. There is no clear
whole-face beauty improvement sufficient for the requested High setting.

Saved 8-bit checks show exactly zero difference outside the eye/brow edit region
and on the selected pupil-core/sclera/hair pixels for both photos. Mouth, face
outline, body and detailed background are unchanged by construction, not newly
improved. Neither output introduces teeth. Hair and apparent age outside this
small edit are inherited. Eight CPU regression tests pass.

Output SHA256:

- House: `8d693c5236ceb9c7de827c1f925c1bedbf0fdbc162d35169b81b60c6319cbb59`
- Canyon: `4c8b0f1b93b6415cb671eb390762d373b2bf7577185443805254857f6348386b`

Decision: retain as a measured, unpromoted component; **closed as a stand-alone
stronger-High solution**. Do not run the optional .65 refinement: reducing an
already insufficient effect does not address the observed failure. Do not turn
this into another contrast/whitening grid. No third-photo or production test is
claimed. The goal remains incomplete; this turn made progress by resolving the
contrast hypothesis, not by delivering the requested full High recipe.
