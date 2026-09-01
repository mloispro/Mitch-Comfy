# FLUX.2 Dev LoRA — 9 Dating Scenes v1

**Current specialty workflow:** `workflows/production/FLUX.2 Dev LoRA - 9 Dating Scenes v1.json`.

This workflow uses the protected `m1tch-flux2-dev-identity-v2` step-1000 LoRA with the local
`flux2_dev_fp8mixed.safetensors` model. It has two explicit modes:

- **Prompt only:** the preset or custom text defines a new scene and the LoRA supplies identity.
- **Scene image:** an uploaded image is resized without cropping, VAE-encoded, and attached to the
  prompt with ComfyUI's `ReferenceLatent`. The image supplies composition, pose, props, location,
  lighting, and crop. The prompt tells FLUX.2 not to use the scene person's identity; the LoRA supplies
  Mitch.

No image is uploaded to a hosted service. The workflow does not use face swap, masks, restoration, or
post-processing.

## Evidence for the reference branch

- [Black Forest Labs' FLUX.2 repository](https://github.com/black-forest-labs/flux2) lists FLUX.2 Dev
  as supporting text-to-image, single-reference editing, and multi-reference editing.
- [The FLUX.2 Dev model card](https://github.com/black-forest-labs/flux2/blob/main/model_cards/FLUX.2-dev.md)
  describes the 32B model as capable of generating, editing, and combining images.
- [ComfyUI's official FLUX.2 example](https://github.com/comfyanonymous/ComfyUI_examples/tree/master/flux2)
  says its Dev workflow supports optional multiple reference images.
- [ComfyUI's official FLUX.2 Dev edit blueprint](https://github.com/Comfy-Org/ComfyUI/blob/master/blueprints/Image%20Edit%20%28Flux.2%20Dev%29.json)
  connects the source image through `VAEEncode` and `ReferenceLatent`, then samples an empty FLUX.2
  latent. The same official graph has a model-only LoRA path before the guider.

## Active workflow defaults

- LoRA strength: `1.1`
- Steps: `28`
- Guidance: `4.0`
- Sampler: Euler (locked inside the node)
- Canvas: `832 × 1248` portrait for new scenes
- Uploaded scenes: output automatically follows the scene aspect ratio at approximately one megapixel

## Scene presets

The library includes founder/editorial, cooking, rooftop, night balcony, Amalfi, Italian lake boat,
restaurant, cat, golf, two night-out variants, weekend lake, and downtown menswear. The custom field
can replace the preset or add a short creative direction.

## Limits

- Identity is strongest for portrait and waist-up images. Full-body identity remains a stretch goal.
- A scene image containing another person can compete with the LoRA. The prompt explicitly rejects
  that person's identity, but visual review is still required.
- Live testing on the deliberately difficult night-balcony screenshot showed that strength `1.1`
  improved scene-restage identity over `1.0` without visible overdrive. The visible workflow therefore
  defaults to `1.1`. Use `1.0` only for a controlled prompt-only A/B with the change recorded.
- Group scenes require checking every secondary face for identity leakage.
- Reference mode is a generative restage, not pixel-exact inpainting. It can reinterpret small props,
  hands, clothing details, and background geometry.

The recorded live test and exact raw paths are in
`work/flux2-dev-mitch-scene-studio/live-validation-20260828/VALIDATION.md`.
