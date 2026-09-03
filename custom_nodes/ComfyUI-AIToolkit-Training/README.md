# ComfyUI AI-Toolkit Training nodes

This local custom-node package supports Mitch’s current ComfyUI photo workflows, dataset utilities, and exact
legacy rollback graphs. Current workflow status is maintained in `../../docs/STATUS.md`.

## Nodes used by current photo workflows

| Node | Workflow | Purpose |
| --- | --- | --- |
| `Flux2Klein9BMitchIdentityStudioVisualPresetsV11` | Klein 9B Mitch Identity Studio v1.1 | New whole-frame solo, full-body, and lifestyle photographs with visual scene presets |
| `Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11` | Klein 9B Mitch Group Scene Studio v1.1 | Source-matched group layouts with visual presets and a face-interior-free Canny guide |
| `Flux2Klein9BPhotoRealismUpgradeV11` | Upgrade Photo Detail & Realism v1.1 | Whole-frame re-render of an existing one-face Mitch image |
| `Flux2DevMitchSceneStudio` | FLUX.2 Dev LoRA - 9 Dating Scenes v1 | Prompt or scene-reference generation with the Dev V2 step-1000 LoRA |

These nodes verify protected LoRA/reference hashes and enforce the intended worker/model contracts. They do not
upload images or use face swap. See the corresponding workflow documents in `../../docs` for reference roles,
locked settings, and review gates.

The older `V1` Python classes remain only as generation-locked implementation bases. They are deliberately absent
from `NODE_CLASS_MAPPINGS`, so they do not appear as duplicate public nodes or workflow sheets.

## Dataset/training utility nodes

- `AIToolkitTrainGeneratedDataset` submits or monitors the fixed generated-dataset job.
- `AIToolkitSubmitZImageTraining` submits a captioned flat-folder dataset to AI-Toolkit.
- `AIToolkitTrainingStatus` reads a durable job’s status and log tail.
- `AIToolkitPublishCompletedLoRA` publishes a completed adapter into ComfyUI.

The visible `Train Generated Dataset - AI Toolkit` workflow uses the first node. The other three remain general
submission/status/publication helpers; their presence does not make a retired model family current. Training
completion does not mean an adapter is approved; held-out evaluation and full-size visual review are still required.

The visible `Dataset gen - QWEN 2511 - 3-photo` workflow is a standard ComfyUI graph using Qwen Image Edit 2511
and does not depend on a custom node in this package.

## Legacy nodes

Easy Social Photos, One Reference Photo, scene-routing, ReActor-era helpers, and older Z-Image workbench nodes
remain importable only so exact archived graphs can be inspected or deliberately restored. Their graphs live under
`../../checkpoints/legacy-workflows` and are not the current recommendation.

Do not infer current support from a legacy class still appearing in `NODE_CLASS_MAPPINGS`. The six visible
workflow JSON files under `../../workflows/production` and `../../docs/STATUS.md` define the supported surface.

## Local AI-Toolkit configuration

`settings.json` is machine-local and excluded from Git. On this workstation it points to:

- AI-Toolkit: `C:\projects\AI-Tools\ai-toolkit\AI-Toolkit`
- AI-Toolkit Python: `C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe`
- AI-Toolkit UI/API: `http://127.0.0.1:8675`
- Published LoRA directory: `C:\projects\AI-Tools\ComfyUI\models\loras\aitk`

If AI-Toolkit uses `AI_TOOLKIT_AUTH`, ComfyUI must receive the same environment variable. The token is never
stored in this repository.

Dataset submission requires a flat folder where each supported image has a non-empty same-stem `.txt` caption.
Submission validates the dataset and creates a durable job; it does not edit captions. Unique job names and the
dataset fingerprint prevent accidental duplicate submission.

## Development and verification

The package is linked directly into the live ComfyUI custom-node folder. Restart ComfyUI after changing Python
files, then reopen the workflow.

Run the repository verifier:

```powershell
.\scripts\verify.ps1
```

The verifier runs the local unit suite and checks the live node/model surface. Specialized production workflow
verifiers are listed in `../../docs/STATUS.md`.
