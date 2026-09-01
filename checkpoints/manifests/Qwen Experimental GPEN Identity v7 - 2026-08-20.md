# Qwen Experimental GPEN Identity v7

> **Historical record — not current instructions.** Terms such as “production,” “current,” “selected,” or “recommended” below describe the decision on 2026-08-20. See `docs/STATUS.md` for current state.

Date: 2026-08-20

## Archived v7 workflow

- Exact checkpoint: `checkpoints/workflows/Qwen Experimental Identity Build v7 - GPEN identity finish.json`
- Current checkpoint SHA256: `7F0AAA2CA539562124C588E311B78270584594A6639CA0A24904BB28A7AF6F42`

## Preserved predecessors

- v5 CodeFormer 0.32 SHA256: `8104E3669E9FD67CB8D30A5C9016897242A9F88C00728D286376DCC78FD783F2`
- v6 CodeFormer identity-first SHA256: `282D468E08175A2125AE9DADC45EDC1DC6ADD4878D96ABE7AA1EE264F9A56A14`

## Face-finish decision

The production-facing experiment keeps `inswapper_128.onnx` and the blended face model built from the three genuine photos. The face boost is now `GPEN-BFR-512.onnx`, Lanczos interpolation, visibility `0.70`.

A controlled cached-source A/B compared this finish with the preceding CodeFormer finish. Eight scenes could be scored automatically against all three genuine photos. The group scene was excluded because the similarity node selected a different group member.

| Scene | GPEN mean | CodeFormer mean | Difference |
|---|---:|---:|---:|
| Night Out A | 82.46 | 77.35 | +5.11 |
| Cat — Ragdoll | 73.64 | 69.46 | +4.18 |
| Cat — Tabby | 74.68 | 71.74 | +2.94 |
| Golfer | 82.37 | 79.27 | +3.10 |
| Amalfi | 83.12 | 79.95 | +3.17 |
| Lake Boat | 81.38 | 77.77 | +3.61 |
| Restaurant | 82.30 | 79.71 | +2.59 |
| Night City | 79.94 | 74.64 | +5.30 |
| **Eight-scene mean** | **79.99** | **76.24** | **+3.75** |

The exact v7 finals were rescored after generation. Their eight-scene mean is `80.22`; per-scene means are Night Out A `82.13`, Cat Ragdoll `74.22`, Cat Tabby `76.19`, Golfer `82.36`, Amalfi `83.49`, Lake Boat `81.00`, Restaurant `82.30`, and Night City `80.09`.

HyperSwap 1c 256 was not promoted: the earlier local comparison scored `68.87` versus `77.51` for InSwapper on the same identity test.

## Validation and recovery

- Full v7 validation prompt: `85e54a5d-f886-45a1-88e6-40f1543d0122`.
- Eight scene branches and their GPEN finals completed.
- The restaurant Qwen sampler stopped with `HostBuffer.read_file_slice failed`, a model-streaming read error rather than a workflow or identity error.
- The missing restaurant `qwen-lock` and final were recovered from the already-successful identical cached source and controlled GPEN run.
- Identity scoring prompt: `e362aa6b-9dfd-416f-96cc-02760bb1c1b7` (`success`).
- Final output root: `ComfyUI/output/dating-app-easy-experimental-v7`.

## Scope

This checkpoint improves and validates facial identity. It does not claim exact body identity. The golfer body is anatomy-safe but remains generated; a clean unobstructed full-body front and side reference is still required to validate exact build and leg proportions.
