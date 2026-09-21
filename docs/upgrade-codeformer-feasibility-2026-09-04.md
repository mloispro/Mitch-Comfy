# CodeFormer feasibility: cleaner skin, not a complete High replacement

Status: house full-frame baseline and sole fidelity refinement completed.
The 0.7 result is a useful cleanup preview, but not an accepted stronger High.
The stronger 0.4 result is rejected as a High replacement. No production change
or three-photo success is claimed. Earlier sections below retain the sequence
of hypotheses and tests; corrected scoring and the final review follow them.

Observed failure: existing Upgrade Low/High retains coarse dotted skin and
synthetic facial texture. Repeated native edits and deterministic smoothing did
not produce a convincingly stronger beauty result. The already-installed
CodeFormer model offers a distinct learned reconstruction prior; no download or
installation is required. This is not proposed as a way to hide any failed
LivePortrait, Qwen or masked-native experiment.

The [author README](https://github.com/sczhou/CodeFormer#testing) describes a
quality/fidelity tradeoff: higher weight generally favors fidelity, lower weight
quality. It also explicitly warns that whole-image fusion can damage boundary
hair texture. The [author inference](https://raw.githubusercontent.com/sczhou/CodeFormer/master/inference_codeformer.py)
uses512px aligned RGB, normalization to[-1,1], the CodeFormer512/1024-codebook/
8-head/9-layer architecture, connections32/64/128/256, params_ema, and adain=True.
The whole-image example uses weight0.7; use that single declared weight initially.

The local model is `ComfyUI/models/facerestore_models/codeformer-v0.1.0.pth`,
SHA256 `1009E537E0C2A07D4CABCE6355F53CB66767CD4B4297EC7A4A64CA4B8A5684B7`.
Installed ReActor architecture sources were inspected. No custom node/model is
invented; inference directly uses the installed CodeFormer implementation on CPU.
Do not instantiate auto-downloading helper wrappers or use an upsampler. The
official five-point FFHQ512 template and affine alignment are used with the
existing local SCRFD five-point detector (a documented detector substitution,
not the author's RetinaFace default). Save input-alignment and restoration
separately so alignment loss is not mistaken for model improvement.

Conditioning: the input is the verified v5 Low house image, already derived from
the genuine-trained Klein character LoRA plus genuine portrait. CodeFormer
receives that face RGB only and has no separate identity embedding or reference.
Its fidelity connection may retain input structure, but it is not identity
conditioning or an identity lock. Test against six genuine held-out photographs;
compare whole input, aligned input and restored crop. No synthetic source is
counted as a genuine scoring reference.

Acceptance for proceeding beyond this feasibility check: a visibly cleaner,
more flattering yet recognizable face, closed lips/no invented teeth, preserved
eye direction and natural pores/stubble at full crop and thumbnail. A mere score
increase or smooth skin is insufficient. Reject waxy skin, generic identity,
distorted eye shape, false teeth, or no useful improvement. At most one controlled
weight refinement may follow a diagnosed result. No full-image composite,
background change, hair finish, additional gaze correction, live-node deployment
or three-photo success may be claimed from this cropped preview.

The separate live v5 hair-label validation retains the existing production
50-step PhoneON/TurboOFF recipe; this preview does not alter that running job.

## Aligned preview and next full-frame feasibility check

Weight0.7 CPU inference completed in3.00seconds. The first invocation completed
inference but its detector error occurred before saving. An identical-settings
rerun added failure preservation; this was not a parameter refinement. Artifacts:
`work/upgrade-source-faithful-20260903/codeformer-house-aligned-feasibility/`.
Full512 crop and thumbnail show cleaner, less speckled skin and softer, less
regular hair grooves; eyes are somewhat clearer. Some smoothing and roundness
remain, and the preferred source expression is not established.

SCRFD detects no face on BOTH original and restored512 crops. Diagnostic-only
128px gray padding resolves both to one face without modifying saved pixels.
The initial padded and fixed-input scores were later found to use incorrectly
oriented genuine references; they are superseded by the correction below.
Whole original Low is0.737938. These are distinct
alignment conditions and must not be conflated. Both mouths stay closed, and
paired padded pose differs by less than0.32degrees. Horizontal eye coordinates
change about0.0075; vertical redetection changes more. Source gaze and full-frame
quality still need testing. The small likeness drop alone is not a rejection,
given Mitch's explicit beauty/likeness preference.

Next: test the SAME saved restored crop through the inspected installed
FaceRestoreHelper pasteback, scale1, ParseNet-enabled blending, no background or
face upsampler. This is the author's restoration/fusion route as implemented in
the local ReActor fork, not a source-pixel face swap or native identity lock.
The helper object will use already-verified local ParseNet weights without its
auto-downloading constructor. Whole-frame identity, source gaze, mouth, texture,
boundary/halo and background changes must be measured and reviewed before any
further refinement or promotion. No new fidelity weight or final gaze correction
is bundled into this assembly test. This extension is motivated by the visible
aligned improvement, not by a passing identity score.

## EXIF scoring correction

Both follow-up evaluators initially omitted EXIF transposition. All six genuine
JPG references have nontrivial orientation tags (3 or 6). Consequently, their
scores did not reproduce the frozen control. The original aligned inference
script did transpose correctly, and the generated PNGs were unaffected.

Both evaluators now transpose every input consistently and assert that the
unchanged whole-frame Low reproduces 0.737937689. Existing reports and image
bytes are preserved. Corrected reports are in
`codeformer-house-aligned-feasibility/geometry-diagnostics-exif-corrected.json`
and `codeformer-house-full-frame-exif-corrected/audit.json`, under the usual
`work/upgrade-source-faithful-20260903/` root. The latter reads the saved result;
it does not rerun either inference or blending.

Corrected padded recognition: 0.746924 -> 0.708426. Fixed-input alignment:
0.745290 -> 0.705541. Full-frame recognition is 0.737938 -> 0.719649.
These alignment conditions remain separate diagnostics, not identity locks.
The full-frame source control also reproduces 0.657355.

## Sole fidelity refinement and full-frame review

Changed only CodeFormer's fidelity weight from 0.7 to 0.4, keeping the same
verified Low input, alignment, architecture, normalization, CPU inference,
AdaIN and scale-1 ParseNet pasteback. This tests whether stronger learned
reconstruction delivers the missing attractive result; it is not a seed or
model grid. Inference took 3.05 seconds. No additional gaze pass, upscaler or
background reconstruction was introduced.

| House output | Genuine-reference similarity | Mouth-opening ratio |
| --- | ---: | ---: |
| Low v5 CPU control | 0.737938 | 0.005630 |
| CodeFormer 0.7 | 0.719649 | 0.002522 |
| CodeFormer 0.4 | 0.670791 | 0.002666 |

Both keep closed lips without visible invented teeth. Horizontal pupil-position
errors against the source are 0.00044/0.00864 at 0.7 and 0.00548/0.01781 at 0.4.
Vertical estimates still differ; these are not perfect source-gaze locks.
The inherited head orientation already differs from the source before restoration.

Full-size, face crop and normal-size review: 0.7 visibly reduces coarse spots and
cleans the eye area, but does not restore the source's cheek contour, brows and
confident expression. At 0.4 the forehead and eye area look smoother and younger,
but brows become weaker, cheeks still look round, and texture becomes more
uniform. This is not a preferable stronger beauty result. Rejection is based on
appearance, not merely the lower similarity number.

The original background detail remains visually intact. Outside the head plus
64 pixels, both composites differ by at most 1/255 (mean 0.02466 and 0.02348/255),
owing to the inspected blending/quantization path. Do not call background pixels
byte-identical. No obvious new outer-head halo is visible, but the smooth face
versus sharper coat is a remaining integration concern.

Artifacts: `codeformer-house-full-frame-quality-refinement/` contains the 0.4
full image, source/Low/result comparisons and audit; image SHA256
`be41b166fb262b3984b84b0fd20c793c3f732ce9f48d1cae1013d0fe3446bbcc`.
The retained 0.7 full image SHA256 is
`1f6d69f5e18d314ec031d5f2aed4f702a46cffe94c380620b537396f2500f55a`.

Conclusion: learned restoration addresses texture, not the missing flattering
source geometry/expression. Neither result is promoted as High. No further
CodeFormer weight sweep, cross-photo success claim or automatic deployment.
The aesthetic question about the 0.7 preview has not received a specific reply;
Mitch's general preference for a stronger but recognizable edit remains in force.

Regression test `scripts/test_upgrade_codeformer_evaluation.py` passes across
all five relevant readers at EXIF orientations 1, 3, 6 and 8, and asserts that
reading does not change the file bytes. The read-only public-workflow verifier
also passes with the narrow live-v5 review status; production code/default
hashes remain unchanged by the restoration experiments.

## Input-stage diagnosis

The closed fidelity test does not isolate whether feeding already-retouched Low
causes restoration to reinforce artificial corner lifting, cheek lighting or
texture changes. Earlier deterministic-only removal of mouth lifting and cheek
highlighting helped a little but did not solve High; that work is not repeated.

One input-stage ablation now feeds the pinned native raw house render directly
to the same CodeFormer 0.7. The exact Low-control FFHQ affine is reused, so a
different face alignment is not bundled into the change. Same weights, RGB
normalization, AdaIN, CPU, 512 resolution and scale-1 ParseNet assembly. No new
weight, prompt, seed, source-face compositing, final gaze or upscaling stage.
The raw input was visually inspected. Identity still originates in the
genuine-trained Klein LoRA and native reference conditioning; CodeFormer itself
has no identity reference and is not being relabeled as one.

This is a diagnosis of stage interaction, not a claim that cleanup now controls
expression. Compare raw/Low and both reconstructed results at full size and
thumbnail, score the same six genuine EXIF-oriented references, and inspect
brows, mouth, cheeks, gaze, texture and whole-frame integration. If bypassing
Low still leaves the same failures, do not keep tuning this combination.

Completed with the fixed affine and weight 0.7 in 2.96 seconds. Full-frame raw
input similarity is 0.779115, direct-restored result 0.744679, versus 0.719649
for restoration after Low. Mouth-opening ratio remains closed at 0.001881.
Horizontal source-eye errors are 0.01116/0.02880; vertical differences remain.
Outside the head plus 64 pixels, maximum RGB error remains 1/255.

Full-size/crop/thumbnail review shows a cleaner face and more likeness retained
than the stacked version, but still the same tense brow and rounder expression.
It does not recover the source's preferred cheek contour or smile. Thus Low
stacking contributes to the likeness tradeoff but is not the root explanation
of the whole beauty failure. Do not tune the raw/Low-restoration combination
further or promote it as High. No production/default change or three-photo
validation is claimed.

Evidence: `codeformer-house-raw-input-ablation/` and
`codeformer-house-raw-input-full-frame/`. Full result SHA256:
`a4516ca63918a05dafd0cc1a5c28a7798d60d383e2de9fe07dcd2efd91c1e0e1`.
Its audit SHA256 is
`d2e30e9a9b9bccb7c93226fdee75cd040adb964b1cf27a38a0265259b5b99f6a`.
