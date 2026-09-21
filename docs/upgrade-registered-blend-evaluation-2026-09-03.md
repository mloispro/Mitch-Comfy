# Registered native-variant blend — bounded fallback experiment

Status: canyon pilot/refinement and frozen house validation evaluated; not a
successful general solution, not production. The preceding goal turn made progress: it
measured texture loss and removed redundant smoothing from experimental High on
three cached photographs. That retained detail but did not resolve the central
expression/likeness conflict. Do not repeat a texture/sharpening sweep.

## Evidence and scope

The compact-negative canyon native output has the source-like closed smile and
head angle requested, but genuine-reference likeness is0.422 versus baseline
raw0.752. Its inherited four-reference identity mechanism did not guarantee a
recognizable result. The previous native/Qwen and source-relative geometry routes
are documented failures or incomplete results, not accepted alternatives.

This one CPU pilot tests a registered **face-region composite of two generated
variants**, not an identity-photograph face swap. It is a fallback to the project's
preferred native whole-image approach, not a claim that compositing is inherently
better or identity preserving. No genuine reference pixels are pasted into a face.
No source photograph is used as an identity scoring reference.

The two inputs are the audited raw canyon baseline and the completed negative-
guided native variant `ef7fce54-a1b5-4351-8175-2fa721b10a23`. Both originally used
the same genuine-photo-trained V3 rank32 step1600 Klein Base9B identity LoRA0.9,
genuine portrait, smartphone v13 LoRA0.25, Base9B fp8 loading, Qwen3-8B encoder,
full Flux2 VAE,50Euler/CFG4 and seed8675412. Phone on/Turbo off. Their text policies
differ; this is not an isolated generation-prompt comparison.

The unchanged native conditioning mechanism remains:

1. Scene1 -> Flux2 VAE -> ordered native reference latent: edit-source/composition.
2. Face-free edge guide -> VAE -> reference2: composition geometry.
3. Genuine portrait -> VAE -> reference3: explicit identity image alongside the
   independently genuine-trained character LoRA.
4. Genuine hair-material crop -> VAE -> reference4: material/style, not identity.

