# High skin and eye-contour experiments — not production

Mitch selected **stronger beauty, still recognizably him**. These are CPU-only
experiments on the previously audited Klein outputs. No model, native generation,
phone/Turbo default, production node, UI, or workflow was changed. No uploads,
downloads, GPU interruption, or extra identity conditioning occurred.

The image-edit preservation checks guided separate one-variable comparisons and
full-size/thumbnail review. The project-local ComfyUI scope was retained.

## Skin: two separate mechanisms, neither a finished High solution

`experimental_upgrade_skin_polish.py` provides anatomically aligned skin regions,
protected eyes/brows/lips/hair, compact spot selection and bounded Lab warmth.
`evaluate-upgrade-brow-edit.py` reproduces the frozen brow/crease baseline exactly
before either isolated treatment; paths and hashes are saved in each audit.
All experiment folders below live under `work/upgrade-source-faithful-20260903/`.

Initial dark-compact spot selection was too broad: house 839 components, 26.6759%
coverage; canyon 819 components, 22.1445%. Both exceed the unchanged 18% maximum.
**No repair was applied.** Failed masks and unchanged candidates are saved in
`high-skin-spots-house` and `high-skin-spots-canyon`. The first invocations raised
before saving; identical reruns added failure reporting, not new parameters.

The one selection refinement additionally requires local component-mean positive
Lab chroma contrast above .5; it is a heuristic, not a validated freckle classifier.
`high-skin-pigmented-spots-house` selected 165 components, 949 core pixels, 4.85527%
coverage. Selected dark response decreased .0203271 -> .00152819 (92.4820%), but
many visible marks remain. Likeness .728138 -> .722979. The selection mask and face
comparison were inspected. This is a limited cleanup, not proof of all-freckle
removal or enough Low/High separation. It has not been frozen-tested on all3 or
promoted. Do not report the selected-pixel reduction as a whole-face improvement.

Warmth keeps Lab lightness unchanged and adds 35% of positive source/target median
chroma difference, capped at [3,5] in Lab a/b. House shift [2.275,.557813], likeness
.728138 -> .725632. Canyon shift [3,5], likeness .684388 -> .644833. Initial masks
left cool eye/feature surrounds, creating a makeup-like effect. Saved as
`high-skin-warmth-house` / `high-skin-warmth-canyon`; not accepted.

The **one warmth refinement**, `high-skin-warmth-feather-canyon`, changes only the
application mask to separate outer-boundary and feature feather widths. Source
statistics and [3,5] shift are identical. Likeness .671662. The rings are reduced,
but the localized orange/rosy eye/cheek coloration is still not a sufficiently
natural overall improvement. No further warmth sweep or combination was run.
Do not include this coloration in the selected eye-only comparisons.

Ten CPU tests pass, including existing imported source-expression tests, exact
unselected pixels, chromatic versus neutral dots, bounded shift, identical-source
no-op and unchanged dilated eye pixels with the refined feather.

## Why the earlier eye edit remained modest

`diagnose-upgrade-eye-guards.py` saves `eye-guard-diagnostic.json`. Final gaze lock
edits only the eroded eye interior; it does **not** revert eyelid boundaries.
The source-contour experiment requested approximately .2–2.3 px upper-lid moves.
Its full inferred iris disk guard blocks one upper-lid target outright in four of
the six eyes and partially blocks additional targets in all six. A fitted iris
disk can overlap an occluding eyelid, so exact full-disk pixel protection conflicts
with changing that lid. These geometric constraints are not a measurement of
achieved movement. Whole-face landmark redetection remains noisy.

## Stronger contour experiment and one refinement

`experimental_upgrade_eye_contour.py` remaps candidate pixels using a bounded TPS:
eye width requested 1.035x, outer corner lifted .035 eye widths, pupil **core** fixed,
brows/lips/nose/hair/outline protected. This is cosmetic geometry, not identity
conditioning. Initial aperture request .82x introduced an unwanted squint.
Existing source-gaze correction is applied last and audited separately.

Initial frozen recipe, `high-stronger-eye-contour-{photo}`:

| Photo | Likeness | Maximum horizontal source-gaze error | Review |
| --- | ---: | ---: | --- |
| Canyon | .682219 | .023131 | Visible but not compelling; gaze gate fails |
| House | .709515 | .024363 | Squinted presentation; gaze gate fails |
| Third | .770923 | .007425 | Gaze gate passes, but too squinted |

The **single parameter refinement** changes aperture .82 -> 1.0 (no extra narrowing).
Width/corner targets, masks, safety rules and final gaze method are unchanged.
All3 used the same revised parameters, `high-eye-contour-no-narrowing-{photo}`:

| Photo | Before this eye stage | After | Max horizontal gaze error | Minimum inverse Jacobian |
| --- | ---: | ---: | ---: | ---: |
| Canyon | .684388 | .689839 | .013167 | .705820 |
| House | .728138 | .715796 | .004605 | .829589 |
| Third | .800576 | .790079 | .004747 | .761395 |

All retain 100% of the requested field after the safety check. Eight CPU safety
tests pass (four new eye tests and four imported source-expression tests).
Full-size, face-crop and thumbnail review performed on all3 refined outputs.
Removing narrowing looks more natural; no new teeth, mouth change, background
damage or head/hairline movement is introduced by this eye stage. The supplied
generated skin/hair, existing smile/cheek differences and base pose drift remain.
The overall stronger-beauty goal is **not established**, especially at thumbnail.
Passing a geometry/gaze test is not an attractiveness or full identity lock.

The original .70 likeness / .03 drop diagnostics are not silently waived or rounded
into passes. Mitch allows a modest likeness tradeoff, so these numbers alone are
not the reason to reject a beauty edit; visual improvement is still insufficient.
House remains about3.84 degrees from source yaw due to its existing generated base.

Third uses the previously corrected single-source native base, with its genuine
source excluded from the five scoring references. Canyon/house retain four-reference
bases. Thus this is a shared **postprocess** test, not proof of one general native
generation policy across all3. Third Low is accurately labeled REVISED LOW.

## Saved outcome and remaining work

Production still uses the existing subtle High. Defaults stay Low, phone ON,
Turbo OFF. No end-to-end production promotion or current-goal completion occurred.
Independent pixel verification is provided by `audit-upgrade-contour-invariants.py`.
Its saved `eye-contour-independent-invariants.json` reports exactly0/255 difference
outside the eye edit, on dilated brow/lip pixels, and on the pupil core before final
gaze correction for all3. The final gaze correction is intentionally allowed to
move iris pixels; do not extend the pre-correction exact-pupil claim to that stage.
The live GPU queues were both empty; cached3090 models were left untouched.

Do not repeat the closed warmth or squint sweeps. Retain the no-narrowing contour
as an experimental component, not a finished stronger High. Clearer attractive
eyes/expression without puffiness, better skin, one general generation policy and
the final integrated three-photo/defaults verification remain outstanding.
