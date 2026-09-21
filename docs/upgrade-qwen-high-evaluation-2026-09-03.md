# Local native Qwen High evaluation — research gate

Status: prepared experiment, not production. Stronger High is explicitly requested, with a modest
likeness tradeoff allowed while remaining recognizably Mitch. Low stays conservative. The repeated
Klein full-frame/crop editing failures are preserved in `upgrade-source-faithful-plan-2026-09-03.md`.

## Why this mechanism is eligible

[Qwen's 2511 model card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) specifically documents
portrait editing with improved identity/character preservation. This is a prediction to test, not an
identity lock. The [official Comfy example](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511)
and installed `comfyui_workflow_templates_json/templates/image_qwen_image_edit_2511.json` supply the graph.
The latter's nodes, links and false/Turbo-off branch were read before implementation.

The input is the accepted phone-on Klein raw render: a **synthetic edit target**, never a genuine
identity scoring reference. `LoadImage -> FluxKontextImageScale` supplies image1 to both positive and
negative `TextEncodeQwenImageEditPlus`. The installed `comfy_extras/nodes_qwen.py` encodes that image
as grounded Qwen-VL vision at about384² pixels and Qwen-VAE reference latents at about1024² pixels.
Those ordered reference latents enter the denoiser with `index_timestep_zero`. The source is also
VAE-encoded for the sampler's shape/latent input, following the author graph at denoise1. The identity
prediction comes from the model's documented trained portrait editing and joint semantic/appearance
conditioning, **not** from generic img2img initialization, a text name, a style reference or face swap.

Only image1 is used; image2/3 are absent. No invented equivalent-identity-reference roles. No masks,
head replacement, restoration, selective sharpening, expression driving or new lighting stages.
No Klein identity/smartphone LoRAs are loaded into Qwen. Smartphone rendering is inherited from the
phone-on upstream image and must be visually rechecked after editing, not claimed as an active Qwen adapter.

## Exact compatibility and runtime

Local whole-file hashes match the official Comfy-Org files:

| File | SHA256 |
| --- | --- |
| qwen_image_edit_2511_fp8mixed.safetensors | c9fdc158e46d3b61ef75f21ae866ca2fe808bf4a53643120d1c1e87c19280a4e |
| qwen_2.5_vl_7b_fp8_scaled.safetensors | cb5636d852a0ea6a9075ab1bef496c0db7aef13c02350571e388aea959c5c0b4 |
| qwen_image_vae.safetensors | a70580f0213e67967ee9c95f05bb400e8fb08307e017a924bf3441223e023d1f |

[Edit model](https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/blob/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors),
[encoder](https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/blob/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors),
[VAE](https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/blob/main/split_files/vae/qwen_image_vae.safetensors).
Use UNET weight_dtype default to preserve mixed-precision metadata; not forced unscaled FP8.
ModelSamplingAuraFlow shift3.1, CFGNorm1/post-CFG, Euler/simple, CFG4, denoise1, seed8675412,
one approximately1MP image. Start20 steps, explicitly recommended by the installed Comfy template;
its Qwen-author recommendation is40. Lightning/Turbo and multiple-angle LoRAs are absent.

The existing Qwen dataset utility is only an inventory item, not quality evidence. It uses Lightning
and a viewpoint LoRA, neither appropriate for this test. No dependencies or models are installed or changed.
The3090's24GB with standard Comfy offloading is the target; the20.5GB diffusion model and9.38GB encoder
cannot both be assumed resident. Preflight must inspect hardware, RAM, live nodes and both GPU queues.
Record measured memory/runtime; no promised latency or unsupported VRAM claim. Keep the Upgrade3090 lock.

## Acceptance and experiment budget

Compare native full-frame candidate against actual Low, source and accepted raw, with six genuine held-out
photos for identity diagnostics. Inspect full size and thumbnail: obvious but believable improvement in eyes,
brows, closed-lip asymmetric smile, non-puffy cheek/jaw shape, skin and hair; preserve head/hairline/pupil
direction and detailed coherent phone background. About0.70 similarity is a diagnostic target, not proof of
identity or a beauty score. A modest dip may be acceptable only with convincing visual likeness.

One initial canyon run and at most one controlled refinement before deciding this mechanism. If successful,
freeze the recipe and test house and a third genuine source, excluding that source from identity scoring.
No production integration before those checks and an end-to-end run.

## Initial submission

Prompt `e2773e82-bc19-4295-822a-054aeec674d3`, port8188, canyon accepted raw,20steps/CFG4.
Manifest: `work/upgrade-source-faithful-20260903/qwen-high-canyon/experiment.json`.
Preflight: both GPU queues idle,3090 released only after our previous run completed,4070 idle;
system RAM67.8GB total/47.0GB free. Comfy0.33.0, templates0.11.44, torch2.12.1+cu130;
Comfy git revision `b78cec879b9460d5cb25228a83a942fb78d2cd24`. Model/encoder/VAE hashes matched.
The example's scale node selects1024² exactly for canyon, so no crop/aspect change here. For another
aspect ratio its preferred-size center crop must be reviewed explicitly before use; no automatic
claim of identical source framing for the house/third image.

Initial20-step result finished in122.82s. It visibly follows the beauty edit but overshoots: generic younger
face, redesigned nose/jaw/brows and uniform synthetic skin. Genuine-reference similarity0.336348 versus
raw0.751794, despite pose delta only0.987degrees and closed lips. Rejected; this is not the modest likeness
tradeoff the user authorized. No production change.

The single controlled refinement changes ONLY the instruction to a specific age/structure-preserving
retouch: soften half the creases, reduce speckles, groom existing brows, reduce eye shadows, slightly relax
inner brow, keep the existing small asymmetric closed-lip smile. Explicitly retain nose/jaw/eye/lid geometry,
age and hairline. Same input,20steps/CFG4, seed, model files and author topology. No more broad prompt or
strength sweeps if this also fails.

Targeted refinement `31370c83-3893-4812-aadf-323a236141df` finished in121.413s. Exact input/seed/
model/sampler parity was checked; only positive prompt and output filename changed. Likeness0.386944,
pose delta0.570degrees, closed-lip ratio0.003264. It still de-ages/redesigns the face and renders uniform
artificial pores. **Reject this whole-frame Qwen beauty-edit mechanism for this workflow.** Do not queue
house/third through this failed recipe or promote it. Production remains unchanged, including phone-on
and Turbo-off defaults. This is not a successful strong-High implementation.

## Bounded failure diagnosis: source-latent retention, not another prompt sweep

The two full-noise recipes remain rejected. The third genuine Klein baseline also changes head pose
and opens a closed mouth before polish, despite good face similarity. The geometric High cannot repair
that or provide a sufficiently obvious beauty improvement. A concrete conditioning limitation is now
being isolated: both rejected Qwen recipes use denoise1, so the target is a semantic/appearance reference
but its spatial latent is not retained in the initialization. This is not proof that denoise alone caused
the generic face; test that hypothesis directly, without changing the prompt or adding a new model.

The installed `comfy/model_sampling.py` CONST path mixes noise*sigma + latent*(1-sigma).
`comfy/samplers.py` KSampler.set_steps uses the last steps of a longer schedule for denoise<1.
[Official KSampler documentation](https://docs.comfy.org/built-in-nodes/sampling/ksampler) explicitly
describes lower denoise as preserving initial structure. The Qwen native grounded-VL and VAE-reference
conditioning, author graph, actual model hashes, seed, CFG4, Euler/simple and20 evaluated steps remain
unchanged. Identity prediction still rests on trained Qwen portrait editing, not img2img alone.

Single diagnostic: targeted prompt from the rejected refinement, denoise0.35 instead of1.0, on the SAME
accepted canyon raw. It is not a claim that0.35 means35% pixel change. Compare exact graphs and manifest,
full-size/thumbnail identity, expression, realistic skin/background and six genuine references. No
automatic postprocess. If this only produces another tiny polish or still redesigns the face, reject it;
do not start a denoise/prompt grid. A useful result would justify freezing this recipe and testing the
other photos. It cannot repair the third baseline's already-wrong pose simply by preserving that baseline.

Diagnostic completed as `777e6888-9203-4572-9bc6-ff65e10650b5` in117.100s. Graph comparison confirms
only denoise1->0.35 and output filename changed from the targeted full-noise refinement. Output:
`ComfyUI/output/upgrade-source-faithful/qwen-latent-retention-canyon/raw_00001_.png`.
Six-reference likeness0.636080 versus raw0.751794; pose delta0.817degrees from raw,2.542degrees from
source; closed-lip ratio0.003086. No postprocess. Source-relative redetected eye delta0.049360 still needs
attention; this is not an exact-gaze pass. The stronger brows/eye presentation and smoother skin are
visible, but brow density and facial character drift, fine skin looks more uniform, and some freckles
remain. It fails the existing likeness diagnostic gate. Source retention improves likeness relative to
full-noise0.386944, but does not establish a successful High. Do not silently relax the gate or promote.

Present the exact source/actual-Low/candidate comparison for Mitch's judgment of the already-authorized
beauty/likeness tradeoff. No further denoise sweep is queued. House, third-source structural repair,
final gaze and production end-to-end remain unresolved. Production node/UI/workflow hashes were checked
unchanged after the diagnostic. Eight CPU geometry/closed-lip regression tests passed.

CPU-only final-gaze check uses the existing production iris correction, without changing that module or
adding Low/High skin processing. Verified native audit/input hashes are prerequisites; original native
failures are copied into the finish audit. `final-gaze-2d-audit` reports max horizontal source error0.007431,
1388 selected eye-region pixels and exact pixels outside the mask. Identity0.636080->0.638486 is essentially
unchanged, not a recovered likeness pass. Full-size review retains the same eye/brow/skin appearance.
Two-dimensional pupil-target errors are0.923px and0.508px (1.76% and0.69% of eye width). The first eye's
small error actually rose from0.809px; don't claim both dimensions improve or that gaze is mathematically
locked. The second improved from2.725px. This is additional fidelity evidence, not production approval.

## Fixed-recipe generalization, still experimental

The previous goal turn made progress on the third source: native source-only editing retained pose,
closed lips and0.826 likeness, where the original four-reference baseline failed. Now test the SAME
targeted Qwen prompt, denoise0.35,20Euler/CFG4, shift3.1 and exact model hashes on house and that corrected
third base. This is cross-image validation, not another prompt/denoise refinement, and does not promote
the canyon candidate or erase its0.636 likeness failure. Its visibly stronger effect justifies measuring
whether the requested tradeoff generalizes while Mitch's exact appearance judgment is pending.

Framing gate: the shipped FluxKontextImageScale uses preferred-aspect center crops. It would discard
about0.4% of house width and0.9% of third width. Replace ONLY preprocessing node160 with the live
ImageScale node, Lanczos/crop disabled, at a computed exact-aspect multiple-of16 size near1MP:
canyon1024x1024 (unchanged), house1360x816, third864x1152. Preserve all model, native grounded-VL/
reference-latent and sampling connections. Qwen's internal native reference encoder still scales to its
documented384² vision/~1024² VAE budgets. Unsupported exact-aspect sizes outside0.75–1.25MiPixels fail
closed rather than silently crop. Five dimension tests cover these cases and invalid inputs. This is
full-frame resampling, not face cropping, an identity mechanism, restoration or a new lighting stage.

The outputs are experimental at their recorded dimensions, not final production replacements; output
resolution/whole-frame texture must still be reviewed. Both GPUs/queues and all model hashes are checked
again, with the3090 lock retained. Use six genuine scoring photos for house; exclude the original genuine
third photo so it has five. Final gaze may be separately evaluated with its unchanged CPU module and
honest native-failure retention. Do not force a failing three-photo recipe into production.

## Completed three-photo native test and common finish

House prompt `8c306abb-18ca-4d8e-93ba-a105c09a4e1b` completed in121.607s at1360x816.
Third prompt `3823a6fc-17fe-430e-b8d3-310396d62568` completed in114.910s at864x1152.
Both use the frozen targeted instruction,20Euler/CFG4/denoise0.35 and no Lightning/Turbo.
Third uses the corrected single-reference Klein base, not the rejected four-reference result.
Native genuine-reference similarities are0.744987 (house) and0.784779 (third); source-pose
errors3.413893 and0.2961degrees. Both retain closed lips. House still has prominent spots,
inner-brow tension and creases; third is more promising but softens facial character/fullness.

The user's explicit preference is now **stronger beauty edit, still recognizably me**. Preserve
the conservative numerical diagnostics, but do not mistake their0.03-drop flag for a calibrated
boundary of the user's acceptable tradeoff or for an attractiveness score.

The native images had not received the existing freckle/hair cleanup. Evaluate that complete
finish once, without another diffusion run: native High -> common deterministic polish -> source
gaze last. In the isolated CPU evaluator only, disable forced mouth lift and cheek highlight;
restore those module constants after each call. Do not stack the old High/TPS treatment on top.
Create matched revised Low from each accepted base using the same common-polish/gaze finish.
These revised Low outputs are experimental, not the production Low. All inputs/reference hashes
are checked against native audits; third still excludes its original photo from the five scoring refs.

Results in each `qwen-latent-retention-{canyon,house,third}/common-polish-finish` directory:

| Image | Revised Low likeness | Finished High likeness | High source-pose error | Selected spot-contrast reduction |
| --- | ---: | ---: | ---: | ---: |
| Canyon |0.753381|0.653306|2.659degrees|67.3%|
| House |0.770816|0.732281|3.776degrees|71.0%|
| Third genuine |0.824368|0.783743|0.306degrees|60.0%|

Spot contrast is a local algorithm diagnostic on its detected components, not a claim that every
freckle was removed. All final mouths pass the closed-lip landmark check and show no visible teeth.
Maximum horizontal gaze errors0.011097/0.002893/0.014135; both eyes'2D target errors improve in
all three finishes, with final errors below0.8pixels in the fixed pre-gaze eyelid frame. This is
not an exact-gaze lock. Pixels outside the union of polish/gaze masks are exact to the respective
native Qwen image, **not** necessarily exact to the original source or upstream Klein base.

Full-size and equal-height face comparisons were reviewed: the freckle cleanup is genuinely useful,
and canyon has clearly stronger brow/eye presentation. House is still too similar in expression;
third still appears somewhat fuller through the cheeks. Canyon likeness drops about0.10 from its
base. This is not yet a consistent, accepted three-photo High and has not been integrated into
production. Native failure records are retained; strict likeness flags remain for all three,
with the existing source-pose flag also retained for house. No production hashes changed.

Eight expression/identity diagnostic regression tests pass. The original gaze-only path is also
replayed separately with common polish disabled; the option is not silently applied to old callers.

## Next bounded conditioning test: genuine identity during the strong edit

The complete-finish test is progress, not production acceptance. It establishes that adding the
existing cleanup cannot resolve the native editor's uneven expression changes or canyon identity loss.
The new hypothesis is that an explicit genuine same-person reference during Qwen editing can reduce
reinterpretation of the synthetic Klein face. This is a hypothesis, not a promise or identity lock.

Rechecked primary evidence: [Qwen2509's training description](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)
documents multi-image training via concatenation, person+scene/person+person inputs, and strongest
performance with1–3 images. [Qwen2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) retains the
two-image native pipeline and specifically improves portrait identity and multi-person consistency.
The installed2511 author template's node83 connects to image2 of BOTH native positive/negative
encoders, without the image1 scale node. This is not an invented extra equal identity slot.

Trace: Picture1 (same accepted canyon raw) -> node160 -> grounded VL and VAE appearance reference1,
plus VAEEncode -> sampler latent. Picture2 -> native grounded VL and VAE appearance reference2.
Ordered native references enter index_timestep_zero conditioning on both CFG branches. Role text
assigns scene/pose/expression/gaze to Picture1 and identity/recognizable proportions to Picture2;
it explicitly forbids a second person or borrowing Picture2's scene, pose or expression. No face
embedding swap, mask, restoration, additional lighting or unverified identity node.

Use already-staged genuine camera still `mitch-upgrade-calm-genuine-0e9f30d5.jpg`, byte-identical to
training07_sweater_front_neutral, SHA2560e9f30d584646b3455674fa88e03c3c8b5a534d0fcbc2083088032ecb35da93a.
Its current full-frame viewing preview and dataset provenance were inspected. This is a training
photo, separate from all six held-out scoring photographs. The experimental runner now fails closed
unless the reference hash matches a genuine training camera-still record. It does not stage/upload
photos or accept a held-out validation reference as identity conditioning.

First canyon test: SAME2511 model/encoder/VAE hashes,20Euler/simple steps,CFG4,shift3.1,denoise0.35,
seed8675412,1024square, targeted instruction, phone appearance inherited, no Lightning/Turbo. Only
add the genuine native second reference and its necessary role instruction. Reference-image scaling
is handled by the native384²-VL/~1MP-VAE budgets; retain the3090 lock and standard offload.
Check both queues/hardware before generation and do not touch the4070. At most one controlled
refinement after evaluating this conditioning test. No production changes or model downloads.

Acceptance remains a visible High benefit with recognizable likeness, closed lips, source direction
and detailed whole-frame realism. Measure native output before common finish; score genuine held-out
references, retain exact graph provenance and existing diagnostic failures. Do not extrapolate a
canyon result to house/third or present stronger edit training support as proof of beauty quality.

Initial two-reference result `71de1857-a15d-4fb9-8223-b8a9cf1b972b` completed in194.124s.
Exact graph comparison confirms changes only at positive/negative reference inputs and role text,
new genuine loader83, and output filename. Likeness0.684474 versus single-reference0.636080;
raw0.751794. Source pose error2.887degrees; lips closed0.001736. The additional reference helps
this diagnostic but does not pass the conservative likeness/drop check. Skin still needs common
cleanup; source-relative pupil error remains for the final gaze stage. No production promotion.

One controlled refinement is justified by a prompt/requirement conflict: the targeted instruction
explicitly forbids eye-shape, cheek-volume and mouth-shape changes, whereas the user's stronger High
request explicitly permits beautifying these. Keep both references, models, seed, steps, denoise,
framing and all conditioning topology fixed; change only the positive instruction to the runner's
original stronger High request (relaxed confident closed smile, appealing lids/brows, leaner cheek/jaw,
clear natural skin and subtle highlights). The image1 role says **starting expression**, not an
immutable expression. Identity, adult character, head angle, pupil direction, hairline and whole scene
remain constrained. This is one prompt refinement, not a strength/seed grid. Reject rather than keep
sweeping if it produces a generic face, puffy cheeks, new pose or unrealistic skin/background.

Stronger-prompt refinement `48d41f3b-6c37-40bf-8688-1448617a58ef` completed in194.180s.
Canonical graph comparison proves that only positive prompt151 and filename9 changed; both reference
records are identical. Native likeness0.691575; complete common-polish/gaze finish0.696216, versus
0.653306 for the earlier single-reference complete finish and revised Low0.753381. Source pose error
2.900948degrees after finish, closed-lip ratio0.003644, maximum horizontal gaze error0.009641, exact
pixels outside the polish/gaze union. The conservative likeness/drop diagnostic still fails;0.696
must not be rounded up into a passed0.70 threshold. This is not a claim of identity lock.

Visual review at native size, normalized face size and thumbnail shows a clearer brow/eye presentation
than Low and a closed, more defined smile. Some smoothing and facial-character tradeoff remain. The
genuine reference improves the tradeoff enough to justify testing the unchanged recipe on house and
the corrected third base, not enough to claim three-photo or production acceptance. Freeze this exact
two-reference/default-strong-prompt recipe for those tests; no further prompt, seed or denoise sweeps.

## Frozen genuine-reference recipe: house and third completed

House `7d3a3220-17e5-456d-8370-ff072c6e7b04` completed in197.422s at1360x816.
Third `6acf541b-fb92-436c-9d4a-0a9097630ce5` completed in190.587s at864x1152.
Both preserve the strong canyon prompt,20steps/CFG4/denoise0.35, same genuine training07 reference,
model hashes, native two-input topology and phone-on upstream/Turbo-off provenance. Source image,
baseline seed and exact-aspect dimensions follow their existing per-photo inputs. No new prompt tuning.

| Image | Native High likeness | Finished High likeness | Revised Low likeness | Finished source-pose error |
| --- | ---: | ---: | ---: | ---: |
| Canyon |0.691575|0.696216|0.753381|2.900948degrees|
| House |0.772997|0.761413|0.770816|3.792002degrees|
| Third genuine |0.809947|0.804725|0.824368|0.356699degrees|

Third uses five independent scoring references, excluding its original genuine photo. House/third
pass the conservative identity/drop diagnostic; canyon retains its failure rather than rounding
0.696 up to0.70. All mouths stay closed, with no visible teeth. Final maximum horizontal gaze errors
are0.009641/0.004599/0.010651. Finish-exterior pixels remain exact to each native Qwen output, not to
the original source. Native/finished images and normalized face/full-frame thumbnails were reviewed.

This is a meaningful improvement over the earlier single-reference finish0.653/0.732/0.784, particularly
in retained identity. It is still not production acceptance. Third is recognizably the same person
with a cleaner, softer presentation, though cheek fullness remains a visual concern. House is cleaner
but still inherits much of the old base's tense brow/expression and source-pose difference. Its native
mouth-coordinate error improves0.027753->0.018808, but a landmark improvement alone is not proof of a
more attractive expression. Next isolate the house's source-preserving BASE, as documented in the
master plan, instead of another High prompt/denoise sweep. No production defaults or node bytes changed.

Six new reference-layout tests pass: original single-reference compatibility, two native branches,
scene-latent initialization, no unreviewed third input, genuine training-only provenance, and matching
loader/hash roles. Native evaluation now verifies the actual provenance manifest, dataset/staged file
hashes, exact executed graph and separation from scoring references for the new identity input.

Gaze limitation from the complete two-dimensional audit: canyon final target errors1.548/0.656px;
house0.274/1.006px; third0.392/0.461px in each pre-gaze eyelid frame. House's second eye worsens
from0.654 to1.006px even while horizontal error passes. Do not claim both axes/eyes are perfectly
locked or uniformly improved. These subpixel/low-pixel measurements need full-size visual judgment.
Selected dark-dot contrast reductions are68.9%/70.0%/59.0%, not a guarantee of freckle-free skin.

## Face-fullness diagnostic (no pixel changes)

Added a read-only projected face-oval diagnostic using the installed MediaPipe oval topology.
It measures outline width at30/50/70% of the outer-eye-line-to-chin distance, normalized by
outer-eye span. This removes uniform scale, translation and roll; it does NOT remove yaw/pitch,
perspective, landmark error, changed eye spacing or apparent fullness from lighting/smoothing.
It is not an attractiveness, physical cheek-volume or production-acceptance score.

For the finished genuine-reference third High, widths rise1.645/2.075/2.682% versus its native
base (and1.480/1.412/0.722% versus the actual source), while pose error is0.357degrees.
This supports retaining the visual fullness concern, not dismissing it based on likeness0.805.
The exact diagnostic is `qwen-genuine-strong-third/common-polish-finish/contour-diagnostic.json`.
Five tests cover scale/roll/translation invariance, known widening, identical outlines, invalid
geometry and JSON serialization of actual float32 landmark arrays. No images were altered.

Important measurement limitation: the third native Qwen output measures only +0.979/+1.273/+1.393%
versus raw; finishing changes detected widths another +0.659/+0.792/+1.272%. The experimental common
finish has zero mouth displacement and no face-outline warp. Its lighting/texture and iris changes
can move redetected landmarks. Thus the final 2–3% figure is a projected landmark diagnostic, not
evidence that the physical face boundary was literally warped wider by that amount. Visual fullness
can also be caused by smooth shading and expression; do not prescribe a contour warp from this
measurement alone.

## Source-preserving house base followed by unchanged High

Prompt `da8eae96-bf44-423d-8b8e-5f4068ee0a24` completed in 197.523 seconds. Only the verified
upstream base changes from the earlier house test; the two native references, genuine portrait,
stronger instruction, 20 steps, CFG 4 and denoise 0.35 are unchanged. Native likeness 0.694595,
finished 0.688376, matched new Low 0.683992. The absolute 0.70 diagnostic still fails. Finished
source-pose error is 2.536129 degrees, closed-lip ratio 0.003432, horizontal gaze error 0.0184.
Both two-dimensional gaze errors improve (2.446 -> 0.399 px, 1.138 -> 0.721 px). Finish-exterior
pixels remain exact to the native candidate. Native-size, normalized-face and thumbnail review
completed; High keeps a much closer source eye/mouth presentation than the previous base, but
its separation from the new Low remains modest. The existing soft source background also remains
soft despite phone-on upstream. Therefore it is not a complete phone-on Upgrade replacement.

## Next conditioning test: retain detailed base, add original expression source

The source-only Klein test cannot be a universal base: canyon loses pose and both outdoor sources
retain unwanted blur. The old detailed base must therefore remain available. Existing two-reference
Qwen High receives that generated base plus genuine identity, but never sees the original source's
eye/brow presentation or asymmetric closed smile. Its low-denoise latent can retain the already
drifted expression. Test the missing original source as native Picture 3, rather than silently
discarding background detail or compensating with a face-outline warp.

Primary evidence rechecked: [Qwen's 2509 card](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)
describes trained multi-image concatenation, best with one to three inputs, and native pose/keypoint
conditions. [The 2511 card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) documents improved
portrait consistency. The installed 2511 author subgraph exposes optional image3 and explicitly
connects it to BOTH encoders 151/149 (links 368/369, origin -10 slot 2 -> target slot 4). Its root
example leaves image3 unconnected; this test enables that existing optional input, not an invented
identity node. Installed `comfy_extras/nodes_qwen.py` was read through the full Plus encoder.

Roles/trace: Picture 1 is the accepted detailed phone-on Klein raw and controls whole-frame
environment, body, clothing, lighting and output latent initialization. Picture 2 remains the verified
genuine training portrait and supplies identity/recognizable adult proportions. Picture 3 is the
original source and supplies original head direction, pupil focus and eye/brow/closed-lip expression.
All three enter ordered native grounded-VL (~384²) and VAE (~1 MP) reference latents on both CFG
branches; only Picture 1 initializes the sampler latent. Picture 3 is NOT a genuine identity or
scoring reference, and its identity influence cannot be claimed absent simply because of role text.
No source pixels are copied, no face swap, generation mask, restoration or new model is added.

First test: HOUSE accepted old detailed raw, original house source as Picture 3, same genuine Picture 2,
20 Euler/simple, CFG 4, shift 3.1, denoise 0.35, seed 8675416, 1360x816 whole-frame, same official
Qwen2511/encoder/VAE hashes. Phone appearance inherited, no active Klein adapter in Qwen, no Turbo or
Lightning. The experimental variable is adding the native source input and its necessary role text;
keep the stronger prompt body and other settings fixed. The two-reference run used about 21 GiB
of cached 3090 memory. The third input adds context cost; use existing native offload on the locked
24 GB 3090, verify both queues and live image3 support, and record actual runtime/any memory failure.
Do not bypass the lock or evict another job to make it fit.

Require the new reference hash to match SOURCE in an existing verified native evaluation whose BASE
RAW hash matches Picture 1. Keep genuine training/scoring separation and old one/two-reference tests;
reject unrecorded or swapped third inputs. Evaluate source pose, closed lips, expression, actual
background detail, freckles/hair, likeness against six genuine photos and thumbnail/full-size realism.
This is a prediction of useful conditioning, not proof of precise expression transfer. At most one
controlled refinement after this mechanism test; no prompt/seed/denoise grid or production promotion.

Preparation verified that nodes 9, 149, 151 and the new native loader 184 are the only graph changes
versus `qwen-genuine-strong-house`: output filename, added native third input on both CFG branches,
and required positive role text. First two reference records and all model hashes are byte-for-byte
equivalent after JSON parsing. Eleven reference-layout tests pass, including existing one/two-input
compatibility and rejection of swapped, missing, unaudited or duplicated third references.

Sampler-source clarification from a fresh template read: shipped KSampler 169's widget values are
40 steps / CFG 3 / denoise 1, while template MarkdownNote 157 recommends Qwen 40 / CFG 4 and
Comfy 20 / CFG 4. The experimental 20 / CFG 4 follows that explicit note, not the literal widget
defaults. Denoise 0.35 is the documented local retention experiment, not an author default.

Three-reference house prompt `ad44ffea-a44b-4292-b37b-604e31936654` is now running on the locked
3090. Both queues were empty before preflight; only this thread's completed canyon cache was freed.

Three-reference house completed in 290.597 seconds, with observed GPU memory 23,114 MiB and the
4070 untouched. Native likeness 0.773640 versus old two-reference 0.772997, source-pose error
3.229908 degrees versus 3.589449, mouth-coordinate error 0.019233 versus 0.018808. Lips remain
closed (0.000601); source-pose diagnostic still fails. The detailed house/branches remain present.
Visual change is still too restrained and retains the base's tense brow; adding the original source
at denoise 0.35 did not sufficiently restore the flattering eye/expression presentation.

Use the one allowed controlled refinement to test latent constraint directly: SAME three references,
stronger prompt, seed, 20 steps, CFG 4, dimensions, models and topology; change only denoise 0.35 -> 1.
This enables the native full-noise editing behavior already supported by the author graph. The
original target still supplies grounded vision and appearance-reference conditioning, but its VAE
pixels no longer contribute a retained spatial initialization. Identity support remains genuine
Picture 2 via the trained native portrait/multi-image mechanism. The old full-noise failures had only
one synthetic edit input, so they did not test this genuine-plus-original-expression configuration.
Risk: identity, source geometry and texture can drift more; do not assume extra redraw is better.
If this refinement becomes generic, puffy, unrealistic or loses source direction, reject the mechanism
instead of running a denoise grid. No production default change or automatic acceptance override.

The complete 0.35 three-reference finish scores 0.761418 versus revised Low 0.770816; source-pose
error 3.455427 degrees, closed lips 0.000165, max horizontal gaze error 0.014131. Both 2D gaze
diagnostics improve to 0.417/0.669 px, and finish-exterior pixels are exact. Full-size/face/thumbnail
review confirms retained detailed background but insufficient expression improvement; it remains
experimental, not an accepted High. No native failure flags were erased by finishing.

Full-native refinement `8e4dbc6a-4c5f-4ed3-be7a-f03db05cb09d` has been submitted. Canonical comparison
proves only KSampler 169 denoise and SaveImage 9 filename changed. All three reference records,
model hashes and remaining sampler inputs match. Reference audit wording now distinguishes the
scene-supplied VAE input from an actually retained spatial initialization; denoise 1 is explicitly
reported as no retained spatial prior. The native appearance references remain connected throughout.

Full-native refinement completed in 298.679 seconds. Native likeness is 0.754328 (raw 0.779115;
the conservative identity/drop check passes), source-pose error 3.619232 degrees, mouth-coordinate
error 0.030128, closed-lip ratio 0.001399. The eyes/smile and crease reduction are visibly stronger
than the 0.35 version, but native-size review shows overly smooth, uniform facial texture and a
discontinuous strip along the bottom edge. The face also still has a fuller-looking presentation
than desired. The source-pose diagnostic fails, and acceptable likeness does not waive these visual
failures. Preserve `qwen-source-expression-house-fullnative/evaluation` as a rejected unretouched
result; do not apply further polish or conceal the border with a crop. No more denoise/prompt grid
for this mechanism. The cause of the border is unproven; do not assert a resize or VAE bug from
appearance alone. Both native reference configuration and executed PNG graph verified successfully.

This round improves the diagnosis, not production quality: 0.35 retains the detailed base but has
insufficient expression separation; full-native redraw produces stronger beauty with an unacceptable
realism/whole-frame tradeoff. All three-photo production work remains incomplete. Public node, Low,
High, gaze, UI and workflow hashes remain the pre-goal values. No generation remained queued after
the completed full-native test. The pending user appearance question referred to the earlier
`qwen-genuine-strong-house-sourcebase` comparison, not this rejected full-native redraw.

## Codec/resize isolation before further generation

Previous goal turn is classified as progress: it completed verified source-only and three-reference
experiments, preserved the failures, and ruled out a universal single-source base or the tested High
recipes. No production implementation was promoted. The next step is a reconstruction diagnostic,
not a new beauty recipe or a continuation of the denoise grid.

The failed full-native house uses an exact-aspect 1360x816 resize of a 1680x1008 base. Isolate that
resize and the Qwen VAE before assigning all smoothing/bottom-edge failure to diffusion. Extract the
existing verified graph's LoadImage 41 -> ImageScale 160 -> VAEEncode 156, Qwen VAE loader 146,
and decode that latent directly through the installed stock VAEDecode. Save both the actual resized
input and reconstructed output. No denoiser, text/vision conditioning, LoRA, mask or postprocess is
used. This is not an identity-generation mechanism: it tests reconstruction of exact existing pixels,
so it cannot establish a new identity lock or an accepted High.

The installed stock `nodes.py` encode/decode implementations were read. The same Qwen VAE hash and
native dimensions are retained, and live nodes/models plus both GPUs/queues are checked. Use locked
3090 only after releasing this thread's confirmed completed cache. Compare pixel-aligned texture,
face appearance and the bottom-edge strip at full size; a clean reconstruction would locate the
visible failure after encoding, but would not by itself prove an exact cause inside the denoiser.
The current [Qwen model card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) also uses 40 steps,
whereas the evaluated pilot used the installed Comfy note's 20-step option. Only if the codec check
supports it, consider a single 40-step numerical-quality check without changing prompt or denoise.

Codec isolation completed as prompt `7b1c749e-a67b-4352-a0af-ea7ff4d1a3df` in 0.929 seconds.
Executed PNG graph and file hashes verified. Identity is 0.784666 resized base, 0.777827 VAE-only,
and 0.754328 generated High. Reconstruction PSNR is 34.69 dB / MAE 2.87 in 8-bit units.
Visual face comparison retains pores/crease detail in the VAE-only result; it does not reproduce
the generated result's uniform smoothing. The bottom-strip discontinuity is also absent from the
reconstruction: maximum near-bottom mean row step is 5.41 versus 17.67 for generated High at row808.
These observations locate the large visible failures after encoding, not an exact denoiser cause.
Audit and comparison files: `work/upgrade-source-faithful-20260903/qwen-house-vae-diagnostic/evaluation`.

Proceed with ONE 40-step quality diagnostic on the same three-reference full-native house graph.
Change only sampler steps20 ->40 and output filename. Keep exact prompt, seed8675416, denoise1,
CFG4, Euler/simple, shift3.1, CFGNorm1, official model hashes and 1360x816 whole-frame dimensions.
This tests the model card's 40-step setting after codec isolation; it is not a prompt/denoise grid.
Native genuine portrait/reference conditioning and its limitations remain as documented above.
Accept only with visibly real skin/hair/background, no border, recognizability and closed-lip/source
direction checks. More steps are not assumed to fix any failure. If unchanged, reject insufficient
sampling as the explanation; do not promote or hide artifacts with cropping/restoration.

## Newly isolated reference-packing discrepancy (not yet a proven artifact cause)

While the 40-step job runs, inspection found a specific inference-preparation difference.
The installed native Plus encoder scales each VAE reference to ~1MP and rounds each edge to8.
House Picture1/3 become1320x792 ->165x99 latent cells; genuine Picture2 becomes888x1184 ->111x148.
The installed Qwen transformer `process_img` packs2x2 latent patches using
`common_dit.pad_to_patch_size`, whose default is **circular**. Thus house reference latents wrap one
cell at both right/bottom, and the portrait wraps one cell at right. The OUTPUT1360x816 itself has
even170x102 latent dimensions and needs no such patch padding. This is a reference issue, not proof
that output dimensions must be64-aligned or that the VAE itself creates the strip.

The [Qwen-authored Diffusers Plus pipeline](https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/qwenimage/pipeline_qwenimage_edit_plus.py)
uses `calculate_dimensions` rounded to32 for VAE references, explicitly accounting for2x2 packing.
Its actual house dimensions are1312x800, genuine portrait896x1184. This avoids odd latent edges.
[Current Comfy Plus source](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_qwen.py)
still uses8; [packing helper](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/ldm/common_dit.py)
still defaults circular. The wrapped-reference border is a testable explanation for the generated
edge strip, not an established cause of smoothing or a claimed upstream bug affecting all images.

A bounded packing diagnostic can retain all native grounded-VL inputs and disable only the optional
VAE argument to Plus. Use the SAME images through native area ImageScale -> VAEEncode ->
ReferenceLatent, appended in original1/2/3 order to BOTH CFG branches, then the unchanged
index_timestep_zero method. Source review verifies ReferenceLatent appends the exact same
`reference_latents: [latent samples]` conditioning field with the same helper as Plus; stock VAEEncode
wraps `vae.encode(pixels)` in a samples dictionary. All three LoadImage inputs are RGB, so this is
the same three-channel input as Plus's `pixels[:,:,:,:3]` slice. No custom model/node,
identity mechanism, mask, postprocess or extra model is introduced. Only reference VAE sizing changes
to the author's32 rounding; semantic384² processing, output framing and all sampler settings stay fixed.
This avoids modifying/restarting the live encoder. Check every link and actual reference size before
submitting. Compare against the20-step full-native run at20steps, not against40 with two variables
changed. If attempted, retain failure evidence and judge skin/identity independently from border removal.

Preparation tests now exercise the actual installed Plus/VAEEncode/ReferenceLatent method bodies
with shape-only image/encoder fakes (no GPU/model imports). At native8 sizing, split and combined
paths yield identical token inputs, conditioning metadata and ordered appearance inputs on both CFG
branches. At author32, only the VAE reference dimensions change. This is algebra/shape coverage,
not numerical VAE or visual proof. Three such tests and17 layout tests pass; layout checks reject
duplicate Plus+explicit VAE inputs, swapped/missing latent chains, odd sizing, crop and bypassed CFG
branches. The live API exposes all required native nodes. The runner's default remains native packing.

Forty-step job `31d76126-4ea8-4cf8-9524-2fba4c61f8f9` completed in573.173seconds. Native likeness
0.750044, source-pose error3.712536degrees, closed-lip ratio0.000258. Native/full-size, face and
thumbnail review shows the same uniform smoothing and bottom strip as20steps. The near-bottom row
discontinuity is18.18 (20steps17.67), at the same row808. Canonical executed-graph comparison confirms
only steps and output filename differ. More steps did not remedy this failure; preserve the rejected
unretouched result and `qwen-house-vae-diagnostic/steps20-40-comparison`. Proceed with the independently
diagnosed native reference-packing test at20steps. The first packing preparation failed before writing
a manifest or submitting due to PowerShell comma/division precedence in diagnostic dimension metadata;
parentheses corrected that expression. No generation was submitted by that failed preparation.

Aligned-reference run `5b58a6cb-36ee-489e-918a-4403951b994c` submitted once after successful preparation.
Structural JSON comparison confirms identical sampler node, prompt, ordered reference records and model
hashes to the20-step full-native parent. Existing-node changes are151/149 (optional VAE removed),148/147
(same method after explicit append chains) and9 (filename), plus12 native sizing/encoding/append nodes.
A preceding stringified-JSON comparison falsely flagged property ordering; parsed-dictionary comparison
and reference-layout validation pass. Locked3090 preflight passed after freeing only our completed40-step
cache, verifying memory fell to1095MiB. Secondary4070 remains untouched. Twenty Python native/layout
tests and five PowerShell dimension tests pass. No production node/UI/workflow files changed.

Aligned-reference test completed in288.794seconds. Native likeness rises0.754328 ->0.782525,
source-pose error3.376024degrees, closed-lip ratio0.003264. The bottom strip is absent at native size;
near-bottom row discontinuity falls17.67 ->3.66. The strict packing-only comparison verifies prompt,
seed, steps, CFG, model/reference hashes and all unrelated graph fields unchanged. This supports the
packing diagnosis for this case; it does not prove circular padding alone caused every artifact.
Full-frame/face/thumbnail review still finds uniformly smoothed skin and a tense brow, and the strict
source-pose diagnostic still fails. No common polish or gaze correction was applied to hide this.
It is a successful technical refinement, not accepted three-photo High quality.

Use ONE controlled refinement of the corrected graph: add a focused negative text describing the
observed tense scowl/puffy cheeks/waxy skin/painted hair/teeth failure modes. Keep the positive prompt,
three references, author32 sizing, seed8675416,20Euler/simple,CFG4,denoise1 and whole frame unchanged.
The native negative encoder still receives all three semantic references and the same ordered VAE
appearance latents; only its previously empty text changes. The official Diffusers Plus pipeline
documents `negative_prompt` and computes positive/negative predictions with the same reference images.
This is trained classifier-free guidance, not a new identity signal or a proven aesthetic remedy.
Exact text: `work/upgrade-source-faithful-20260903/qwen-high-negative-realism.txt`.
Check recognizable features, more appealing eye/brow/closed smile, non-puffy contours, actual pores/
hair/background and source pose/gaze. Preserve any failure and do not run a negative-prompt grid.

Negative-text refinement `8a0fd5e3-9c74-4897-9139-1e11ac7d26a0` submitted once. Prepared graph
passes the explicit native-reference validator; restoring only node149's negative text and node9's
filename makes it equal to the aligned parent graph. Reference records and model hashes also match.
Both queues were empty and3090 memory1160MiB after releasing only the completed aligned-test cache.

Negative refinement completed in289.030seconds. Native likeness0.753165, source-pose error3.091040
degrees, closed lips0.001500, source-mouth error0.019008 (aligned parent0.024425). The clean bottom
edge remains. Native-size review finds more visible skin texture but also more dark facial speckles;
the tense brow is not satisfactorily relaxed. Preserve this result; no negative-text sweep follows.

The existing common freckle/hair treatment and final source-gaze finish were then applied once on CPU,
with forced mouth lift and cheek highlight disabled as in prior experimental finishes. Complete likeness
0.748471 versus matched revised Low0.770816; relative to raw0.779115 the drop is0.030644, slightly
beyond the unchanged conservative0.03 diagnostic. Do not silently round that to a pass. Source-pose
error3.138025degrees remains over3. Lips remain closed0.001478, max horizontal gaze error0.01047;
both2D gaze errors improve1.245->0.543px and1.187->0.429px. Finish-exterior pixels are exact to the
native candidate. Full-size/face/thumbnail review still finds artificial-looking facial texture and
insufficient recovery of the original appealing expression. This is NOT an accepted stronger High,
not three-photo validation, and not a production update. The comparison labels the experimental Low
accurately as REVISED LOW, not the current shipped Low.

This goal turn is progress: codec isolation, the failed40-step quality hypothesis, and a successful
reference-packing correction isolate actual technical behavior. The allowed negative-text refinement
does not solve aesthetic quality. Stop this parameter sequence and diagnose the remaining expression/
appearance conditioning before another generation. Original sources have more directional/contrasting
facial illumination than the accepted detailed bases, while the present Qwen role text explicitly locks
Picture1 lighting and rejects Picture3 color/texture. This is an observed difference and a possible
constraint conflict, NOT a proven reason for attractiveness or permission to blindly add a relighting
stage. Any illumination hypothesis needs a measurable source/base comparison and its own bounded
native test; do not add a lighting/mask/restoration stage merely because High remains difficult.
No generation remains queued. Public node, High/Low, gaze, UI and workflow hashes retain their
pre-goal values. Integrated three-photo quality and production delivery are still outstanding.
# Direct-original diagnostic (experimental; not production)

First result `8520bd17-8e18-4a04-9542-8913264057e7`, saved under
`work/upgrade-source-faithful-20260903/qwen-original-direct-house/`, failed badly.
Native likeness .314652 (source .657355, old raw .779115); source pose drift6.716381
degrees, eye-coordinate drift .137187. Closed-lip diagnostic passes and no teeth
are visible, but the expression is exaggerated, the face generic/stylized, skin has
uniform rendered texture, hair is ridged/painted, and background remains blurred.
This is not the user's permitted *slight* likeness tradeoff. No finish or production
promotion. One controlled refinement: denoise1 to .35, keeping everything else
including the two originals, seed, prompt and corrected packing unchanged. This
tests retaining source spatial initialization; it does not add an identity mechanism.

The one refinement completed as `d0f658bf-5550-4a08-8bb4-5073640bd79f` (196.44s),
under `qwen-original-direct-house-retained/`. Parsed graph comparison confirms ONLY
denoise1 -> .35 and output prefix changed; all reference records and model hashes
are identical. Native PNG graph/hash/provenance verification passes. CPU diagnostics:
likeness .684268, source-pose delta .970767 degrees, raw-pose delta3.342089 degrees,
closed lips .000654, maximum source-relative eye-coordinate delta .060447. Likeness
is above the original's .657355, but below raw .779115 and actual Low .738950; the
strict .70/.03 and raw-pose diagnostics remain failures. This is not rejected solely
by those thresholds: full-size/thumbnail visual review shows overly uniform rendered
skin, ridged/painted hair, and still-blurred background. Eyes/brow expression is much
closer to the original than Low, no teeth are visible, and there is no bottom strip.
No finish, production promotion, or redundant canyon/third run of this failed recipe.
The two-test direct-original route is closed; do not run a prompt/strength grid.

An asynchronous user question shows Source / actual Low / this .35 result and asks
whether its eyes/expression are closer, explicitly excluding the failed texture and
background from approval. This is NOT the older question about the generated
sourcebase .688 result. No answer yet. This qualitative check helps distinguish the
desired presentation from a misleading numeric-only acceptance decision.

Re-inspected earlier source-contour-final-gaze canyon and house comparisons: their
background/detail and likeness are safer, but the house High change is still modest.
The geometry prototype explicitly fixes brow pixels, unlike the source's different
brow presentation; its existing High warmth is tiny. These are diagnostic facts, not
proof that broader geometry or color transfer would solve the problem. No new
postprocess was added or queued. Do not claim those earlier trials are approved.

23 Qwen reference/packing unit tests pass, including rejection of false inherited or
active smartphone-LoRA claims on a direct-original experiment. Production node,
High/Low/gaze modules, UI and workflow hashes remain unchanged from the goal's
baseline. Both generation queues are empty after these completed experiments.

The presentation diagnostic compares broad low-frequency RGB/Lab statistics in an
eroded face oval excluding brows, eyes and lips. It is not a lighting/beauty estimator.
House source / raw / negative-High relative luminance spans are .362 / .550 / .460;
canyon .475 / .411 / .402. Thus a universal "add contrast" correction is unsupported.
Both outputs are less warm/red-yellow than their sources, especially canyon. The
comparison sheets also show that the generated base already changed the appealing
eye/brow presentation. No color transfer or relighting stage was added.

All previous Qwen trials edited a generated base; inventory confirms none edited the
original directly. Next bounded hypothesis: original as Picture 1, genuine training
camera still as Picture 2, no competing generated face or third reference. Reuse the
installed 2511 author-derived graph, fixed 20-step Euler/simple CFG4, shift3.1,
CFGNorm1, full denoise, whole-frame ~1MP, author32 reference packing, seed8675416,
existing positive text and empty negative. This tests the source/conditioning route,
not a new model or prompt grid. One controlled refinement maximum before diagnosis.

Research gate: the ordered images enter BOTH grounded QwenVL semantic encoding and
VAE appearance-reference latents. The original controls composition/expression and
the distinct camera still supplies identity appearance through Qwen's trained
portrait/multi-image edit mechanism, not generic img2img alone. At full denoise the
sampler's encoded source supplies shape, not retained spatial initialization. Roles
are requested, not perfectly isolated. [Qwen 2511 author card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)
documents improved portrait consistency and a two-image example; [2509 card](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)
documents the inherited multi-image editing capability. This supports an experiment,
not a promise of identity preservation. Native node/template/model compatibility and
author32 packing were verified in the preceding sections and remain unchanged.

Phone provenance is explicitly different: **experimental native phone prompt only**,
NO active Klein phone LoRA, NO inherited phone-on image, Turbo/Lightning off. The
Klein baseline report supplies only comparison and seed. Production's phone-on default
is unchanged; this candidate must not be described as an equivalent phone-LoRA test.
Evaluate source presentation, realism/background, obvious High improvement, no teeth,
identity against six separate genuine photos, pose and gaze. Preserve failures.
