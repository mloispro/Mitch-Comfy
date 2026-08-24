# Krea2 Gokay Realism Evaluation

## Decision

Gokay Realism adds more whole-frame street structure and pedestrian variation than the smartphone
slider, but it also changes Mitch's face more. Do not replace the selected smartphone `0.35`
setting with Gokay for the current identity-sensitive workflow.

## Compatibility finding

The published `krea2_realism_lora.safetensors` contains 528 LoRA tensors whose keys begin with
`base_model.model.`. The installed ComfyUI Krea2 loader did not map that prefix: every tensor was
reported as `lora key not loaded`. The initial nominal `0.50` and `0.75` runs were therefore no-op
mechanism failures and are excluded from evaluation.

The local converter changes only the key prefix to `diffusion_model.` and preserves every tensor
value. The converted file loaded without adding any unloaded-key warnings. Reproduce it with:

```powershell
.\scripts\download-krea2-gokay-realism-lora.ps1
```

## Conditioning mechanism

Gokay is a whole-model realism LoRA. It receives no reference photograph and supplies no identity
signal. Mitch's genuine photograph still enters through both training-matched Identity Edit paths:

1. VAE appearance tokens through `Krea2EditModelPatch`.
2. Image-aware Qwen3-VL instruction conditioning through `Krea2EditGroundedEncode`.

The valid model chain is Krea2 Turbo -> converted Gokay LoRA -> Identity Edit v1.2 -> Identity Edit
model patch.

## Valid controlled results

All images used the same genuine reference, prompt, seed `9472103`, `832x1248` resolution, 12
steps, CFG `1`, Euler/simple sampling, Identity Edit strength `1`, `ref_boost=6`, and 768-pixel
grounding.

| Variant | Four-reference centroid | Visual result |
| --- | ---: | --- |
| Smartphone 0.35 | 0.7225 | Best identity; modest added background texture |
| Gokay 0.35 | 0.7130 | More varied crowd and street structure; visible face shift |
| Gokay 0.50 | 0.7073 | Stronger scene change; greater identity loss |

The scores are local InsightFace AntelopeV2 diagnostics against four genuine held-out photographs.
They are useful for rejecting drift but do not prove identity or overall photographic quality.

## Preserved artifacts

- `output/krea2-gokay-realism-ab/gokay-realism-0p35-seed-9472103.png`
- `output/krea2-gokay-realism-ab/gokay-realism-0p50-seed-9472103.png`
- `work/identity-evals/krea2-gokay-realism-valid-ab-seed-9472103.json`

## Source

- https://huggingface.co/gokaygokay/Krea-2-Realism-LoRA
