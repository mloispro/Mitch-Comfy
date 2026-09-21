# Upgrade High: local FLUX.2 Dev native-edit pilot

Status: rejected as a complete High replacement after one strength refinement.
Clearer skin is a partial result, not a finished beauty/pose solution. No production changes.

## Why a different mechanism

The Klein constant-strength, reference-expression and scheduling routes preserve
likeness but retain or intensify coarse skin and tense expression. The common
finish does not repair this. Do not repeat those grids or add another smoothing
layer. Test the already-installed Dev32B native editor and its separately trained
Mitch V2 step1000 adapter. Larger capacity is a hypothesis, not a quality guarantee.

Inventory: current Dev specialty node `flux2_dev_mitch_studio.py`, its live
20260828 validation and cooking output were inspected. The latter has natural
skin/hair and off-camera expression, likeness0.7581. Scene-restage1.1 was0.6240:
native scene references can compete with identity, so this is not an identity lock.
The existing rank16 attention-block V2 adapter was trained on the genuine V3
camera-still dataset with trigger `m1tch_person`, not on generated scene plates.
No new training, model/dependency downloads or installation is part of this test.

## Primary sources and exact supported path

- [BFL official inference repository](https://github.com/black-forest-labs/flux2):
  Dev supports native single- and multi-reference editing and LoRA fine-tuning;
  it is guidance-distilled but NOT step-distilled.
- [Dev model card](https://huggingface.co/black-forest-labs/FLUX.2-dev).
- [ComfyUI author edit blueprint](https://github.com/Comfy-Org/ComfyUI/blob/master/blueprints/Image%20Edit%20%28Flux.2%20Dev%29.json):
  VAEEncode -> ReferenceLatent -> BasicGuider, FluxGuidance4, Euler,
  Flux2Scheduler, empty Flux2 latent -> sampler output0 -> VAE decode.
  Its optional Turbo branch is omitted. Its model-only LoRA hook accepts the
  compatible Dev identity adapter, NOT the Klein identity or phone adapters.
- Local primary training artifacts: `config/flux2-dev-identity-v2.yaml`,
  protected LoRA metadata, dataset manifest and recorded Dev specialty validation.

Keep the proven local Dev FP8 mixed model, local Mistral FP4 encoder (typeflux2),
full Flux2 VAE, Dev V2 identity1.1,28Euler, embedded guidance4 and BasicGuider.
This is NOT Klein CFG4 with a negative branch. Use the author graph with one
additional native reference chain, a capability documented by BFL. Each reference
is resized without cropping to about1MP with16-pixel alignment; output follows
the target reference at about1MP. No latent img2img, face swap, mask, restoration,
selective sharpening, RGB compositing or intermediate beauty stage.

## Image roles and falsifiable test

Picture1: existing audited, detailed PhoneON Klein raw; edit target, whole scene,
background material and camera appearance. Picture2: exact original source;
head angle, pupil focus, appealing eyelid/brow contour and closed-lip expression.
Both are LoadImage -> scale -> full VAE -> ordered ReferenceLatent chains feeding
the SAME guider. Neither is labeled a genuine identity anchor. Identity comes
from the compatible genuine-photo-trained Dev LoRA; native references can still
compete, so measure six independent genuine held-outs and review visually.

PhoneON is INHERITED through Picture1, not an active Dev phone adapter. TurboOFF.
Do not advertise this experimental two-engine route as a9B-only production
workflow. Existing Off/Low/High and PhoneON defaults remain untouched.

First pilot: house seed8675416. Ask for clearly more flattering eyes/brows,
rested clear skin with fine real pores/stubble, lean cheeks, a restrained
asymmetric CLOSED-LIP smile, and natural highlighted hair. Preserve original
head/hairline proportions and source pupil focus; retain Picture1's detailed
background and whole-frame photographic integration. Acceptance is visible
improvement over Low and recognizable Mitch, not a0.7 score alone. Pose, mouth,
gaze and identity diagnostics must be reported even if they disagree with visual
review. At most one controlled refinement; if it fails, diagnose and close this
route. Only a successful pilot can advance to canyon and held-out third with
one coherent policy and a final end-to-end integration test.

Safety: locked3090/8188 only. Check both GPUs/queues, live nodes/model choices,
fresh protected hashes and source provenance before submission. Permit normal
Comfy memory management only when the latest cached job is the exact saved,
owned terminal success. No explicit free, worker restart or4070 intervention.

## Pilot execution

Six offline tests pass: ordered native-reference wiring, embedded guidance and
empty-latent path, compatible model pins, rejection of false phone/Turbo claims,
bounded parameter checks, and read-only ownership/queue guards. Live API accepts
all nodes and four installed model choices. All four weights were freshly SHA256
verified, as were the original/raw pair and all19 genuine dataset photographs.
LoRA header confirms Dev architecture, V2, genuine V3 dataset, trigger and step1000.

Job `06e6bb34-29b2-4d8c-b13b-27818891725d`, queue43, was submitted ONCE on8188
with no node errors. Both cards/queues were inspected before and after hashing;
only the exact owned terminal early15 cache was reused via normal Comfy memory
management. No explicit free or restart. Output and evaluation are pending here;
no quality or production acceptance is implied by successful submission.

All six production implementation/UI/workflow hashes still match the prior
checkpoint. New code is confined to experimental scripts, tests and documentation.

## First result and sole refinement

The1.1 pilot completed in402.25seconds at1328x800. Native output SHA256:
`4fb261ae3a383ee7cd493eef93de242c0553c3a8182b4ef6c00ded4241929e03`.
Six-genuine-reference likeness0.78834915 (raw0.77911484); closed-lip ratio0.00143788.
Head pose[-0.04169,29.75150,5.93023], maximum original-source error3.98361588degrees,
source eye-coordinate error0.11175364. Native PNG metadata exactly matches the
submitted graph; original/raw pairing, protected models and PhoneON inheritance
were independently checked by the evaluator.

Full-size, face and thumbnail review: clearer skin and retained detailed siding/
branches; recognizable face and closed lips. However the eyes are MORE hooded,
the brow remains tense, cheeks look full, and skin/hair still look somewhat
rendered. This is different from Low but NOT the desired High. Source pose/gaze
are also not adequately preserved. No acceptance based on the high likeness score.

Sole controlled refinement: Dev identity1.1 ->0.8 (the existing specialty node's
lower allowed bound). All references, roles, text,28steps, guidance4, seed,
size policy and phone inheritance stay fixed. Hypothesis: reducing the learned
identity patch permits the original attractive eye/expression geometry more
influence; it may instead lose likeness and must be reviewed. This is NOT a
promise that identity and expression disentangle. No later strength/reference/
prompt grid. Do not add a smoothing layer to conceal a failed native result.

The0.8 refinement was submitted once as job
`c38eedd6-f0ce-4896-b028-b973961a7183`, queue44, with no node errors. Fresh
four-model/dataset/source checks and both GPU/queue snapshots passed. Actual
submitted graph comparison proves only node2 strength and node27 output prefix
changed; reference records, model hashes and effective prompt are exact.
The seven graph/safety/refinement unit tests pass. Awaiting the render here.

Existing source-gaze correction is also evaluated separately on the native Dev
outputs, with NO common smoothing or High geometric postprocess. This measures
whether the already-shipped gaze step works on the new raw; it cannot repair
hooded eyelids, cheek shape or head-pose drift and is not a beauty acceptance.

## Final evaluation: partial texture improvement, not the requested High

The0.8 job succeeded in390.69seconds at1328x800, SHA256
`55eb1e316d44db561794170f711a0ba77bb625ed01cb1635a5b4946ab5dac853`.
Six-reference likeness0.79438698; closed-lip ratio0.00101096; original-source
pose error4.95845604degrees; eye-coordinate error0.12377456. Lowering this
identity weight did NOT lose likeness or restore the original eyes. The stronger
score is not evidence of greater attractiveness.

Native full-size, face and thumbnail review: a slightly softer closed smile and
clearer, less creased skin than current Low; detailed siding/branches, stable
body/wardrobe and no obvious cutout halo. However, eyes remain too hooded, the
face appears fuller than the source, hair/skin still have some rendered quality,
and the face turns more toward the camera. It is not the requested eye/expression
and lean-face improvement. Do not run the same failed High on the other two
photos merely to fill a three-photo checklist; no production integration yet.

The unchanged gaze-only finish (no smoothing/High geometry) gave:

| Dev identity | Finished likeness | Source pose error | Max horizontal gaze error |
| --- | ---: | ---: | ---: |
|1.1|0.79226494|4.00748 degrees|0.029672|
|0.8|0.79254770|4.86906 degrees|0.049783|

Both mouths stay closed; pixel difference outside the gaze mask is exactly0.
Both miss the existing0.02 horizontal tolerance. These are diagnostic failures,
not the sole reason for rejection: gaze-only correction cannot restore the
original eyelid shape, smile geometry, cheek proportions or head angle. Final
face comparisons were viewed. No additional eye warp/smoothing/rescue layer.

Diagnosis supported by this experiment: this native two-reference edit can
improve skin while retaining the genuine-trained identity, but it does not obey
the separate original-expression/pose reference closely enough. The0.8 test
does not support solving that failure by simply lowering identity strength.
No claim that the exact internal cause is proven. No later Dev strength,
reference-order or prompt grid under this experiment.

Final checks: all six production hashes are unchanged;3090 queue is empty and
its owned cache was left alone.4070 had active unrelated work at the final
snapshot and was not interrupted or freed. Seven offline tests and diff checks
pass. The full three-photo, end-to-end stronger-High goal remains unfinished.
