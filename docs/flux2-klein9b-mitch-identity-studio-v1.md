# FLUX.2 Klein 9B Mitch Identity Studio v1

> Historical internal-engine contract. The duplicate public v1 sheet was removed on 2026-09-03. Use
> `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets`.

## Production decision

This is the normal local photo workflow. It packages the selected nine-scene result: undistilled FLUX.2
Klein Base 9B, the V3 rank-32 DOP identity LoRA at step 1600 and strength `0.90`, and genuine native
reference photographs. The default Fast Turbo route loads the locked rank-256 BF16 Turbo LoRA first at `1.0`,
then the identity LoRA, then Smartphone Snapshot Photo Reality v13 at `0.25` with its trained
`casual snapshot` trigger. It generates the whole image
once and does not use a source-scene latent, face swap,
identity pass, restoration, or sharpening.

The protected LoRA SHA-256 is
`D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC`.
The smartphone-style LoRA SHA-256 is
`1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90`.
The Turbo LoRA SHA-256 is
`A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600`.
Generation is locked to `832×1216`, Euler, `Flux2Scheduler`, and the RTX 3090. Fast Turbo opens on at
8 steps / CFG `1.0`; disabling it restores the exact previous 50-step / CFG `4.0` route without loading Turbo.

## Use

The controls below describe the retained internal engine exposed through the v1.1 visual-preset workflow.

1. Choose `GROUP` when anyone besides Mitch is present. It uses one frontal identity photograph to reduce
   identity duplication into bystanders.
2. Choose a `SOLO` angle profile for a one-person portrait. It uses the frontal photograph plus the matching
   genuine three-quarter angle.
3. Choose `FULL BODY` for head-to-feet or body-proportion scenes. It uses the frontal photograph plus the
   genuine full-body reference.
4. Keep `Visible flattering enhancement` enabled for the clearly visible default treatment, or disable it to
   reproduce the previous exact natural-appearance prompt.
5. Keep `Fast Turbo — 8 steps` enabled for the validated fast route. Disable it only when you deliberately want
   the old `Quality — 50 steps` fallback.
6. Describe the complete new photograph and queue on the RTX 3090.

The enhancement is positive prompt conditioning only. It asks for a recognizably same-person best-day treatment:
roughly 3–5 years younger, a slightly stronger natural jaw and chin, modestly higher cheekbones, improved facial
balance, a slight confident closed-lip expression with every tooth covered, clearer natural eye catchlights and
balanced eyelids, finer-but-visible pores, neatly groomed stubble, reduced fine-line and under-eye emphasis, and a
noticeable light bronze tan. Natural eye size, color, spacing, and gaze remain anchors alongside core face width,
distinctive nose, mouth, ears, and hairline. It adds no reference, mask, face pass, or post-processing stage. The
enabled states are recorded separately as `appearance_polish` and `fast_turbo`; the smartphone-style LoRA remains
locked on regardless of either toggle.

### Prompting rules for Klein Base 9B

The Production node uses the `bfl-flux2-positive-natural-language-v2` prompt contract. Put Mitch and
his required expression or pose first, then describe the other people, setting, camera, and lighting.
Describe the target state positively and concretely. For example, use `lips gently closed, jaw and
cheeks relaxed` instead of `not a big smile`, and use `both hands resting separately on his thighs`
instead of a list of unwanted anatomy failures. Let the genuine reference provide facial detail rather
than adding a long facial-feature inventory that can compete with it.

FLUX.2 Klein has no prompt upsampling, so scene prompts should remain descriptive, but every phrase
should change something visible. A multi-person scene can be longer than a simple portrait; repeated
quality terms, negative-prompt lists, and conflicting expression words should be removed.

The node verifies every reference and the LoRA by SHA-256 before loading them. It refuses to run on the RTX
4070. Important results still require full-size and thumbnail review of identity, apparent age, hair, anatomy,
scene detail, and bystanders.

The style promotion is based on the isolated 2026-09-01 RTX 4070 one-variable A/B at the same seed and graph.
At `0.25`, held-out identity improved from `0.7891` to `0.8100` centroid and from `0.6711` to `0.7029` on the
weakest genuine view, while skin diagnostics showed no oversharpening regression. The exact test and raw outputs
are under `output/smartphone-snapshot-klein9b-fastest-compatible-4070-ab/20260901-203847`.

The 2026-09-01 Turbo rollout used the production node and the same group prompt, references, appearance setting,
seed, resolution, sampler, and scheduler. The 8-step result completed in `27.03` seconds versus `156.55` seconds for
the 50-step control, improved six-photo centroid similarity from `0.5859` to `0.6552`, preserved a closed-lip
expression with no visible teeth, and passed full-size eye, skin, hair, anatomy, and bystander review. The exact
graphs and reports are under `work/flux2-klein9b-turbo-rollout/rollout-20260901-v2`.

## Evidence and rollback

The selected nine-scene run is preserved under
`work/flux2-klein9b-identity-v3-r32-dop/lora-native-reference-nine-scenes/full-nine-s090-ref025`.
Six scenes passed the strong held-out identity diagnostic, the golfer and rooftop were near, the sunglasses
boat scene required manual identity review, both group scenes contained one Mitch only, the rooftop looked
down-left, and the golfer passed full-body anatomy review.

The former Easy Social Photos v1.0.4 graph remains in the hidden legacy archive as the rollback. Other prior
FLUX.2 Dev, Krea 2, ReActor, HiDream-O1, and InfiniteYou graphs remain archived with their evaluation records so
failed or superseded mechanisms are not unknowingly retried.

## Publication validation

The packaged Production node completed its default group scene on the RTX 3090 on 2026-08-30. The raw
`832×1216` output is under
`ComfyUI/output/flux2-klein9b-mitch-identity-studio-v1/20260830-160708-880846` with SHA-256
`2BEBDE16604016A541B801D43F34CCFB54B261068C6450019A76A89046A622EA`.

Full-size review found four adults, one intended Mitch, three visibly distinct bystanders, and complete arms and
hands. AntelopeV2 detected four faces and passed the identity-scope gate: main held-out-centroid similarity
`0.6127`, maximum secondary identity similarity `0.2629`, maximum secondary-to-main similarity `0.3974`, and
maximum secondary-pair similarity `0.4312`, with no leakage failures.
