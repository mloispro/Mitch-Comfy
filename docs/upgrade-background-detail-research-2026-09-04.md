# Protect the better source-like person; repair only background detail

Status: pilot and sole explicit-scene refinement both failed. This background
repair route is closed; no production promotion or further parameter grid.

The earlier source-only Base9B outputs were inspected again at native size.
House and canyon retain more of the preferred source eye/expression presentation
than the four-reference native base, but their backgrounds are visibly soft.
The reduced-portrait-detail experiment did not resolve that tradeoff. This test
addresses the observed background failure directly; it is not another masked
face beautification attempt or a claim that segmentation creates identity.

## Research gate and conditioning

The [official Diffusers Klein inpaint implementation](https://raw.githubusercontent.com/huggingface/diffusers/main/src/diffusers/pipelines/flux2/pipeline_flux2_klein_inpaint.py)
provides a Base9B BF16 source/mask/reference example. Its source is both an
initial latent and first reference; an optional additional image is second.
The noised source is restored outside the edit mask at each sampling step.
The already-tested local adaptation uses the same ordered source-first layout:

1. Audited source-faithful native house image, full-frame resized to1280x768,
   enters LoadImage -> Flux2 VAE. This is an edit target, not a genuine identity
   photograph. Its latent supplies both first ReferenceLatents and masked start.
2. Genuine training photograph07 enters LoadImage -> bicubic1MP/16px scale ->
   Flux2 VAE -> second ReferenceLatents, on both positive/negative CFG branches.
3. CPU human silhouette enters LoadImage -> ImageToMask -> SetLatentNoiseMask
   only. White means regenerate background; black preserves person latents.
4. The same source latent is independently decoded as a codec-only control.

Identity remains supported by the genuine-photo-trained Base9B V3 step1600 LoRA
at0.9 and genuine portrait, with the source person's latents protected. It is
not a mask, host-face swap, source-image-only identity claim or face restoration.
The [BFL model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
and [training documentation](https://docs.bfl.ai/flux_2/flux2_klein_training)
support the base editing/character-LoRA mechanism. Local training config and
dataset-lock verify Base9B,768/1024 buckets and13 genuine training images, with
held-out validation excluded from training. These support compatibility, not
an exact likeness or beauty guarantee. The upstream source-only house similarity
is0.691008; recognizability/beauty must be judged visually, not dismissed by0.70.

Installed SetLatentNoiseMask, SamplerCustomAdvanced and KSamplerX0Inpaint were
re-read: mask passes into sampling and source latents replace the protected
region. Whole-image decoding can still change pixels. This is not pixel-space
compositing, and it is not a byte-exact person guarantee.

## Segmentation and fixed pilot settings

Use the already-installed `u2net_human_seg.onnx` with its inspected rembg CPU
normalization/prediction. Its MD5 matches the installed author's release pin:
`c09ddc2e0104f800e3e1bb4652583d1f`; SHA256 is
`01EB6A29A5C4D8EDB30B56ADAD9BB3A2A0535338E480724A213E0ACFD2D1C73C`.
No constructor/download path is invoked. [U2Net's author](https://github.com/xuebinqin/U-2-Net)
explicitly notes that the human model is not hair-accurate. It supplies a broad
silhouette, not strand-level matting or an identity signal. The mask uses>=26/255
support,9px protective margin and15px background-only feather. Every detected
person pixel is black. Full-size overlay/mask review covers hair/forehead/ear,
face/neck, coat/collar and frame edges; no visible subject area is left editable.
The protected band may retain a soft halo, which is an explicit failure test.

The existing verified masked graph is reused; only its edit target/mask and
background-specific text differ in purpose from the failed masked-face route.
Base9B actual BF16, unchanged Qwen3 mixed-FP8 encoder/full VAE, identity0.9,
Smartphone Snapshot v13 at0.25,50Euler/CFG4,Flux2Scheduler,seed8675416. One
1280x768 full-frame pilot. No crop/stitch, upscaler, polish, restoration, gaze
stage, new model, dependency change or production mutation. PhoneON/TurboOFF.
All required graph nodes are live on8188. Exact models and image bytes are
hashed at submission; both GPU queues,3090 lock, Forge and32GiB host headroom
are checked twice. No restart, automatic retry or other-task interruption.

## Acceptance before any promotion

First compare candidate against its codec control deep inside the protected
person (>=64px from editable support): meanRGB<=0.5/255,p99<=3/255 as leakage
diagnostics, plus explicit source-to-codec loss. Inspect face/pupil/lip/cheek and
hair preservation against resized input and genuine references. Scores alone
are not beauty acceptance. Review full image, thumbnail and head/collar borders
for blur bands, halos, cutout integration, lighting and noise discontinuities.

Background must gain visible real material detail, not just noise. Use fixed
unoccluded wall/branch crops and gradient/Laplacian diagnostics, but require
visual approval of straight seams, physical tapered branches and consistent
perspective. Failure to improve background or preservation closes the pilot
after at most one diagnosed refinement; no prompt/seed/strength grid. Success
still requires the same policy on canyon/genuine third and a coherent tested
Off/Low/High public implementation. This component is not complete High.

Prepared manifest SHA256 `2204825B75FFED259FD6DB0733BA11793F9FCAD7795A07BB493968729CB49B94`.
Reviewed mask SHA256 `6D86AC3A277ADEB245B1282212AE32665EFB1AADAAFC1015E9D093946DF655C9`.
Artifacts: `work/upgrade-source-faithful-20260903/background-detail-house-pilot/`.

The first preflight stopped before staging or submission: free host RAM was
about16GiB. The preceding portrait probe had completed and its exact saved
graph was still the latest primary owner. After two fresh dual-queue/ownership
checks, only that task-owned8188 cache was released through `/free`; no4070
mutation, worker restart, generation cancellation, output deletion or history
clearing occurred. HTTP200 was recorded. RAM then reached42.65GiB and3090
usage1191MiB. A subsequent fresh double-checked submitter passed all asset hashes,
live schemas and memory requirements and made its first and only prompt POST.
The response contains job `a604aade-2954-4a16-aba0-bfb07dc141a2`, queue2, no node
errors. Saved cache-release and submission intents distinguish this from a retry.

Fixed house detail ROIs, declared before generation review: wall normalized
xyxy[.04,.06,.24,.36], branches[.76,.04,.97,.39]. Both must lie at least98% within
fully editable background; no outcome-dependent crop selection.

## Completed result and mechanism diagnosis

Job `a604aade-2954-4a16-aba0-bfb07dc141a2` completed in367.623seconds. The scoped
log verifies actual diffusion BF16, manual cast None. Executed native and codec
PNG graphs and all LoadImage hashes match. Native SHA256
`022F8FC9D62C5DA58052A687D6B66FA760AE4F12A3ABAAC9286739037B0BFD99`;
codec SHA256 `37CD92FCC335704A531985081C74758448A330D4BA535C618C9D7B7E690ECE9F`.

Full-size, face, thumbnail and fixed detail crops show an unacceptable result:
the house is replaced by a wooded waterfall/cliff scene, with a light blurry
halo around the person. More texture is not a valid detail upgrade. The preferred
source-like features mostly remain, but the person is darker/more contrasty.
Lips are closed with no visible teeth; skin/hair still need a finish.

Six-genuine similarity0.657611 versus resized input0.688587; source pose maximum
delta1.736183degrees. Person-core (>64px from editable support) versus codec
meanRGB9.61618/255,p99=24, well outside the predeclared0.5/3 limits. Source-to-codec
meanRGB3.20723/255 is separately recorded. Wall gradient rises9.48->80.79 and
branch-region gradient33.68->76.97, but these measure an invented scene, not a
successful repair. Both the scene and person-preservation tests fail.

The soft edit source and broad conditional material list did not anchor scene
semantics. The installed Flux2 VAE resolves to AutoencoderKL's standard Decoder,
which uses spatial GroupNorm and attention. Global decode interaction is a
plausible contributor to the person tone shift, not independently proven as its
sole cause. This run did not save final latents, so do not claim exact protected
latent equality from the RGB result. A single scene-reference refinement could
add the already-detailed original background as a third, composition/material
reference while preserving source/person mask, genuine identity, seed and
sampling. If pursued, save source and final latents as diagnostics, and retain
the same scene/halo/person acceptance criteria. No compositing or extra retouch
is justified by this failed output alone.

## Sole refinement submitted

The explicit-scene conditioning refinement is prepared at
`background-detail-house-scene-reference/experiment.json`, SHA256
`FC6AE95058CB48A67981EE6F5F2A3C427628D149C19571AFE7A6E6E4DD2DC699`.
It adds the actual audited public house `before-polish_00001_.png` as Picture3,
not as a genuine identity photograph. The full reference was visually reviewed:
it contains the desired siding, roof perspective and leafless-tree background.
Its existing face is explicitly excluded from the reference's intended role.
LoadImage -> bicubic1MP/16px scaler -> VAE -> third ReferenceLatents on both CFG
branches is the same extension already exercised by the previous three-reference
masked graph. BFL's native multi-reference editing supports this model input;
the exact source/genuine/background triple remains an experiment, not an
author-endorsed beauty/identity guarantee.

The source, genuine portrait, person mask, adapters, sampling, dimensions and
seed remain byte/config-identical to the pilot. Only the extra background
reference and its role-specific text change conditioning. Two SaveLatent leaf
outputs observe the already-existing source/final latents without feeding back
into sampling or decoding. This will separate protected-latent equality from
global VAE decode differences if the tone issue recurs. The source/codec, scene,
halo and likeness acceptance criteria are unchanged. No second refinement or
grid is authorized by this design. Recheck live queues and actual latest cache
ownership before submission; never reuse the earlier ownership assumption or
release another task's cache. No promotion or completed High is implied.

After fresh checks confirmed the same task's completed pilot was still the
latest primary owner and both GPU queues were empty, only its8188 cache was
released to recover the32GiB requirement. The separately recorded release
returned HTTP200. The guarded submitter then rehashed every source/mask/model,
checked live SaveLatent and other nodes, and made one prompt POST: job
`3cb18d51-fff0-4a5c-a757-8fbe272dc82f`, queue3, no node errors. Consult its actual
history; do not treat this static note as live status or resubmit.

## Refinement completed: route closed

Job `3cb18d51-fff0-4a5c-a757-8fbe272dc82f` completed in545.023seconds. Both PNGs
and both saved latent files match the prepared graph and reference hashes.
The native image, matched face comparison and thumbnail were reviewed. It still
replaces the house with a wooded rocky waterside scene and retains a conspicuous
pale/blur halo. Source-like eyes and closed lips largely survive, but person
tone darkens and skin/hair remain unfinished. No cosmetic finish was run on
this failed whole frame. More reference/prompt/mask/seed sweeps are not planned.

Native SHA256 `EC40604261C9AA80BB01BE6529CD0377EA7D25BAFA0EDD2C62021CCB926D7BCA`.
Six-genuine identity0.665583 versus resized source-faithful input0.688587; source
pose maximum delta1.348103degrees and closed-mouth ratio0.000450. These numbers
do not override the decisive scene and integration failures.

The saved128-channel,48x80 float32 latents resolve the preservation question:
all1333 black-mask cells have maximum absolute source-to-final error5.96e-8;
the845-cell deep-person region mean error is1.30e-10. Every protected channel
vector is within1e-5. Edited background mean latent difference is0.995988.
Yet protected person RGB differs from its codec control by mean8.12898/255,
p99=19. The mask preserved latents to numerical precision, not final RGB.
This supports the spatially coupled VAE-decode explanation; it does not isolate
which decoder operation accounts for every color difference.

Pixel audit SHA256 `36B07D44C86AEA5CF1E46DFF1913D10944CDC8C3CA0FDA6FB2EE296E94CDF82F`.
Latent audit SHA256 `57ECAF9DC6BF3EA6373F6632CC7C7A70C1B0200A2F9722E6B6AD72E5D729172E`.
Face audit SHA256 `9D57C28A87947E9B73A0EED25DFC587190040B73B09FD90A0C3197F71EAAF141`.
All failure artifacts and explicit review files are retained. Five mask/graph
contract tests and one synthetic CPU latent-diagnostic fixture pass; these are
implementation checks, not image-quality acceptance. Production remains unchanged.
