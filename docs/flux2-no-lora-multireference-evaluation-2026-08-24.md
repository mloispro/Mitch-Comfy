# FLUX.2 no-character-LoRA multi-reference evaluation — 2026-08-24

> **Historical record — not current instructions.** These routes were rejected or superseded. See `docs/STATUS.md` for current state.

> **Superseded by a stronger tested route:** the later Inline Studio audit and controlled two-stage experiment found that a Klein 9B street plate followed by an undistilled Klein 4B Base whole-frame identity edit reached a `0.7584` held-out centroid and a `0.6262` weakest view. See `docs/flux2-no-lora-strong-identity-street-v1-evaluation-2026-08-24.md`. The one-stage native and PuLID rejections below remain valid for those tested graphs.

## Decision

**Updated after Mitch's full-size visual rejection:** do not use the native FLUX.2 workflows as a Mitch identity solution. Dev and Klein render detailed crowd scenes, but neither preserves his recognizable eye, mouth, and jaw structure well enough without a character LoRA.

- Preserve the Dev and Klein graphs as background/detail experiments only.
- **Do not use PuLID-Flux2 for Mitch.** It produced polished photographs but failed held-out identity at both documented and maximum strength.
- **Do not add the current third-party FLUX.2 IP-Adapter.** Its repository supplies node code but no author-linked trained checkpoint, shipped workflow, identity validation, or face-recognition input. Its SigLIP-only signal is generic appearance conditioning, not verified face identity.

The best no-character-LoRA fallback tested at the time was the one-pass Krea2 Identity Edit street-corner
workflow documented in `docs/no-character-lora-street-corner-evaluation-2026-08-24.md`. It scored `0.7459`
against five held-out genuine photos and is now archived; visual review remains authoritative.

## Conditioning that was actually tested

Four genuine photos enter in fixed semantic order:

1. front face;
2. three-quarter face;
3. upper body; and
4. full-body build.

Each whole photograph is resized independently to `0.40 MP`, encoded with the FLUX.2 VAE, and appended through chained core `ReferenceLatent` nodes. The prompt explicitly assigns each image its role. There is no character LoRA, output crop, mask, face swap, compositing, restoration, relighting, upscaling, or finishing pass.

This is the released native FLUX.2 editing mechanism. Black Forest Labs documents multi-reference editing and recommends explicit image roles, high-quality references, and fewer references when roles become ambiguous. The official repository lists Dev and Klein as native single- and multi-reference models. ComfyUI's shipped FLUX.2 template uses the same VAE-encode-to-`ReferenceLatent` trace.

## Adapter and control screen

| Candidate | What the image actually controls | Compatibility evidence | Decision |
| --- | --- | --- | --- |
| Native `ReferenceLatent` | Whole-reference semantic conditioning: identity, body, clothing, pose, or style according to explicit image roles | Official BFL model/repository, BFL multi-reference guide, and shipped ComfyUI workflow | Tested; rejected for Mitch identity after full-size visual review |
| PuLID-Flux2 v2 | One InsightFace face embedding plus one EVA-CLIP face crop injected as identity tokens | Author node, weight, and Klein example; exact trained width is Klein 9B | Exact 9B test failed identity; Dev/4B random-width path rejected |
| Third-party FLUX.2 IP-Adapter | SigLIP appearance tokens, including multi-image batches | One-commit node repository; no linked trained file, author example workflow, face-recognition branch, or identity benchmark | Rejected before install: unverified weights and generic appearance signal |
| Depth/pose/edge controls and RefControl-style LoRAs | Geometry, pose, layout, or reference structure | Useful for composition, but not a face-identity mechanism | Not added because they do not address the observed identity failure |
| FLUX.1 FaceID/PuLID/PhotoMaker/WithAnyone/USO adapters | Identity or subject features for different base architectures | Their trained block maps and hidden widths target FLUX.1 or another family | Incompatible with FLUX.2; not stacked |
| Character LoRA | Person-specific learned identity | Valid only for its trained base variant | Explicitly excluded by this experiment |

No realism LoRA, ControlNet, or finishing adapter was added. The observed Dev background failure responded measurably to camera/depth wording alone, so another stage would add complexity without an identity acceptance path.

## Controlled results

All candidates were `832×1248` untouched whole-frame outputs. Identity was measured locally with InsightFace AntelopeV2 `glintr100` against five held-out genuine photos. The genuine-reference pairwise range is `0.6206–0.8652` with mean `0.7471`. YOLO and InsightFace crowd counts are diagnostics, not aesthetic scores.

