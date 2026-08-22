# FLUX.2 One Reference Identity v1

## Accepted and frozen

Mitch visually accepted this baseline on 2026-08-22: the result looked great and looked like him. This is the
decisive acceptance signal; the automated scores below remain supporting drift diagnostics.

- Release tag: `flux2-one-reference-v1.0.0`
- Frozen registry: `config/frozen-baselines.json`
- Workflow SHA-256: `CB5BAD60751997EF37F8A5D6DE1215F65CDB83E35F3D7BEB539EFDFFB42AF875`
- Identity-core SHA-256: `060AFDBE97433C7CB567C74682D4C45F52AC7B81E1CC5F9B4ED6CED4DC54E7CC`

`scripts/verify.ps1` rejects accidental changes to the workflow or identity core. Presets, multi-reference
support, and other experiments must be implemented beside this baseline and compared against it. The private
LoRA is hash-locked below but is not stored in Git, so it must also have a separate private backup.

## Production route

- Workflow: `workflows/production/FLUX.2 One Reference Photo.json`
- Visible controls: one genuine face upload and one plain-language scene prompt
- Model: `flux-2-klein-base-4b-fp8.safetensors`
- Text encoder: `qwen_3_4b_fp8_mixed.safetensors`
- Identity LoRA: `aitk/m1tch-flux2-klein-4b-identity-v1-best.safetensors`
- Selected training checkpoint: step 1,250 of 1,500
- LoRA strength: `0.6`
- Sampler: Euler, 20 steps, Flux2Scheduler, guidance `4.0`
- Resolution: 768×1024
- Reference strategy: full upload plus automatic 2x face crop, one megapixel each
- Hidden fixed seed: `8675310`
- Conditional retry: once only when single-upload cosine is below `0.75`

The production LoRA SHA-256 is
`8A7D1477914D0A5262BF219F71F303418130449841CF220226B4E979D7232F87`.
The ignored local dataset fingerprint is
`9de44d494c11dc3f0a61f44a65fd3ebfd63e7ac51e4c6c2d5f842718d6b97fe9`.

## Evidence

Four genuine photos were excluded from training and used for local AntelopeV2 centroid evaluation. Their
pairwise cosine floor was `0.7186` and mean was `0.7750`.

| Route | Professional | Phone/candid | Action/profile | Approx. time/image |
| --- | ---: | ---: | ---: | ---: |
| Native 9B KV, four steps | 0.8089 | 0.7505 | 0.4737 | 14–20 s |
| Selected LoRA, 20 steps | 0.8714 | 0.8913 | 0.8216 | 45–48 s |
| Selected LoRA, 30 steps | 0.9205 | 0.9078 | 0.8369 | about 66 s |

Alternate 30-step action checks at the selected checkpoint and strength scored `0.8565` and `0.8755` on
two additional seeds. Visual review confirmed photographic skin/lighting and plausible professional, cafe,
and walking scenes. Pose direction varied across alternate seeds, so production retains the validated hidden
seed rather than exposing seed search as a user control.

The final 1,500-step checkpoint was rejected: its action/profile score regressed to `0.7694` in the controlled
30-step, strength-0.8 comparison. Step 1,250 was selected on held-out results and visual realism, not training
loss or checkpoint recency.

## Final smoke test

The exact production node was restarted and queued with only `face_reference` and `scene_prompt`. It completed
in `47.803` seconds without retry, scored `0.8993` against the upload and `0.8509` against the four held-out
photos, and wrote schema-v3 metadata under `ComfyUI/output/flux2-one-reference`.

These scores are local ranking and drift-rejection diagnostics, not proof of identity. The subject's visual
judgment remains the final acceptance standard.
