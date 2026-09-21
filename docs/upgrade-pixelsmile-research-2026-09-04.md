# PixelSmile: approved download and isolated pilot

## Current state, 2026-09-04

Mitch explicitly approved: **"download whatever you want"**. The prior download
blocker is resolved. No new character LoRA training remains a hard constraint.
Downloaded author revision `c9a15a2f544f1af6c3daa38800f54388099bb21a`, file size
849543736 bytes, with the previously reviewed SHA256. It is now installed at
`ComfyUI/models/loras/pixelsmile/PixelSmile-preview.safetensors`. Receipt:
`work/vendor/PixelSmile/verified-download.json`. No dependencies were changed.

The initial test uses genuine `val_02_body_mirror_sleeveless.jpg`, SHA256
4b32845393fbcbf6ea0ca80068c48af10db52bc81909dba9638370bc7ee0a622. It is already
square, so the author's 512-input/1024-output layout can be tested without
cropping, stretching, or a synthetic character-LoRA parent. This is a mechanism
pilot, not a substitute for the required house/canyon/genuine-third validation.

### First live result and one controlled diagnostic

Job `2d9b1307-d5ba-418b-a553-c33a8650f5ef` completed in 147.930 seconds.
The runtime confirmed all 720 layer patches, conditioning `[1,344,3584]`, and
one reference latent `[1,16,1,128,128]`. Observed 3090 use reached 23637 MiB;
4070 was idle at 249 MiB. The output, graph, evaluation and comparisons are in
`work/upgrade-source-faithful-20260903/pixelsmile-genuine-mirror-s05` (raw PNG
under the matching ComfyUI output subfolder).

Full output, face comparison and thumbnail were visually reviewed. Score 0.5
does not pass: eyes look enlarged/different, the nose narrower, the familiar
slight smile is replaced by a serious/pursed expression, and the face is too
soft. Lips remain closed without visible invented teeth. Bathroom composition
and phone-photo lighting broadly survive, but the phone lenses and shirt graphic
are redrawn. Hair is softer, not a demonstrated realism improvement. No obvious
face cutout/halo is visible. This is a single-person scene, not a crowd test.

Against the other five genuine photographs, likeness falls from source
0.797263 to candidate 0.328812. Pose delta is 3.359 degrees and the maximum
normalized iris-coordinate delta is 0.044982. These support the visual
identity/expression rejection; they are not the sole acceptance criteria.

The sole controlled diagnostic keeps source, seed, 50 steps, all models, adapter
strength, schedule and output dimensions fixed, changing only expression score
0.5 -> 0 (plus the save prefix). It tests neutral reconstruction drift versus
the confident expression direction. Score zero still runs the trained adapter
and generates a neutral edit; it is NOT an implementation of beauty Off. Exact
baseline graph and output checks guard this comparison. Job
`cae799eb-ec2b-4a4e-a52d-d277b0bc7c6f` was submitted to 3090/8188 after both queues
and GPUs were inspected. No character training, identity LoRA, photo upload,
production promotion or extra processing stage was introduced.

### Completed neutral control and decision

The score-0 control completed successfully in 139.590 seconds. Raw PNG SHA256:
`1248160474c4c8c603940fc7d0855140c5888f478c3569557a30df773da3d761`.
Manifest SHA256: `f3e9e6fa16c2d792aab0ccf29b6e98ef7a68b739198ab0851cfb70d9a9d73f27`.
Evaluation is under `pixelsmile-genuine-mirror-s00/evaluation`; all original
manifests, PNGs, audits and histories are preserved. Runtime reports the target
direction as `confident` with score 0; the blend endpoint is exactly neutral,
as verified by the CPU tests. It does not mean the target direction was applied.

Full image, full-frame side-by-side, face crop and thumbnail reviewed: the control
retains the same substantial eye/nose identity changes, serious rather than
source-smiling mouth, softened hair/skin and redrawn phone/graphic details.
Body, room composition and overall lighting broadly survive; no obvious face
paste seam. No invented teeth. A younger/smoother appearance is not accepted
as a recognizable better-looking result. The first candidate's failure was not
resolved by neutral conditioning.

| Genuine-reference diagnostic | Source | Confident 0.5 | Neutral 0 |
| --- | ---: | ---: | ---: |
| Five-reference centroid likeness | 0.797263 | 0.328812 | 0.365971 |
| Max pose delta from source, degrees | 0 | 3.359087 | 2.894131 |
| Max normalized iris-coordinate delta | 0 | 0.044982 | 0.058568 |
| Mouth opening ratio | 0.005266 | 0.012293 | 0.013011 |

