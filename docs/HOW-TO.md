# Maintenance guide

## Workflow folders

- `workflows/production`: validated workflows intended for normal use.
- `workflows/experiments`: active experiments. This folder appears when it contains its first workflow.

Both appear under the `Mitch` folder in ComfyUI. New or moved files require pressing **Refresh** in the Workflows sidebar. Changes to a workflow that is already open require reopening it.

Version-controlled scene templates live under `assets/comfy-input`. Running `scripts/setup-links.ps1` synchronizes them into ComfyUI's input root with `mitch-workbench-` filenames.

## Custom nodes

The two custom-node folders in this repository are linked directly into ComfyUI. Python changes require a ComfyUI restart. Workflow JSON changes do not.

Third-party custom nodes such as ReActor remain in their own upstream repositories. Their exact revisions are recorded in `config/dependencies.lock.json`.

## Single-person scene matching

Open `Mitch/production/Qwen + ReActor Single-Person Scene Match` and queue it normally. Both included scenes run in one queue:

- Qwen Image Edit 2511 preserves the supplied composition and performs the full-head identity edit.
- The Amalfi branch uses the genuine frontal face model for its ReActor finish.
- The night branch uses the genuine angled face model for its ReActor finish.
- Both templates are processed at two megapixels before the final face pass for better detail.

The template images and Qwen prompts are normal editable nodes. Qwen drafts and ReActor finals are saved separately under `ComfyUI/output/qwen-reactor-single-person`.

## Nine-photo dating pack

Open `Mitch/production/Qwen 2512 + ReActor - 9 Dating Photos`. The workflow exposes all nine prompts, seeds, scene switches, identity reference images, and ReActor finish nodes.

It opens on the green **START HERE** panel. **CREATE NEW PHOTOS** controls exact versus generated mode, and **PHONE CAMERA STRENGTH** controls the Samsung look. After setting those two values, click **Queue Prompt** in ComfyUI's upper-right corner.

### Fast exact mode

Leave **MODE — REGENERATE WITH QWEN 2512** set to `false`. The lazy switches bypass Qwen generation and use the nine approved compositions, so the complete identity-finished pack runs quickly and repeatably.

### Generated mode

Set **MODE — REGENERATE WITH QWEN 2512** to `true`. Qwen Image 2512 regenerates every enabled scene at 1056 by 1584 using the shared four-step Lightning model. ReActor then applies the pose-appropriate genuine face model. The two group scenes already target the intended man rather than the first face in the frame.

For a quick test, queue only the selected scene's final `Save Image` node. Queue the entire workflow after the prompt, seed, and identity finish look good.

### Optional phone-camera look

The Samsung realism LoRA is connected only to generated mode:

- `0.00`: disabled.
- `0.45`: subtle natural-camera texture.
- `0.65`: validated default for a stronger casual phone-photo look.
- Above `0.80`: use cautiously because composition and facial texture can drift.

This LoRA was trained for Qwen Image 2512, so the workflow deliberately uses the matching Qwen 2512 base rather than Qwen Image Edit 2511. Outputs are stored by scene under `ComfyUI/output/dating-app-pack`, with `stage1` and `final` subfolders.

## Experimental pose-safe identity dating pack

Open `Mitch/experiments/EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos`.

Leave the five green controls at their defaults and click **Run**. The workflow uses three stages internally:

1. Select the approved composition or generate a fresh Qwen 2512 scene.
2. On the cat and restaurant close scenes, Qwen Edit 2511 applies the pose-matched full-head identity.
3. ReActor applies the same face model blended from all three genuine photos to every scene, followed by the tuned detail boost. This replaced the weaker per-angle models after a seven-scene A/B test improved mean genuine-reference similarity from 72.02% to 79.35%.

The workflow automatically takes safer routes where a global edit is risky:

- Lounge group scenes use a left-to-right targeted ReActor index and never send the full group through Qwen identity editing.
- Golfer, Amalfi, lake boat, and night city bypass whole-frame Qwen editing so gaze, arms, hands, leg proportions, clothing, and composition remain intact.
- The restaurant scene uses a normal long-sleeved tailored blazer to remove the false muscular-arm cue without using the body silhouette.
- Cat scenes use angle-matched head references.

### Green controls

- **CREATE NEW PHOTOS**: keep `false` for the deterministic approved pack. Set `true` only when editing the nine scene prompts or seeds.
- **FULL HEAD IDENTITY LOCK**: keep `true`. Turning it off is a diagnostic comparison.
- **REACTOR FACE FINISH**: keep `true` for the sharpest and most genuine face identity.
- **PHONE CAMERA STRENGTH**: `0.00` off, `0.45` subtle, `0.65` recommended. It applies only when **CREATE NEW PHOTOS** is true. Changing it in approved-image mode does nothing because the generation model is intentionally bypassed.
- **FACE DETAIL**: leave this at the validated GPEN value of `0.70`. Use `0.55` for a softer finish or `0.85` for stronger restoration.

Finals are saved by scene under `ComfyUI/output/dating-app-easy-experimental-v8`. Eight scenes use the direct ReActor route; only the tabby scene retains Qwen full-head editing. The direct route improved the ragdoll identity mean from 74.22% to 79.14% and the restaurant from 82.30% to 83.16% while avoiding two slow Qwen branches. The previous v5 through v7 workflows are preserved under `checkpoints/workflows`. The rejected full-frame body-redraw workflow is preserved at `checkpoints/workflows/Qwen Easy Identity + Build - unsafe-body-v3.json`; these checkpoints are intentionally hidden from the ComfyUI workflow browser. A clean neutral full-body front-and-side photo is required to validate exact leg and build identity rather than merely plausible anatomy. The current partial mirror and surf references do not establish complete leg shape or an unobstructed full-body contour.

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
