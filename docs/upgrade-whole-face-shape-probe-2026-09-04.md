# Whole-face source-shape probe — not production

This CPU-only pilot tests an observed failure: native house output has heavier
upper lids, a flatter mouth and rounder-looking lower-face presentation than the
preferred edit source. Prior eye-only and registered-blend tests fixed the face
outline; this test deliberately does not. It is not another diffusion prompt or
mask run and does not load another generative model.

## Mechanism and research gate

- The saved public raw house frame supplies **all RGB texture**. Its existing
  V3 identity LoRA and reference conditioning are unchanged; Phone ON/Turbo OFF.
- Original house image supplies **2D geometry only**, not genuine-reference
  identity evidence. No source RGB is copied or uploaded.
- Existing MediaPipe refined landmarks identify eyes, lips and face contour.
  [Author documentation](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md)
  describes estimated landmarks and AR use, not guaranteed likeness or beauty.
- Existing SciPy's degree-one thin-plate RBF interpolator fits an output-to-input
  displacement field. [Author implementation/docs](https://raw.githubusercontent.com/scipy/scipy/v1.16.0/scipy/interpolate/_rbfinterp.py)
  documents distinct controls, polynomial rank and smoothing; it does not imply
  a fold-free map. We explicitly measure Jacobians and reject unsafe maps.
- One policy: 80% source-shape transfer after outer-eye similarity alignment,
  with 10%-face-width control cap, fixed upper forehead and protected hair.
  Lower silhouette can move. Source iris radius/color are never transplanted.
- The existing source-gaze correction is evaluated after the geometry, with
  its changed pixels included in the final preservation audit.
- Local background/collar within a 14%-face-width outline transition can move.
  Pixels beyond this support must be exact. This is an explicit limitation, not
  a claim of whole-background pixel equality.

Identity prediction: most texture remains from the generated person, but shape
is an identity signal too; a likeness decrease is expected and is not proof of
failure by itself. Six genuine held-out EXIF-oriented photographs supply
independent recognition diagnostics. No invented threshold is a beauty score.

## Acceptance before executing

1. Stronger visible improvement versus actual Low at thumbnail and full face:
   source-like eyes, asymmetric closed smile, less puffy presentation.
2. No invented teeth, obvious distortions, hairline damage, bent nearby siding,
   cutout seams or gaze/head-direction change.
3. No changes outside the declared geometry/gaze support; Jacobian >=0.20.
4. Review genuine-reference likeness alongside images; ~0.70 is diagnostic,
   not an automatic pass or rejection.
5. Only if useful on house, apply the same policy to canyon and genuine third.
   Do not cherry-pick native-parent policies or call this public integration.

No skin cleanup is stacked in this pilot: it isolates whether a substantial
shape edit fixes the feature/expression failure before adding another stage.
No production edits, generation, cache release, downloads, or peer messages.

## Dense pilot and sole structural refinement

The dense 478-point pilot was stopped before saving any candidate by a negative
inverse Jacobian (-3.910, maximum displacement16.409px). Read-only localization
places the fold at x900/y459, near projected far-cheek/nose landmarks
278/323/438/457/331/439/344/266. This is a correspondence failure, not proof the
desired shape edit is unattractive. Intent and failure records are preserved in
`work/upgrade-source-faithful-20260903/whole-face-shape-house-pilot`.

The sole structural refinement retains the same80% target, image inputs,
alignment, upper-forehead/hair protection, exterior support and safety thresholds.
It uses face outline, eyelids, brows, outer lips and sparse nose anchors instead
of every projected surface vertex. The interior surface is interpolated freely.
This cage does not explicitly constrain the iris ring; final source-gaze
correction and visual review are therefore required. No strength reduction or
new skin/lighting stage is included. This is still an isolated geometry test.

## Completed result — route closed as a stronger-High solution

The115-control cage passes the inverse-map safety check (minimum Jacobian0.28036,
maximum18.733px displacement). Source-gaze correction yields held-out likeness
0.686348 versus actual public Low0.739620 and raw0.779115. Exterior and protected
hair pixels are exact at the geometry stage. At full frame, face crop and
thumbnail, the result has a visibly longer/source-like lower face, but retains
the worried brow, serious mouth and coarse texture. No teeth or obvious new
halo/bent siding appeared. This is not a clear attractiveness win.

A subsequent **equal-common-finish comparison** applies the existing Low v5
skin/hair treatment to both unwarped raw and cage output, using the previously
tested process-local policy that disables forced corner lift and cheek highlight.
It changes no other retouch constants and does not invoke the legacy High warp.
The finished candidate remains too tense/serious and speckled; the source still
has the preferred eye/smile presentation. Candidate likeness0.685309 versus
equally finished unwarped control0.772648; source pose diagnostic0.636356deg,
closed-lip ratio0.002002. Rejection is visual, not merely the score drop.

Preserved evidence folders:

- `work/upgrade-source-faithful-20260903/whole-face-shape-house-feature-cage`
  — output SHA8359B7CCD65B113D3767AE2B18B34E64CCA41143E53135BB580AE550B82E841B;
  audit SHA118B5AB9850C70BF1F62AE6C6C8CEC93E1BCB8878D05B38E69E6D435B3303791.
- `work/upgrade-source-faithful-20260903/whole-face-shape-house-feature-cage-common-finish`
  — output SHAFC96C447D99AD9BB0731A936485847D62DF48A3D500BD3F16FF234B6FA70789A;
  audit SHA293DB4647A89E1B4B177885101B223C731BC9C8D34EB3D801DE529F64898EC80.

Both have explicit review.json records. The common-finish review corrects stale
boilerplate in its original audit that incorrectly says no cleanup was applied;
the actual true flag and full cleanup reports were already recorded correctly.
Original audits/images are preserved, not overwritten to hide the error.

No canyon/third expansion, no generation or public deployment. No further
dense/cage strength or landmark-grid sweep. Production main/Low/High hashes
remain DAF62197/3F37FD56/0E38B630 respectively. The full High objective is open.