Decision: **reject this local configuration; not promoted**. The sole refinement
is exhausted. Do not start a score/seed grid or run the required three cases on
a mechanism that has not passed the first genuine-photo test. Both queues are
empty after completion; the 4070 remains unchanged. The six protected production
Low/main/High/gaze/UI/workflow hashes still match the pre-pilot values. Only the
experimental node registration, test scripts and documentation were added here.

Causal conclusion is limited: identity drift occurs even at the neutral endpoint,
so the confident-direction strength is not its sole cause. The test does not
separate trained-preview behavior from FP8/vision-preprocessing differences, and
does not prove that an existing character LoRA is necessary. No direct claim
about the full BF16 author pipeline follows from this Comfy result. Any return
to this model should first resolve author-backend parity, not add a face repair,
another beauty prompt or more strength settings. The author paper explicitly
includes both close-up and full-body source photographs; do not invent a
headshot-only training explanation for this failure.

The download/test permission is handled. The broader stronger-High, realistic
whole-frame, three-photo objective remains unfinished; this experiment is not
a new production checkpoint.

### Pilot research gate

- Genuine original -> EXIF-aware LoadImage -> whole-frame Lanczos 512 square.
- Same source -> image-conditioned Qwen prompt encoding, interpolating the
  author's neutral/confident instructions at score 0.5; exact shape/mask checks.
- Same source -> Lanczos 1024 square -> Qwen VAE -> one reference-latent slot.
- Qwen Edit 2511 FP8 mixed -> only PixelSmile preview strength 1.0 -> positive-only
  guider -> 50 Euler steps with the published dynamic/terminal sigma schedule ->
  native whole-frame decode. Seed 42, no Turbo, masks, restoration or postprocess.
- Identity prediction comes from the published same-identity/ArcFace-supervised
  expression training plus grounded image and native reference-latent paths;
  not from a prompt name, generic img2img, source-face pasteback or style reference.
- Released file has 1440 matrices / 720 layer pairs, rank 64, across the expected
  attention and feed-forward targets. There are no stored alpha tensors. Use the
  author inference loader's matrix scale, not the training example's alpha/rank
  factor as an invented extra multiplier. Header shapes must match every base
  target; the runtime node refuses missing patches, stacking or unexpected scale.
- Known implementation differences remain explicit: local FP8 mixed inference
  and Comfy's native bilinear vision interpolation versus author BF16/bicubic.
  It is a compatible local backend experiment, not a bit-identical author replay.
- RTX3090/8188 only. Both queues and GPUs were inspected. The 20.5 GB base plus
  9.4 GB encoder require Comfy offloading on 24 GB; no simultaneous-residency claim.
  Existing Qwen runs on this worker establish practical offloading feasibility;
  runtime and memory still need measurement for this adapter.

The five CPU node tests pass (blend endpoints, invalid inputs, shape/mask guards,
schedule endpoints, unsupported layout/model rejection). An owned-idle primary
reload exposes the new experimental node; primary PID 38400 -> 5232, secondary
PID 44164 unchanged. Reload evidence: `pixelsmile-reload-20260904-100953` under
the experiment work directory. Public graph and production Low/High unchanged.

Acceptance: native full-frame and face/thumbnail review, source pupil/head/mouth
measurements, and recognition against the other five genuine photographs. The
input original is excluded. No acceptance on similarity alone. Require more
appealing closed expression with recognizable identity and plausible texture;
record background, phone/hand/clothing distortions. One controlled refinement
maximum before deciding this mechanism; no strength/seed grid. Genuine phone
appearance is inherited, not an active Klein phone LoRA inside Qwen.

The following sections preserve the earlier research/approval history.

User clarification, 2026-09-04: no new character LoRA training; prefer no character
LoRA anywhere in the workflow, allowing the existing one only if necessary for
the best result. PixelSmile is a general expression adapter, not a character
LoRA. This distinction does not confer download approval. A PixelSmile pass
over an upstream Mitch-LoRA render must not be labeled character-LoRA-free.

The stronger-High objective is still open. PixelSmile is a distinct hypothesis
for the persistent eye/brow/smile-expression problem, not a proven beauty fix.
No adapter, dependency or repository has been installed; no workflow has been
built or queued, and no photographs have been uploaded.

## Evidence and mechanism

