# Krea2 ReID iPhone Photo Evaluation

## Outcome

The exact Krea2 ReID ComfyUI route was installed and validated locally, but it is rejected as a
Mitch identity solution. It generated coherent, realistic sidewalk photographs without a face-swap
boundary, yet all genuine-reference outputs depicted a different, younger man with different facial
geometry and hair.

No personal Mitch LoRA, face swap, head mask, restoration, selective sharpening, or hosted service
was used.

## Why the mechanism was worth testing

The adapter is a rank-32 functional LoRA trained on paired same-identity images. Exactly one reference
enters through two training-matched paths:

1. Qwen3-VL image conditioning in the prompt embedding.
2. Clean VAE reference tokens with isolated reference attention and cached reference K/V.

That is a native whole-image identity-generation mechanism rather than style transfer, generic
img2img, or host-face replacement. Sources:

- https://huggingface.co/yijunwang2/krea2-reid
- https://github.com/ostris/ComfyUI-Krea2-Ostris-Edit
- https://huggingface.co/Comfy-Org/Krea-2

## Exact tested configuration

- Krea2 Turbo INT8 ConvRot
- Qwen3-VL 4B BF16
- Qwen Image VAE
- `krea2_reid_rank32.safetensors`, strength `1.0`
- Pinned custom-node commit `7756566160c4a1b24bb1bd9f0ff3ced1a83d7547`
- Reference budget `384 * 384` total pixels
- Cached reference K/V enabled
- Eight steps, CFG `1.0`, Euler/simple, denoise `1.0`
- `832x1248` portrait output
- RTX 4070 low-VRAM worker on port `8189`; the RTX 3090 training process was not touched

## Results

Three genuine photographs calibrated at `0.7748` minimum and `0.8163` mean pairwise similarity.
All scores below are candidate-to-genuine-reference-centroid cosine similarity from local
InsightFace AntelopeV2.

| Test | Similarity | Result |
|---|---:|---|
| Direct reference, seed 17072027 | 0.0663 | Identity drift |
| Direct reference, seed 17072028 | 0.0606 | Identity drift |
| Direct reference, seed 17072029 | 0.1155 | Identity drift |
| Direct reference, seed 17072030 | 0.1406 | Identity drift |
| Alternate genuine reference | 0.1182 | Identity drift |
| Synthetic bridge from the prior 0.7594 Identity Edit result | 0.0293 | Identity drift |

The release's own synthetic woman reference was then run with the author's fixed prompt and seed.
Identity, hair, apparent age, outfit change, and scene change were preserved visually. This proves
the local models, LoRA, image conditioning, VAE tokens, node patch, and K/V cache are functioning.
It also isolates the failure: this adapter does not preserve Mitch reliably from the available real
references.

## Photograph quality

The direct outputs were internally coherent and free of a pasted-head boundary. However, they still
favored smooth portrait rendering and noticeable background defocus. Because identity failed by a
large margin, no post-processing or further seed search was justified.

## Decision

Do not promote Krea2 ReID as a direct Mitch reference-photo workflow and do not spend time rerolling
the same configuration. The best established no-personal-LoRA Krea2 result remains Identity Edit
v1.2 single-reference restaging at `0.7594`, with its remaining weakness being excessive background
defocus rather than a head seam.

The next experiment should therefore operate from that stronger Identity Edit mechanism and change
only the camera/background rendering while preserving the full subject. ReID should not be used as
the identity stage for that experiment.
