# Current workflow and model status

Last audited: **2026-09-03**

This file is the canonical current-state inventory. Workflow JSON, the linked custom-node code, and the
verification scripts are the implementation authority. Dated evaluation reports and checkpoint manifests are
historical evidence; words such as “current,” “production,” or “selected” inside those reports describe the
decision at that time unless their status banner says otherwise.

Fresh shipped-default runs of Identity v1.1, Group v1.1, and native Upgrade v1 all passed on 2026-09-03. The exact
prompt IDs, output hashes, six-genuine-reference scores, leakage results, structure diagnostic, report invariants,
and visual checks are recorded in `docs/flux2-klein9b-production-revalidation-2026-09-03.md`. The frozen registry
now tracks the three engines and the visual-preset shell as separate baselines.

The subsequent reuse review kept all three workflows separate and hardened only shared, non-generative plumbing:
manifest/path/hash validation, exact frontend/backend manifest parity, prepared-source geometry resolution, maintenance
checks, GPU-service preflight, reporting, and the specialized verifiers. The generation recipes and shipped defaults
were not changed. Rationale, exact conditioning roles, upstream references, and deferred v2 performance experiments
are recorded in `docs/flux2-klein9b-reuse-hardening-2026-09-03.md`.

## Visible Production workflows

| Workflow | Current role | Identity mechanism | Worker |
| --- | --- | --- | --- |
| `FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets` | **Default** new solo/full-body/lifestyle workflow; clickable scene gallery | Hash-frozen v1 engine: Klein Base 9B + protected V3 step-1600 identity LoRA + genuine native references + smartphone-realism LoRA at `0.25` | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets` | **Default** source-matched group workflow; clickable layout gallery | Hash-frozen v1 group engine: face-interior-free Canny layout + protected V3 step-1600 identity LoRA + separate genuine identity photograph + smartphone-realism LoRA at `0.25` | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B Mitch Identity Studio v1` | Hash-frozen text-control rollback | Same identity engine as v1.1, without the visual preset shell | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B Mitch Group Scene Studio v1` | Hash-frozen manual-source rollback | Same group engine as v1.1, without the visual preset shell | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1` | Restored milestone one-person upgrade; handsome polish and phone style on by default | Four ordered native references + V3 step-1600 identity LoRA; deterministic face/iris/hair polish; accepted Smartphone v13 deep-focus default at `0.25`; optional edge-safe phone-off background finish | RTX 3090, port `8188` |
| `FLUX.2 Dev LoRA - 9 Dating Scenes v1` | Validated specialty workflow for the nine dating-scene templates or controlled scene restaging | FLUX.2 Dev + protected Dev V2 step-1000 LoRA; optional scene image is composition conditioning, not identity | RTX 3090 |
| `Dataset gen - QWEN 2511 - 3-photo` | Dataset-generation utility | Qwen Image Edit 2511 Lightning + multiple-angle LoRA | Local ComfyUI |
| `Train Generated Dataset - AI Toolkit` | Training submission/monitoring utility | AI-Toolkit durable job queue | Local AI-Toolkit |

The first six create or edit photographs. The last two are utilities and are not evidence that a generated
dataset or newly trained adapter is approved.

## Installed LoRAs to keep

Ten LoRA files are currently retained:

| LoRA | Current reason to keep |
| --- | --- |
| `m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors` | Current Klein 9B Identity, Group, and Upgrade workflows |
| `smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors` | Accepted subtle realism layer for Identity and Group; visually accepted deep-focus default in Upgrade, with its automated tradeoffs documented |
| `flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors` | Validated default 8-step acceleration for Identity Studio and optional speed experiment in Group; rejected for Upgrade quality |
| `flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors` | Current FLUX.2 Dev dating-scenes workflow |
| `aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors` | Accepted One Reference/Easy Social rollback |
| `aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors` | Validated Klein 4B portrait/profile specialty adapter |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | Qwen dataset utility |
| `qwen-image-edit-2511-multiple-angles-lora.safetensors` | Qwen dataset utility |
| `krea2_identity_edit_v1_2.safetensors` | Archived no-character-LoRA Krea2 fallback |
| `krea-smartphone-photo-slider.safetensors` | Archived Krea2 fallback camera appearance |

Protected custom LoRA hashes:

- Klein 9B V3 step 1600: `D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC`
- Smartphone Snapshot Photo Reality v13: `1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90`
- Klein Base 9B rank-256 BF16 Turbo: `A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600`
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

- The v1.1 Identity and Group galleries are thin shells around the unchanged hash-frozen v1 engines. Their labels,
  prompts, thumbnails, recommended identity profiles, group source assets, and target geometry come from the single
  canonical `web/assets/scene-presets/manifest.json`. Prepared Identity presets enforce their recorded reference
  profile on the backend; custom prompts retain the user's explicit profile selection.
- The three Klein 9B production workflows expose a `Visible flattering enhancement` prompt-conditioning toggle.
  Identity Studio and Upgrade open with it enabled. Group Scene opens in the separately validated identity-first
  natural-appearance mode; its optional enabled clause is short and rendering-only. The toggle never switches models
  or references.
