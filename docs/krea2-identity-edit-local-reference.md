# Local Krea 2 Identity Edit Reference Workflow

## What the RioShiina Space is actually doing

`RioShiina/ImageGen` does not run Google's Nano Banana 2 locally. For Krea 2 reference-photo work,
it loads the community `krea2_identity_edit_v1_2.safetensors` adapter and the
`comfyui-krea2edit` custom nodes on top of local Krea 2 Turbo or Raw.

The identity reference enters the model through two training-matched paths:

1. `Krea2EditModelPatch` VAE-encodes the source and prepends it as in-context appearance tokens.
2. `Krea2EditGroundedEncode` shows the same image to Qwen3-VL while it encodes the instruction.

Stock Krea 2 style-reference nodes do not provide this combination. That is why the earlier local
reference experiment could accept a photograph but did not hold Mitch's identity reliably.

## Installed local components

- Base: `krea2_turbo_fp8_scaled.safetensors`
- Text encoder: `qwen3vl_4b_fp8_scaled.safetensors`, loaded as `krea2`
- VAE: `qwen_image_vae.safetensors`
- Identity adapter: `krea2_identity_edit_v1_2.safetensors`, strength `1.0`
- Nodes: `Krea2EditModelPatch` and `Krea2EditGroundedEncode`
- Fidelity: `ref_boost=6` in the selected local graph (`4` is the author's baseline)
- Grounding: `768 px`
- Sampling: Krea 2 Turbo, `12` steps, CFG `1`, Euler/simple
- Output: `832x1248` (about 1 MP, 2:3 portrait)

The ready ComfyUI graph is:

`templates/krea2-workflows/Krea 2 Identity Edit - Local Reference Restage.source.json`

The repeatable API runner is:

`scripts/smoke-krea2-identity-edit.ps1`

## Correct reference modes

### One-input restaging

Use one genuine portrait as the sole reference. The model creates the person and new scene together.
This is the cleanest first identity test and does not use a host, mask, face swap, or head inpaint.

```powershell
.\scripts\smoke-krea2-identity-edit.ps1
```

### Two-input scene plus identity

The adapter was trained with a fixed order:

1. Image 1 is the scene plate.
2. Image 2 is the person reference.

Do not feed two portraits as if they were equal identity references; that is not the trained
two-image layout and can degrade results. To place Mitch into an accepted busy-sidewalk plate:

```powershell
.\scripts\smoke-krea2-identity-edit.ps1 -SceneReference "busy-sidewalk-plate.png"
```

The script automatically wires the scene to `source_latent`/`image` and Mitch to
`source_latent_b`/`image_b`. `SceneRefBoost` controls `ref_boost_a` for the scene (default `1`),
while `RefBoost` controls the person-reference fidelity.

## First local proof

The RTX 4070 completed the single-reference workflow in about one minute while the RTX 3090 stayed
on its separate training process. The output was a coherent full-frame sidewalk photograph with no
head seam or face-swap boundary. InsightFace ranked it as a calibrated near-match, not yet a strong
match, so visual approval and a final identity improvement are still required.

The best automated score in the first two controlled settings was produced by `ref_boost=6` and
`12` steps. The gain over the recommended baseline was small. This confirms the pipeline is working
but also matches the adapter author's stated limitation: distinctive facial geometry can regress
toward a close relative. Once the Mitch Krea 2 character LoRA is available, stack it with this
identity-edit adapter; the identity-edit model is explicitly designed to compose with character
LoRAs.

## Smartphone-depth tests

The strongest single-reference result is
`mitch-sidewalk-single-ref_00003_.png`. It used the selected identity settings (`ref_boost=6`,
`12` steps, grounding `768`) and an ordinary 1x-phone/deep-focus instruction. Its local AntelopeV2
score against three genuine photographs was `0.7594` (calibrated `near_match`), improving over
`mitch-sidewalk-single-ref_00002_.png` at `0.7311`. It also retained whole-frame integration with no
head boundary, although Krea 2 still imposed more background defocus than an ordinary 1x phone
would typically show.

The trained two-input fallback used FLUX.2 plate `plate-8675351_00001_.png` as image 1 and Mitch's
front photograph as image 2 at `896x1344`, `SceneRefBoost=2.25`, `RefBoost=6`, `12` steps, and
grounding `768`. It preserved the plate's deeper street detail and produced a coherent frame, but
retained the plate man's identity: centroid similarity was only `0.3149` (`identity_drift`). Preserve
the output as a mechanism failure; do not promote it or repeat this exact setting as an identity
solution.

## Smartphone realism adapter test

The Elusarca smartphone-photography LoRA was tested as one model-chain addition before Identity
Edit at strengths `0.35` and `0.50`. Both retained the baseline identity score, but neither
materially reduced the excessive background defocus. The `0.35` setting is safe as an optional
camera-appearance control; it is not the deep-focus solution. See
`docs/krea2-smartphone-lora-evaluation.md` for the controlled comparison and exact artifacts.

## Face-attention v2 — selected no-personal-LoRA route

The visible subject/background separation was traced to global `ref_boost=6`: the node applies the
extra target-to-reference attention to every source token unless `ref_boost_mask` is connected. The
v2 workflow detects the largest face in the genuine reference on CPU and restricts the extra boost
to an internal oval. Hair, ears, jaw boundary, neck, clothing, body, and reference background stay
outside that boost. The mask exists only in reference-token space; no generated pixel is masked,
composited, restored, sharpened, or inpainted.

The versioned workflow is:

`workflows/production/Krea 2 Identity Edit - Face Attention v2.json`

Selected settings are Identity Edit `1.0`, masked boost `6`, grounding `512`, Smartphone LoRA
`0.35`, `832x1248`, 12 steps, CFG `1`, Euler/simple. The automatic mask defaults are width scale
`0.82`, height scale `0.86`, and vertical offset `0.02` relative to the detected face.

Against four genuine photographs, global boost plus Smartphone `0.35` scored `0.7225`; the earlier
manual face-attention experiments scored `0.7789` at grounding `768` and `0.7783` at grounding
`512`. The reusable automatic-mask workflow reached an identity maximum of `0.7899`. A controlled
prompt-only deep-focus variant scored `0.7822` and was selected because it produced materially more
believable storefront, sidewalk, and midground-pedestrian detail while remaining a calibrated
strong match. An 8-step refinement fell to `0.7479` without enough additional scene improvement and
was rejected. The far end of the street can still be somewhat softer than an ordinary 1x phone
camera. Exact settings and artifacts are locked in
`config/krea2-face-attention.lock.json`.

The selected workflow now ends with a deterministic CPU-only whole-frame phone finish. It applies
very light global sharpening, fine luminance/chroma texture, and one quality-95 JPEG round trip to
every pixel equally. It has no detector, mask, face branch, model pass, relighting, restoration, or
selective processing. The mean absolute change was `1.2556` pixel levels with a 95th percentile of
`3.0`; the background gradient metric was preserved (`3.3181` before, `3.3443` after). Identity
scored `0.7884`, versus `0.7822` before the finish, and remained a calibrated strong match.

## Sources

- https://huggingface.co/spaces/RioShiina/ImageGen
- https://huggingface.co/conradlocke/krea2-identity-edit
- https://github.com/lbouaraba/comfyui-krea2edit
