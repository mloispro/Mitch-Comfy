# FLUX.2 Dev Mitch identity LoRA v1 evaluation

> **Historical record — not current instructions.** This V1 campaign was rejected; the later protected Dev V2 step-1000 adapter is the retained specialty route. See `docs/STATUS.md`.

Status: **campaign complete; all candidates rejected; no best adapter published**.

Training itself succeeded exactly at the requested settings. Several checkpoints passed the automated portrait/half-body identity and secondary-person leakage gates, but none passed the required full-size and thumbnail visual review. The strongest rejected candidate is step 900 at strength 1.0; this is a diagnostic label, not a production promotion.

## Reproducibility lock

- Base architecture: `black-forest-labs/FLUX.2-dev` (`arch: flux2`)
- FLUX.2 Dev snapshot: `26afe3a78bb242c0a8bb181dcc8937bb16e5c66c`
- Mistral snapshot: `68faf511d618ef198fef186659617cfd2eb8e33a`
- AI Toolkit commit: `0f788923aef28e3a87fa68cfa15a761d9d499d6c`
- AI Toolkit version in adapter metadata: `0.12.23`
- Compatibility patch: `patches/ai-toolkit-flux2-dev-win64gb.patch`
- Compatibility patch SHA-256: `0251c7a199e6e9e7bcb3aa20495a7c69e778e5a7b8d832c666ecd47cf7c27156`
- Required environment: `AI_TOOLKIT_PIN_QUANTIZED_OFFLOAD=0`
- Training config: `config/flux2-dev-identity-v1.yaml`
- Training config SHA-256: `495a0ba5e8e198dd11aed42c9ab32c07dd1f85869c55a3676f04ad3c272c5331`
- Dataset: `datasets/mitch-identity-stills-v3`
- Dataset manifest SHA-256: `d56fe2d752febfa63ca0e76689dfd9d4eaac7443ca086ffa9dfef51186563003`
- Dataset contents: 13 genuine byte-identical training stills with TXT captions; 6 untouched held-outs
- Trigger: `m1tch_person`
- Privacy: all training and evaluation ran locally; no photographs were uploaded.

### Training model hashes

| Component | SHA-256 |
| --- | --- |
| `flux2-dev.safetensors` | `6159a3f19f829c8e84ba6e9996b7afaf7c0a5f3428677f5b37445778a320d275` |
| `ae.safetensors` | `868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3` |
| Mistral shard 01 | `4d735fce2330e13fa96c0ad839fbf703481ab05680593ad32b9219be30c9ff92` |
| Mistral shard 02 | `99c38a089b14a0fca228899132eb8db54ea551bdc96b639267d5177e4a172776` |
| Mistral shard 03 | `4917b19a128315c56c8ff3cdf531d9a88371314098c2698e28ac03a6d8c77813` |
| Mistral shard 04 | `acc83eeee5e993095ca9ad7518bf29f511b9e13b6b57d4f53580e9b8b6c084fe` |
| Mistral shard 05 | `5d81e8c278b8af82f96a69f36ce71e743a70aa8fe28d3118bd8d24dae5001b62` |
| Mistral shard 06 | `8ca257e4f5ee8446536562de3e0b7e1e2614d23b22311bf29bb88385218ba1d9` |
| Mistral shard 07 | `f880e9065a25eac3e4986d9b4d45ae0225fe59e093731ad633fded7e91ce058f` |
| Mistral shard 08 | `3bc98dc787b471919b469862a9c67f39f9ab2a407e641614da858cd35cb65823` |
| Mistral shard 09 | `b1ad95f53916db9384b80f3a233fb524d3085136b9065fd39a1fdf4f1749c401` |
| Mistral shard 10 | `97a62f323631157567b35651d7f835baaf290e5fc17c92bb888023cdb43218d1` |

The frozen transformer and Mistral encoder were quantized to `qfloat8` for training, with low-VRAM mode and full layer offloading. The rank-16 LoRA tensors are BF16 and remain normal FLUX.2 Dev adapters; quantized inference is not required.

