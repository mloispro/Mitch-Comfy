# Z-Image Base texture pass on HiDream identity proof

> **Historical record — not current instructions.** This experiment was rejected and its runnable files are archived. See `docs/STATUS.md`.

Date: 2026-08-28
Worker: local RTX 3090 (`http://127.0.0.1:8188`)
Privacy: all image handling, generation, and evaluation stayed local.

## Outcome

Rejected as an identity-safe refinement. Both Z-Image passes make the face look somewhat more like
a conventional photograph by adding color variation, stubble, and small skin marks, but both alter
facial geometry and score worse against the five held-out genuine photographs. Neither improves the
measured fine texture.

The `0.10` image is the better visual compromise and is preserved for Mitch to inspect. It is not an
approved final image.

## Mechanism

The exact HiDream output is loaded, scaled to approximately 1 MP, encoded with the official Z-Image
VAE, and passed to Z-Image Base as the sampler's starting latent. This is generic low-denoise img2img:
the source supplies composition and appearance through latent conditioning, but it is not a native
identity reference. No identity LoRA, face swap, mask, restoration, or hosted service is used.

The graph begins with the official ComfyUI Z-Image Base recipe—BF16 Z-Image, Qwen 3 4B text encoder,
`ae.safetensors`, model shift `3`, CFG `4`, `res_multistep`, and `simple` scheduler—then replaces the
empty latent with `LoadImage -> ImageScaleToTotalPixels -> VAEEncode` and lowers denoise.

Primary sources:

- <https://docs.comfy.org/tutorials/image/z-image/z-image>
- <https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_z_image.json>
- <https://huggingface.co/Tongyi-MAI/Z-Image>

## Locked test

- Source: HiDream seed `8675603`, `1728x2304`, SHA-256
  `D867BE7CCFD5562C1822879E9C1B8AC7CE516A3B7AC71A29729D4FE83D5B6508`
- Output: `896x1184` (approximately 1.06 MP)
- Steps: `30`
- CFG: `4.0`
- Model shift: `3.0`
- Sampler/scheduler: `res_multistep` / `simple`
- Seed: `8675603`
- Initial denoise: `0.15`
- Single controlled refinement: denoise `0.10`
- Everything except denoise stayed fixed.

## Identity results

| Image | Centroid | Mean | Minimum | Genuine floor passed? |
|---|---:|---:|---:|---|
| HiDream source | **0.8101** | **0.6960** | **0.5693** | yes |
| Z-Image denoise `0.10` | 0.7696 | 0.6612 | 0.5343 | no |
| Z-Image denoise `0.15` | 0.7360 | 0.6323 | 0.5152 | no |

The `0.10` pass loses `0.0405` centroid similarity. The `0.15` pass loses `0.0741`. Visual review
agrees: eyes, nose, mouth, and face shape shift slightly, with more drift at `0.15`.

## Texture results

| Image | Micro-luma variation | Normalized Laplacian variance |
|---|---:|---:|
| HiDream source | **4.176** | **163.121** |
| Z-Image denoise `0.10` | 3.762 | 126.117 |
| Z-Image denoise `0.15` | 3.819 | 127.208 |

The added mottling and stubble can look less waxy at first glance, but the local diagnostic finds less
fine detail after the 1 MP edit. The downscale and redraw are not a real texture recovery.

## Decision

Keep both images as rejected examples. Do not use this whole-frame Z-Image Base img2img method as an
automatic HiDream finishing stage. It trades away a meaningful part of the identity gain without
producing measured fine-texture improvement. No further denoise values should be tried without a new
mechanism or acceptance test.

## Artifacts

- Archived runner: `checkpoints/legacy-scripts/zimage-base-identity-v1/run-zimage-texture-pass-hidream-v1.ps1`
- `0.10` result: `output/zimage-texture-pass-hidream-v1/denoise-0p10-seed-8675603.png`
- `0.15` result: `output/zimage-texture-pass-hidream-v1/denoise-0p15-seed-8675603.png`
- Identity report: `output/zimage-texture-pass-hidream-v1/evaluation/identity.json`
- Texture sheet: `output/zimage-texture-pass-hidream-v1/evaluation/face-texture-contact-sheet.png`
- Experiment lock: `output/zimage-texture-pass-hidream-v1/experiment-lock.json`
