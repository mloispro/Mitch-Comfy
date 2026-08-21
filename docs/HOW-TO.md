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

Open `Mitch/production/Social Photo Studio - FLUX.2 Klein 9B KV`. This is the primary workflow for dating-app and Instagram photos.

1. In **1. ADD 1–4 PHOTOS**, upload at least one clear face. A single frontal photo works; front, left, and right views improve identity across camera angles, and an optional unobstructed full-body view helps proportion-sensitive scenes. Keep roles on **Auto** unless classification needs correction.
2. In **2. DESCRIBE THE PHOTOS**, write a normal-language brief and select:
   - **Single**, **Dating Pack** (six), or **Instagram Pack** (nine).
   - **Authentic Phone**, **Professional**, or **35mm Lifestyle**.
   - **Auto Mix**, **Looking at camera**, or **Candid/action**.
   - `photo_count = 0` for the mode default, or 1–9 for an explicit count.
3. Queue once. The generator saves final images, a contact sheet, and `report.json` under `ComfyUI/output/social-photo-studio/<run-id>`.

The workflow automatically rejects clearly mixed-person face references. It resizes each reference to roughly 640×640 total pixels while preserving the full image, so facial identity, hair, pose, and useful context remain available without wasting VRAM. Full-body context is added only for smart-casual, active, travel, and full-body style scenes. A full-body reference with no detectable face is treated as unverified soft context and is never used to claim verified body identity.

### Identity fidelity

- FLUX.2 Klein 9B KV receives every usable genuine facial reference natively through `ReferenceLatent`. Multiple views improve its evidence for face angle, hairline, nose, jaw, and eye area; they are explicitly described as the same person and the prompt requires one copy of the main subject.
- A supplied full-body reference is appended only for a scene that needs build or proportions. The prompt tells the model not to copy the reference pose, clothing, objects, or background.
- The production path has no face swap, face restorer, subject LoRA, generated identity fixture, or post-generation identity patch. That preserves native facial texture and avoids replacing the result with a generic older face.
- A LoRA is a last resort only if strong, varied genuine references still fail visual review. The previously tested Klein LoRA is explicitly rejected and is never selected by the workflow.

Every run reports an `identity_route`. InsightFace cosine scores are diagnostics, not proof that a photo looks like the subject. Mean similarity of at least 0.60 with every scored image at least 0.50 is reported as `similarity_target_met_unverified`; 0.55–0.60 with no score below 0.50 is reported as near-target visual review. Both require visual comparison with genuine camera originals. If similarity misses, add a current, sharp front view and then different genuine side angles before considering an adapter.

Identity acceptance must use genuine, ungenerated camera originals. Files named `mitch-qwen-id-*` or `mitch-workbench-qwen-id-*` are historical generated fixtures, not photographs of Mitch. The production node and `scripts/smoke-social-photo.ps1` always reject them, and the script requires an explicit first reference.

### First-time model setup

Run `scripts/setup-social-photo-models.ps1`, restart ComfyUI, then run `scripts/verify.ps1`. The setup script installs only three pinned files required by the primary workflow—the official FLUX.2 Klein 9B KV FP8 model, Qwen3 8B FP8 mixed text encoder, and FLUX.2 VAE—resumes partial downloads, and verifies exact SHA-256 hashes before installation.

The Black Forest Labs 9B KV weights are under the FLUX Non-Commercial License. Review that license before commercial use.

If the primary resolution runs out of VRAM, the failed photo is retried once at the matching 768-pixel short-side resolution and the fallback is recorded in `report.json`.

For the most reliable result, use recent unfiltered photos with visible eyes and hairline. One strong front or three-quarter photo is enough to start; add different angles rather than four nearly identical selfies. For full-body or action shots, include one unobstructed body reference and keep the subject framed close enough that the face remains readable. Use **Authentic Phone** for ordinary dating/IG realism, **Professional** for cleaner optics and controlled light, and **Candid/action** to make gaze and pose explicitly camera-unaware without a separate workflow.

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
