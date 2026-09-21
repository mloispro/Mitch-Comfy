# LivePortrait expression-control feasibility — research gate

Status: zero-motion control completed and rejected for visible detail loss. No production change,
no expression transfer performed or approved.

## Why this is being investigated

Native Klein prompt/reference variations either preserved the less-flattering expression or introduced
teeth/hair drift. Narrow 2D cosmetic warps have not reproduced the source expression, and stronger skin
retouch alone does not fix the smile/cheek relationship. An additional learned face-rendering stage is
therefore eligible for a bounded test, but must not degrade the existing good whole-image render.

## Inspected implementation and compatibility

- Official source: https://github.com/KlingAIResearch/LivePortrait, pinned locally at
  `9b294b3d0536135442ea73cb01e6cb3ca7029dd3`, sparse source checkout in
  `work/vendor/LivePortrait-code`. The initial full clone was cancelled to avoid unnecessary demo media.
- Read the official wrapper, human image-driving pipeline, model/config files and relevant crop/pasteback
  functions. Model card/weights: https://huggingface.co/KlingTeam/LivePortrait.
- Human base uses appearance F, motion M, learned warper W and SPADE decoder G, plus optional stitching S.
  Network input is256x256; the configured decoder outputs512x512. This distinction matters:512output
  does not guarantee retention of the source's fine skin/hair detail. Main weights total about520MB.
- Author crop:106landmarks,512square crop,scale2.3,vertical offset-0.125,rotation correction enabled,
  downsample to256 with area interpolation. Use the already installed genuine `buffalo_l` detector and
  106-landmark model with the author's `crop_image`; the separate203-landmark model is unnecessary for
  the initial zero-motion core test, which does not use eye/lip scalar retargeting.
- Core imports succeeded with the existing local runtime:torch2.12.1+cu130,numpy2.2.6,OpenCV4.13.0,
  scipy1.15.3. These differ from the author's old pinned environment; a float32 forward pass subsequently
  succeeded without changing dependencies.
  Do not install upstream requirements over ComfyUI or change its CUDA/PyTorch stack.
- This is a standalone author-core feasibility test, not an invented Comfy graph or a registered node.
  If it passes, node/API integration will require its own live validation. No Turbo, LoRA or sampler
  alteration is involved in this test. Preserve the Upgrade3090lock and inspect both cards/queues first.

## Actual conditioning mechanism

The accepted generated raw photograph is the **edit target/appearance source**, not a genuine scoring
reference. Its aligned crop enters F to form a3D appearance volume, and M to estimate canonical points,
pose, scale, translation and expression. Zero-motion reconstruction passes identical transformed source
keypoints to W's source and driving slots, then G decodes. No other face enters that control.

For a later expression-only test, the original scene source would supply **expression coefficients**
through M, not appearance pixels/feature volume. The candidate's canonical face, pose, scale, translation
and appearance stay the source of the reconstructed face. Genuine held-out photographs remain the only
identity scoring references. This is learned animation with source appearance, not identity embedding,
face swap or proof of an identity lock.

The author's regional-control documentation explicitly supports `exp` without pose transfer, but warns
that absolute image driving may leak identity. Relative image driving adds motion relative to a canonical
expression; it is not automatically an exact replacement of the current smile. Inspect and record this
choice rather than confusing the two modes. Source:
https://github.com/KlingAIResearch/LivePortrait/blob/main/assets/docs/changelog/2024-08-19.md.

## First control and acceptance

Download only the human checkpoint files needed by the inspected core, pin the HF revision, verify their
publisher-provided SHA256 hashes, and force tensor-only checkpoint loading. Run one zero-motion
reconstruction of the existing canyon raw at the author crop settings. Save raw crop, decoded crop,
round-trip sampling control and full-frame pasteback, along with exact models/config/hardware metadata.

Compare against the unchanged raw at native size and thumbnail: skin/hair texture, eye/lip shape,
apparent age, identity, forehead/head direction and any face boundary, cutout or halo. Score against
all six genuine references; report crop SSIM and facial detail loss as diagnostics. A centroid below0.70
or a drop over0.03 from the raw, conspicuous softness, altered eye/lip geometry, or a visible seam rejects
this mechanism before any expression transfer. Do not hide reconstruction loss with face restoration,
selective sharpening, source-face blending, or another generation stage. Zero motion passing would
only permit one expression test plus at most one controlled refinement, not establish final quality.

## Result

Verified five human checkpoints against publisher LFS SHA256 at HF revision
`82a4fa6735ca58432b6ce39301b4b9ee066dea47`; tensor-only loading succeeded. Whole control, including
genuine-reference CPU scoring, took6.95seconds; peak allocated GPU memory1.20GB. Initial face detection
at0.15 admitted ambiguous detections; standard0.5 detected the one intended face. No ambiguous selection
was silently accepted.

Raw identity0.751794; exact zero-motion0.754952; stitched zero-motion0.757601. Both preserve all pixels
outside the author's pasteback mask. Exact zero-motion crop SSIM0.938968; stitched0.872810. These
passing scalar diagnostics do not override the visual result: native-size comparison clearly loses fine
pores, stubble, eyelid definition and individual hair strands. The face is softer than its surrounding
frame even before any expression change. The mechanism is rejected for this still-photo workflow.

Artifacts: `work/upgrade-source-faithful-20260903/liveportrait-zero-canyon/`, including sampling controls,
face/full comparisons, input/decoded crops and full audit. The downloaded source/weights remain labeled
evaluation-only, outside production model directories, for reproducibility. Do not retest this same
configuration or add restoration/blending to hide its reconstruction failure.