## Exact training and execution result

- Rank/alpha: `16/16`, linear modules only
- Resolution buckets: `[768, 1024]`; both resolutions were exercised
- Steps: `1200`; batch/accumulation: `1/1`
- Precision: BF16 with gradient checkpointing
- Scheduler/timestep/content: flow-match, weighted, balanced
- Optimizer: AdamW 8-bit; constant learning rate `8e-5`; weight decay `1e-4`; max gradient norm `1.0`
- Text encoder: frozen; latent and text-embedding disk caches enabled
- Disabled: EMA, augmentation, flips, regularization images, caption dropout, token dropout, token shuffling, and training samples
- Runtime: 5 hours 29 minutes on the RTX 3090
- Observed steady-state memory: about 49–60 GB private host memory and 15–17 GB VRAM; no memory leak
- Outcome: exit code 0; no OOM, NaN, traceback, or numerical instability
- Checkpoints: 100-step intervals; 12 adapters retained

Every retained adapter contains 320 tensors / 97,517,568 elements, all finite, with `ss_base_model_version=flux2` and correct step metadata.

| Step | SHA-256 |
| ---: | --- |
| 100 | `54db7065ff8a31929a924675cbdd6fb604e054d1d3baa400926889b7c9a40ab7` |
| 200 | `6bf105746cffef49b371ed58559536738f5cabc864a518c9178f80c805a75d5d` |
| 300 | `1994272c55ecd58318b812ac72b1e822c5abb370244d83690a721adfb9d0b200` |
| 400 | `63fbd5bd9c03a37a0221c645e5401ff7b7932dbc230493a2c73f9210c8167517` |
| 500 | `30593cc5ed330fbad38f152678e8f37ce55f47b82a302288a02775fe2a76b9a7` |
| 600 | `ef31ea8de624b176e3870a6be6663c69f0d53b3a97287ff3b335ff4891f5faf6` |
| 700 | `ce31edfeda62960e049b8746b86fa30c4d6da2f40c6eff4c01b245d19dac27b2` |
| 800 | `50453aedacb890661e3405acd66652003c78a72494fecd683b062c4af19df8b2` |
| 900 | `288a90bce6084cef92897122000830ee1427149712bd36a9b3de1074152839bc` |
| 1000 | `d5c60a83bb666eeb88571465d5bda401333a87918a6a34a021cda67342fa24d4` |
| 1100 | `c419de247ef2eaedfa32e54084e47fabd86f6e7210f783bfa1d10787208ecab6` |
| 1200/final | `c43f63ebf5cdcff99437a1c3938175e79bfab76e56f04f122ad736151ba3a419` |

## Smoke gate

The temporary 20-step config completed at both target resolutions. Loss was finite (`0.4718` to `1.086`), the saved adapter contained the expected 320 tensors, and the production job resumed the same adapter plus optimizer state from metadata step 20.

- Step-20 SHA-256: `6ab9eda82b0a0a09692d6c3d0c1913e9183b6403ced0f6dbd33914e4a5809f45`
- Step-20 size: 195,077,160 bytes
- Production resume proof: `Found step 20 in metadata`, with no missing keys

## Benchmark lock and gate correction

The benchmark uses FLUX.2 Dev only, no reference conditioning, face swap, masks, restoration, or post-processing. Every candidate uses 832×1248 output, 20 Euler steps, guidance `4.0`, LoRA strength `1.0`, and scene seeds `8675310` through `8675314`.

Every solo face was compared against all six genuine held-outs with local AntelopeV2 recognition. The crowd gate follows the campaign rule exactly: secondary identity leakage or duplication fails the gate; weak identity on the intended center person is reported separately as a limitation. An initial report revision treated weak center identity as a leakage-gate failure; the evaluator and all JSON reports were corrected without regenerating or rescoring images.

## Checkpoint ranking

Status values are calibrated from the six held-outs. The number in parentheses is centroid similarity.

