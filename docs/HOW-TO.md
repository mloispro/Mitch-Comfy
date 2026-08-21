# Maintenance guide

## Workflow folders

- `workflows/production`: validated workflows intended for normal use.
- `workflows/experiments`: active experiments. This folder appears when it contains its first workflow.

Both appear under the `Mitch` folder in ComfyUI. New or moved files require pressing **Refresh** in the Workflows sidebar. Changes to a workflow that is already open require reopening it.

Version-controlled scene templates live under `assets/comfy-input`. Running `scripts/setup-links.ps1` synchronizes them into ComfyUI's input root with `mitch-workbench-` filenames.

## Custom nodes

The two custom-node folders in this repository are linked directly into ComfyUI. Python changes require a ComfyUI restart. Workflow JSON changes do not.

Third-party custom nodes such as ReActor remain in their own upstream repositories. Their exact revisions are recorded in `config/dependencies.lock.json`.

## Everyday Social Photo Studio workflow

Open `Mitch/production/Social Photo Studio - FLUX Klein`. This is the primary workflow for dating-app and Instagram photos.

1. In **1. ADD 1–4 PHOTOS**, upload at least one clear face. Additional front, left, right, and full-body views improve identity and angle coverage. Keep roles on **Auto** unless classification needs correction.
2. In **2. DESCRIBE THE PHOTOS**, write a normal-language brief and select:
   - **Single**, **Dating Pack** (six), or **Instagram Pack** (nine).
   - **Authentic Phone**, **Professional**, or **35mm Lifestyle**.
   - **Auto Mix**, **Looking at camera**, or **Candid/action**.
   - `photo_count = 0` for the mode default, or 1–9 for an explicit count.
3. Queue once. The generator saves final images, a contact sheet, and `report.json` under `ComfyUI/output/social-photo-studio/<run-id>`.

The workflow automatically rejects clearly mixed-person face references. A full-body reference with no detectable face is treated as unverified soft context and is never used to claim verified body identity.

### Identity finish and optional LoRA

- **Auto** is the default. ReActor/GPEN is kept only when identity improves by at least 0.03 and the isolated subject crop stays within pose, position, and scale safety limits. Unchanged background faces are not edited.
- **Native Only** uses FLUX.2 multi-reference identity without a face swap.
- **Force ReActor** skips the improvement threshold but still refuses failed targeting or unsafe subject geometry.
- Leave **identity_lora** on **None** for reference-only operation. The installed `mtch35` LoRA is Mitch-specific, architecture-validated, and optional; never select it for another person. Its trigger remains blank because no reliable trigger exists in its metadata.

### First-time model setup

Run `scripts/setup-social-photo-models.ps1`, restart ComfyUI, then run `scripts/verify.ps1`. The setup script downloads only the official FLUX.2 Klein 4B FP8 diffusion model and FLUX.2 VAE, resumes partial downloads, and verifies exact SHA-256 hashes before installation.

If the primary resolution runs out of VRAM, the failed photo is retried once at the matching 768-pixel short-side resolution and the fallback is recorded in `report.json`.

## Legacy regression archive

The old fixed Qwen dating graphs and Z-Image experiments are preserved under `checkpoints/legacy-workflows` and intentionally hidden from the normal ComfyUI workflow browser. The validated Qwen v8 workflow and its 80.81 historical identity benchmark remain under `checkpoints/workflows`. Use these only for regression work; the five-node Social Photo Studio is the supported everyday generator.

Exact body identity still requires a clear, neutral full-body reference with an unobstructed contour. A face-less silhouette can guide composition, but the report labels it `reference_supplied_unverified` rather than claiming verified body identity.

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
