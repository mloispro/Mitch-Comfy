# Qwen experimental blended-identity v5

Workflow: `workflows/experiments/EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos.json`

Workflow SHA256: `60202824877529F823D54282646F357AF4C1B188037B86594BAF7CA15D0EC070`

## Face identity change

Every ReActor scene now uses the face model blended from all three genuine photos. The former per-angle models remain visible as inputs to that blend but are no longer connected directly to a scene.

A controlled A/B test used the same seven solo-scene inputs and face-detail settings. Each result was compared independently with all three genuine photos:

- Old angle-specific face models: 72.02% mean similarity across scenes.
- Blended three-photo face model: 79.35%.
- The blended model improved the three-reference mean in all seven solo scenes.

Per-scene blended means were: Ragdoll 77.40%, Tabby 65.31%, Golfer 84.25%, Amalfi 79.13%, Lake Boat 83.12%, Restaurant 83.05%, and Night City 83.16%.

## Samsung control

The Samsung LoRA is installed, connected after the Qwen 2512 Lightning LoRA, and controlled by node 4. It is intentionally bypassed when `CREATE NEW PHOTOS = false` because approved images do not pass through the Qwen 2512 generator.

ComfyUI history confirmed an apparent 0 versus 0.70 no-change test was executed in approved-image mode. A controlled generated-mode 0 versus 0.65 test changed the full image in all three tested scenes, with mean absolute RGB-channel differences between roughly 19 and 44 levels. The LoRA is therefore active in generated mode.

v5 defaults to approved-image mode for safe anatomy and sets Samsung strength to 0.65 so it becomes active automatically when the user turns `CREATE NEW PHOTOS` on.

## Validation

- 178 nodes and 256 links.
- All nine ReActor nodes resolve to the blended model node.
- No duplicate node IDs, duplicate link IDs, or broken endpoints.
- The `final_00001_` nine-photo validation run completed successfully under `ComfyUI/output/dating-app-easy-experimental-v5`.
- The pose-safe routing from v4 remains unchanged.

Exact body identity is not claimed. The available genuine inputs include only a partial mirror view and do not establish full height, leg proportions, or complete body shape. A neutral full-body front photo—and preferably one side photo—is required before a golfer body can be called an identity match.

## HyperSwap 1C evaluation

The official `hyperswap_1c_256.onnx` model was downloaded from FaceFusion's 3.3.0 repository and verified with SHA256 `5528C2D76FE9986C99D829278987EF9F3A630CB606DB7628D02B57B330F406A5`.

It was tested on the same v5 ReActor inputs with the same blended three-photo identity model. HyperSwap was rejected for this workflow:

- InSwapper 128: 77.51% seven-scene three-reference mean.
- HyperSwap 1C 256: 68.87%.
- HyperSwap reduced likeness substantially on Ragdoll, Golfer, Amalfi, Lake Boat, Restaurant, and Night City; Tabby improved by only 0.19 points and showed a visibly worse expression.

v5 therefore deliberately remains on `inswapper_128.onnx`. The 256px model's higher native resolution did not improve Mitch's identity fidelity.
