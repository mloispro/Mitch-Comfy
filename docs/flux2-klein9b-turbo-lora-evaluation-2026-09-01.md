# FLUX.2 Klein Base 9B Turbo LoRA evaluation — 2026-09-01

## Decision

The rank-256 BF16-standard Turbo LoRA is implemented as a reversible **8 Euler steps / CFG 1** control in
Identity Studio and Group Scene. Identity Studio passed its production-node A/B and opens with Turbo on.
Group Scene keeps it off by default. Upgrade Photo failed both its earlier test and a later clean no-phone-LoRA
same-seed test, so its production node does not expose Turbo.
The 4-step variant remains rejected.

## Primary-source compatibility

The author describes the adapter as a LoRA extraction between FLUX.2 Klein 9B and FLUX.2 Klein Base
9B for Base-model use at 4–8 steps and CFG 1. The current workflow uses the matching BF16 Base 9B
checkpoint. The standard BF16 rank-256 file was therefore selected; FP8 and experimental Frobenius
variants were excluded.

- Author repository: <https://huggingface.co/kalle07/FLUX.2-klein-9B-turbo-lora-set>
- File: `Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors`
- Bytes: `1,386,477,008`
- Verified SHA-256: `A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600`
- Tested order: Base → Turbo `1.0` → Mitch identity `0.90` → Smartphone Reality v13 `0.25`

The author does not document a separate strength recommendation. Strength `1.0` was treated as the
neutral full application of the extracted checkpoint delta and is recorded as an inference, not an
author-stated setting.

## Controlled test

All candidates used the same exact prompt, genuine front-neutral reference, seed `8675411`,
`832×1216`, Euler sampler, and `Flux2Scheduler` on the local RTX 3090. The current prompt included the
default-on appearance treatment, strict closed-lip geometry, eye refinement, and the trained
`casual snapshot` trigger. No image was uploaded.

| Candidate | Time | Speedup | Identity centroid | Weakest held-out | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Current Base quality, 50 steps / CFG 4 | 153.855 s | 1.0× | 0.8105 | 0.6257 | Baseline; visible-teeth prompt miss |
| Turbo, 8 steps / CFG 1 | 15.799 s | 9.738× | 0.7966 | 0.6145 | Pass initial gate |
| Turbo, 4 steps / CFG 1 | 6.468 s | 23.787× | 0.7895 | 0.6362 | Reject; centroid drop 0.0210 |

The six-photo AntelopeV2 genuine pairwise floor was `0.5533`. All candidates remained calibrated
`strong_match` results and cleared that floor against every held-out view. The predefined promotion
limit allowed at most `0.02` centroid loss relative to baseline. Eight steps lost `0.0139`; four steps
lost `0.0210` and was rejected despite its stronger weakest-view score.

## Full-size review

The 8-step candidate kept a single closed lip line with no visible teeth. The 50-step baseline exposed
teeth even though the prompt explicitly prohibited them. Eight steps retained natural eye geometry and
gaze, visible pores, individual stubble, coherent hair, clothing weave, and stone/background structure.
No obvious plastic-skin or etched-edge failure was visible.

The local texture diagnostic found nearly identical mid-frequency facial structure (`12.980` baseline
versus `12.959` Turbo). Turbo was modestly crisper: micro-luma variation rose from `5.591` to `6.041`
and normalized Laplacian variance from `397.710` to `441.880`. Those metrics do not prove realism, but
the full-size crop did not show objectionable sharpening.

## Production-node rollout

The follow-up used the real custom nodes, native saved reports, the same sources/prompts/seeds per pair, and no
extra restoration or post-processing.

| Production path | Quality control | Turbo | Identity result | Decision |
| --- | ---: | ---: | --- | --- |
| Identity Studio group profile | 156.55 s | 27.03 s | centroid `0.5859 → 0.6552` | Default on |
| Group Scene, current concise production node | 264.94 s | 42.21 s | selected-main `0.5958 → 0.5672`; leakage stayed below limits | Default off; drop `0.0286` exceeds allowance |
| Upgrade Photo | 537.35 s | 51.34 s | centroid `0.8078 → 0.6957`; weakest `0.6151 → 0.5057` | Default off |
| Upgrade Photo, Turbo identity reference refined to `1.00 MP` | 537.35 s | 76.56 s | centroid `0.8078 → 0.7069`; weakest `0.6151 → 0.5283` | Reject for final Upgrade output |

Full-size review found the Identity Turbo output natural, closed-lip, and free of obvious eye/skin/hair/anatomy
regression. The current Group Turbo frame remained coherent with four distinct detected faces, but the quality face
was visibly more faithful and the measured identity loss exceeded the promotion limit. Upgrade Turbo looked
plausible but changed facial geometry and gaze, agreeing with the substantial automated identity drop.

Evidence is preserved under `work/flux2-klein9b-turbo-ab/`, including the exact API graphs, hashes,
queue snapshots, raw timing reports, full-size images, identity report, texture report, and three-way
comparison sheet. Production-node evidence is under `work/flux2-klein9b-turbo-rollout/rollout-20260901-v2`.
The 4-step and Upgrade-default failures are retained and labeled so they are not accidentally promoted later.

The Upgrade refinement kept the exact Turbo graph, source, prompt, seed, LoRA order/strengths, and sampling settings,
changing only the protected genuine identity-reference encoding from `0.50 MP` to `1.00 MP`. It cleared the requested
`0.70` centroid target and improved every aggregate identity measure. It remained below the 50-step route on identity
and tolerant structure F1 (`0.6036` versus `0.6862`). Mitch's full-size review found insufficient background detail
and an artificial whole-photo appearance, so the identity improvement did not constitute a visual-quality pass.
A fresh Turbo-off run reproduced the quality route's `0.8078` identity and `0.6862` structure F1 and remains the
verified final path. Evidence is under `work/flux2-klein9b-turbo-upgrade-idref100/seed8675416` and
`work/flux2-klein9b-upgrade-quality-recheck-20260902/seed8675416`.

## Clean restored-Upgrade retest — 2026-09-02

The restored Upgrade workflow was retested without Smartphone Snapshot v13, removing that earlier confound. The
source, prompt, four ordered reference latents, reference sizes, identity LoRA, seed `8675416`, output resolution,
and deterministic v3 polish were held fixed. The only treatment was Base → rank-256 Turbo `1.0` → identity,
with the documented 8 Euler steps / CFG `1.0` replacing the quality route's 50 steps / CFG `4.0`.

Turbo completed its in-node run in `55.694 s` versus `531.231 s` for quality (`9.54×` faster), but failed the
quality gates. Polished six-reference identity fell `0.7662 → 0.6958`; its weakest view fell `0.5677 → 0.4979`,
below the genuine-reference pairwise floor `0.5533`. Raw yaw changed `+1.6934°`. Guide-to-image mean edge distance
worsened `6.9815 → 11.6686 px`. Background micro-luma detail fell `11.9536 → 4.5229` and Laplacian variance fell
`1268.27 → 255.12`. Facial micro-luma rose `5.565 → 7.073`, with normalized Laplacian variance rising
`366.55 → 890.88`; full-size review showed a softer background and harsher, more synthetic skin/stubble.

The clean test confirms that the Upgrade limitation belongs to this Turbo treatment rather than the phone-camera
LoRA. No further 4-step test was run because the already-rejected 4-step route is outside the stronger 8-step
quality point. The production Upgrade workflow remains Turbo-free. Evidence is preserved under
`work/flux2-klein9b-upgrade-safe-polish-20260902/clean-turbo-ab/` and the candidate run at
`ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260902-171835-440300`.
