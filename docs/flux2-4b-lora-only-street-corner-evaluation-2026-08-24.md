# FLUX.2 Klein Base 4B LoRA-only street-corner evaluation

> **Historical record — not current instructions.** This route was rejected. See `docs/STATUS.md` for the current workflow and LoRA inventory.

## Verdict

Rejected for identity preservation. The native whole-frame route produced coherent, detailed street scenes
without crops, masks, inpainting, reference latents, face swapping, compositing, or selective finishing, but
neither tested LoRA strength preserved Mitch's identity. Do not promote this graph to production or describe
it as identity locked.

## Fixed test configuration

- Model: `flux-2-klein-base-4b-fp8.safetensors`
- Text encoder: `qwen_3_4b_fp8_mixed.safetensors`
- VAE: `flux2-vae.safetensors`
- LoRA: `aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors`
- Trigger: `m1tch_person`
- Resolution: 768x1024
- Sampler: Euler
- Steps: 20
- Guidance: 4.0
- Seed: 8675310
- Conditioning: prompt plus LoRA only
- Identity references used for evaluation: four held-out genuine photographs

The prompt requested one full-body Mitch walking toward the photographer on a moderately busy commercial
street corner, five unrelated pedestrians, and two vehicles. It also requested deep smartphone focus and
detailed storefront, curb, traffic, pavement, tree, and block context.

## Results

| LoRA strength | Centroid similarity | Calibration | Detected people | Detected cars | Face size | Result |
| ---: | ---: | --- | ---: | ---: | --- | --- |
| 0.6 | 0.3114 | identity_drift | 14 | 1 | 55.6x71.9 px | rejected |
| 1.0 | 0.3023 | identity_drift | 10 | 5 | 60.9x78.0 px | rejected |

The held-out genuine-reference pairwise floor was 0.7186. Raising only LoRA strength from 0.6 to 1.0 did not
recover identity; it reduced centroid similarity by 0.0091 and worsened vehicle-count adherence.

## Visual review

- Backgrounds were coherent and comparatively detailed: brick and painted storefronts, windows, trees,
  curb, crosswalk, pavement, vehicles, and deep-block structure remained readable.
- The subject was integrated into the whole frame with no cutout edge or halo, confirming that masking was
  not involved.
- The subject looked like a different, younger man in both outputs.
- Pedestrians formed an overly orderly procession and several background faces, outfits, and body types
  repeated. Strength 1.0 made this repetition more apparent.
- Prompt count control was unreliable in both tests.
- Sign and plate text was malformed, and the overall texture was cleaner and more synthetic than a true raw
  phone photograph.

## Preserved artifacts

- Strength 0.6 raw PNG: `C:\projects\AI-Tools\ComfyUI\output\flux2-lora-only\street-corner-4b-lora-s8675310_00001_.png`
- Strength 1.0 raw PNG: `C:\projects\AI-Tools\ComfyUI\output\flux2-lora-only\street-corner-4b-lora-s1.0-seed8675310_00001_.png`
- Strength 0.6 identity report: `work\identity-evals\flux2-4b-lora-street-corner-s8675310.json`
- Strength 1.0 identity report: `work\identity-evals\flux2-4b-lora-street-corner-s1.0-seed8675310.json`

Both PNGs retain their exact ComfyUI API prompt metadata. No production workflow was changed.

## Next highest-confidence experiment

Do not spend more seeds or strength sweeps on this checkpoint for a distant full-body crowded scene. Its
training coverage is dominated by close and upper-body selfies, with only one full-body training photograph.
The next evidence-driven route is a new Base 4B LoRA trained and held out against a broader genuine-photo set
that includes multiple full-body and three-quarter walking views at street-scene subject scale. Test that LoRA
first in a simple one-person walking frame, then add the crowd as a single controlled change.

## Half-body framing follow-up

A later prompt kept the same Base 4B model, LoRA, strength 0.6, 20-step Euler sampler, guidance 4.0,
768x1024 resolution, and seed 8675310, while changing the composition to one subject framed from the top of
the hair through the waist on a simple commercial sidewalk.

- Raw PNG: `C:\projects\AI-Tools\ComfyUI\output\flux2-lora-only\half-body-example-4b-lora-s0.6-seed8675310_00001_.png`
- Identity report: `work\identity-evals\flux2-4b-lora-half-body-s0.6-seed8675310.json`
- Face size: 138.4x194.2 pixels
- Held-out centroid similarity: 0.5010
- Calibration: `identity_drift`

The requested half-body framing succeeded and the larger face improved the diagnostic score substantially
over the crowded full-body tests, but it remained well below the 0.7186 genuine-reference floor. Preserve it
as a framing example only, not an identity-success example.

A controlled follow-up changed only LoRA strength from 0.6 to 1.0:

- Raw PNG: `C:\projects\AI-Tools\ComfyUI\output\flux2-lora-only\half-body-example-4b-lora-s1.0-seed8675310_00001_.png`
- Identity report: `work\identity-evals\flux2-4b-lora-half-body-s1.0-seed8675310.json`
- Face size: 147.7x203.6 pixels
- Held-out centroid similarity: 0.6309
- Calibration: `identity_drift`

Strength 1.0 improved centroid similarity by 0.1299 over strength 0.6 and produced a visibly closer face. It
still missed the calibrated near-match boundary of 0.6386 and the 0.7186 genuine-reference floor. It is the
better half-body LoRA-only result, but it is not identity locked.
