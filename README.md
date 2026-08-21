# Mitch Comfy Workbench

This repository is the source of truth for Mitch's ComfyUI workflows and locally maintained custom nodes.

## How ComfyUI sees these files

The repository is connected to ComfyUI with Windows directory junctions:

- `workflows` → `C:\projects\AI-Tools\ComfyUI\user\default\workflows\Mitch`
- `assets\comfy-input` is synchronized into `C:\projects\AI-Tools\ComfyUI\input` with `mitch-workbench-` filenames by `scripts\setup-links.ps1`
- `custom_nodes\ComfyUI-AIToolkit-Training` → the corresponding ComfyUI custom-node folder
- `custom_nodes\ComfyUI-AlwaysRunImage` → the corresponding ComfyUI custom-node folder

Workflow and custom-node files are used in place. Version-controlled scene templates are synchronized into ComfyUI's input folder because its image picker does not follow directory junctions.

## Experimental pose-safe dating pack

Open `Mitch/experiments/EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos` in ComfyUI.

It opens on a green **EASY RUN** panel and contains the nine scenes, three genuine face references, and pose-matched Qwen head references. Leave the defaults alone for a deterministic review run, then click **Run**.

- **CREATE NEW PHOTOS**: `false` uses the approved compositions; `true` regenerates the editable Qwen 2512 scene prompts.
- **FULL HEAD IDENTITY LOCK**: Qwen Edit 2511 fixes face, skull, hairline, and head shape on solo scenes.
- **REACTOR FACE FINISH**: uses the proven face model blended from all three genuine photos. Its seven-scene mean similarity improved from 72.02% to 79.35% versus the old angle-specific models.
- **PHONE CAMERA STRENGTH**: works only when **CREATE NEW PHOTOS** is `true`. `0.00` is off; `0.45` is subtle; `0.65` is the default Samsung look. It cannot affect approved-image mode.
- **FACE DETAIL**: the workflow now uses the installed `GPEN-BFR-512` restorer at `0.70`. It improved mean genuine-reference similarity by 3.75 points across the eight automatically scoreable scenes versus the preceding CodeFormer finish, while remaining sharp. Use `0.55` for softer restoration or `0.85` for stronger restoration.

Eight scenes now use the targeted ReActor-only route. A direct cached-source test improved the ragdoll identity mean from 74.22% to 79.14% and the restaurant from 82.30% to 83.16%, while also removing two slow Qwen branches. Only the tabby scene retains the Qwen full-head stage because it scored better there. This prevents whole-frame editing from moving arms, changing gaze, stretching legs, or altering composition. Outputs are separated under `ComfyUI\output\dating-app-easy-experimental-v8` into `stage1`, the optional tabby `qwen-lock`, and `final` folders. The prior v5 through v7 workflows are preserved outside the ComfyUI browser under `checkpoints/workflows`.

`workflows/production` contains only the five stable operational workflows. The two older Z-Image workflows are retained under `workflows/experiments/legacy-z-image`, and the rejected strong-body version is preserved outside ComfyUI's workflow browser under `checkpoints/workflows`.

## Earlier nine-photo dating pack

Open `Mitch/production/Qwen 2512 + ReActor - 9 Dating Photos` in ComfyUI.

The workflow opens on a green **START HERE** control panel. Set the two everyday controls there, then click ComfyUI's **Queue Prompt** button.

- Leave **MODE — REGENERATE WITH QWEN 2512** off for the fast, repeatable pack built from the nine approved compositions.
- Turn that mode on to regenerate all scenes from the nine editable Qwen prompts and seeds.
- Set **PHONE LOOK — SAMSUNG QWEN 2512 LORA** to `0.00` for the clean Qwen look or start at `0.65` for a natural Samsung-phone look.
- Queue only one scene's final image node while tuning, then queue the complete workflow when it is approved.

Drafts and identity-finished images are saved separately under `ComfyUI\output\dating-app-pack`.

## Everyday workflow

1. Open a workflow under `Mitch/production` or `Mitch/experiments` in ComfyUI.
2. Edit and save normally in ComfyUI. The Git working tree changes immediately.
3. Validate the result.
4. Run `scripts\checkpoint.ps1 -Message "Describe the working change"` to verify and commit it.
5. Use an optional tag for important milestones, for example `-Tag "multiperson-sharp-v2"`.

Production filenames stay stable. Git history replaces duplicate files named `v2`, `final`, or `final-final`.

## What is intentionally not tracked

- Models, LoRAs, and Python environments
- Generated datasets and outputs
- Personal input/reference photographs
- Scene templates outside `assets\comfy-input`
- Logs, caches, and compiled Python files
- Machine-local settings such as the live AI-Toolkit `settings.json`

Tracked manifests record important external revisions and hashes without copying large files into Git.

See [docs/HOW-TO.md](docs/HOW-TO.md) for restoration and maintenance details.
