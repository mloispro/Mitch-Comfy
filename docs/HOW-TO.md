# Maintenance guide

## Workflow folders

- `workflows/production`: validated workflows intended for normal use.
- `workflows/experiments`: active experiments. This folder appears when it contains its first workflow.

Both appear under the `Mitch` folder in ComfyUI. New or moved files require pressing **Refresh** in the Workflows sidebar. Changes to a workflow that is already open require reopening it.

Version-controlled scene templates live under `assets/comfy-input`. Running `scripts/setup-links.ps1` synchronizes them into ComfyUI's input root with `mitch-workbench-` filenames.

## Custom nodes

The two custom-node folders in this repository are linked directly into ComfyUI. Python changes require a ComfyUI restart. Workflow JSON changes do not.

Third-party custom nodes such as ReActor remain in their own upstream repositories. Their exact revisions are recorded in `config/dependencies.lock.json`.

## Everyday one-reference workflow

Open `Mitch/production/FLUX.2 One Reference Photo`. It is the primary dating-app and Instagram photo workflow and deliberately exposes only two choices:

1. Upload one recent, unfiltered camera photo with a clear face.
2. Describe the new photo in ordinary language, then queue once.

The node derives two identity views from that one upload: the complete photo and an automatic 2x face crop. Both are resized to one megapixel and passed into the official FLUX.2 Klein Base 4B reference-latent path with the locally trained identity LoRA. The prompt supplies phone-versus-professional appearance, camera gaze, pose, clothing, framing, and action; there are no model, sampler, crop, face-swap, or seed controls in the production graph.

Each candidate is checked locally against the uploaded face. Only a result below the calibrated `0.75` cosine retry threshold triggers one additional attempt, and the better-scoring candidate is returned. The selected score, both attempted seeds when applicable, elapsed time, and settings are written to `ComfyUI/output/flux2-one-reference/<run-id>/report.json`. This score is a drift filter, not proof of identity; compare important results visually with the real person.

The workflow rejects historical generated identity fixtures. Do not train or evaluate against generated portraits, beauty-filtered images, or photos of another person.

### Prompt examples

- Phone: `A casual waist-up smartphone photo at an outdoor cafe in soft afternoon daylight, navy T-shirt, relaxed posture, small natural smile, looking just past the camera.`
- Professional: `A natural professional waist-up portrait beside a large loft window, charcoal blazer over a pale blue shirt, looking at the camera, realistic 50mm photograph, restrained retouching.`
- Candid/action: `A candid smartphone action photo walking along a lakeside path at golden hour, three-quarter profile looking ahead, photographed by a friend, natural stride and slight believable motion.`

The production LoRA is checkpoint 1,250 from the ten-photo local dataset, used at strength `0.6`, 20 Euler steps, and guidance `4.0`. It was selected from all six checkpoints by held-out professional/action scores and visual review, then verified on phone, professional, and action scenes plus alternate action seeds. The final 1,500-step checkpoint was rejected because difficult-angle identity regressed.

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

## External backups

Git history is local version control, not an off-computer backup. A private remote can be added later. Large models, LoRAs, datasets, genuine reference photos, and outputs should be backed up separately; their hashes can be recorded under `checkpoints/manifests`.