[The author repository](https://github.com/Ammmob/PixelSmile) identifies
Qwen-Image-Edit-2511 as its base and offers preview weights. The matching local
base `ComfyUI/models/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors`
exists, but a filename match alone does not establish inference parity.

[The paper](https://arxiv.org/html/2603.25728v1) describes same-identity expression
training with an ArcFace identity loss and expression objectives. This is the
reason to test identity retention, not a claim of an inference-time face lock.
The input photograph reaches the image-conditioned prompt encoder and the
Qwen edit reference-latent path. There is no separate identity-photo embedding
at inference. Expression strength interpolates neutral and target text
embeddings; it does not blend source RGB or transfer another person's face.

The [author inference implementation](https://raw.githubusercontent.com/Ammmob/PixelSmile/main/pixelsmile/infer.py)
uses a 512x512 input crop, 50 steps, seed 42, BF16, `score_one_all`, and no classifier-free
guidance (`true_cfg_scale=0`). It includes a `confident` expression category.
The [conditioning code](https://raw.githubusercontent.com/Ammmob/PixelSmile/main/pixelsmile/linear_conditioning.py)
has now been read in full: `score_one_all` interpolates the entire neutral/target
embeddings and returns the target mask. It assumes compatible embedding shapes;
the mask/sequence behavior must be checked before any ComfyUI adaptation.

## Download requiring approval

[PixelSmile-preview.safetensors](https://huggingface.co/PixelSmile/PixelSmile/blob/main/PixelSmile-preview.safetensors)
is approximately 850 MB, published under Apache-2.0. Expected SHA256:

`9bb2f7981e8cd59a5d6e31c2ca08cc0961ac46c267b81af9bce7f8d542ca319a`

The author calls this a preview, not stable weights. Approval should cover only
this adapter and an isolated local test, not dependency upgrades, replacements,
new base downloads, hosted services or production changes.

## Unfinished research gate

- Verify weight keys, rank, exact loader/base compatibility and actual VRAM
  requirements. Existing local FP8 inference differs from the author's BF16.
- Inspect the live nodes and preserve the Upgrade 3090/8188 lock. Check both
  GPUs and queues immediately before any authorized generation.
- Compare author conditioning and scheduler behavior with the local graph.
  The author-linked community implementation is not automatically trusted.
  Its example uses Lightning/8 steps and square resizing; those differ from
  the author's non-distilled baseline and may alter aspect ratio.
- Do not patch or downgrade the existing diffusers/torch environment to match
  the author's requirements. Any required new dependency needs approval.
- Establish trained resolution/aspect expectations before adapting the
  author's 512 crop to a whole photograph. No silent aspect stretching,
  face pasteback, extra beauty LoRA or unsupported identity stack.
- Inspect closed lips, pupil focus, source head direction, skin, hair and
  whole-frame integration, alongside genuine-reference similarity. The
  category `confident` does not guarantee the user's desired closed smile.
- Test one minimal mechanism, with at most one controlled refinement before
  deciding whether it works. No expression-strength or seed grid.

This could address expression; bone structure, skin polish and universal
Off/Low/High behavior still need independent evidence. The gate is **not passed**.

## Alternatives checked, not selected

The [Klein face-restoration listing](https://huggingface.co/happyinhappy/flux2-klein-face-restore-lora)
is a model card without public weights, so it is not an available local test.
[BeautyGRPO](https://github.com/vivoCameraResearch/BeautyGRPO) requires
FLUX.1-Kontext-dev, a different uninstalled base. Neither warrants an unapproved
download, hosted upload or installation.

The desired canyon expression reference remains unconfirmed: the neutral-colored
clipboard image versus the warmer original. Do not silently substitute one or
claim this ambiguity caused the failures.

## Offline compatibility diagnosis (subsequent goal continuation)

Previous turn classification: **progress** (closed and documented the failed
three-case composition, validated evaluators, identified this new trained
adapter). Download approval has not arrived. This continuation did read-only
research and CPU diagnostics, not an authorized download or model inference.

Current Comfy revision is `b78cec879b9460d5cb25228a83a942fb78d2cd24`.
Both live queues were empty; 3090 memory was 11941 MiB, 4070 249 MiB. No cache
release, process restart or job submission occurred. These observations expire;
recheck immediately before an authorized run.

The live primary API exposes Qwen Edit Plus, the expected base/encoder/VAE,
model-only LoRA loading, ConditioningAverage, AuraFlow sampling and KSampler.
The adapter remains absent. Reading only the local base header confirms the
2511 `__index_timestep_zero__` marker and all 12 target module types in the
[author's example training config](https://raw.githubusercontent.com/Ammmob/PixelSmile/main/pixelsmile/configs/example.yaml),
each across 60 blocks. That example config specifies rank 64/alpha 128; it does
**not** prove the released adapter uses those values. Its actual key coverage,
rank, alpha and successful patch loading remain unverified.

`scripts/audit-upgrade-pixelsmile-compatibility.py` completed on CPU, without
CUDA initialization, weights loading, photo reads or network access. Evidence:
`work/upgrade-source-faithful-20260903/pixelsmile-compatibility/audit.json`.

### Conditioning and reference checks

Offline tokenization gives equal-length neutral/confident instructions (only
the expression token changes). Installed ConditioningAverage matches the
author's full-embedding blend within 1.2e-7 on tiny equal-shape test tensors;
it preserves the target reference and mask objects. Thus a community package
is not inherently necessary for a score between 0 and 1, **provided** actual
multimodal shapes, masks and source references agree. They still require a
runtime check. Unequal sequence lengths silently truncate the neutral input;
that case is not approved. The UI also limits this node to interpolation, not
scores above 1. Neutral score 0 is a neutral-expression edit, not Off/source-copy.

The [author's diffusers patch](https://raw.githubusercontent.com/Ammmob/PixelSmile/main/scripts/patch_qwen_diffusers.sh)
addresses a mask shortcut in that pipeline. It is not evidence that Comfy's
separate implementation needs patching. No such patch or dependency change
was made.

### Corrections to a naive port

1. **No CFG means Comfy CFG 1, not 0.** The inspected Comfy sampler uses the
   positive prediction alone at 1; 0 selects the negative prediction. The
   author's `true_cfg_scale=0` instead disables the negative branch.
2. **512 is input preprocessing, not necessarily output resolution.** The
   author passes a cropped 512 input and omits output dimensions. The current
   [Qwen pipeline](https://raw.githubusercontent.com/huggingface/diffusers/main/src/diffusers/pipelines/qwenimage/pipeline_qwenimage_edit_plus.py)
   derives approximately 1 MP output from aspect ratio (1024 square here).
   The author also pre-encodes prompts with that original input; Comfy's Edit
   Plus node rescales its vision input to approximately 384 square. Therefore
   using the shipped Comfy node unchanged is not exact encoder parity.
3. **Shift 3.1/simple is not the author's schedule.** The published
   [2511 scheduler config](https://huggingface.co/Qwen/Qwen-Image-Edit-2511/blob/main/scheduler/scheduler_config.json)
   uses dynamic exponential shifting and terminal stretch to 0.02. Applying
   the documented [scheduler equations](https://raw.githubusercontent.com/huggingface/diffusers/main/src/diffusers/schedulers/scheduling_flow_match_euler_discrete.py)
   at 1024 square/50 steps gives mu 0.693548, equivalent pre-stretch rational
   shift 2.000803. Compared at 50 steps, constant shift 3.1 differs by up to
   0.120303 in sigma and ends at 0.059501 before zero, not 0.02. This analytic
   comparison is not execution of the author's scheduler. Do not describe
   the community Lightning/8-step workflow as a matched author baseline.

The training config and resize helper use square crops. A square canyon pilot
can preserve its entire frame while matching this input layout, but whole-frame
house/third aspect generalization is still unproven. No face pasteback or crop
is silently authorized for those images. Phone rendering would be inherited
from the upstream input, not a compatible active Klein phone LoRA inside Qwen.

Next decision remains approval to acquire the adapter, followed by exact loader
and encoder/scheduler validation before a single local pilot. Do not launch
another adapter-free Qwen beauty test or reopen closed geometry/strength sweeps.
The full three-photo High and public integration remain incomplete.

## Blocked audit: awaiting adapter download approval

The same approval condition has now persisted across three consecutive goal
turns: the initial download request, the offline compatibility continuation,
and this revalidation. The previous turn was progress (concrete tokenizer,
model-header and conditioning tests plus scheduler/encoder differences). This
turn is not a verified wait: both live queues are empty, the adapter is absent
from disk and both live LoRA lists, and no inference process is being awaited.

No approval has arrived. The existing local approaches are already preserved
as failed or insufficient; additional adapter-free mocks cannot establish
PixelSmile quality or finish the three-photo objective. Actual weight-loading
and visual validation require the proposed download. Mark the goal blocked,
not complete, until Mitch approves that approximately 850 MB adapter download
and isolated local test or supplies different direction. Do not infer approval
from an automatic goal continuation.

Fresh checks still match the protected Low/main/High implementation hashes.
No production, GPU cache, dependency, model or image changes were made during
this revalidation. All previous failure evidence remains intact.
