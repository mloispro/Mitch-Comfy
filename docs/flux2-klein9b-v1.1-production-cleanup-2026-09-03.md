# Klein 9B public v1.1 cleanup and validation — 2026-09-03

## Decision

The production sidebar now contains exactly three Klein 9B workflow sheets, all v1.1:

- `FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets`
- `FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets`
- `FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1`

The duplicate Identity and Group v1 sheets and the inconsistently named Upgrade v1 sheet were deleted. Their three
old public node registrations were also removed. The underlying V1 Python classes remain internal because the
v1.1 Identity and Group interfaces inherit them, and Upgrade v1.1 maps directly to the exact validated Upgrade
class. Deleting those implementation bases would break v1.1 or unnecessarily change its pixels.

Both configured ComfyUI workflow trees are junctions to this repository, so the source deletion removes the
duplicates from both sidebars after refresh. Git history and the previous milestone tags preserve recovery.

## Generation parity design

- Identity and Group generation methods, presets, model/LoRA choices, prompt resolution, reference order, sampling,
  and postprocessing were not edited.
- Upgrade v1.1 is a direct `NODE_CLASS_MAPPINGS` alias to `Flux2Klein9BPhotoRealismUpgradeV1`; it adds no wrapper
  method and therefore dispatches the same class object.
- Changes to Identity/Group wrapper wording affect only public documentation and additive report provenance.
- Historical output folders and embedded engine-report namespaces remain unchanged for comparability.

## Verification

The port-8188 and port-8189 workers were reloaded in sequence only after ports `8188`, `8189`, and `8190`, Forge,
and both physical GPUs were confirmed idle. The auxiliary RTX 3090 service and Forge were left running and
untouched. After reload, both production workers exposed all three public v1.1 nodes and none of the three retired
v1 node names.

The full repository verifier passed, including 20/20 visual-preset sources, all active frozen-baseline hashes, live
model/node checks on both production workers, and 131/131 Python tests. It now checks the secondary worker's
v1.1-only registry explicitly so a stale reload cannot pass unnoticed. The three specialized read-only verifiers
also passed.

### Identity v1.1 shipped default

- Prompt ID: `9799a06c-058c-4b5f-a082-6a754884c1d1`
- Output: `C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-mitch-identity-studio-v1\20260903-105604-510459\photo_00001_.png`
- Settings: rooftop-cocktail preset, left-facing solo references, seed `8675411`, Turbo on, 8 steps, guidance `1.0`
- Engine time: `24.642 s`; end-to-end verifier time: `30.096 s`
- Six-genuine-photo identity: centroid `0.7354`, mean `0.6344`, minimum `0.5544`, `strong_match`
- Leakage: intended face `0.6918`; maximum secondary identity `-0.0583`; no failures
- Decoded RGB SHA-256: `D3FC7F14C52ABCA09B315D6E89F43BA50BD6863157AC7B189E6698CCF9596480`
- Pixel comparison with the prior accepted default: exact, maximum difference `0 / 255`

Full-size and thumbnail review passed identity, apparent age, hair, closed-lip expression, hands and glass, body
proportion, night depth, background diversity, flash integration, and halo/cutout checks.

### Group v1.1 shipped default

- Prompt ID: `84a13a0a-6c39-4df1-ad37-73501b119bac`
- Output: `C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-mitch-group-scene-studio-v1\20260903-110220-664630\photo_00001_.png`
- Settings: approved-lounge preset, seed `8675412`, appearance enhancement off, Turbo off, 50 steps, guidance `4.0`
- Engine time: `259.954 s`
- Four detected faces; intended Mitch `0.5781`, above the `0.55` gate
- Maximum secondary identity `0.2866`, secondary-to-main `0.3381`, and secondary-pair `0.3365`; no leakage or
  duplicate-face failures
- The generated guide is decoded-pixel-identical to the prior accepted guide:
  `4C32FFD23310E2ED3F2690BAE796646884C7E09767676F988CC7A14711444D40`
- The prompt, seed, reference order and sizes, guide geometry, model, LoRAs, sampler, scheduler, steps, and guidance
  match the prior accepted default. Expected CUDA/VAE numerical variation was small: mean absolute image difference
  `0.3196 / 255`, 95th percentile `1 / 255`; identity improved slightly from the prior `0.5769` diagnostic.

Full-size and thumbnail review passed intended-person selection, exactly one Mitch, distinct bystanders, head scale,
hands, anatomy, booth depth, phone-flash integration, and halo/cutout checks. The target guide retains head placement
while blanking internal eye, nose, and mouth edges.

### Upgrade v1.1 shipped default

- Prompt ID: `7ace657c-7e00-41f0-9ac7-60e81cac2ff7`
- Output: `C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260903-111226-463056\photo_00001_.png`
- Settings: native `1680×1008`, seed `8675416`, appearance polish on, phone-camera realism on, 50 Euler steps,
  CFG `4.0`, `Flux2Scheduler`
- Engine time: `506.727 s`; end-to-end verifier time: `526.045 s`
- Raw identity: centroid `0.7791`, minimum `0.5890`, `strong_match`
- Final identity: centroid `0.7400`, minimum `0.5377`, `strong_match`; the weakest view remains below the genuine
  pairwise floor and therefore still requires the recorded visual review
- Raw tolerant Canny structure F1: `0.2961`; guide recall `0.6562`
- Decoded RGB hashes exactly match the locked accepted values:
  - final: `1CF807B50A1AA1BA963AEF3B0E0C08B81C3FFA8E4C3FC5402FB1804459C5085C`
  - raw: `9CB8AC28BC4D3D5E22FFBD6A9D2F7A5EFF441A30B2A608F80044B134897F8C5A`
  - guide: `D2DB8B2D2A9EDFDA734009D7C5EAD62F2F35F5492C3D57F6A21570675A06780B`

The schema-v2 report confirmed the four trained reference roles, unisolated source-face influence disclosure, and
the absence of Turbo, source-latent initialization, generation masks, face swap, restoration, upscaling, and a
second model pass. Full-size and thumbnail review passed identity, pose, gaze, closed lips, hairline and forehead,
skin/hair material, coat boundaries, siding and tree detail, whole-frame depth, and halo/cutout checks.

## Conclusion

The cleanup changed the public names and interface surface, not the accepted photo recipes. All three v1.1 defaults
execute successfully and remain suitable as the current local Production workflows, subject to the normal per-image
full-size and thumbnail review requirement.
