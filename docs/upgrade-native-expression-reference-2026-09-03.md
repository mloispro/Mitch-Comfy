# Native Klein High with explicit source-expression reference

Status: initial test and sole phone-repeat refinement completed and rejected visually;
not production. This route is closed, not a three-photo High fix.

The prior single-source Klein second pass retained the less-flattering expression.
Qwen three-reference edits changed skin/hair realism. Whole-expression LivePortrait transfer
and calibrated semantic controls fail the house expression/closure tests. CPU movement
retains texture but cannot redraw persistent creases and pigmentation. The next mechanism
test uses native Klein9B multi-reference editing of the already detailed good raw, with
an explicit close source-expression reference in the second slot.

## Evidence and graph

Rechecked the Base9B model card, BFL multi-reference guidance, installed ReferenceLatent
implementation and shipped author `image_flux2_klein_image_edit_9b_base.json` template.
Sources: https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B
https://docs.bfl.ai/guides/prompting_editing_multi_reference
https://docs.bfl.ai/flux_2/flux2_klein_training

Klein supports four references with explicit roles. This establishes compatibility, not
a guarantee of expression/identity disentanglement. The identity mechanism remains the
existing genuine-photo-trained Base9B V3 rank32 step1600 LoRA0.9 plus genuine portrait3.
The detailed raw already contains the intended identity; it is an edit target, not a
genuine validation photo. Slot2 supplies expression/feature presentation, not an identity
embedding or proof of a genuine photograph. Never score against synthetic sources.

Trace every input through LoadImage -> scale -> full Flux2 VAE -> ordered ReferenceLatent
on both positive and negative CFG branches:
1. Existing detailed raw:1MP bicubic, edit target/whole-frame pixels/head/body/background.
2. Close square crop from ORIGINAL scene source:0.5MP nearest-exact, expression/eye-brow-
   closed-lip relationship only. No synthetic face is described as a genuine identity anchor.
3. Existing genuine neutral identity portrait:0.5MP nearest-exact, recognizable identity.
4. Existing genuine isolated hair material:0.1MP bicubic, natural hair texture.

Use the already working four-reference runner, five protected weights and exact compatible
native Base9B configuration:fp8-loaded9B, Qwen3-8B text encoder, full Flux2 VAE, identity0.9,
SmartphoneSnapshot v13 at0.25,50Euler/CFG4, original house seed8675416 and1680x1008.
This larger-than1MP control preserves comparison dimensions; do not claim speedup. TurboOFF.
No masks, face swap/pasteback, upscaler, restoration, external service or new model install.
Runtime node/model presence, all five model hashes and both queues/GPUs are checked before
submission. Keep Upgrade's3090lock. Only release the latest owned terminal job's cached
models after both queues are confirmed idle, then verify memory release.
Alternatively reuse the exact known owned idle server cache without an explicit free:
verify latest successful history ID359b70af-a7a5-4c9f-8ea9-5bd484082b59 and matching
base/identity/phone model names, empty3090queues and idle utilization. Recheck history
after hashing before submission. Comfy handles its own server memory; another worker
is never freed/restarted. This permits the compatible3090 job while4070 is active.

The current shipped template SHA256 isB5B6E389B6892CF739DBA45A76FDADB48611C38505C1C3829BAE75D783DF229B.
Its current sample uses20steps/CFG5 and the small decoder; the established project adaptation
uses the already verified full VAE and the model card's50steps/CFG4. Do not imply the numeric
settings or decoder are identical to that template. Its one/two-reference subgraphs confirm
the same LoadImage/scale/VAE/ReferenceLatent native mechanism; BFL documents four-reference support.

House expression crop was detected on the original source with1.25face-context factor,
box[483,127,1049,693], no resize/rotation. SHA256
07dbb0c21c439cbc1e7778bbfcd61a62e63e4127124c2822379749680ac28d7e;
byte-identical staged input `mitch-source-expression-07dbb0c21c43.png`.

The close crop is only a conditioning image; the final is a native whole-image output.
The crop is detected on the ORIGINAL source, not an arbitrary region in another image.
Save source/crop hashes and box; preserve head angle by cropping without rotation/warping.

## Test scope

This is a mechanism pilot combining a different edit target/reference layout and matching
role prompt, NOT a one-knob ablation. Do not attribute improvements to one change alone.
No graph is invented: reuse the already validated native author-based reference mechanism.
Keep all model/sampling variables fixed; at most one controlled refinement afterwards.
The negative CFG text stays the previously tested compact negative, not a new word sweep;
its use is experimental and not a BFL-endorsed negative-prompt recommendation.

Run house first. Require native-size and thumbnail review of recognizable likeness,
clearly improved eyes/brows/closed smile, less puffiness/freckles/creases, realistic pores,
stubble/hair and detailed coherent background. Compare six genuine held-outs, original
scene and old raw/Low. Inspect pose/gaze and explicit lips; scalar passes are not acceptance.
If useful, apply this same recipe to canyon and a genuine third, not case-specific presets.
No production promotion until the full user requirements and end-to-end path are verified.

