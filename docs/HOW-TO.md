# Maintenance guide

## Workflow folders

- `workflows/production`: validated workflows intended for normal use.
- `workflows/experiments`: active experiments. This folder appears when it contains its first workflow.

Both appear under the `Mitch` folder in ComfyUI. New or moved files require pressing **Refresh** in the Workflows sidebar. Changes to a workflow that is already open require reopening it.

The normal workflow is **Workflows → Mitch → production → FLUX.2 Easy Social Photos - 1-4 References**.
The accepted one-reference v1 remains beside it as a frozen rollback/comparison baseline. If a ComfyUI tab
stayed open while custom nodes were restarted and shows the node as missing, open a fresh tab.

Version-controlled scene templates live under `assets/comfy-input`. Running `scripts/setup-links.ps1` synchronizes them into ComfyUI's input root with `mitch-workbench-` filenames.

## Custom nodes

The two custom-node folders in this repository are linked directly into ComfyUI. Python changes require a ComfyUI restart. Workflow JSON changes do not.

Third-party custom nodes such as ReActor remain in their own upstream repositories. Their exact revisions are recorded in `config/dependencies.lock.json`.

## Everyday social-photo workflow

Open `Mitch/production/FLUX.2 Easy Social Photos - 1-4 References`. It deliberately exposes only the useful choices:

1. Upload one to four recent, unfiltered camera photos in any order.
2. Describe the scene and clothing in ordinary language.
3. Choose phone/professional, framing, and gaze/action, then queue once.

The node selects the best detected source, then derives its complete-photo view and an automatic 2.4x face
crop. Both are compact 0.25 MP references for the official FLUX.2 Klein Base 4B reference-latent path and the
local identity LoRA. The prompt supplies phone-versus-professional appearance, camera gaze, pose, clothing,
framing, and action; there are no model, sampler, crop, face-swap, or seed controls in the graph.

Generation is `896×1344`. The built-in natural-skin instruction keeps face, ears, neck, arms, and hands under
one white balance, shadow direction, edge softness, and sensor response while requesting subtle nonuniform
redness, pigmentation, stubble, vellus hair, pores, and ordinary marks. This replaced the overly smooth v1.0.0
wording; no face refiner or local sharpening pass is used.

Each candidate is checked locally against the supplied genuine-photo centroid. Balanced scenes retry below
`0.75`; action/full-body scenes use a calibrated `0.70` floor because the detected output face is smaller.
The higher-scoring result is returned when a retry occurs. Scores, selection measurements, seeds, elapsed
time, and settings are written under
`ComfyUI/output/flux2-reference-studio/<reference-count>-references/<run-id>/report.json`. This score
is a drift filter, not proof of identity; compare important results visually with the real person.

The workflow rejects historical generated identity fixtures. Do not train or evaluate against generated portraits, beauty-filtered images, or photos of another person.

### Frozen v1 baseline

Mitch visually accepted the v1 result on 2026-08-22. The exact graph and identity-core implementation are
locked in `config/frozen-baselines.json` and tagged `flux2-one-reference-v1.0.0`. Normal verification fails if
either file drifts. Keep this workflow untouched; add presets, multi-reference support, or UI experiments as
new files and measure them against v1 before promotion.

The model and private identity LoRA are also checked by SHA-256. Git preserves the small workflow/code files,
but not the private LoRA, dataset, or reference photos. Keep the LoRA and genuine training set in a separate
private backup if recovery after a disk failure matters.

### Reference selection and generation profiles

Supply the photos in any order. The workflow detects every usable face, rejects likely mixed identities, and
ranks face size, sharpness, exposure, detector confidence, edge context, and frontal angle to select the best
generation source. Extra photos form the identity centroid used for local output ranking. They are not all
passed into FLUX.2: controlled tests found that two/three model latents scored `0.7285` in `124.6` seconds and
four latents scored `0.7344` in `164.1` seconds, both worse than the two derived views from one selected photo.

