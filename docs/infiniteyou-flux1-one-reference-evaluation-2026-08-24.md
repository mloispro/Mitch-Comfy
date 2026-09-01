# InfiniteYou-FLUX v1.0 one-reference evaluation — 2026-08-24

> **Historical record — not current instructions.** This route was rejected and its runnable files are archived. See `docs/STATUS.md`.

## Decision

InfiniteYou is installed and reproducible, but it is **rejected for Mitch's identity-photo workflow**.
The official AES Stage 2 model produced a coherent whole frame without a pasted-head seam, but changed
Mitch's facial structure and apparent age and rendered the requested real background with strong portrait
blur. The author's identity-focused SIM Stage 1 variant improved the held-out score only from `0.5080` to
`0.5502`. That remains far below the genuine-photo calibration and the accepted FLUX.2 production result
of `0.8309`.

This result is preserved so InfiniteYou is not rediscovered and retried as an untested solution.

## Primary sources and compatibility

- Official implementation: <https://github.com/bytedance/InfiniteYou>
- Official native ComfyUI node: <https://github.com/bytedance/ComfyUI_InfiniteYou>
- Official model repository: <https://huggingface.co/ByteDance/InfiniteYou>
- ICCV 2025 paper: <https://openaccess.thecvf.com/content/ICCV2025/papers/Jiang_InfiniteYou_Flexible_Photo_Recrafting_While_Preserving_Your_Identity_ICCV_2025_paper.pdf>
- Base model: FLUX.1 Dev, matching both released InfiniteYou v1.0 variants.
- Author defaults retained: 8 identity tokens, 864×1152, 30 steps, guidance `3.5`, InfuseNet strength
  `1.0`, start `0.0`, end `1.0`.
- `aes_stage2` is the author's default for alignment and aesthetics. `sim_stage1` is the documented
  alternative for higher identity similarity and was the one permitted controlled refinement.
- Optional realism and anti-blur LoRAs were not used; the authors state that they were not used in the
  paper, and adding them would confound the identity-mechanism test.
- The released InfiniteYou weights are CC BY-NC 4.0 and are limited to non-commercial research use.

## Actual conditioning path

The official ComfyUI wrapper was traced before generation:

1. AntelopeV2 detects faces and five landmarks in the genuine input photograph.
2. The largest face is aligned to 112×112.
3. FaceXlib ArcFace IR-SE50 creates one normalized 512-dimensional face embedding.
4. The released image projection model converts that embedding into eight 4096-dimensional identity
   tokens.
5. `InfuseNetApply` attaches those tokens to the released InfuseNet, which injects residual control into
   FLUX.1 Dev transformer blocks during the full denoising schedule.
6. A black `EmptyImage` is the no-pose control hint from the author's minimal graph. It contributes no
   identity, style, scene, or source pixels.

The identity photograph therefore enters through a trained face-embedding and residual-injection path,
not through style reference, generic img2img, prompt text, face swap, a mask, or latent compositing.

## Pinned installation

| Component | Revision or SHA-256 |
| --- | --- |
| Official `ComfyUI_InfiniteYou` node | commit `1c979397c5c80f5ac83a2473a2f7d4503104110f` |
| `flux1-dev-fp8.safetensors` | `8e91b68084b53a7fc44ed2a3756d821e355ac1a7b6fe29be760c1db532f3d88a` |
| AES `image_proj_model.bin` | `f85518431d7367de30b9558a939c003462a7e331e8c8b929146916dc27e471d6` |
| AES `infusenet_aes_fp8e4m3fn.safetensors` | `7f6526ae545731182f95e5ff2f1dedddfe4adb3895ba727f332029e7df8395a7` |
| SIM `image_proj_model.bin` | `b7a8a1b6fecf2731b2ac64bde33a1885014949c8c08f3efaebd0665bb0e8ad8f` |
| SIM `infusenet_sim_fp8e4m3fn.safetensors` | `de810f98f99ff103ea2529a141cdbe62c856177851d1660b33c3ade7ff0dba56` |
| FaceXlib `recognition_arcface_ir_se50.pth` | `a035c768259b98ab1ce0e646312f48b9e1e218197a0f80ac6765e88f8b6ddf28` |