All references enter both native CFG branches. This documented
[Base9B native edit model](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
and [character-training mechanism](https://docs.bfl.ai/flux_2/flux2_klein_training)
are upstream conditioning; the new blend itself is **not identity conditioning**.
The recorded raw/variant provenance and current file hashes must be verified.
No model download, installation, new graph, GPU job or service restart is required.

## One recipe and acceptance

Start with amount0.4, shared by geometry and appearance. Refined landmarks from
both generated variants define intermediate internal eye/brow/nose/lip/cheek
locations. Fix the base outline/hairline controls. Map both images to this common
geometry with thin-plate-spline inverse maps, then blend within a feathered face
interior. Preserve base hair, body and background exactly outside that region.
Use the existing final source-gaze correction and inspect raw blend separately.
Do not add smoothing, relighting, grain, restoration or hair polish to this pilot.

[SciPy RBFInterpolator](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.interpolate.RBFInterpolator.html)
documents the spline/smoothing solver; [OpenCV remap](https://docs.opencv.org/4.13.0/da/d54/group__imgproc__transform.html)
documents output-to-input pixel sampling. These sources support the mathematics,
not a prediction of beauty or likeness. RGB/geometry interpolation does not imply
linear identity similarity. Reject folded maps (minimum inverse Jacobian0.25),
oversized displacements, visible double features or cutout seams.

Evaluate genuine-photo likeness, source pose/gaze, closed lips, face placement,
forehead, cheek fullness, texture, boundary integration and Low/High separation
at full size and thumbnail. Verify exact background/hair guards before gaze and
the combined exterior afterward. Preserve failures without changing acceptance
thresholds. At most one controlled amount refinement after diagnosing this pilot;
do not begin a blend/mask/color-strength grid. A successful canyon pilot still
requires the same recipe on house and an excluded-from-scoring genuine third
photograph, followed by production integration and end-to-end verification.

The first evaluator preflight stopped before creating a candidate because the
public node's before-polish PNG has no embedded `prompt` metadata. Its sidecar is
the public two-node wrapper, not the expanded native graph. The evaluator now
requires its exact previously audited image hash and validates the recorded
source hash, wrapper class, seed, phone setting and engine/model sidecar. It reports
that provenance limitation explicitly; only the beauty variant's embedded executed
graph is verified. It must not claim both executed graphs were independently
verified from the PNGs. Five CPU geometry/blend safety tests pass.

## Amount0.4 pilot

Completed CPU evaluation in `registered-native-blend-canyon/` with no diffusion.
Raw blend likeness0.677671; after source gaze0.677109, versus actual Low0.746137,
base raw0.751794 and extreme native variant0.422163. It still fails the recorded
conservative likeness diagnostic; that is not the sole visual acceptance decision.

Both inverse maps are nonfolding (minimum Jacobians0.5310/0.4787). Base/variant
maximum displacements5.56/8.71px; fitted landmark errors0.27/1.44px before boundary
taper. Base hair and composite-exterior pixels are exact. Final source pose error
2.205891degrees; lips remain closed(.003039) and horizontal gaze error.013178.
Full two-coordinate eye error.037382 is recorded separately, so no exact-gaze claim.

Native-size, face and thumbnail review finds a visibly more source-like eye/brow
and closed-smile presentation than Low, with less likeness loss than the extreme
variant and no obvious hard pasted boundary. It still contains baseline freckles/
creases and some softer mixed detail. It is not a completed handsome polish.

One controlled refinement uses amount0.3 with identical inputs, registration,
boundary policy and final gaze. The aim is to recover likeness while retaining
visible separation, not to optimize only the embedding score. No further amount,
mask or color sweep follows from this experiment.

## Amount0.3 refinement and frozen cross-photo test

The sole refinement completed in `registered-native-blend-canyon-030/`.
Final likeness0.699880 (raw blend0.696606), source-pose error2.299782degrees,
closed-lip ratio0.003466, horizontal gaze error0.013358 and full eye-coordinate
error0.047748. Both maps remain nonfolding (minimum Jacobians0.6230/0.3966),
hair is unchanged before gaze, and final combined-exterior pixel error is zero.
Full-size, face-crop and thumbnail review shows no obvious hard pasted seam,
but the smaller eye/smile change moves back toward Low. Skin speckles and
forehead creases remain. Neither amount is a complete beauty solution.

Mitch explicitly chose **stronger beauty editing while remaining recognizable**.
Accordingly amount0.4, not0.3, is frozen for a house-photo generalization test.
This is a visual tradeoff, not a claim that0.677 is an identity lock or that the
old0.70/0.03 diagnostic passed. No thresholds or production defaults change.
The house beauty render uses the exact canyon positive and negative prompt files,
four reference roles, five model weights,50Euler/CFG4, identity0.9 and phone0.25;
only the case-specific source/guide, baseline dimensions and recorded seed differ.
The same registration and final gaze recipe then applies without per-photo tuning.

The current BFL model card and training documentation were rechecked before the
house test; they support native editing and character LoRA conditioning, not a
promise of identity preservation. BFL's help page does not endorse negative
prompting. This remains the already-tested experimental local CFG negative branch,
not an official BFL recommendation; see the compact-prompt evaluation for source
code evidence and limitations. No new model or conditioning mechanism is introduced.

House job `3e30ed4f-7448-4bb0-b332-e3aff50d1443` was submitted only after both
queues were empty, the latest completed3090 job matched our canyon job, its idle
model cache was released, and3090 memory was rechecked at1123MiB/utilization0.
The4070 remained idle and was not used because Upgrade is explicitly3090-locked.
The runner freshly verified the five model hashes and all required live node/model
names. House manifest SHA256:
`D90422510E24CC94178FE894AD4D9D069EA1DDF091A857CF1251C1627ED1FFA4`.
An exact submitted-graph comparison found only source100, guide110, recorded
seed20, width/height23/24 and save-prefix27 changes. Both text branches, model
settings and ordered reference policy match canyon. Executed-PNG verification
is still required after completion.

The house baseline uses the observed `Flux2Klein9BPhotoRealismUpgradeV11` wrapper,
where canyon usedV1. The evaluator now accepts exactly those two recorded public
classes and additionally validates `source_photo == ['1',0]`; it does not relax
image/hash/seed/phone provenance or claim an embedded graph for these intermediates.
Eleven CPU tests pass, including input immutability, fixed exterior/hair, invalid
inputs, folded-map/oversized-shift rejection and both wrapper provenance cases.

## House result and mechanism decision

The house job completed successfully in501.707seconds at the baseline's actual
1680x1008 resolution (1.69MP, not an approximately1MP timing benchmark). The raw
PNG's executed graph matches the saved manifest. It scores0.741355 against six
genuine photographs, versus raw0.779115/actual Low0.738950. Source pose error is
2.198845degrees, source mouth-corner error0.014931, lips closed0.005476 and raw
eye-coordinate error0.044975. The conservative likeness-drop diagnostic fails
by0.007760 beyond its0.03 allowance; that alone is not the rejection reason.

The frozen0.4 blend completed in `registered-native-blend-house/`. It scores
0.757880 after gaze (0.760332 before), with closed lips0.000450 and horizontal
gaze error0.013833. Full eye-coordinate error is0.026763. Exact hair protection
and zero final combined-exterior pixel change pass. The maps remain nonfolding:
minimum Jacobians0.597736/0.513234 and maximum shifts3.53/6.11px.

However, source-pose error is3.531103degrees, worse than the native beauty
variant's2.198845 and still near the baseline's3.672880-degree yaw error. This
is an observed limitation of retaining the base outline/geometry, not permission
to silently relax the source-pose gate. Native/full-size, face-crop and thumbnail
review of both raw beauty and blend finds the following:

- The raw beauty keeps a tense inner-brow/frown presentation and does not recover
  the input's more appealing eyes/expression; its background also remains soft.
- The blend keeps the baseline's detailed siding/tree background exactly, but
  looks too similar to Low at thumbnail scale. It does not provide consistently
  stronger attractive eyes/expression on this second photo.
- There is no obvious hard pasted boundary, but residual speckles, forehead lines
  and the requested expression improvement remain unresolved. Good likeness and
  seam diagnostics do not turn this into a visual pass.

**Decision:** the canyon improvement does not generalize sufficiently to house.
Do not promote this route, add smoothing to disguise its expression failure, or
run another amount/mask/color sweep. Third-photo diffusion was not queued after
this failed held-out case; it would not establish a three-photo success. No
production node/UI/workflow/model files changed. Phone stays on/Turbo off.

The key evidence for subsequent work is that registration can reduce the extreme
canyon variant's likeness loss, but cannot supply a better expression when the
house beauty render itself does not contain one. The house face also inherits
some pose error from the retained base. These are separate from skin cleanup and
should be addressed at the generation/conditioning level before adding finishing
stages. That is a diagnosis, not proof of which individual model/reference causes it.
