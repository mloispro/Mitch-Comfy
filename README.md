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

Open `Mitch/production/Social Photo Studio - FLUX.2 Klein 9B KV` in ComfyUI. It has five visible nodes and only three steps:

1. Upload one to four photos of the same consenting adult. A clear face is required; front, left, right, and full-body roles are inferred automatically and can be overridden.
2. Describe the desired photos. Choose a single photo, six-photo dating pack, or nine-photo Instagram pack; then choose phone, professional, or 35mm style and camera-facing, candid/action, or an automatic mix.
3. Queue once. Final photos, a contact sheet, and a privacy-safe run report are saved under `ComfyUI\output\social-photo-studio`.

The generator uses the official FLUX.2 Klein 9B KV FP8 model in its native four-step image-editing path. Every usable genuine face angle is encoded as a native reference; a full-body reference is added only to proportion-sensitive scenes. There is no face swap, restorer, subject LoRA, synthetic identity fixture, or fake phone-photo post-processing in the production path. `FluxKVCache` keeps repeated pack generation fast.

Run `scripts\setup-social-photo-models.ps1` once before first use, then restart ComfyUI. `scripts\verify.ps1` checks the workflow, presets, unit tests, external model hashes, and live nodes.

Full-body identity is reported conservatively: `reference grounded`, `reference supplied unverified`, or `not supplied`. A plausible generated body is never reported as verified. Automated InsightFace scores are diagnostics only; likeness acceptance is visual and must be against genuine camera originals.

## Validated baseline and legacy workflows

On the local RTX 3090, the restart baseline produced a one-reference 768×1024 phone portrait in about 13 seconds and a four-reference 1024×1536 candid action photo in about 15 seconds. The tested outputs were visually recognizable as Mitch; their InsightFace cosine diagnostics were approximately 0.69 for a three-angle portrait and 0.61 for the tighter four-reference action shot. These are machine-specific proof runs, not a universal benchmark or an automated identity guarantee.

The old Qwen v8 benchmark remains preserved for regression history. Its historical percentage and current InsightFace cosine diagnostics are different metrics and must not be compared numerically. Superseded fixed Qwen and Z-Image graphs remain under `checkpoints/legacy-workflows`; versioned Qwen identity experiments remain under `checkpoints/workflows`.

The v2.1 Social Photo Studio numbers are withdrawn. Those runs accidentally used generated `mitch-workbench-qwen-id-*` portraits as identity ground truth, so their speed measurements remain diagnostic only and their identity scores do not measure likeness to Mitch. The production graph now opens with an empty required reference and the Social Photo node excludes/rejects those fixtures. They remain only for legacy workflow archaeology; Social Photo Studio acceptance must use genuine camera originals supplied explicitly at invocation time.

## Everyday workflow

1. Open `Mitch/production/Social Photo Studio - FLUX.2 Klein 9B KV` in ComfyUI.
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
