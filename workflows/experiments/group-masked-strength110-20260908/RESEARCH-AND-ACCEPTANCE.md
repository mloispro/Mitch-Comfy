# One controlled Group identity-strength refinement

Requested by Mitch's September 8 "fix it". This is a new experiment; the completed
0.90 pilot, its rejected image, and every prior runtime receipt remain unchanged.
No production replacement or quality claim is authorized by preparation alone.

## Decision before generation

Change only node50 `strength_model` from 0.90 to 1.10, plus the output filename
prefix. Same seed8675412, 832x1216, 30 Euler steps, CFG4, legacy FP8 Base9B,
Qwen3 mixedFP8 encoder, full Flux2 VAE, Phone LoRA0.25, V3 rank32 DOP step1600,
references, prompts, masks and conditioning layout. No sharpening, face swap,
restoration, crop replacement, upscale or alternate seed.

The previous pilot completed correctly but failed identity: centroid .5225072503,
minimum genuine-reference similarity .3565687537. All six declined from the
all-white image-only control. Bystander distinctness passed. The native main-face
interior is already mask1.0; increasing mask strength does not repair an omitted
face. Both regional model calls still share the evolving full-frame latent.

Earlier 9B V3 step1200 LoRA-only .90-to-1.10 diagnostics improved main similarity
in all eight tested failure scenes (+.0285 to +.0694), while six still failed
and some crowd leakage worsened. This is directional evidence only, not proof
for step1600 with native references and regional hooks. A 22.2% weight increase
does not imply a 22.2% likeness gain. The current identity deficit is substantial.

More directly relevant counterevidence is preserved in the September3 global
Group30 step1600 .90-to-1.00 test: centroid .619344 to .633458, minimum .503593
to .512850, without a clear visible improvement or a full identity pass. That
global branch was closed, not extended to a1.10 sweep. This single newly masked
branch refinement is distinct, but that result lowers confidence in a cure and
must not be hidden behind the earlier step1200 directional evidence.

## Actual identity mechanism and compatibility

The V3 character LoRA was trained against FLUX.2 Klein Base9B with the
`m1tch_person` trigger, rank32/alpha32, UNet training and no text-encoder training.
The preserved scalar audit confirms .90 was applied as .90, not divided by rank.
The selected step1600 checkpoint and all installed node/model pins are reused.

Target branch: guide LoadImage10 -> 416x608 -> VAE -> first ReferenceLatent;
genuine front04 LoadImage20 -> 864x1152 -> VAE -> second ReferenceLatent;
genuine angled photograph LoadImage40 -> 432x576 -> VAE -> third ReferenceLatent.
Both positive and negative receive these ordered native latent references.
Node50 adds the trained character model hook to both target conditionings at
node53, through the whole-visible-person mask. Complement branch receives only
the face-cleared composition guide, no character hook or genuine identity refs.
The complementary masks mix full-frame denoising predictions. They do not lock
attention or mathematically isolate identity across sampling steps.

The composition guide is not an identity photograph. Evaluation uses the same
six genuine photographs, never synthetic outputs. EmptyFlux2LatentImage supplies
the initial latent; this is not img2img or host-face swapping.

Primary sources inspected for this work:

- [BFL Base9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
  identifies the undistilled base and native multireference editing capability.
- [BFL Klein training documentation](https://docs.bfl.ai/flux_2/flux2_klein_training)
  supports Base-model character LoRAs and trigger-based use.
- [Comfy author's model-hook masking documentation](https://blog.comfy.org/p/masking-and-scheduling-lora-and-model-weights)
  and [shipped masking example](https://raw.githubusercontent.com/Kosinkadink/ComfyUI/workflows/lorahookmasking.json)
  support native conditioning-bound hooks. The example is not a validated Klein
  identity workflow; compatibility comes from the installed native contract,
  alpha checks and completed previous run, not its older model choice.

The BFL example uses 50 steps/CFG4; the existing 30-step FP8 route is a local
tested adaptation, not an official identity guarantee. Existing training uses
768/1024 resolution buckets. This approximately1MP aspect and hook layout were
already executed; no new trained-aspect guarantee is inferred.

Local evidence: `work/flux2-klein9b-identity-v3-r32-dop/nine-scenes/`
`v3-dop-step1200-s1.10-acceptance-failures-diagnostic/strength-comparison.json`,
the V3 training configuration, and the previous masked pilot ROOT-RESULT.md.

## Fixed acceptance, declared before seeing a new image

One image only. Two independent full-size and thumbnail visual reviews before
scoring. Main selection is geometric, not highest-scoring. Keep every raw score.
Centroid >=.55; all six genuine comparisons >=.5533463954925537;
maximum bystander-to-genuine <.42; bystander-to-main <.50;
distinct bystander-pair <.72. A classifier `near_match` is not acceptance.

Require recognizably correct likeness, age/hair, natural skin, plausible bodies,
own arms/hands/glass contact, closed lips and source-compatible gaze, distinct
bystanders, coherent depth/sharpness/noise and no pasted-head halo. Preserve four
principal adults and readable partial fifth-person coverage at the right edge.
The existing prompt names four principal adults, not the edge person explicitly;
its previous disappearance is a known separate scene-preservation risk. That
requirement is not waived and the prompt is not silently changed in this test.

Before queueing: live node/model availability, both GPU/production queues and
exact worker ownership checked. Use a new disposable3090 worker; preserve the
explicit3090 lock, other work, original41/41 prequeue,40/40 preUNet,30/28
presampler gates and12/10 host/commit observer floors. Stop only the exact owned
worker after terminal evidence. Existing evaluation provenance checks remain.

If this one refinement fails, close it with an explicit mechanism decision.
No strength grid, rescue seed, lowered identity floor or automatic promotion.
