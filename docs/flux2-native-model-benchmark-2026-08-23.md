# FLUX.2 Native Model Benchmark — 2026-08-23

## Decision

Keep the accepted FLUX.2 Klein Base 4B plus Mitch identity LoRA route in production. Neither Klein 9B KV nor FLUX.2 Dev is a better default for local dating/IG generation on the RTX 3090.

FLUX.2 Dev produced the more believable and varied crowd scene, but it was 12.8 times slower than Klein 9B, scored slightly worse for identity, and still contained a near-duplicate secondary-face pair. It is not promoted to production.

## Controlled comparison

- Prompt: `Create a new candid smartphone photo of the same adult man shown in Pictures 1 through 4 walking down a busy city street. Use the pictures only to preserve his identity; do not copy their poses, clothing, framing, or backgrounds.`
- Four genuine identity references, resized independently to 640 × 640.
- Same seed (`8675311`), output size (`896 × 1344`), Euler sampler, FLUX.2 VAE, and untouched single-pass output.
- Klein 9B used its native distilled regime: four steps and KV cache.
- FLUX.2 Dev used its native quality regime: 20 steps and guidance 4.0.
- No identity LoRA, scene constraints, compositing, refiner, phone finish, post-processing, or candidate ranking.

## Results

| Route | Identity | Total | Sampling | Faces detected | Secondary identity leakage | Secondary duplicate maximum | People / vehicles |
|---|---:|---:|---:|---:|---:|---:|---:|
| Klein 9B KV | 0.6300 | 19.745 s | 15.031 s | 5 | 0.0567 | 0.1480 | 11 / 4 |
| FLUX.2 Dev | 0.6096 | 251.991 s | 244.087 s | 13 | 0.0806 | 0.6228 | 11 / 1 |

The accepted 4B+LoRA minimal reality proof remains the production identity reference at 0.8959 in 46.723 seconds. It used the same seed, size, 20 steps, four source photos, and LoRA strength 0.50, but a shorter token-based prompt and 512 × 512 reference conditioning, so it is context rather than a strictly identical third row.

## Visual inspection

### Klein 9B KV

- Sharper and more detailed architecture and street surface.
- Main subject is larger, but identity is not strong enough for production.
- The crowd repeats the same dark-jacket male archetype.
- The all-white outfit has an implausible repeated/crinkled texture.
- The result still reads as generated rather than a naturally captured crowd photo.

### FLUX.2 Dev

- More natural full-body candid composition and more varied crowd clothing, sex, pose, and activity.
- Better large-scene coherence than Klein 9B and the accepted 4B proof.
- The subject is smaller and his face is less faithful to the references.
- The background is strongly depth-of-field blurred despite the need for detailed backgrounds.
- The maximum secondary-pair face similarity is 0.6228. This passes the current 0.72 rejection limit, but is close enough to confirm that Dev does not eliminate crowd repetition.
- On the 24 GB RTX 3090, the 33.8 GB staged model required CPU offload and took about 3 minutes 47 seconds for diffusion sampling alone.

## Production implication

Do not replace the current 4B+LoRA generator with either native model. Klein 9B does not buy enough crowd realism, while Dev buys better scene realism at unacceptable speed and identity cost.

If a future crowd-heavy route is tested, FLUX.2 Dev is only a background/scene research candidate. It first needs a Dev-compatible identity solution and must beat the existing identity threshold without copy-paste compositing. Until then, the smallest reliable workflow remains the accepted 4B+LoRA route plus scene-quality rejection and regeneration.

## Artifacts

- Direct comparison: `C:\projects\AI-Tools\ComfyUI\output\flux2-model-benchmark\20260823-144606-362027\comparison_00001_.png`
- Klein 9B: `C:\projects\AI-Tools\ComfyUI\output\flux2-model-benchmark\20260823-144606-362027\klein-9b-kv_00001_.png`
- FLUX.2 Dev: `C:\projects\AI-Tools\ComfyUI\output\flux2-model-benchmark\20260823-144606-362027\flux2-dev_00001_.png`
- Machine-readable report: `C:\projects\AI-Tools\ComfyUI\output\flux2-model-benchmark\20260823-144606-362027\report.json`
- Accepted 4B+LoRA context image: `C:\projects\AI-Tools\ComfyUI\output\flux2-minimal-reality-test\20260823-125645-836640\raw_00001_.png`
- Accepted 4B+LoRA context report: `C:\projects\AI-Tools\ComfyUI\output\flux2-minimal-reality-test\20260823-125645-836640\report.json`

## Official sources

- Black Forest Labs FLUX.2 repository: https://github.com/black-forest-labs/flux2
- Official FLUX.2 Dev model: https://huggingface.co/black-forest-labs/FLUX.2-dev
- Official ComfyUI FLUX.2 Dev guide: https://docs.comfy.org/tutorials/flux/flux-2-dev