Choose style, framing, and moment from the short preset menus, then describe only the scene, clothing, and
activity. Select **Prompt decides** when the prompt already contains detailed camera, framing, or gaze
instructions. Multi-photo camera-facing phone and professional modes use the private identity LoRA at strength
`0.4` and guidance `2.0`. One-photo, candid, action, and full-body modes automatically use strength `0.6` and
guidance `4.0` to protect small/off-angle faces. All profiles use 20 Euler steps plus a full reference and 2.4x
face crop at 0.25 MP each. Candid tries its validated off-angle seed first and retains the ordinary seed as a
fallback. The compact references are intentional: the
exact city A/B improved from `0.8704` identity in `47.6` seconds to `0.9112` in `25.3` seconds while reducing
the harsh, separately rendered face texture.

### Prompt examples

- Phone: `A casual waist-up smartphone photo at an outdoor cafe in soft afternoon daylight, navy T-shirt, relaxed posture, small natural smile, looking just past the camera.`
- Professional: `A natural professional waist-up portrait beside a large loft window, charcoal blazer over a pale blue shirt, looking at the camera, realistic 50mm photograph, restrained retouching.`
- Candid/action: `A candid smartphone action photo walking along a lakeside path at golden hour, three-quarter profile looking ahead, photographed by a friend, natural stride and slight believable motion.`

The frozen-v1 production LoRA setting is checkpoint 1,250 from the ten-photo local dataset, used at strength
`0.6`, 20 Euler steps, and guidance `4.0`. Easy Social Photos reuses that same checkpoint and selects between
its balanced and action profiles automatically; this is not a different or missing LoRA.
The checkpoint was selected from all six checkpoints by held-out professional/action scores and visual
review. The final 1,500-step checkpoint was rejected because difficult-angle identity regressed.

Easy Social Photos v1.0.1 is frozen separately under `flux2-easy-social-v1.0.1`. The previous v1.0.0 tag remains
available for exact rollback, while the active registry hashes protect the natural-skin production files.

### First-time model setup

Run `scripts/setup-one-reference-photo.ps1`, restart ComfyUI, then run `scripts/verify.ps1`. The setup script installs the pinned Base 4B FP8 model, Qwen3 4B FP8 mixed text encoder, and FLUX.2 VAE; it also verifies the private production identity LoRA. The LoRA is not downloaded because it was trained locally from private photos—back it up separately or recreate it with `scripts/flux2-identity-lora.py` and the ignored local dataset.

The FLUX.2 Klein Base 4B weights are Apache 2.0. The workflow remains personal and local; generated photos should not be presented deceptively.

For the most reliable result, use a recent photo with visible eyes, hairline, and natural skin texture. Full-body scenes can be requested from the same face reference, but exact body proportions cannot be inferred from a face-only upload.

## Legacy regression archive

The superseded five-node Social Photo Studio, old fixed Qwen dating graphs, and Z-Image experiments are preserved under `checkpoints/legacy-workflows` and intentionally hidden from the normal ComfyUI workflow browser. The validated Qwen v8 workflow and its historical benchmark remain under `checkpoints/workflows`. Use them only for regression work.

## Checkpointing

Use:

```powershell
.\scripts\checkpoint.ps1 -Message "Improve ReActor face detail"
```

For an important milestone:

```powershell
.\scripts\checkpoint.ps1 -Message "Validate sharper multi-person workflow" -Tag "multiperson-sharp-v2"
```

The script runs repository and live-link checks before committing.

## Restoring a workflow

View history:

```powershell
git log --oneline -- workflows/production
```

Restore a specific workflow from an earlier commit:

```powershell
git restore --source <commit> -- "workflows/production/Workflow Name.json"
```

Then refresh and reopen it in ComfyUI.

Restore the accepted one-reference baseline directly with:

```powershell
git restore --source flux2-one-reference-v1.0.0 -- "workflows/production/FLUX.2 One Reference Photo.json" "custom_nodes/ComfyUI-AIToolkit-Training/one_reference_photo.py" "custom_nodes/ComfyUI-AIToolkit-Training/__init__.py"
```

Restart ComfyUI after restoring Python files, then run `scripts/verify.ps1`.

## External backups

Git history is local version control, not an off-computer backup. A private remote can be added later. Large models, LoRAs, datasets, genuine reference photos, and outputs should be backed up separately; their hashes can be recorded under `checkpoints/manifests`.