- Identity Studio and Group Scene automatically load Smartphone Snapshot Photo Reality v13 after the identity LoRA at
  strength `0.25` and prepend its trained `casual snapshot` trigger. It is third when Turbo is active. Upgrade loads it
  by default when `Phone-camera realism` is on; its optional phone-off path uses the separate natural-lens background finish. The
  isolated same-seed 4070 A/B improved
  held-out identity centroid from `0.7891` to `0.8100` and weakest-view similarity from `0.6711` to `0.7029`, with
  a subtle realism gain and no visual hair or sharpening regression. This layer is independent of the appearance toggle.
- Identity Studio and Group Scene expose the reversible Fast Turbo control. Identity Studio opens with its validated
  8-step / CFG `1.0` route; Group defaults it off because selected-main identity fell `0.5958 → 0.5672`. Upgrade does
  not expose Turbo: its clean phone-style-off retest was `9.54×` faster, but polished identity fell `0.7662 → 0.6958`,
  yaw moved `+1.6934°`, and background micro-luma detail fell `11.9536 → 4.5229`. Evidence is under
  `work/flux2-klein9b-upgrade-safe-polish-20260902/clean-turbo-ab`.
- The current Upgrade acceptance run uses the restored four-reference 50-step whole-frame path and deterministic v4
  face/hair-interior polish. Sparse local-median dot removal reduced fixed-threshold dark facial dots `35.9%` versus v3,
  while existing-luminance-guided hair highlights added only `1.32 / 255` mean active-hair lift. Final gaze-locked identity
  is `0.7476` (`strong_match`) with a `0.5546` weakest view above the `0.5533` genuine floor. Protected pixels remain exact,
  and the detailed siding/tree, forehead, and three-quarter direction remain intact. It has no source-latent passes,
   generation masks, Turbo, face swap, restoration, or second model pass.
- Upgrade's report schema is now v2. Picture 3 plus the protected LoRA are the explicit identity mechanism. Picture 1
  is intended for scene, pose, expression, clothing, lighting, and composition, but it contains the source face and is
  encoded as a `ReferenceLatent`; its identity influence has not been isolated and must not be described as absent.
- Upgrade defaults to the accepted deep-focus Smartphone v13 phone rendering. Turning phone style off optionally applies
  a deterministic natural-lens finish after the full detailed render. A hash-locked local
  U2Net human matte excludes subject colors from normalized near/far Gaussian filters, uses a dilated safety rim, and
  copies protected subject pixels back exactly. On the accepted `1680×1008` v4 frame, `64.4717%` of the background was
  softened with `0 / 255` maximum protected-subject error and no visible cutout halo. Phone-on skips this stage and
  preserves the accepted crisper Smartphone v13 rendering.
- Upgrade's default handsome-polish path now also locks pupil direction to the source using MediaPipe refined iris
  landmarks and a bounded iris-interior warp. The accepted prototype reduced horizontal gaze error `74.1%`, changed
  only `0.0948%` of frame pixels, kept all eyelid/outside pixels exact, and retained `0.7508` six-photo identity with
  negligible pitch/yaw/roll change. It copies no source pixels and does not rerun the diffusion model.
- Separate 4070 rollout smokes passed both production Canny mechanisms. Group identity improved `0.5603 → 0.5626`
  on the established six-photo group gate with no bystander leakage; Upgrade identity stayed `strong_match` and
  improved `0.7575 → 0.7739`, while skin/sharpening metrics remained stable and source geometry was retained. Exact
  graphs and reports are under `output/smartphone-snapshot-klein9b-production-rollout-4070/20260901-210410`.
- Visual review found the first styled Group face too broad, but the attempted detailed skull/proportion lock made the
  internal face more generic and reduced six-photo likeness to `0.5465`. A controlled same-seed 3090 diagnostic kept
  the Canny guide, genuine reference, protected identity LoRA, Smartphone Snapshot v13 at `0.25`, and all sampling
  settings while restoring the concise approved identity prompt. Likeness rose to `0.6007`, above the original
  approved frame's `0.5946`; four faces remained distinct and every leakage gate passed. Group therefore defaults to
  the concise identity-first prompt, not exact-skull or best-day feature-editing instructions. Identity and Upgrade
  retain their separately accepted appearance behavior. The reloaded production Group node then reproduced the fix at
  `0.5958` with maximum bystander identity `0.3026` and no gate failure; exact evidence is under
  `output/group-identity-correction-3090/20260901-220033`.
- The final best-day controlled solo result passed the held-out identity gate on 2026-09-01 at `0.8106` centroid
  and `0.6156` weakest-view similarity, ranking above the enhancement-off baseline. It permits small same-person
  improvements to bone structure, expression, pores, stubble, and apparent age in addition to tan and fine-line
  treatment. See
  `docs/flux2-klein9b-appearance-polish-evaluation-2026-09-01.md`. A new scene still requires review at full size
  and thumbnail.
- The enabled expression uses closed-lip geometry rather than the word `smile`: a slight confident corner lift, one
  unbroken lip line, and every tooth behind the lips. The same-seed straight-on acceptance frame scored `0.7897`
  centroid and `0.6175` weakest-view similarity with no visible teeth and natural eye catchlights.
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
