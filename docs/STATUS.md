# Current workflow and model status

Last audited: **2026-09-01**

This file is the canonical current-state inventory. Workflow JSON, the linked custom-node code, and the
verification scripts are the implementation authority. Dated evaluation reports and checkpoint manifests are
historical evidence; words such as “current,” “production,” or “selected” inside those reports describe the
decision at that time unless their status banner says otherwise.

## Visible Production workflows

| Workflow | Current role | Identity mechanism | Worker |
| --- | --- | --- | --- |
| `FLUX.2 Klein 9B Mitch Identity Studio v1` | Primary workflow for completely new solo, full-body, or prompt-defined group photographs | Klein Base 9B + protected V3 step-1600 LoRA + genuine native reference photographs | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B Mitch Group Scene Studio v1` | Source-matched group composition | Face-interior-free Canny layout + protected V3 step-1600 LoRA + separate genuine identity photograph | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1` | Re-render an existing one-person Mitch image while preserving its layout | Exact source + face-free guide + genuine identity photo + genuine hair reference + V3 step-1600 LoRA | RTX 3090, port `8188` |
| `FLUX.2 Dev LoRA - 9 Dating Scenes v1` | Validated specialty workflow for the nine dating-scene templates or controlled scene restaging | FLUX.2 Dev + protected Dev V2 step-1000 LoRA; optional scene image is composition conditioning, not identity | RTX 3090 |
| `Dataset gen - QWEN 2511 - 3-photo` | Dataset-generation utility | Qwen Image Edit 2511 Lightning + multiple-angle LoRA | Local ComfyUI |
| `Train Generated Dataset - AI Toolkit` | Training submission/monitoring utility | AI-Toolkit durable job queue | Local AI-Toolkit |

The first four create or edit photographs. The last two are utilities and are not evidence that a generated
dataset or newly trained adapter is approved.

## Installed LoRAs to keep

Exactly eight LoRA files survived the 2026-09-01 cleanup:

| LoRA | Current reason to keep |
| --- | --- |
| `m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors` | Current Klein 9B Identity, Group, and Upgrade workflows |
| `flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors` | Current FLUX.2 Dev dating-scenes workflow |
| `aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors` | Accepted One Reference/Easy Social rollback |
| `aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors` | Validated Klein 4B portrait/profile specialty adapter |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | Qwen dataset utility |
| `qwen-image-edit-2511-multiple-angles-lora.safetensors` | Qwen dataset utility |
| `krea2_identity_edit_v1_2.safetensors` | Archived no-character-LoRA Krea2 fallback |
| `krea-smartphone-photo-slider.safetensors` | Archived Krea2 fallback camera appearance |

Protected custom LoRA hashes:

- Klein 9B V3 step 1600: `D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC`
- FLUX.2 Dev V2 step 1000: `7C0C4F1726189C51E19C8392C12FE3E03A26BD084FFFB8D84B907C966A77CC3E`
- Klein 4B V1 best: `8A7D1477914D0A5262BF219F71F303418130449841CF220226B4E979D7232F87`
- Klein 4B V3 portrait/profile: `C43D7C1FCA404A8B316A9D0C8756E140033E4763532628F62FACC791F0B8A149`

All four Mitch-trained keepers are also versioned through Git LFS under `checkpoints/loras/mitch`. The Qwen and
Krea2 files are third-party dependencies and remain installation-only.

See `docs/lora-cleanup-2026-09-01.md` for the removed families and disk totals.

## Archived and rejected routes

The following are not normal-use Production workflows:

- Easy Social Photos and One Reference Photo are exact, recoverable 4B rollbacks under
  `checkpoints/legacy-workflows/production`.
- Krea2 Identity Edit/Identity Anchor graphs are archived fallbacks, not the current primary workflow.
- ReActor, masked host replacement, native no-LoRA, HiDream-O1, InfiniteYou, Z-Image identity training,
  non-selected 9B LoRA versions, and Krea2 character-LoRA experiments remain historical evidence only.
- Retired launchers, configs, and templates are under `checkpoints/legacy-scripts` and must not be run in place.
- Failed or superseded LoRA weights were deleted. A historical report saying a rejected weight “remains
  preserved” is superseded by the 2026-09-01 cleanup record.

## Acceptance rules that still apply

- Automated face similarity is a ranking and rejection diagnostic, not proof of identity.
- Full-size and thumbnail visual review remains mandatory.
- Use genuine photographs for identity evaluation.
- A scene/style reference is not automatically an identity reference.
- Do not add face swap, masks, restoration, relighting, or sharpening without a measured failure and acceptance test.
- Inspect both GPU queues before generation and never interrupt active training or generation.

## Verification

Run the repository verifier before check-in:

```powershell
.\scripts\verify.ps1
```

The specialized read-only workflow verifiers are:

```powershell
.\scripts\verify-flux2-klein9b-mitch-identity-studio-v1.ps1
.\scripts\verify-flux2-klein9b-group-scene-studio-v1.ps1
.\scripts\verify-flux2-klein9b-upgrade-photo-detail-realism-v1.ps1
```

Do not pass `-Smoke` during routine verification; that option queues a generation.