| Route | Identity centroid | Weakest held-out view | Time | People / faces | Visual decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Dev native v1, seed `9472363` | 0.6404 | 0.4639 | 229.2 s | 9 / 4 | Coherent but softer background and weaker likeness |
| Dev native v2, seed `9472363` | 0.6865 | 0.5788 | 229.1 s | 11 / 6 | Best FLUX.2 background/detail result, but Mitch rejected the likeness |
| Klein 9B native, seed `9472363` | 0.6351 | 0.5036 | 16.1 s | 12 / 2 | Reject this seed: apparent extra limb beside subject |
| Klein 9B native, seed `8675311` | 0.6618 | 0.5368 | 14.1 s | 12 / 2 | Clean whole frame, but not a likeness solution |
| Klein 9B + PuLID v2, strength `1.3` | 0.5210 | 0.4236 | 24.5 s first load | 13 / 4 | Identity drift |
| Klein 9B + PuLID v2, strength `2.0` | 0.4896 | 0.3646 | 8.1 s cached | 14 / 4 | Identity regressed; reject mechanism |

The Dev v2 prompt was the single controlled refinement from v1. It changed only framing/camera wording to ask for a standard 1× phone image with resolved subject, nearby people, stalls, signs, umbrellas, pavement, and Ferris wheel. It improved the identity centroid by `0.0461`, increased crowd detections, and materially sharpened the full scene.

Klein 9B's single refinement changed only the seed. Seed `8675311` removed the extra-limb failure and improved identity by `0.0267` while retaining the same four photos, prompt, model, sampler, and resolution.

## Why PuLID was rejected

The installed PuLID v2 file is `1,364,389,800` bytes with SHA-256 `D5D291CB054EB6ECEB25E3B46EFF8F05F7B58F8F19A89EC76BA730A6BA8935BB`. The exact Klein 9B FP8 checkpoint is `9,433,061,528` bytes with SHA-256 `865BA09F5B4C3CBD3468A4BD3ACB9FCB2F8740C54317482F0BCD4ED1D3655CEE`.

For Klein 9B, PuLID has a real mechanism: AntelopeV2 face embedding plus EVA-CLIP features are converted to identity tokens and injected into matching 4096-wide transformer blocks. The author workflow's strength `1.3` and the node's maximum `2.0` were tested exactly. Both failed Mitch identity; maximum strength made it worse.

The same node is not a valid Dev or Klein 4B identity solution. Its released v2 weights are 4096-wide. For a width mismatch, the code creates a randomly initialized projection and a fresh randomly initialized injector rather than loading trained weights for that width. Therefore the advertised Dev/4B path was rejected at the research gate and was never queued.

The node also reads only `image[0]`; it does not average multiple identity photos. Adding a body photo as another native reference cannot repair a failed face embedding.

## Reopened identity audit after visual rejection

The reference inventory found that the first four-reference graph used three lower-resolution, same-burst images and omitted stronger independent photographs. Replacing those inputs, raising reference scale to the official Klein `1.0 MP`, reducing to a single reference, running Dev single-reference mode, reproducing PuLID's author-shipped 512-square preprocessing, and using a previously approved synthetic anchor all failed. Scores ranged from `0.4371` to `0.6275`, and full-size review still showed the wrong facial structure.

This closes FLUX.2 native and PuLID as no-character-LoRA identity mechanisms for Mitch. The result is a mechanism limit, not a step-count or background-detail problem.

## Installed and packaged artifacts

- Archived quality comparison: `checkpoints/legacy-workflows/experiments/FLUX.2 Dev Native 4-Reference No-LoRA - Tested v2.json`
- Archived fast comparison: `checkpoints/legacy-workflows/experiments/FLUX.2 Klein 9B Native 4-Reference No-LoRA - Tested.json`
- Archived Dev runner: `checkpoints/legacy-scripts/native-no-lora/run-flux2-dev-multiref-no-lora.ps1`
- Archived 9B runner: `checkpoints/legacy-scripts/native-no-lora/run-flux2-klein9b-native-multiref-no-lora.ps1`
- Archived rejected PuLID runner: `checkpoints/legacy-scripts/native-no-lora/run-flux2-klein9b-pulid-no-lora.ps1`
- Dev measurements: `output/flux2-dev-multiref-no-lora/comparison-identity.json`
- 9B/PuLID measurements: `output/flux2-klein9b-pulid-no-lora/`

The PuLID custom node remains installed as a reproducible research dependency, but neither promoted workflow loads it.

## Primary sources

- [Black Forest Labs FLUX.2 official repository](https://github.com/black-forest-labs/flux2)
- [Black Forest Labs multi-reference editing rules](https://github.com/black-forest-labs/skills/blob/master/skills/flux-best-practices/rules/multi-reference-editing.md)
- [Black Forest Labs image-to-image prompting rules](https://github.com/black-forest-labs/skills/blob/master/skills/flux-best-practices/rules/i2i-prompting.md)
- [Official ComfyUI FLUX.2 workflow template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux2.json)
- [PuLID-Flux2 author repository, tested commit `3a0a3f5`](https://github.com/iFayens/ComfyUI-PuLID-Flux2/tree/3a0a3f5f18260fc914f96a8c7f0f23c835e881cd)
- [PuLID-Flux2 author weights](https://huggingface.co/Fayens/Pulid-Flux2)
- [Third-party FLUX.2 IP-Adapter node reviewed but rejected before installation](https://github.com/youwenjing/comfyui-ipadapter-flux2)