The node requirements were already satisfied by the ComfyUI environment: FaceXlib `0.3.0`, ONNX Runtime
`1.23.2`, InsightFace `1.0.1`, OpenCV `4.13.0.92`, Hugging Face Hub `0.36.2`, and PyTorch
`2.12.1+cu130`. No package upgrade or downgrade was performed.

## Controlled test

- GPU: RTX 3090, isolated ComfyUI low-VRAM worker on port `8190`.
- Normal 3090 and 4070 queues were confirmed idle before both runs.
- Genuine identity input: `mitch-inline-author-ref-01-face.jpg`, byte-identical to
  `datasets/flux2-klein-identity-v2/train/02_closeup_tan_indoor.jpg`.
- Held-out calibration: five genuine images from `datasets/flux2-klein-identity-v2/validation/`.
- Seed: `8675367`.
- Canvas: 864×1152 (`0.995 MP`).
- Sampler: Euler, beta scheduler, CFG `1.0` with FLUX guidance `3.5`.
- No pose control, character LoRA, optional realism LoRA, anti-blur LoRA, face swap, mask, restoration,
  relighting, sharpening, or postprocess.
- AES runtime: `52.552 s`; SIM runtime: `50.472 s`.

The fixed prompt requested one unposed rear-phone photograph of Mitch on a busy downtown sidewalk with
resolved pedestrians, cars, storefronts, signs, and ordinary daylight. It explicitly rejected portrait
blur, beauty filtering, flash, face cutout, and selective subject sharpening.

## Results

The genuine held-out set had pairwise cosine similarity from `0.6206` to `0.8652`, mean `0.7471`.

| Variant | Centroid | Mean to refs | Minimum | Face size | Automated status | Visual decision |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| AES Stage 2 | `0.5080` | `0.4537` | `0.4411` | 108×149 px | `identity_drift` | Reject |
| SIM Stage 1 | `0.5502` | `0.4914` | `0.4503` | 123×164 px | borderline `near_match` | Reject |

The SIM result barely clears the evaluator's broad `near_match` label but remains outside the genuine
pairwise floor and is visually not Mitch. The label is diagnostic, not an identity lock.

Whole-frame review for both variants:

- Identity: facial proportions, eyes, nose, jaw, and apparent age drifted substantially.
- Integration: the head and body were generated coherently; there was no cutout edge or pasted-head halo.
- Background: plausible bricks, cars, sidewalk, trees, and pedestrians, but strong shallow depth of field
  contradicted the requested resolved real background.
- Body/hair: internally coherent, but not a sufficient likeness benefit to offset the facial drift.
- Sharpness/noise: technically clean, with a polished portrait look rather than an ordinary phone capture.

## Reproducible artifacts

- Archived UI graph: `checkpoints/legacy-workflows/experiments/InfiniteYou FLUX.1 Dev One Reference - Tested Rejected.json`
- Isolated worker launcher: `scripts/start-infiniteyou-comfy.ps1`
- Archived API runner: `checkpoints/legacy-scripts/infiniteyou/run-infiniteyou-flux1-one-ref.ps1`
- Combined local score report: `output/infiniteyou-flux1/aes-vs-sim-evaluation.json`
- AES image: `output/infiniteyou-flux1/aes-stage2-seed8675367.png`
- SIM image: `output/infiniteyou-flux1/sim-stage1-seed8675367.png`

## Final interpretation

InfiniteYou answers the mechanism question correctly: a single face photograph can drive a trained identity
adapter while FLUX generates the whole image. It does not answer the outcome question for Mitch. On the
same machine and honest held-out test, both official variants are weaker than already-rejected local methods,
and the background rendering repeats the stylized portrait failure the workflow was intended to escape.
Do not promote it or spend another tuning cycle on it.
