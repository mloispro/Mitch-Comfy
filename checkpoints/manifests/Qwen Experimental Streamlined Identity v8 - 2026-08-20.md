# Qwen Experimental Streamlined Identity v8

> **Historical record — not current instructions.** Terms such as “production,” “current,” “selected,” or “recommended” below describe the decision on 2026-08-20. See `docs/STATUS.md` for current state.

Date: 2026-08-20

## Archived workflow

- Former mutable workflow is archived at `checkpoints/legacy-workflows/experiments/EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos.json`
- Current archive SHA256: `8C2A7250D04DEECEE4FC277DFE7C36639AB8FF8CB079B29B8469547626CCA9F0`
- Exact checkpoint: `checkpoints/workflows/Qwen Experimental Identity Build v8 - streamlined GPEN.json`
- Current checkpoint SHA256: `8C2A7250D04DEECEE4FC277DFE7C36639AB8FF8CB079B29B8469547626CCA9F0`

## Streamlined routing

- All nine scenes retain `inswapper_128.onnx`, the face model blended from the three genuine photos, and `GPEN-BFR-512.onnx` at visibility `0.70`.
- Night Out A/B, Ragdoll, Golfer, Amalfi, Lake Boat, Restaurant, and Night City use direct targeted ReActor finishing.
- Only Cat Tabby retains the Qwen Edit 2511 full-head stage because it scored better with Qwen before ReActor.
- The change removes the slow/failure-prone Qwen branches from Ragdoll and Restaurant.

The direct cached-source comparison produced:

| Scene | v7 Qwen + ReActor mean | Direct ReActor mean | Decision |
|---|---:|---:|---|
| Cat Ragdoll | 74.22 | 79.14 | Direct |
| Cat Tabby | 76.19 | 74.12 | Keep Qwen |
| Restaurant | 82.30 | 83.16 | Direct |

## Full validation

- Full v8 prompt: `6ce4a218-8f6c-4a07-864a-2b6e7985cb00` (`success`).
- Identity scoring prompt: `075a8351-2532-4f7b-9459-56c38694d020` (`success`).
- All nine finals exist under `ComfyUI/output/dating-app-easy-experimental-v8`.
- The eight automatically scoreable scene means are Night Out A `82.04`, Cat Ragdoll `79.01`, Cat Tabby `76.04`, Golfer `82.45`, Amalfi `83.26`, Lake Boat `81.10`, Restaurant `82.48`, and Night City `80.09`.
- Overall mean of those eight scenes: `80.81`, up from v7 `80.22` and the preceding CodeFormer comparison baseline `76.24`.
- Night Out B is a four-person scene; the generic similarity node selects the wrong group face, so it is visually inspected rather than included in the numeric mean.

## Known boundary

Facial identity is improved and validated. Exact body identity is not. The golfer body is anatomy-safe but generated. A neutral, unobstructed full-body front photo and preferably a side photo are required to validate exact build and leg proportions; the surf photo is useful context but the board and wetsuit obscure the required body outline.