| Step | Portrait | Waist-up | Near-profile | Core gate | Full-body | Max secondary identity | Automatic gate | Manual review | Disposition |
| ---: | --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| 400 | near (0.516) | near (0.520) | drift (0.407) | fail, 0 strong | drift (0.356) | 0.062 | fail | automatic failure | rejected |
| 600 | strong (0.742) | near (0.560) | near (0.565) | fail, 1 strong | drift (0.442) | 0.231 | fail | automatic failure | rejected |
| 800 | strong (0.771) | strong (0.634) | strong (0.710) | pass, 3 strong | near (0.542) | 0.072 | pass | fail | rejected |
| 900 | strong (0.778) | strong (0.759) | strong (0.647) | pass, 3 strong | near (0.523) | 0.136 | pass | fail | **best rejected candidate** |
| 1000 | strong (0.753) | strong (0.727) | strong (0.676) | pass, 3 strong | drift (0.465) | 0.267 | pass | fail | rejected |
| 1100 | strong (0.779) | drift (-0.033) | strong (0.709) | fail, 2 strong | strong (0.599) | 0.213 | fail | automatic failure | rejected |
| 1200 | strong (0.695) | strong (0.629) | strong (0.632) | pass, 3 strong | drift (0.478) | 0.224 | pass | fail | rejected |

Step 1000 led the first-pass 400/600/800/1000/1200 ranking on core mean/minimum. Both ±100 neighbors were then evaluated. Step 900 overtook it on core mean and retained a near-match full-body result, so step 900 is the strongest rejected checkpoint.

## Raw reports and outputs

Each JSON contains exact prompts, seeds, settings, adapter hash, absolute raw image paths, six-reference scores, crowd face measurements, and disposition.

- `work/flux2-dev-identity-v1/benchmarks/flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s0400.safetensors-s1.00-20260825-220936.json`
- `work/flux2-dev-identity-v1/benchmarks/flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s0600.safetensors-s1.00-20260825-221916.json`
- `work/flux2-dev-identity-v1/benchmarks/flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s0800.safetensors-s1.00-20260825-222728.json`
- `work/flux2-dev-identity-v1/benchmarks/flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s0900.safetensors-s1.00-20260825-225243.json`
- `work/flux2-dev-identity-v1/benchmarks/flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s1000.safetensors-s1.00-20260825-223542.json`
- `work/flux2-dev-identity-v1/benchmarks/flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s1100.safetensors-s1.00-20260825-230059.json`
- `work/flux2-dev-identity-v1/benchmarks/flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s1200.safetensors-s1.00-20260825-224359.json`

Raw images are preserved under `C:\projects\AI-Tools\ComfyUI\output\identity-eval\flux2-dev-v1`.

## Manual review and limitations

Full-size and thumbnail review was completed for every automatically qualified endpoint (800, 900, 1000, and 1200), with additional review of step 400.

- Apparent age fails: the generated subject reads younger and smoother than current held-outs.
- Hair fails: density, hairline, and volume are consistently too full.
- Facial geometry fails: eyes, forehead, nose, and jaw vary materially between scenes.
- Skin texture fails: overly even synthetic texture plus visible forehead/neck artifacts remain.
- Expression fails: profile eye direction and some mouth shapes look generated.
- Scene integration passes: lighting, clothing, and whole-frame placement are generally coherent.
- Crowd leakage passes: secondary people remain distinct, but the intended center person is visibly not Mitch at every tested checkpoint.
- Full-body remains a stretch failure: proportions are plausible, but the 90–140 pixel face is generic or unstable. This dataset has only two body-framed mirror photographs.

Strength 1.0 was not visibly overdriven; the problems are identity/realism limitations rather than clear excessive LoRA strength. The conditional strength-0.8 comparison was therefore not run.

## Outcome

No checkpoint met the combined automatic and manual promotion gate, and
`m1tch-flux2-dev-identity-v1-best.safetensors` was never created. Raw outputs and evaluation records remain;
the staged V1 adapter weights were deleted on 2026-09-01. No result should be described as full-body identity
locked.
