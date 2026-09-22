# Qwen 2.1: compatibility evidence, no image acceptance

September 21, 2026. This is a separate prospective mechanism after the
[UMO visual rejection](group-umo-visual-rejection-2026-09-21.md), not a continuation
of its guidance/prompt/seed sweeps. The user-visible task remains natural head/body
proportions and convincing face/scene rendering together with recognizable identity.
The raw-image [diagnosis](group-umo-failure-diagnosis-2026-09-21.md) already establishes
that the UMO failure is present before display or finishing.

## What is different, and what is not proven

The [author release](https://github.com/QwenLM/Qwen-Image-2.1) dated September 20
provides new weights and a unified generation/editing architecture. Its published
multi-person example and claims about portrait rendering justify investigating a
different mechanism; they do not demonstrate a solution for Mitch. The example's
remote image host was blocked in the browser, so it was not visually reviewed.
Older Qwen-Image-Edit-2511 failures remain valid for their tested recipes.

The [official editing template](https://github.com/Comfy-Org/workflow_templates/blob/371a7b7171bbd11e9cc92ef615ba5ad223d7e5b4/templates/image_qwen_image_2_1_image_edit.json)
and [pinned Comfy source](https://github.com/Comfy-Org/ComfyUI/tree/b0f4b7b294ce482a2e071d9d762c133d38c7aa07)
trace ordered images through Qwen3-VL grounded encoding and dedicated VAE reference
latents, interleaved with text inside a single-stream diffusion model. The first
reference determines the output canvas. The proposed scene-first, genuine-person-second
roles supply composition and identity; they do not enforce pixel preservation or
head/body scale. No face embedding, face swap, mask repair, restoration or character
LoRA is involved. Better integration remains an untested prediction.

The [plan](../work/qwen21-gate-20260921/PLAN.md) records exact template settings,
three required weight hashes, reference roles and a one-image stopping rule. The
required weights total 17,283,091,112 bytes (16.10 GiB); **none were downloaded**.
The inspected author license permits research/evaluation; no production rights or
production release are asserted here.

## Completed runtime check

The existing public core lacks these new nodes. A separate clone at
`b0f4b7b294ce482a2e071d9d762c133d38c7aa07` and five pinned dependency overlays live
under `work/qwen21-gate-20260921/runtime/vendor`. Public Comfy's checkout, environment
and workers were not updated or restarted.

A CPU-only worker on loopback8194 exposed all nine required nodes, including
`TextEncodeQwenImage21`, `QwenImage21Cache` and `SaveImageAdvanced`. Its custom/API
nodes were disabled, model directories were empty, queue was empty, and no prompt
was submitted. The saved [schema](../work/qwen21-gate-20260921/node-schema.json)
establishes API visibility, not model loading, quantized-kernel execution, VRAM
capacity, exported graph validity or photo quality.

The first probe expected the launcher PID to own the listener. Windows' uv Python
trampoline instead created a child process. The
[separate listener check](../work/qwen21-gate-20260921/cpu-listener-check.json)
verified that child's exact main path and CPU arguments, read the API and stopped
only that owned child. The original [probe receipt](../work/qwen21-gate-20260921/cpu-runtime.json)
retains its resulting failure status rather than being rewritten as a pass; it
also confirms the port was no longer listening. The saved probe is historical,
not a ready-to-reuse worker controller.

## Decision and remaining question

Source/schema investigation is complete. No GPU inference or image has been
admitted by this result. No new weight download, generation, training, production
change or deletion occurred. General Group and stronger High remain unfinished.

Qwen 2.1 is a candidate with an available implementation, **not an established fix**
for oversized heads or pasted-on faces. A later admission must explicitly retain
that uncertainty, verify exact assets/runtime/resources, and review any first
image at full size and thumbnail against genuine photos before similarity scores.
The familiar proportion or rendering failure ends that trial immediately; another
prompt, guidance, seed or finishing sweep must not follow automatically.

Keep the small source/schema evidence and reproducible runtime pins. Neither this
compatibility result nor closing UMO authorizes deleting unresolved unique assets.
Evidence recovery is recorded separately in
[the local archive verification](../local/qwen21-gate-20260921/verification.json).
