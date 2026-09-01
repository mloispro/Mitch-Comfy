# FLUX.2 Klein identity LoRA v3 training and evaluation

> **Historical evaluation with a retained specialty adapter.** Klein 4B V3 remains installed for validated portrait/profile use, but current primary generation uses Klein 9B V3. See `docs/STATUS.md`.

Status: **trained successfully and published for portrait/profile use; full-body identity is not approved**.

## Provenance and mechanism

The dataset contains 13 genuine training photographs and six genuine held-out photographs. No generated,
retouched, or validation image entered training, the train/validation SHA-256 sets do not overlap, and no
image was uploaded. The locked manifest hash is
`d56fe2d752febfa63ca0e76689dfd9d4eaac7443ca086ffa9dfef51186563003`.

Identity enters through a character LoRA trained directly on the 13 captioned photographs with the unique
token `m1tch_person`. There is no reference image, face swap, mask, restoration, style adapter, or generic
img2img path in the evaluation graph. This is the identity mechanism documented for character LoRA training,
not an inference-time claim that an ordinary image input preserves identity.

The implementation follows the official [FLUX.2 repository](https://github.com/black-forest-labs/flux2),
[Klein training guide](https://docs.bfl.ai/flux_2/flux2_klein_training),
[worked 10–15 image example](https://docs.bfl.ai/flux_2/flux2_klein_training_example), and
[BFL/Hugging Face LoRA guide](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora). Those sources
support Klein Base rather than the distilled model for training, the 4B model on a 12 GB-class GPU, detailed
captions, checkpoint comparison, and roughly 800–1200 steps for a 10–15 image character set. Rank 16 was kept
from the stronger local v1 baseline because the prior rank-32-plus-convolution v2 run overfit and failed its
profile/full-body evaluation.

## Locked training settings

| Setting | Value |
| --- | --- |
| Base model | `black-forest-labs/FLUX.2-klein-base-4B` |
| AI Toolkit | `0.12.23`, commit `0f788923aef28e3a87fa68cfa15a761d9d499d6c` |
| GPU | Physical NVIDIA RTX 4070, isolated with `CUDA_VISIBLE_DEVICES=1` |
| Trigger | `m1tch_person` |
| Network | Linear LoRA rank/alpha `16/16`; no convolution LoRA |
| Optimizer | AdamW 8-bit, weight decay `1e-4`, max grad norm `1.0` |
| Learning rate | Constant `8e-5` |
| Updates | `1200`, batch `1`, accumulation `1` |
| Resolutions | Multi-resolution `512`, `768`, `1024` |
| Precision | BF16 training/saves; qfloat8 model and text encoder |
| Memory | Low-VRAM mode, gradient checkpointing, cached latents/text, unloaded text encoder |
| Timestep/loss | Weighted flow-match timesteps, balanced content/style, MSE |
| Disabled | Flips, caption/token dropout, token shuffling, EMA, training-time samples |
| Saving | Every 100 steps, 12 retained adapters plus optimizer state |

The smoke test completed 20 finite updates at about 7.4 GB VRAM. The production run completed 1200/1200 in
about 51.5 minutes, with approximately 8.1 GB observed VRAM use. The RTX 3090 remained idle. All 12 retained
adapters contain 160 tensors and passed a full finite-value scan; the transcript contains no NaN, infinity,
OOM, traceback, or error marker.

## Checkpoint selection

The fixed-seed quick benchmark used two novel scenes, Klein Base 4B FP8, Euler, 20 steps, guidance 4, strength
0.60, and no reference conditioning. Scores are cosine similarities to the centroid of all six genuine
held-outs.

| Step | Phone | Professional | Mean | Worst |
| ---: | ---: | ---: | ---: | ---: |
| 600 | 0.5098 | 0.4445 | 0.4772 | 0.4445 |
| 800 | 0.5019 | 0.5563 | 0.5291 | 0.5019 |
| 1000 | 0.5199 | 0.5740 | 0.5470 | 0.5199 |
| **1200** | **0.5666** | **0.5613** | **0.5639** | **0.5613** |

Step 1200 was the strongest balanced checkpoint. The full four-scene strength sweep then changed only LoRA
strength:

| Strength | Phone | Professional | Side profile | Full body | Mean |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.60 | 0.5666 | 0.5613 | 0.4740 | 0.1623 | 0.4410 |
| 0.80 | 0.6561 | 0.6880 | 0.4754 | 0.2902 | 0.5274 |
| 1.00 | 0.6942 | **0.7717** | 0.5900 | 0.2923 | 0.5870 |
| **1.20** | **0.7287** | 0.7661 | **0.6128** | **0.3696** | **0.6193** |

At strength 1.20, phone, professional, and side-profile scenes are calibrated `strong_match`. Full body
remains `identity_drift`; its detected face is only about 55 x 69 pixels. Automated similarity is a local
diagnostic, not proof of identity.

## Manual review and operating envelope

- Portrait and profile results are recognizably Mitch at full size and thumbnail, with coherent hair, head,
  neck, clothing, and scene integration. There is no cutout edge or halo.
- Depth, anatomy, sharpness, and noise are coherent. Close faces are somewhat smoother and the hair somewhat
  darker/more groomed than the genuine photographs, so the LoRA is not described as an identity lock.
- Apparent age is broadly plausible but can read slightly younger in the polished professional scene.
- The full-body result has plausible average-fit body shape and natural integration, but its small face does
  not preserve reliable identity. Use a closer waist-up framing when likeness matters.
- The strength-1.20 phone scene passed the local leakage audit: two faces detected, main similarity `0.6970`,
  maximum secondary identity similarity `0.0700`, and maximum secondary-to-main similarity `0.0843`.

## Selected artifact and inference settings

- Training artifact: `work/ai-toolkit-output/m1tch-flux2-klein-4b-identity-v3/m1tch-flux2-klein-4b-identity-v3.safetensors`
- ComfyUI alias: `aitk/m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors`
- SHA-256: `C43D7C1FCA404A8B316A9D0C8756E140033E4763532628F62FACC791F0B8A149`
- Recommended prompt token: `m1tch_person`
- Recommended baseline: Klein Base 4B, LoRA `1.20`, Euler, 20 steps, guidance `4.0`, `768x1024`
- Optional conservative strength: `1.00` when the highest professional-scene score is preferred
- Approved scope: head-and-shoulders, waist-up, and clear side-profile images
- Not approved: distant/full-body identity-critical images or any claim of universal identity lock

The exact training configuration is `config/flux2-klein-identity-v3-4070.yaml`; the reproducible training and
evaluation entry points are `scripts/run-flux2-klein-identity-v3-4070.ps1` and
`scripts/benchmark-flux2-klein-identity-v3.ps1`.
