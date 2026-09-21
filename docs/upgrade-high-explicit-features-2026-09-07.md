# Explicit-feature High: completed, rejected for insufficient change

Mitch's verdict on source / BeautyGRPO256 / BeautyGRPO512 was "all of them look
about the same". The trained-retouching route is closed as insufficient High
differentiation. Nothing from that route is promoted.

## Diagnosis, not a retrospective excuse

The recent refined prompt explicitly preserves natural eye shape and cheek
width. It tests limited expression/texture changes, not the requested stronger
eye/cheek morphology. Earlier Klein and Dev experiments did allow morphology;
their identity/realism failures remain valid and those routes remain closed.

The final controlled comparison used the already-completed adapter-OFF
base-Kontext canyon control retained likeness0.751564 versus source0.753158,
but it used that restrictive prompt. Change only its text to permit more open
relaxed eyelids, natural well-shaped brows, leaner cheeks, a defined jaw and a
warmer asymmetric closed-lip smile. Preserve pupil focus, head direction, nose,
hairline, forehead height, body, framing and lighting. No beauty adapter, character
adapter, mask, face replacement, restoration, new model or extra processing.

This is one explicit editing-policy refinement, not isolation of individual
adjectives or proof that a stronger prompt always works. No further wording,
strength or seed sweep if it fails.

## Research gate

- Baseline: `kontext-canyon-adapter-off-control`, successful job
  `c3aa6628-6003-41fb-ae14-6afb3894c75d`; raw, graph, source and six genuine
  reference diagnostics are saved and pinned.
- Source: the latest user-supplied693x701 canyon image; provenance unknown,
  possibly synthetic. It is an edit source, never a genuine identity anchor.
  Existing uniform-contain1024-square staging with6px edge padding is unchanged.
- Conditioning: LoadImage -> native Flux VAE -> ReferenceLatent appended to
  positive text conditioning. Kontext jointly attends the source latent and
  generated image. No separate face embedding. Identity preservation is a
  hypothesis grounded in trained character-consistent editing and the successful
  local source-fidelity control, not an identity lock.
- Primary evidence: the [BFL dev model card](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)
  explicitly supports instruction editing and character reference without
  finetuning. The official installed `flux_kontext_dev_basic.json` template is
  the native graph's source. Pro/API-only guarantees are not substituted for
  local dev behavior.
- Compatibility: existing originalBF16 Kontext, official CLIP-L/T5FP16, exact
  Flux AE; all hashes verified by the runner. Native T5 minimum256 is deliberately
  retained from the control. No512 correction is bundled into this comparison.
 28Euler/simple steps, embedded guidance2.5, CFG1, seed42, full denoise,1024square.
- The standard BeautyGRPO loader at strength0 returns the base model without
  loading its weights; no active LoRA. Phone appearance comes from the source,
  not a smartphone adapter. This is not the public Phone-ON Upgrade pipeline.
- RTX3090/8188 lock, both worker queues and both GPUs checked before submission.
  Only exact latest-owned successful cache may be reused through normal Comfy
  memory management. No restart, free, queue interruption or4070 generation.

## Acceptance

The edit must be visibly more useful at ordinary photo size, with recognizable
identity and attractive rather than generic eyes/closed smile. Reject absent
shape change, puffiness, invented teeth, head/pupil drift, hairline damage,
artificial skin or a broken scene. Review full size, face crop and thumbnail;
six genuine reference scores are diagnostics, not attractiveness judgments.
One successful canyon pilot still does not establish three-photo/public-node
acceptance. Off/Low and production defaults remain untouched.

## Execution

The reviewed prompt fits native T5 conditioning at166 tokens including EOS;
no truncation or512-token option node is introduced. Prepared graph comparison
shows exactly the node8 text and node14 output-prefix changes. Runner SHA256:
`db02b29d0675e2e75a461be568be1027013189a7aabd5b767549b08a8c1c4ba2`.

Submitted once on8188 as `8c3dfee8-df53-4386-85e3-210e257b0690`, with no node
errors. Fresh source/model checks and both GPU/queue checks passed. The exact
owned512-test cache was reused normally. The job completed successfully in
69.372 seconds. Eight focused offline regression/safety tests pass.

## Result: no meaningful High differentiation

Source likeness against six genuine references is0.753158; the base fidelity
control is0.751564 and explicit High is0.755352. Maximum source-pose delta is
0.060013 degrees and normalized iris-coordinate delta0.019524. These are
diagnostics, not proof of identical gaze or improved attractiveness.

Main and independent reviews of the raw1024 image, matched face crop, full-frame
sheet and thumbnail agree: eyes remain similarly hooded, brows/cheek/jaw shape
are essentially unchanged, and the closed asymmetric smile is not noticeably
warmer. Forehead creases and fine dotted skin remain. Likeness, hairline, head
angle, body and canyon integration are retained, with no visible teeth or new
face halo. Preservation succeeds; the requested stronger beauty edit does not.

Raw output SHA256:
`4b3be05df339961dd2261869e70cafba44c9f7b544b143bf72c23498d1e4422f`.
See the [saved visual review](../work/upgrade-high-20260907/kontext-canyon-explicit-high/VISUAL-REVIEW.md)
and [face comparison](../work/upgrade-high-20260907/kontext-canyon-explicit-high/evaluation/source-candidate-face.jpg).

This closes the one explicit-feature base-Kontext refinement. Do not run another
prompt, strength or seed sweep or reinterpret the small recognition-score gain
as a beauty result. This does not prove that all local editors are incapable of
the task; it establishes failure of the tested recipes. No candidate qualified
for three-photo expansion or public-node integration. Stronger High remains
unfinished; production Low/Phone ON/Turbo OFF are unchanged. No further jobs or
automatic follow-ups are queued.

## Alternatives screened in this turn

- [Klein Face Restore](https://huggingface.co/happyinhappy/flux2-klein-face-restore-lora):
  author explicitly has not released weights and excludes jaw-slimming/eye-size
  beautification from the intended task. No installation.
- [NNSG-Diffusion](https://github.com/LisaLy123456/NNSG-Diffusion): matching-title
  repository is README-only, revision2ac94c80aa1b32962b4e35babed0cc56642327d2.
  No implementation or required prototype database. Its
  [paper](https://arxiv.org/html/2503.14402v1) describes structural guidance but
  does not establish exact photorealistic Upgrade behavior. Do not equate its
  reconstructed3D identity metric with ArcFace likeness.
- [3DFACENet](https://github.com/Oliver-YX/3DFACENet): released geometry research
  components, but the inspected BFM path renders224px faces with optional mask
  compositing. Not a verified native whole-photo solution.
- [WithAnyone.Ke](https://huggingface.co/WithAnyone/WithAnyone): released editing
  preview, distinct from previously tested1.0 T2I. The
  [author editing implementation](https://github.com/Doby-Xu/WithAnyone/blob/5297f1dfacc0beb2ed870738791a9279f596119c/gradio_edit.py#L360)
  blurs source faces then regenerates them from ArcFace identity. It removes the
  source pupil/expression detail without an exact corresponding control, so it
  fails this workflow's source-preservation/host-replacement gate. Not tested,
  not proven to fail all identity generation, and not installed in this turn.
