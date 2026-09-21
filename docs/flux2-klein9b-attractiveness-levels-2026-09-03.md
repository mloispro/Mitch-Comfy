# Upgrade attractiveness levels — 2026-09-03

## Decision

The public Upgrade v1.1 exposes `off`, `low`, `high` through the existing `appearance_polish` input name.
Low stays the default; phone style stays on. No sampling prompt, model, LoRA, reference, seed, sampler, or
background-rendering change was made. No extra diffusion pass is required.

- Off: exact decoded generation, skipping the existing face/hair/iris polish.
- Low: the unchanged v4 handsome treatment plus the existing source-gaze lock.
- High: Low followed by source-guided upper-lid curvature, darker existing upper-lid/outer-corner definition,
  symmetric iris/limbal clarity, restrained sclera and under-eye lift, brow-fiber definition, middle-frequency
  forehead/under-eye crease attenuation, and restrained extra warmth. Broad shading and fine texture are retained.

High uses source and generated landmarks but only generated pixels. It does not copy a source face, redraw brows,
enlarge eyes, move eye corners or pupil centers, alter jaw anatomy, or create teeth. Its bounded source-guided warp
changes only the upper-lid neighborhood; the measured canyon correction was below 0.84 pixels. The full source still
enters the pre-existing generation as a native ReferenceLatent; its unintended identity influence remains unisolated,
as previously reported. The explicit identity signal remains the protected Base 9B identity LoRA plus genuine identity
reference.

## Observed issue and limits

Mitch's subsequent visual review found High insufficiently different from Low, with an inferior smile
and rounder-looking cheeks than the source. The levels are implemented, but that appearance objective
is **not resolved**. The separate expression investigation and preserved experiments are recorded in
[High expression investigation](flux2-klein9b-high-expression-investigation-2026-09-03.md).

The canyon source has stronger brow contrast, warmer color, and different eyelid emphasis. Its eye aperture ratios
were approximately 0.326 / 0.256 versus 0.324 / 0.272 in the earlier output. Eye-line angles differed by about 4–5°.
These estimates do not establish ideal facial geometry or attractiveness. Refined upper-lid landmark differences were
only about 0.01 of eye width, so a large geometry warp was not justified. High transfers that small measured curvature
and gets most of its visible eye change from tonal definition; it does not claim to restore every aspect of the source.

MediaPipe landmarks are used for local feature placement, not as an identity score. See the
[official face landmark guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker).
Filtering uses ordinary local Gaussian frequency decomposition; see
[OpenCV image filtering documentation](https://docs.opencv.org/4.11.0/d4/d86/group__imgproc__filter.html).

## Controlled saved-render evaluation

One raw phone-on render per scene was reused, avoiding diffusion variability. All processing and six-genuine-photo
AntelopeV2 scoring ran locally. Reference photographs are EXIF-transposed and their hashes are recorded in each audit.
The source scene image is not included in the scoring reference set.

| Scene | Off centroid | Low centroid | High centroid | Low → High pose change (pitch/yaw/roll) |
| --- | ---: | ---: | ---: | --- |
| Canyon | 0.751794 | 0.746137 | 0.724661 | −0.0036° / −0.2473° / −0.0197° |
| House | 0.779115 | 0.738950 | 0.727175 | +0.0724° / −0.1775° / +0.0460° |

High is an optional appearance/identity tradeoff, not an identity improvement or lock. The weakest genuine-reference
similarities remain below the 0.553346 pairwise floor: canyon 0.515342; house 0.534933. Visual preference still needs
Mitch's judgment. Full-size and thumbnail inspection found the final frequency-based treatment free of the forehead
patch seen in the rejected first mechanism. Background, pupil-core, lip, hairline, and other protected pixels have
exactly zero error. Post-High landmark checks found maximum normalized detected-gaze changes of 0.017938 on canyon and
0.008838 on house, under the 0.02 acceptance limit. High runs after the existing source-gaze correction.

Evidence: `work/flux2-klein9b-attractiveness-20260903/canyon-eye-final/` and `house-eye-final/`.
Saved-raw previews can differ slightly from the old final PNG due to decoding/rounding before reapplying Low.
The v4 implementation itself is unchanged and hash-tested.

## Rejected prototypes

The dark-trough/morphological-closing High v1 mechanism was rejected for flattened forehead patches and larger
identity loss (canyon 0.698828 before stage-order repair; 0.704523 after). Raising its strength did not solve that
mechanism. The next design replaced that operation with symmetric middle-frequency attenuation.
Artifacts remain under `canyon-v1`, `canyon-v2`, `canyon-gaze-order-fixed`, and `house-validation`.
The first `canyon-v1/audit.json` used a reader without EXIF transpose; its identity scores are invalid and must not be
compared. All later audits correct orientation and recover the established 0.553346 genuine-reference floor.

## Compatibility and validation

Legacy API booleans map explicitly: true → low, false → off. Invalid values fail validation; string `off` never
passes through a truthiness check. The browser migrates legacy widget values and leaves phone style/seed untouched.
Tests cover normalization, defaults, validation, unchanged Low hash, stage order, and High's protected pixels.
`scripts/preview-flux2-klein9b-attractiveness.py` reproduces the comparison without queuing diffusion.

Validation completed: all 135 project Python tests, browser-widget migration tests, the focused live Upgrade
verifier, and the full project verifier passed. The live 3090 worker exposes the three levels with Low/default,
phone/default on, and serves the migration extension. These image comparisons replay saved raw renders;
they are not newly sampled end-to-end diffusion runs.
