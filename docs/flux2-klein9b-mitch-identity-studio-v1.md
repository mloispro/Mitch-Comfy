# FLUX.2 Klein 9B Mitch Identity Studio v1

## Production decision

This is the normal local photo workflow. It packages the selected nine-scene result: undistilled FLUX.2
Klein Base 9B, the V3 rank-32 DOP identity LoRA at step 1600 and strength `0.90`, and genuine native
reference photographs. It generates the whole image once and does not use a source-scene latent, face swap,
identity pass, restoration, or sharpening.

The protected LoRA SHA-256 is
`D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC`.
Generation is locked to `832×1216`, 50 Euler steps, CFG `4.0`, `Flux2Scheduler`, and the RTX 3090.

## Use

Open `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1`.

1. Choose `GROUP` when anyone besides Mitch is present. It uses one frontal identity photograph to reduce
   identity duplication into bystanders.
2. Choose a `SOLO` angle profile for a one-person portrait. It uses the frontal photograph plus the matching
   genuine three-quarter angle.
3. Choose `FULL BODY` for head-to-feet or body-proportion scenes. It uses the frontal photograph plus the
   genuine full-body reference.
4. Describe the complete new photograph and queue on the RTX 3090.

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