## Submission and pre-output verification

House job9f9b660d-06b9-4e00-af27-425b6d4f6195, port8188, queue number38, node_errors empty.
All five protected model hashes and live node/model visibility passed. Another4070 job
was active; its queue was inspected and left untouched. No explicit free/restart occurred.
The matching owned3090 cache was reused after terminal-history/model-name checks.

Submitted manifest SHA256:
27654a2046713f83cbca7d61e81eb5398b88c05cf0487c414fadd65289476445.
Read-only verification proves slot1 equals the previously audited detailed raw; slot2 is
pixel-exact to the original source crop box; source/crop/staged hashes agree; genuine
identity3 and hair4 match the protected baseline; all four inputs trace through VAE into
both CFG reference chains. This is input/graph provenance, not output quality evidence.

## Initial result and sole controlled refinement

House native output completes with likeness0.75405 (old raw0.77911; actual Low0.73895),
closed lips0.00129 and only0.167degree change from the raw pose. Original-source pose
error remains3.762degrees; source eye-coordinate error0.08369. Native/face/thumbnail
inspection finds the detailed background retained but skin roughness, dark speckles and
creases stronger, with the tense brow largely unchanged. This is not an acceptable High.

Hypothesis for ONE refinement: reapplying the SmartphoneSnapshot adapter to an already
phone-styled detailed raw amplifies rough texture. Keep the existing PhoneON first-stage
raw, all four references, both prompt branches, identity0.9,50steps/CFG4/seed/dimensions
unchanged; set only SECOND-stage phone LoRA strength0. This is inherited phone appearance,
not turning off the user's Phone option in the base workflow. The stage's inactive adapter
must be reported honestly. No production/default change, and no subsequent phone-strength
grid. Score the same six genuine references and inspect actual skin/background/expression.

## Completed phone-repeat refinement

Job `2901d734-bdd7-4d6c-80a4-c4a628e770d5` completed successfully on
RTX3090/8188 in 499.54 seconds. The original runner session had already ended;
the saved submission and exact history were recovered without resubmission.
Both queues were empty at the final check. No explicit model free, worker
restart, new dependency/model installation or photo upload occurred.

Manifest: `work/upgrade-source-faithful-20260903/native-expression-reference-house-phone-inherited/experiment.json`
SHA256 `14d22e4a543d630276d893456f72341718d737d2c19c12bd0804570519178fb6`.
Raw: `ComfyUI/output/upgrade-source-faithful/native-expression-reference-house-phone-inherited/raw_00001_.png`
SHA256 `da46985c310d7eaab0d283e82b0981aacbb14b33d79803585e1874a950ec50a4`.
Evaluation: the experiment's `evaluation/audit.json` and source/Low/High face,
full-frame and thumbnail comparison sheets.

Read-only graph assertions confirm that the ONLY changes from the initial
expression-reference test are node3 phone strength 0.25 -> 0 and node27 save
prefix. Every reference record, both text branches, identity strength, seed,
sampler, steps, CFG and dimensions are unchanged. Evaluator syntax validation
passes. The executed PNG graph matches the manifest, and the evaluator verifies
the hashed upstream PhoneON report plus the inactive second-stage phone adapter.
This is inherited phone appearance, not an active final-stage phone adapter and
not a change to the public PhoneON default.

Six genuine held-out photographs were scored on CPU. Candidate likeness is
0.75923485 (initial test 0.75405431, old raw 0.77911484, actual Low 0.73894978).
Per-reference similarities are 0.57243204, 0.63013816, 0.70947742, 0.66177273,
0.67903328, 0.67710149. Closed-lip ratio is 0.00233969; source mouth-corner
error is 0.02412626. Raw pose changes only 0.11969185 degrees, while original
source pose error remains 3.75363731 degrees. Maximum source-relative eye
coordinate error is 0.06008390. The evaluator exits1 for source-pose failure;
that is an evaluation failure, not a failed render. These scores are diagnostics,
not proof of attractiveness or an identity lock.

Native-size, face-crop and thumbnail visual review: closed lips and detailed
siding/branches are retained, but the face still has stronger dark speckles,
forehead/glabellar creases and coarse-looking skin than actual Low. The tense
eye/brow/smile presentation persists. Hair remains strongly ridged rather than
an improvement in natural strands. Removing the second phone application does
not materially repair these failures. The specific hypothesis that repeated
Phone LoRA application explains this route's poor result is unsupported; this
does not prove the first-stage phone adapter is irrelevant in every workflow.

No canyon/third repeat of this visually failed recipe, no phone-strength grid,
no postprocessing rescue or promotion. High still lacks a coherent validated
three-photo recipe. All six protected production hashes (main node, High, Low,
gaze, UI and public JSON) remain unchanged from the repair effort's baseline.
Keep the user's stronger-but-recognizable High preference; do not redefine it
as accepting rougher/older-looking skin merely because similarity passes.
