# Identity candidate screening

This log records why an experimental identity path was promoted or rejected. The
accepted `flux2-one-reference-v1.0.0` production baseline is not changed by these
experiments.

## Promotion gates

A candidate must pass all of these before it can replace production:

1. The released weights load into the released inference implementation without
   missing identity tensors or randomly initialized identity layers.
2. The same genuine references, prompts, framing, and seeds are used for the
   comparison set: close/waist-up, candid, three-quarter/profile, and full body.
3. The largest detected face is scored locally against held-out genuine photos
   with AntelopeV2. Identity similarity is a rejection/ranking signal, not a
   substitute for visual review.
4. The face/head boundary, skin, hair, ears, neck, expression, hands, body, and
   scene are reviewed for copy-paste, waxy/plastic texture, age drift, and other
   artifacts.
5. Runtime and peak VRAM fit the RTX 3090. A quality improvement must justify any
   added model footprint or workflow complexity.

## PuLID-FLUX2 Klein v2 — rejected before generation

- Source audited: `iFayens/ComfyUI-PuLID-Flux2`, commit
  `3a0a3f5a4709fcecb3d7dfa5272c4691984327da`.
- Weight audited: `pulid_flux2_klein_v2.safetensors`, 1,364,389,800 bytes,
  SHA-256 `d5d291cb054eb6eceb25e3b46eff8f05f7b58f8f19a89ec76ba730a6ba8935bb`.
- The weight file contains identity cross-attention tensors under
  `pulid_ca_double.*` and `pulid_ca_single.*`.
- Current inference code instantiates the modules as `double_ca.*` and
  `single_ca.*`, then loads with `strict=False`. The released cross-attention
  tensors therefore do not map to those modules and the mismatch is silently
  ignored.
- The code also hard-codes BF16 despite documentation that advertises automatic
  FP16 on RTX 20/30-series hardware.

Installing or benchmarking that combination would produce an invalid test, so it
was rejected at the integrity gate. No live ComfyUI files and no production files
were changed.

## USO v1 — rejected after generation

USO is the next candidate because its official ByteDance release has native
ComfyUI support and a documented FP8/offload path for consumer GPUs. The isolated
test uses the official Comfy-packaged files and the native USO reference-latent
conditioning already present in this ComfyUI build.

Required files are pinned by SHA-256:

| File | SHA-256 |
| --- | --- |
| `flux1-dev-fp8.safetensors` | `8e91b68084b53a7fc44ed2a3756d821e355ac1a7b6fe29be760c1db532f3d88a` |
| `uso-flux1-dit-lora-v1.safetensors` | `a03fa8430997f1c371c2471b133bdc03433a50564e0a29c096217077b0309e41` |
| `uso-flux1-projector-v1.safetensors` | `9a0dfcd6644e3acaf6995625562ab0af1f9cf048bf739c7e5822ee106fb44311` |
| `sigclip_vision_patch14_384.safetensors` | `1fee501deabac72f0ed17610307d7131e3e9d1e838d0363aa3c2b97a6e03fb33` |

The projector and SigCLIP files above support USO style references. They are not
active in the subject-only identity test; that path uses the FLUX.1 checkpoint,
USO DiT LoRA, VAE-encoded content reference, the native `uxo/uno` reference
method, and guidance 3.5. Keeping these two paths distinct prevents an identity
photo from being misinterpreted as an artistic style reference.

The test deliberately bypassed EasyCache because the official ComfyUI tutorial
says it trades away detail. The first pass initially exposed an important wiring
error: USO's style-reference projector is not its subject-identity path. That
invalid result was discarded. The corrected subject-only graph used the
official reference-latent path, then compared 1024- and 512-pixel reference
scales and the official 25-step/guidance-4 settings.

The best corrected candidate scored `0.6188` against the held-out genuine-photo
centroid. It was visually coherent and photorealistic, but changed the subject's
age and facial structure. The frozen production result scored `0.8309` under the
same local evaluator. USO therefore failed the identity gate before the larger
four-scene suite. Its setup and smoke scripts remain reproducible experimental
tools; it is not part of the production workflow.

## WithAnyone 1.0 — rejected after generation

WithAnyone is the remaining no-training candidate because its released model
explicitly combines ArcFace identity features with SigLIP appearance features
and was trained to reduce rigid face-copy artifacts. The official checkpoint is
FLUX.1 Dev based and the adapter alone is 6.19 GB.

The linked community ComfyUI wrapper is not safe to install unchanged:

- it selects the BF16 model even though its bundled loader contains an FP8 mode;
- it unconditionally converts the loaded model back to BF16;
- its offload flag is disabled and the inference moves required for offload are
  commented out; and
- on an InsightFace folder assertion it can delete and move model directories.

The isolated candidate reused the pinned FLUX.1 Dev FP8 checkpoint, extracted
only its diffusion tensors, preserved calibrated stored dtypes, reused the
existing AntelopeV2 installation without folder surgery, and strictly checked
the adapter tensor map. The official adapter was 6,186,204,560 bytes with SHA-256
`b66880610111fd83eebbb623d1aef57397e03877871819ba43cb6381ef8b2bfb`.
All 780 base tensors and 822 adapter tensors mapped; the only extras were six
known SigLIP projection tensors unused by this inference path.

The 768×1024, 25-step tests took about 32 seconds. SigLIP weight `0.25` scored
`0.6951`; ArcFace-only conditioning scored `0.7009`. The official square
geometry took 42 seconds and regressed to `0.6652`. Results were coherent and
recognizable, but identity stayed far below the frozen FLUX.2 score of `0.8309`
and the skin/camera rendering was not a compensating improvement. WithAnyone
therefore failed the identity gate and was removed from the normal ComfyUI node
set.

## FLUX.2 low-denoise realism finish — rejected

A separate finishing pass was tested because it could, in principle, correct
head/skin integration without changing the accepted identity generator. At
denoise `0.15` it reduced held-out identity from `0.8309` to `0.7937`; at `0.10`
it scored `0.7921`. Both variants exaggerated facial lines and apparent age.
The finish was rejected. Realism is handled in the primary generation prompt
and balanced profile instead of stacking another generative pass onto the face.

## FLUX.2 natural-skin primary render — promoted as Easy Social v1.0.1

Controlled same-seed tests showed that wording alone did not recover small full-body facial texture: the frozen
768×1024 control measured `2.444` micro-luma variation, while balanced wording at the same size measured
`2.447`. Raising only the production canvas to `896×1344` increased the detected face from roughly `85×120`
to `121×179` pixels, micro variation to `4.043`, and supplied-reference identity from `0.7576` to `0.8246`.
Runtime increased by about seven seconds, without another model or postprocess pass.

The promoted prompt asks for subtle spatially nonuniform albedo and microtexture that follow three-dimensional
lighting while explicitly preserving apparent age and avoiding separate facial sharpening. Final phone,
professional, and candid crops measured within the genuine-photo texture comparison band. The full-body action
face remains resolution-limited, as expected at 103 pixels wide, but the complete photo passed visual and
calibrated action-identity review. See `docs/skin-realism-v1.0.1-evaluation.md` for the fixed suite.

## Final decision

The promoted route remains FLUX.2 Klein Base 4B plus the validated local
identity LoRA. Easy Social Photos v1.0.1 adds automatic local quality/angle selection,
one-to-four-reference centroid verification, higher face pixel budget, natural-skin primary conditioning,
phone/professional/candid/action presets, and difficult-angle identity profiles. No PuLID, USO, WithAnyone,
face swap, or post-generation face refiner is in the production graph.
