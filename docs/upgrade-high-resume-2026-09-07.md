# Upgrade High resumed, 2026-09-07

Mitch explicitly resumed the full task. The 2026-09-04 experiment checkpoint is
preserved. No new character LoRA training; prefer no character LoRA throughout
the image lineage, using the existing one only when supported by results.

## Diagnosis and remaining experiment

Current High runs after the identical Low generation/finish. It protects lip
pixels and has no cheek-shape correction. Its mostly subpixel eyelid adjustment
and tonal treatment cannot reconstruct the smile/eye presentation lost during
generation. Low's fixed image-Y mouth lift and cheek highlight have already been
ablated with limited benefit. Prior 2D source geometry carries the tense shading
with the pixels and failed to produce a convincing stronger High; do not repeat
that strength grid. PixelSmile failed even at its neutral endpoint.

BeautyGRPO is a new pretrained retouching hypothesis, not proof of expression
improvement. [Author repo](https://github.com/vivoCameraResearch/BeautyGRPO),
[paper](https://arxiv.org/html/2603.01163v1),
[inference code](https://raw.githubusercontent.com/vivoCameraResearch/BeautyGRPO/main/src/inference/infer.py).
The trained dimensions include blemish removal, smoothing, texture, clarity and
identity. It does not document independent cheek/smile/eye attractiveness control.

## Research gate for first native pilot

Source: original genuine square mirror photo, EXIF normalized, entire frame
resized bilinearly to 1024 square (no crop/stretch); original excluded from the
five-reference identity score. No synthetic or character-LoRA ancestor.
Preparation uses PIL BILINEAR before staging a metadata-free PNG, matching the
author's antialiased downsampling. Comfy's tensor bilinear scaler is not used:
its downsampling differs visibly in fine texture. The original has EXIF
orientation 6; normalizing it keeps the subject upright, an intentional difference
from the author's EXIF-ignorant inference script.

Mechanism: source -> Flux VAE -> native Kontext ReferenceLatent appended to
positive conditioning -> denoiser attends source appearance plus output noise.
The identity prediction comes from the trained face-retouching adapter's
identity-preservation objective and Kontext's trained character-consistent edit
mechanism, not a text name, style-only input or generic img2img initialization.
There is no separate identity embedding at inference. Full denoise, one source,
no masks, face paste, restoration, character LoRA or phone adapter in this pilot.

Compatibility: author adapter revision 241d57903834ba55cb544b665686eb5d494b3dcf,
179400528 bytes, SHA256 23105cbd94fcd9f7b14d224dd28ce84cb5fa0f9bd5ba077cc0de27428e46c8a1.
Existing legitimate HF access permits original BF16 BFL Kontext at revision
24e9dedc4ef646698dc8eb4e18ae2cec3c9fea0d, 23802947360 bytes, SHA256
843a26dc765d3105dba081c30bce7b14c65b0988f9e8d14e9fbc8856a6deebd5.
Full precision T5 FP16 is also selected, SHA256
6e480b09fae049a72d2a8c5fbccb8d3e92febeb233bbe9dfe7256958a9167635.
Original BF16 Kontext, the adapter and T5 FP16 are now installed and verified
(`work/upgrade-high-20260907/models/verified-download.json`). Official Comfy
CLIP-L is installed and visible through the
live DualCLIPLoader: revision 6af2a98e3f615bdfa612fbd85da93d1ed5f69ef5,
246144152 bytes, SHA256
660c6f5b1abae9dc498ac2d21e1347d2abdb0cf6c0c0c8576cd796491d9a6cdd.
The existing extracted clip_l_fp16.safetensors was preserved unchanged.
Existing ae.safetensors matches the exact BFL Kontext VAE: SHA256
afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38.
Use native Comfy offloading on the locked RTX3090/8188; no dependency replacement.

Start from installed official template `flux_kontext_dev_basic.json`, subgraph
654c828f-2572-47e8-ba85-8a832c89b30c. Keep its VAE/reference/Euler/CFG1 structure,
with author 28 steps, embedded guidance2.5, seed42, LoRA1 and default author prompt.
For the square pilot the Flux shift1.15 matches the author's retrieved scheduler
config (base shift0.5 at256 tokens, max shift1.15 at4096; dynamic exponential).
The installed native loader consumes all684 adapter tensors as342 rank32 patches;
every target shape and packed attention offset matches the original BF16 header.
The preflight also exercises the actual native model_lora_keys_unet alias builder,
not only the theoretical Diffusers conversion table. Adapter metadata confirms
rank 32 / alpha 32 without RSLoRA, DoRA or per-layer scaling overrides.
Comfy's tabulated simple
schedule and CPU noise generator are recorded implementation differences.
The model is BF16, T5 is FP16; this is not a bit-identical Diffusers reproduction.
Native model/LoRA key coverage and live visibility must pass before generation.
The adapter preflight runs in a fresh process with CUDA devices hidden before
Comfy/torch imports; it verifies that CUDA remains uninitialized. Merely setting
Comfy CPU mode was insufficient because the attention capability probe touched
CUDA. This change affects the client preflight only, not either live worker.
Seventeen focused CPU tests pass for source preparation, adapter coverage and
submission safety, including immutable prepared-graph checks and exclusive
submission-intent creation to prevent duplicate concurrent submissions.

Acceptance: original/candidate full-frame, face crop and thumbnail; skin, real
stubble/hair, expression and pose/pupils, body/clothing/phone/background details;
five other genuine identity photos. One controlled refinement maximum. If skin
alone improves, count only that as demonstrated. Stronger High and three-photo
integration still require additional evidence. No unsupported promotion.

## BeautyGRPO author-settings result

The first full-precision native pilot completed successfully as
`52c67455-5c40-4618-94ac-9b12b6dfab58` in 77.264 seconds. It is recognizable and
preserves head/pupil direction and whole-frame integration without any character
LoRA. Likeness against five independent genuine photos is 0.756671 versus 0.817675
for the resized source; maximum pose delta 0.276144 degrees and eye-coordinate
delta 0.014745. All original-source references are excluded from scoring.

Visual review finds clearer eyes and modest hair/skin rendering improvement,
but cosmetic-looking dark eyelid rims, residual skin dots/lines and no stronger
attractive smile. It is limited retouching success, not completed High. All 342
adapter pairs loaded into 190 underlying packed parameters; the unused CLIP
projection warning does not affect Flux conditioning. Runtime is BF16 diffusion,
FP16 text and BF16 VAE.

The one prompt-only refinement completed as
`0e6bd4b8-a619-491f-beb7-6feb41eeea6c` in 69.300 seconds. It modestly improves the
closed-lip smile while preserving whole-frame integration, but dark eye rims remain.
Likeness is 0.748130, pose delta 0.319086 degrees and eye-coordinate delta 0.027789.
The smile-lift diagnostic rises to 0.044553 (source 0.033276; author 0.030792).
This is a candidate for fixed-recipe generalization tests, not production High.
No further mirror tuning or broad parameter sweep. Evidence is saved in
`work/upgrade-high-20260907/beautygrpo-mirror-author/` and
`work/upgrade-high-20260907/beautygrpo-mirror-expression-refinement/`.

Read-only diagnostics on the original problem sources find the latest canyon
clipboard is 693x701 with six-reference likeness 0.754768, distinct from the older
orange source. Its provenance remains unknown/possibly synthetic. The house
source is synthetic, 1680x1008, likeness 0.657355, with an already blurred background.
Neither is a genuine scoring anchor. Do not assume a preservation retoucher
repairs the house identity or creates absent background detail.

## Canyon generalization and text-conditioning diagnosis

The fixed refined recipe completed on the latest canyon attachment as
`2c7b50ea-9468-4ab3-bd35-e3d33f229d56` in 67.969 seconds. Uniform contain and
narrow replicated-edge padding preserved framing without stretching the face.
Likeness fell from 0.753158 for the staged source to 0.708252; all six genuine
reference comparisons fell. Head direction remained close (0.562485 degrees
maximum drift), with closed lips, but the smile was not improved. Full/crop/thumb
review rejects this as High: conspicuous pores/stubble/creases and cosmetic-looking
eyelid rims, with little background-detail improvement. No production change.

A causal adapter-off control preserves that exact source, prompt, models, seed
and sampling, changing only BeautyGRPO strength1 to0 and the output prefix.
It is diagnostic only, not a new identity mechanism or a strength sweep.
It completed as `c3aa6628-6003-41fb-ae14-6afb3894c75d` in 67.987 seconds.
Likeness is 0.751564, versus source0.753158 and adapter-on0.708252; pose drift
0.114296 degrees and pupil-coordinate delta0.012011. Independent full/crop/thumb
reviews find source-like eyes/skin and preserved scene but no compelling High
beauty gain. This attributes the additional drift to the adapter within the
tested native256 configuration; it does not establish the same effect at512.

The follow-up implementation audit found an important previously unrecorded
difference: native Flux T5 pads these prompts to256 tokens, while the author's
Diffusers pipeline defaults to512. Neither masks those padding tokens, so their
effect must be measured rather than assumed inert. Earlier results establish
failure of the tested native256 recipe, not an author-equivalent failure.
The installed native `T5TokenizerOptions` node can clone CLIP and set per-encode
`min_padding=0`, `min_length=512`, without mutating the shared tokenizer or
restarting a worker. Actual CPU-only tests of that node left the original at256,
produced512 on the clone, and matched Diffusers-style T5 token IDs exactly for
both prompts. The refined prompt has101 non-padding IDs including EOS. Native
CLIP's first77-token chunk matches Diffusers truncation; Flux uses that first
chunk's pooled CLIP output. CUDA remained uninitialized in these tests.
Remaining dtype, scheduler, noise-generator and EXIF differences still prevent
claiming a bit-identical reproduction of the author's implementation.

The correction completed as `5796f5b3-ef98-4d40-bf7f-8737748be388` in71.604
seconds, changing only native tokenizer options and their connection plus the
output prefix. Likeness modestly recovered to0.715910 (source0.753158), with
maximum pose drift0.604179degrees and pupil-coordinate delta0.038287. Closed
lips and the whole scene survive. Main and independent full/crop/thumbnail
reviews still reject the result as completed High: dark eyelid rims and etched
skin remain, without a clearly more attractive smile than the source. The
encoding mismatch was real but correcting it did not resolve the observed
failure. The conclusion is limited to this tested recipe, not every possible
author implementation or subject.

Fourteen reproducible CPU tests in `scripts/test_upgrade_beautygrpo_t5_parity.py`
cover exact graph differences, adapter/source/settings preservation, token IDs,
native-node schema,64-hex checksum validation and submission guards. An initial
checksum typo was caught before any preparation/submission, corrected against
all eight actual native/tokenizer files, and covered by those tests.

## Current handoff

No production implementation was promoted. The original production graph and
polish/Upgrade/High code hashes remain unchanged from this turn's start. Low is
still default, Phone ON / Turbo OFF. No character training, photo uploads,
dependency changes or worker restarts occurred. All model downloads are verified
and installed. Both queues are checked before each run; the4070 was preserved.

Mitch reviewed the source / BeautyGRPO256 / corrected512 comparison and replied:
**"all of them look about the same"**. This closes the tested BeautyGRPO route
as insufficiently differentiated for High, regardless of its small diagnostic
improvements. It is not pending user approval. No further generation is queued
for this experiment. Future candidates must visibly improve expression/features
at ordinary viewing size, not rely on crop-level texture or score differences.
Three-photo acceptance and public-workflow integration remain unfulfilled;
finishing this test round is not finishing High. Do not resume blind prompt,
strength or seed sweeps, or silently relax the realism/expression requirement.

A separate sole explicit-feature refinement of the base-Kontext adapter-OFF
control is now also complete and rejected. It removes the earlier eye-shape/
cheek-width restrictions without changing source/models/nativeT5/seed/sampler.
Likeness0.755352 is source-like, but eyes, cheeks, jaw and smile show no useful
stronger beauty change at ordinary viewing size. Full/crop/thumbnail reviews
agree. Eight offline runner tests pass; production stays unchanged. See the
[complete base-Kontext result](upgrade-high-explicit-features-2026-09-07.md).
No further prompt/strength/seed sweep or three-photo expansion is queued.

## Independent character-LoRA removal control

While the large Kontext/T5 files download, run one fixed native Klein control on
the genuine third navy-shirt photo. The earlier source-only graph still used the
character LoRA at0.9; it did not test whether that LoRA was needed. The new graph
changes only character strength0.9 to0, plus its output prefix. Prompt (including
the unchanged trigger), genuine source, phone0.25, seed8675412,50steps,CFG4,Euler,
and816x1088 output remain identical. At zero strength the installed standard
loader returns the untouched model before loading the character adapter.

Run: `work/upgrade-high-20260907/third-no-character-control`, job
`f8247896-1dca-476d-9c0f-4ba645aa132f`. Both worker queues and both GPUs were checked;
only idle RTX3090/8188 received work. No new character training, no photo upload,
and no production change. Compare raw0.9 and0 against the source and five other
genuine photographs. This diagnoses source fidelity, not stronger-High success;
the historical baseline was not regenerated under today's runtime.

The control completed in215.897s. Source identity against the other five genuine
photos is0.825853; historical character0.9 is0.825638; character0 is0.814684.
Maximum pose drift remains0.158degrees and the closed asymmetric smile survives.
The no-character version has harsher, coarser skin and stronger wrinkles/spots,
so removal alone is not a beauty improvement. Its eye-coordinate diagnostic also
worsens from0.02154 to0.06669. Full-frame/face/thumbnail review agrees: recognizable
and source-faithful overall, but not a successful High. This supports testing a
single native beauty-prompt refinement without training a character adapter;
it does not establish the same identity behavior on the synthetic house/canyon.

Sixteen existing Upgrade unit tests passed, covering Low's protected hash,
Off/Low/High input compatibility, Phone-on default, presets and reporting.

## Native High prompt pilot: rejected

The no-character source-only graph with explicit stronger beauty instructions
completed as job`58d49f97-8d47-43dd-8c80-2ddafe960f39`. Only positive text and the
output prefix changed from the preceding control. It improves coarse skin, keeps
the closed-lip smile/head angle and coherent detailed room, but gives the man
very dark, thick generic eyebrows and a different eye area. Likeness falls to
0.573564 (down0.241120 from the no-character fidelity control); all five individual
genuine-reference scores fall. Full-size, crop and thumbnail review reject it.
Do not promote or repeat a broad prompt/strength grid.

The observed mechanism limitation is different from ordinary source copying:
native source conditioning preserved this genuine face during a fidelity edit,
but did not sufficiently constrain identity while changing eye/brow appearance.
The paired fallback restores the already-compatible existing character weights
at 0.9 **and its trained m1tch_person token**, with all High semantic instructions
unchanged. The weight-only preparation was preserved without execution because
it omitted that token. This tests the complete supported identity-conditioning
mechanism, not separate weight/token causality or new training.

Phone adapter0.25 is active in the High pilot. Its exact author trigger phrase
`casual snapshot` is absent from that pilot prompt; the paired character test
retained this omission so phone conditioning stayed fixed while the supported
character-weight/token bundle was enabled. This was not a weight-only comparison.
Any eventual public recipe must restore the canonical phone-trigger helper and validate the
final generic template on all three photos. The current room-specific prompt is
not a ready-to-ship generic workflow.

## Matched character fallback and one intermediate refinement

Job `18701e08-31fc-40ed-ba17-f4761d2eabea`, using existing character strength0.9
**with the trained m1tch_person token**, restores likeness to 0.825755
(source 0.825853; historical character-0.9 fidelity 0.825638). Head-pose difference
is only 0.0777 degrees and lips stay closed. The generic black eyebrows disappear.
However, the full/crop/thumbnail comparison also shows that most of the stronger
beauty change disappears: eyes, brows, smile and skin are close to ordinary fidelity.
This proves the identity constraint works, not that the High objective is met.

The one evidence-driven midpoint completed as job
`8fed3424-3662-477b-aff1-d60e7dc6aaee`: strength0.45 with the **exact matched
prompt/token** and every other setting fixed. Likeness is **0.774718**, a drop of
0.051037 versus matched0.9. It stays recognizable, closed-lipped and source-like
in pose (0.157degrees maximum drift), with the room still detailed. Full-size,
face-crop and thumbnail review finds modest brow definition but coarser/dotted
skin and no clearly compelling stronger High; eyes and smile remain broadly
fidelity-like. This does not justify promotion solely because likeness exceeds0.7.

Midpoint versus matched0.9 is a clean strength-only comparison. The earlier
character-OFF High also lacked the token and is not a pure strength-only endpoint.
The separate weight-only0.9 preparation was superseded **without execution**;
it must not be counted as a failed generated result.

The native prompt/strength line is now closed after this sole controlled midpoint.
No further native strengths or prompt variants; no result was promoted. Three-photo
acceptance and public workflow integration remain unproven. See the final
[five-way review and diagnostics](../work/upgrade-high-20260907/third-native-high-character-midpoint/VISUAL-REVIEW.md).
