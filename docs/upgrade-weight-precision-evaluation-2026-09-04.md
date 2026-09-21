# Native High: diffusion-weight precision diagnostic

Status: completed and closed as a stronger-High quality fix; not production. The preceding goal turn
made progress: a single seed change produced visibly different eyes/brows/face,
but PhoneON background detail and skin/hair realism still failed. Its likeness
was .695566; user feedback on that specific beauty/likeness tradeoff is pending.
Do not assume approval or roll further seeds.

## Mechanism and primary-source gate

The same installed Base9B file is stored BF16 but all these Klein High tests force
UNETLoader `weight_dtype=fp8_e4m3fn`. Test the unquantized diffusion weights by
changing **only** that loader field to `default`, plus the SaveImage destination.
This is not a new model and not a fully unquantized pipeline: Qwen3-8B text encoding
remains the same existing mixed-FP8 file. No precision-related quality improvement
is assumed before actual evaluation.

The [BFL Base9B card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
uses BF16, 50steps/CFG4 and CPU offload, and advertises roughly29GB VRAM for the
full model pipeline. This is greater than the3090's24GB; do not claim full-GPU
residency. Local Comfy dynamic loading/offload must handle the difference.
[ComfyUI's loader](https://github.com/Comfy-Org/ComfyUI/blob/master/nodes.py) only
forces float8 when the explicit option is selected. Installed Flux2 declares
BF16 first among supported inference dtypes. `comfy.sd` delegates the default
to `model_management.unet_dtype`; no process dtype-override flags are active.
The actual job log must still confirm BF16 weights. A default widget alone is
not runtime dtype proof.

Identity mechanism remains genuine-trained V3 step1600 Base9B character LoRA .9
and the protected genuine portrait in slot3. Source slot1 supplies composition,
pose/expression/edit-source (identity influence unisolated); face-free edges2
supply structure; genuine isolated hair4 supplies material. Every image follows
LoadImage -> fixed scale -> VAEEncode -> ReferenceLatent on both CFG branches.
This unchanged author-template native edit graph is not style-only identity or
a face swap. Model, identity/phone adapters, all four references, both text branches,
seed8675417, 50Euler/CFG4, 1680x1008 and full Flux2 VAE remain identical.
PhoneON .25, TurboOFF,3090/8188 lock remain. The existing nonempty negative branch
is the previously documented experimental native CFG test, not a BFL-endorsed
negative-prompt feature.

Control manifest: `native-high-seed-probe-house/experiment.json`, SHA256
`454CAFA1BFE433B975B101D7838371AD4F7494F1A76DC3788DE4BA41E3A1F8F7`.
Compare native output with that exact FP8 control, actual Low and source, against
the same six genuine held-outs; no polish may hide a failed native result.

## Memory preflight and bounded execution

Initial free host RAM was about7.3GiB. Both worker queues were empty; latest3090
history was our terminal seed job `adfcbb9f-0626-4474-8bca-d1bae6032958`, and its
graph exactly matched the saved experiment. Only8188 received one successful
`/free` request with unload_models/free_memory true. This clears disposable model/
executor caches, not saved images or model files;4070 was untouched. No restart.
The cache-release guard's pre-action snapshot says explicit_free false because
it records state before the separately issued request, not the request's outcome.

Recheck both queues and actual free RAM after release. Require at least24GiB of
host headroom before and after hashing, no conflicting process dtype override,
and the exact latest owned terminal graph. This is a conservative experimental
headroom check, not a guarantee of peak memory. Verify all five model hashes,
four reference hashes and live node/model names, then submit exactly once.
Record the existing worker-log byte offset before submission for dtype evidence.
Never restart/retry because an observation timed out. Preserve failed results.

## Acceptance

Inspect native size, face comparison and thumbnails: clear natural skin, hair,
eye/brow/expression, no teeth, cheek/forehead/head direction, pupil focus, identity,
body/scene integration and detailed background. Measure identity/gaze/pose but
do not treat those alone as beauty proof. If16-bit weights do not materially
resolve the current visual failures, close this precision hypothesis without
a dtype/seed/prompt grid. A good house result still does not satisfy the required
canyon, genuine-third and production integration/end-to-end checks.

## Completed result

One submission on RTX3090/8188: `c02953e6-6ed6-450b-8ef4-f39edb160252`, queue48,
successful in509.79seconds. Both worker queues were empty after completion.
No retry, restart or further cache release was performed. The4070 was not used
or modified by this experiment; its later memory state changed independently.

Experiment manifest SHA256:
`36B48C7291F0DFBB64C88C6A68205A665FE51F7FB99BE2323D50674DB2F9884E`.
The saved worker-log offset191977 scopes the new load: diffusion weights are
`torch.bfloat16`, manual castNone, Flux2 with17316MB staged and121 patches.
The unchanged text encoder stages8262MB. Thus actual BF16 diffusion execution
is confirmed, not inferred from the widget. Host free RAM remained about18.9GiB
near completion; no out-of-memory or emergency unload occurred.

Output: `ComfyUI/output/upgrade-source-faithful/native-high-bf16-house/raw_00001_.png`
(ComfyUI is the sibling directory), SHA256
`3300AA32E552D0B9E7B86C67DC6E0EBAA8EBAB54A1B25311327A69DCFB78A11A`.
The native PNG graph and reference hashes were verified by the existing CPU
evaluator. No polish, restoration, gaze adjustment or background composite was
applied. Its exit1 records the configured likeness-drop diagnostic, not a
generation or evaluation crash. Seven isolated-probe unit tests passed.

| Diagnostic | FP8 control | BF16 diffusion |
| --- | ---: | ---: |
| Genuine-reference centroid similarity | 0.695566 | 0.700999 |
| Maximum source pose difference | 0.929035 degrees | 1.438381 degrees |
| Mouth opening ratio | 0.001914 | 0.001606 |
| Source mouth-corner error | 0.022210 | 0.024912 |
| Maximum source-relative eye-coordinate difference | 0.080856 | 0.065262 |

These small diagnostic changes do not establish an aesthetic improvement.
BF16's horizontal pupil-coordinate differences are0.023407 and0.065262; exact
source eye focus is not proven. Similarity drops0.078116 from the old raw and
0.037951 from production Low. The user's stronger-beauty/recognizable-likeness
preference means that drop alone is not grounds to reject an otherwise good
result; the unresolved visual failures are the decisive issue here.

Full-size, equal-face-height and thumbnail review: the native variants have
more defined eyes/brows and a less rounded appearance than production Low,
and both keep lips closed without visible teeth. BF16 is visually very close
to FP8, not a meaningful further improvement. Brow tension/frown creases,
cheek speckles, regular bundled highlight strands and the soft PhoneON
background remain. Pose is broadly source-like but not exactly locked.
There is no obvious new head/body cutout halo; the single-person scene does
not test crowd diversity. Background material detail fails at thumbnail and
native size despite the active phone adapter.

Artifacts are under `work/upgrade-source-faithful-20260903/native-high-bf16-house/`:
`evaluation/audit.json`, `control-comparison/audit.json`, and the labeled face/
thumbnail sheets. Comparison provenance verifies that only diffusion dtype
and save prefix changed, with identical source, raw, Low and six genuine
scoring references. Individual face crops are presentation-only resizes.

Decision: close this precision hypothesis without a dtype/seed/prompt grid.
Do not spend canyon/third validation on this unsuccessful quality fix. The
pending aesthetic response to the earlier FP8 face comparison is not assumed.
All six protected production implementation/UI/workflow hashes are unchanged;
Low remains default, PhoneON and TurboOFF remain. The full stronger-High
three-photo goal and production integration are still incomplete.
