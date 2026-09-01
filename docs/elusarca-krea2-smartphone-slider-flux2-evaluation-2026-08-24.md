# Elusarca Krea 2 smartphone slider / FLUX.2 evaluation — 2026-08-24

> **Historical record — not current instructions.** Terms such as “production,” “current,” “selected,” or “recommended” below describe the decision on 2026-08-24. See `docs/STATUS.md` for current state.

## Frozen checkpoint

Before experimentation, the user-accepted FLUX.2 + 4070 whole-frame finish was copied to `output/checkpoints/flux2-smartphone-v1/accepted.png` and locked in `checkpoints/legacy-scripts/amateur-phone-v2/flux2-smartphone-v1.checkpoint.lock.json`. Its SHA-256 is `484D27FC839AAE8BDD21320D0C3E1DBB4615493D66910C6A6D91FE3FB8B3FD71`. Later tests ran on copies and did not change the accepted image or generation graph.

## Compatibility finding

The supplied Hugging Face model is a Krea 2 concept-slider LoRA, not a FLUX.2 adapter. The exact file was already installed locally:

- file: `krea-smartphone-photo-slider.safetensors`;
- size: `28,627,768` bytes;
- SHA-256: `6468A57747EE8953036AEDC28EBA2034AD6355789151F4F85EF63260ED3FA2CE`;
- license: Krea 2 Community License.

Its weights cannot be loaded into Klein 9B or Klein 4B because those are different base architectures. Applying the Krea LoRA therefore requires a Krea 2 generation/edit pass; it cannot behave as a non-generative color filter over the existing FLUX frame.

The author describes it as a strong concept slider for amateur photography, natural skin texture, and reduced polish. The recommended strength is `1.0–2.0`, with `1.5` preferred. The raw result can be heavily saturated, so the author recommends post-decode saturation correction around `-15` to `-20`. Their current sampling route is Euler/Beta for 12 steps followed by `res4s_munthe-kass`/KL-optimal for 3 steps in RES4LYF's ClownsharKSampler.

## Exact-weight Krea 2 test on the RTX 4070

The first controlled test used:

- scene image 1: the frozen accepted FLUX checkpoint;
- person image 2: genuine photograph `20260815_165446.jpg`;
- Krea 2 Identity Edit v1.2 in its trained two-input order;
- exact smartphone-slider weight at `1.5`;
- Euler/Beta, 12 steps, CFG 1;
- reference boost 6 with the established reference-face attention mask;
- `832×1248`, seed `9472103`;
- RTX 4070 / ComfyUI port `8189`;
- no character LoRA, output mask, face swap, crop, compositing, or post-decode finish.

The optional RES4LYF second sampler was not installed, so no unverified built-in sampler was substituted. The first pass matches the author's documented model, LoRA strength, sampler, scheduler, and step count.

Output: `output/flux2-no-lora-strong-identity-street-v1/krea2-smartphone-lora-author-1p5-raw.png`
SHA-256: `C2EB8E3B96DE4EA8A9279BC42BCAAAD4FA2DCE69BB5E277A6E0485AD43BC3B42`

The LoRA produced a visibly more amateur-phone rendering, but the required Krea generation pass changed the face geometry, body pose, clothing drape, and portions of the scene. Held-out identity centroid was `0.7463`; the weakest held-out view fell to `0.5547`, well below the genuine-photo floor of `0.6206`. Color correction can repair saturation but cannot repair this structural identity drift. The Krea LoRA is therefore rejected as a finishing stage for the accepted FLUX route.

## Non-generative transferred recipe

The useful photographic ideas were transferred to a 4070 whole-frame finish without loading the incompatible LoRA or rerendering pixels with a diffusion model:

1. blend a white frame at 7% opacity;
2. reduce saturation to 90%;
3. apply slight global computational sharpening;
4. add deterministic shadow-weighted luminance and chroma sensor noise; and
5. make one quality-95, 4:2:0 JPEG round trip.

This is global processing only. It uses no detection, mask, identity model, face restoration, selective sharpening, generation, or relighting. The 4070 job completed in approximately 3 seconds.

Output: `output/flux2-no-lora-strong-identity-street-v1/phone-finish-elusarca-inspired-4070.png`
SHA-256: `4E813F2BE54885744F56DC0DD88A76EFC4BF07A07AE502A8B5D6B9AB8FD4333B`

Its held-out centroid was `0.7549`, weakest view `0.6175`. The original accepted checkpoint remains frozen and retains the stronger weakest-view score of `0.6228`; visual selection between the two finishes belongs to Mitch.

## Primary sources

- [Elusarca Krea 2 Smartphone Photography LoRA model card](https://huggingface.co/reverentelusarca/elusarcas-krea2-smartphone-photography-lora)
- [Exact Hugging Face file listing](https://huggingface.co/reverentelusarca/elusarcas-krea2-smartphone-photography-lora/tree/main)
- [RES4LYF / ClownsharKSampler author repository](https://github.com/ClownsharkBatwing/RES4LYF)
