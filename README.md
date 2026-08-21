# Mitch Comfy Workbench

This repository is the source of truth for Mitch's ComfyUI workflows and locally maintained custom nodes.

## How ComfyUI sees these files

The repository is connected to ComfyUI with Windows directory junctions:

- `workflows` → `C:\projects\AI-Tools\ComfyUI\user\default\workflows\Mitch`
- `assets\comfy-input` is synchronized into `C:\projects\AI-Tools\ComfyUI\input` with `mitch-workbench-` filenames by `scripts\setup-links.ps1`
- `custom_nodes\ComfyUI-AIToolkit-Training` → the corresponding ComfyUI custom-node folder
- `custom_nodes\ComfyUI-AlwaysRunImage` → the corresponding ComfyUI custom-node folder

Workflow and custom-node files are used in place. Version-controlled scene templates are synchronized into ComfyUI's input folder because its image picker does not follow directory junctions.

## Social Photo Studio — primary workflow

Open `Mitch/production/Social Photo Studio - FLUX Klein` in ComfyUI. It has five visible nodes and only three steps:

1. Upload one to four photos of the same consenting adult. A clear face is required; front, left, right, and full-body roles are inferred automatically and can be overridden.
2. Describe the desired photos. Choose a single photo, six-photo dating pack, or nine-photo Instagram pack; then choose phone, professional, or 35mm style and camera-facing, candid/action, or an automatic mix.
3. Queue once. Final photos, a contact sheet, and a privacy-safe run report are saved under `ComfyUI\output\social-photo-studio`.

The generator uses FLUX.2 Klein 4B at four steps with multi-reference conditioning. ReActor and GPEN are used only when the result safely improves facial identity. The optional FLUX.2 Klein identity LoRA is off by default; no trigger is guessed when metadata does not provide one.

Run `scripts\setup-social-photo-models.ps1` once before first use, then restart ComfyUI. `scripts\verify.ps1` checks the workflow, presets, unit tests, external model hashes, and live nodes.

Full-body identity is reported conservatively: `reference grounded`, `reference supplied unverified`, or `not supplied`. A plausible generated body is never reported as verified.

## Preserved benchmarks and legacy workflows

The validated Qwen v8 benchmark remains preserved with its 80.81 mean identity score. Large fixed Qwen graphs and the earlier Z-Image workflows remain available for regression testing under `workflows/experiments` and `checkpoints/workflows`; they are no longer the documented everyday path.

## Everyday workflow

1. Open `Mitch/production/Social Photo Studio - FLUX Klein` in ComfyUI.
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
