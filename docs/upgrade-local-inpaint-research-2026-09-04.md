# Local Klein inpainting: background protection proven, stronger High rejected

Status: pilot and sole source-geometry refinement completed. Background
preservation works; both fail stronger-High face acceptance. No model or
dependency was installed. The separate versioned ParseNet hair-label code repair
is not part of these native graphs and remains pending live end-to-end validation.

Observed failure motivating this research: stronger native High regenerates a
soft background even with PhoneON. An edit region could protect the already
detailed accepted Upgrade background while the model changes the face. This
would be explicitly mask-bounded editing, not whole-image identity locking.
It cannot by itself solve the tense expression, speckles or artificial hair.
Do not retry a failed crop/retouch route under a different name.

## Primary-source and installed-code findings

The [official Diffusers Klein inpaint implementation](https://raw.githubusercontent.com/huggingface/diffusers/main/src/diffusers/pipelines/flux2/pipeline_flux2_klein_inpaint.py)
includes a Base9B BF16 example with source, mask and optional image reference,
using the Flux2 LoRA loader. It encodes the source as both initial latent and
first reference; an additional reference follows it. References enter both
CFG branches. Outside-mask latents are restored to the appropriately noised
source at each Euler step. It uses an empty negative-text branch, rounds image
dimensions to16 and limits ordinary image inputs to about1MP. This is evidence
for a compatible masked-sampling mechanism, not evidence that a face beauty
edit will retain Mitch's identity.

Installed ComfyUI code was inspected without modification:

- `nodes.py`: `SetLatentNoiseMask` attaches a mask to the encoded latent.
- `comfy_extras/nodes_custom_sampler.py`: `SamplerCustomAdvanced.execute`
  passes that mask into `guider.sample`.
- `comfy/samplers.py`: `KSamplerX0Inpaint` reintroduces the noised source
  outside the mask and restores source clean latents in its prediction.
- `comfy/model_base.py`: Flux2 inherits Flux/BaseModel's latent-inpaint noise
  scaling; `comfy/model_sampling.py` CONST uses the flow noise/source mixture.

These paths are relevant to a local adaptation; node names alone were not
treated as compatibility evidence. Exact edge behavior and decoded-pixel
preservation remain untested. Masked latent preservation is not a promise of
byte-identical background RGB because the VAE still decodes the image.

## Remaining gate before any build or generation

Choose one explicit source/reference layout and trace every image. The
genuine-trained Base9B character LoRA plus a genuine portrait must remain the
identity mechanism; neither a synthetic Upgrade output nor a mask is a new
identity anchor. Any departure from the author's source-first reference layout
must be justified and tested, not silently adopted from the old four-role graph.

Define a measurable edit boundary, background preservation and seam/halo test,
plus ordinary full-size/thumbnail likeness, expression, gaze, hair and skin
review. Prefer no additional stage unless the observed background failure
requires it. Do not introduce face restoration, face swap or selective
sharpening. Preserve failed images and allow at most one controlled refinement.

Validate every selected node/model through the live API and inspect both GPUs
and all worker queues immediately before submission. Upgrade stays on3090/8188,
PhoneON and TurboOFF. Do not install Diffusers, a crop/stitch extension or
LanPaint just to follow an example. Current CPU/local packages may be inspected
but are not assumed to contain the latest upstream pipeline.

## Frozen pilot and completed pre-generation gate

Prepared `native-masked-high-house-ready/experiment.json`, SHA256
`A79D8C16D7D690C88675059040985DDE31D6170C8870BAAB2C81A5C3FBAD55F1`.
It follows source-first/reference-second conditioning from the author algorithm:
the existing PhoneON raw is downsampled without cropping to1280x768 and encoded
once, supplying both masked initial latent and first ReferenceLatent. The second
ReferenceLatent is genuine training photo07, verified against original bytes,
dataset manifest and staged9B V3 training file. Both CFG branches receive both
latents. The mask goes only to SetLatentNoiseMask, never to ReferenceLatent.

Identity is supplied by the unchanged protected Base9B V3 step1600 character LoRA
at.9 plus that genuine portrait, not by a mask or synthetic identity claim. Local
V3 configuration and dataset-lock prove the Base9B/768-and1024-bucket training
contract with the genuine manifest. This is a prediction of plausible identity
retention, not a guarantee. Original source pose/gaze still require evaluation;
the detailed raw already has some drift and is not treated as ground truth.

Base9B diffusion BF16, unchanged Qwen3 mixed-FP8 encoder, full Flux2 VAE, PhoneV13
.25,50Euler/CFG4, seed8675417, empty negative text. No crop/stitch, face swap,
restoration, polish or output upscaling. Full denoise inside the mask. Source-only
VAE decode is saved in the same graph as a codec control. Live standard node
schemas have been inspected. Every weight/ref hash and both GPU queues are
rechecked by the submitter, with32GiB host-RAM headroom; no automatic retry/free.

The first two CPU preparations were rejected before submission: inherited
ParseNet class17 selected neck, and a corrected class13 union left a forehead
gap. The final preview uses a joint face/hair outer envelope,9px context margin,
17px inward feather,13.06% nonzero coverage, and includes the forehead without
the erroneous neck rectangle. The final reviewed mask SHA256 is
`a6f735e3a374f768e6e1bbf8ec78979fe24eba0e718377b780103c710255f22c`.
Six CPU graph/mask/label tests pass. This discovery also requires a separately
verified repair to production's hair-mask mapping; production is still unchanged.

Acceptance: a visibly stronger, recognizable High with better eyes/expression,
closed lips, leaner rather than puffier cheeks, clear natural skin and hair,
source-like head/eye direction and coherent PhoneON background. Compare against
six genuine held-outs, source and actual Low; scores alone do not decide beauty.
For edit leakage, compare native output with the same graph's codec control
beyond a64px dilation of mask support: report mean/p99 RGB error and review
seams/halos at full size and thumbnail. Separately report codec-versus-input
background loss so codec damage cannot masquerade as preserved original pixels.
No acceptance or production promotion follows merely from background preservation.

## First native result

Job `7b92689d-65cf-42f8-ac60-3eb86534014b`, queue49, RTX3090/8188, completed
successfully in368.03seconds. The scoped worker log confirms actual diffusion
BF16 with no manual cast. Both queues were empty afterward. The separate
4070 task finished its own diagnostic and released its own cache before this
submission; no other task's GPU models were touched.

Native `raw_00001_.png` SHA256:
`e03468c2d5b5de7a9a6d72cc48cc65ba2e6c273794c53ab58ccf4806aac9e656`.
Codec `codec-control_00001_.png` SHA256:
`96cbddc9dac443fc8233ad5fe06b9f643e630714a1a76c7681ee85205e6bacaf`.
Both are in sibling ComfyUI's `output/upgrade-source-faithful/native-masked-high-house-ready/`.
Executed graph and every LoadImage hash were verified. Native pixels were not
polished, composited, gaze-corrected or sharpened afterward.

Six-genuine-reference similarity0.766098 (actual Low0.738950, raw0.779115).
Lips are closed, opening ratio0.000325, with no visible teeth. Source maximum
pose difference4.444447degrees; raw-to-candidate1.832707degrees. The inherited
raw already differs from the source, so raw agreement does not establish
source preservation. Maximum mixed eye-coordinate difference0.057180; horizontal
differences0.010673/0.034160. Source-mouth-corner error0.048311. These are
diagnostics; the pose flag is not used alone to reject an otherwise useful beauty
edit. The CPU evaluator's exit1 reflects that flag, not a failed render.

Full native, face comparison and thumbnail review: the environment stays
detailed; the expression is warmer and closed-lip, and some cheek speckling
is reduced. However eyes remain Low-like, the smile adds cheek fullness and
creases, the brow still looks tense and hair retains regular bundled highlights.
The source's more defined eye/face appearance has not been reached. No obvious
new head/body halo was seen. Single-person scene: crowd diversity not tested.

Background evidence beyond64px from mask support (77.89% of frame): native vs
same-graph codec MAE0.18553/255, p99 error1/255, PSNR55.393dB. Codec vs original
resized source MAE2.41403/255 and PSNR36.992dB; native vs source PSNR36.970dB.
Thus the mask largely prevents additional background edits, but VAE loss remains
and the source RGB is not byte-exact. Inside the region, native vs codec MAE4.40595.

Decision: useful mechanism evidence, not accepted High or production. An
initial possible follow-up of identity strength.9 to.6 was considered but NOT
prepared or submitted. Reviewing the conditioning exposes a more direct gap:
the original source is used for evaluation only, not supplied to this pilot.
Picture1 is the already-drifted raw; asking the model to preserve Picture1
therefore reinforces its Low-like eyes/pose instead of the preferred source.

The highest-confidence next correction is to append the actual original source
as an explicitly labeled geometry/expression reference while retaining the
author-style raw initial-latent/first-reference pair and genuine portrait2.
The Base9B card supports multi-reference editing and the installed ReferenceLatent
chain handles additional images, but the exact three-role adaptation still
requires its own frozen graph/role audit before submission. Keep models, identity
strength, mask, seed, sampler and negative branch fixed; change only that
conditioning layout and the necessary source-role wording. Do not also lower
identity strength or roll seeds. This has not been prepared or queued.

A future universal recipe must address inherited raw pose drift and pass
canyon/genuine-third plus live workflow integration, rather than cherry-picking
the third's different raw. Background protection alone is not completion.

## Frozen source-geometry correction

Prepared `native-masked-high-source-geometry-house/experiment.json`, SHA256
`e15287686a84c8ade7a6d795248d23d21d25fcf6173f43731c8624d26536f80f`.
The original house source SHA256 `aef8704873c40c92ec365c091ea142998e72b3d80d22b45f55275309165ba5b4`
is appended as Picture3: LoadImage40 -> approximately1MP/16-aligned scale41 ->
VAE42 -> ReferenceLatent43/44 -> positive/negative CFG. It never replaces the
raw initial latent or genuine Picture2, and is not genuine identity evidence.
The mask is the already-reviewed exact same bytes, not regenerated.

The [Base9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
documents multi-reference editing; the author inpaint pipeline retains source
first and appends optional references. Our exact three-role graph is an
experimental adaptation, not an author-tested identity lock. Identity continues
through the hash-verified genuine-trained character LoRA and genuine photo2.
Expected benefit: recover source eye/expression geometry rather than reinforcing
drifted raw geometry. This is a prediction to test, not a proven fix.

Only five nodes are added, with changes to positive/negative guider links,
positive role wording and two output prefixes. All other existing inputs match
the completed pilot exactly. Picture1's body, clothing, framing and environment
remain invariant; source-specific head/eye/closed-lip expression wording now
refers to Picture3. No strength/seed/mask/precision change is bundled in. Eight
CPU graph/mask/role tests pass, including backward validation of the old manifest.
Same visual/identity/gaze/background acceptance criteria apply. This is the one
controlled conditioning refinement, not a new parameter search. Production is
unchanged until an accepted common three-photo recipe and live integration exist.

## Source-geometry refinement result: closed as a stronger-High route

Job `ebeb1e6d-1031-4f7f-b6f6-b86dc23fc8aa`, queue50,3090/8188, terminal success
in542.30seconds. Reading from the submission's exact worker-log byte offset
confirms `torch.bfloat16, manual cast: None`. All input hashes and the embedded executed native/codec graphs
verify against the frozen three-role manifest. Fifty Euler steps, CFG4,
PhoneV13.25, identity.9, seed8675417 and unchanged mask. No postprocess.

Native SHA256 `c7ce32a84ccc6488b76b190a33f4042cd371e9db1cc7649c18becdd1705ec7a1`;
codec SHA256 `9b1d979be23f1dcb49fe9bc3465dd7cb2e0d0e4aa9fc4001fc144ecab4b038c0`.
Six-genuine-reference similarity0.788298, actual Low0.738950, raw0.779115.
Source maximum pose delta3.561104degrees, raw delta0.344454; mouth opening
0.001711 with no visible teeth. Source eye mixed-coordinate max delta0.040462;
mouth-corner error0.026464. Evaluation exit1 is the source-pose diagnostic,
not generation failure; that threshold alone is not the rejection reason.

Full native, face crop comparison and thumbnail review: background detail is
preserved, without an obvious new head/body halo. The face is less smile-inflated
than the first masked pilot but remains Low-like: hooded eyes, serious/tense brow,
coarse dotted skin and regular bundled hair. Source eye/expression appeal is not
recovered enough. Body/clothing integration remains coherent. Single-person
scene; crowd diversity not tested.

Outside the same64px margin (77.89% of frame), native vs codec MAE0.147114/255,
p99 error1/255, PSNR56.435dB. Codec vs resized source MAE2.414027/255,
PSNR36.992dB. Native vs codec inside the edit region MAE1.835389/255, smaller
than the first masked pilot's4.40595. This is consistent with the model returning
the already-drifted raw face despite receiving the original scene separately;
it does not prove a particular reference's isolated causal weight.

Decision: no promotion, no canyon/third sweep of this failed High recipe, no
additional masked seed/strength/prompt grid. Background protection is useful
mechanism evidence, not a beauty solution. The user's preference for stronger
beauty with recognizable likeness remains unmet. Preserve both native results.

Resource record: immediately before preparation submission, both GPU queues
were idle and the latest3090 success was the exact previous owned graph
`7b92689d-65cf-42f8-ac60-3eb86534014b`. One explicitly authorized `/8188/free`
released only that owned cache (HTTP200) to meet the32GiB host-memory preflight.
No4070 cache action, worker restart or automatic submission retry occurred.
