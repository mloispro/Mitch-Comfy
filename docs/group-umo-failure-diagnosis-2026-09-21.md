# UMO Group: locate the proportion and rendering failure

September 21, 2026. Offline comparison after [Mitch's rejection](group-umo-visual-rejection-2026-09-21.md).
No generation, model loading, model download, training or deletion. The previous goal turn
made progress by correcting and committing the rejection; this inspection supplies
new measurements and traces the failure to the saved raw generation stage.

## What the existing images establish

Re-opened the [scene](../assets/comfy-input/klein9b-scene-presets/group-amber-booth-four-friends.jpg),
the [historical Klein control](../work/9b-readiness-resume-20260907/group-identity-hook-gate/runtime-3090/runs/ready-amber-hook-control/group-amber-hook-control-seed8675412_00001_.png),
both rejected UMO outputs and the actual genuine conditioning portrait. All scene/output
images are 832x1216. The UMO outputs show the rejected head/body mismatch and unnatural
face rendering, with broader loss of natural surface detail in clothing and scenery.
Neither the original scene nor the historical control is newly accepted as Mitch here.

Reused the frozen geometric main-face selections and face boxes in the original
[pilot diagnostic](../work/group-umo-pilot-20260921/evaluation/comparison.json) and
[refinement diagnostic](../work/group-umo-guidance3-20260921/evaluation/comparison.json).
No new detector run, face reselection, scoring change or threshold was introduced.
Widths/heights are `bbox[2]-bbox[0]` and `bbox[3]-bbox[1]`; changes divide by the source.

| Image | Main face box, pixels | Width change | Height change | Mean bystander width |
| --- | ---: | ---: | ---: | ---: |
| Source scene | 76.51 x 106.61 | baseline | baseline | 68.70 |
| Historical Klein | 75.91 x 101.58 | -0.78% | -4.71% | 68.67 |
| UMO imageCFG2 | 92.55 x 122.50 | +20.97% | +14.91% | 69.04 |
| UMO imageCFG3 | 83.73 x 118.17 | +9.44% | +10.85% | 69.63 |

These are face-detector boxes, not skull dimensions or a calibrated head/body test.
Different identity, expression and pose affect them. Nonetheless, enlargement is
present in the raw images, disproportionately to the bystanders, consistent with the
visual rejection. Reducing that enlargement in CFG3 did not make the picture usable.
Do not optimize these ratios as a replacement for whole-photo visual acceptance.

Diagnostic file SHA256 values, respectively:

- `7f93665681cbebb5a0294008e9956e9dc5f64417b6b3157d04fe98b96fb7aed9`
- `3ebd75163d90f30ee37594e82da982c00a06defadf0a47846208fa5a9faff308`

## Where the problem enters

Fresh checks confirm both `photo.png` hashes equal their native worker output and
runtime receipt, and each PNG's embedded prompt equals its saved candidate graph.
The rejection therefore applies to the raw generated pixels, before any browser
display. The graph ends `SamplerCustomAdvanced -> VAEDecode -> SaveImage`; there is
no face-pasting, restoration, sharpening or compositing stage to remove.

The inspected local `LoadImage` applies EXIF orientation. The genuine portrait has
orientation 6: its stored 1164x873 becomes upright 873x1164 before scaling. The scene
is 832x1216. `ImageScaleToTotalPixels` uses one scale factor, area interpolation and
disabled cropping. At the recorded 1.0MP setting its source-derived sizes are
847x1238 and 887x1182. Axis rounding differs by only -0.0062% and +0.0564% respectively.
The Flux VAE's multiple-of-eight center crop gives 840x1232 and 880x1176; it removes
border pixels without stretching the face. These are calculations from the inspected
code and recorded input sizes, not instrumented runtime tensor observations. They do
not support a direct resize distortion explaining the measured enlargement.

Both complete photos enter as VAE reference latents. Output sampling starts from an
empty latent with full noise; the scene is conditioning, not a pixel-preserved canvas.
The single image-guidance coefficient acts on the branch containing both references.
It is not an independent control over identity, head size, scene texture or lighting.
The stronger setting can therefore change several competing properties at once,
as the existing pair demonstrates. The graph has no enforced head/body scale relation.

The close portrait supplies expression, camera perspective and lighting as well as
identity. Their transfer is a plausible contributor to the pasted-on appearance,
not an isolated cause. Neither this comparison nor a high likeness score establishes
that changing the portrait, a prompt or another guidance value would fix it.

Inspected local source hashes:

| ComfyUI source | SHA256 |
| --- | --- |
| `nodes.py` | `abec8a56cececc0579967752c24b4c1d8b4eaf2d327b106b9843bca126553105` |
| `comfy_extras/nodes_post_processing.py` | `6d28d37a0947947ff6bb724c4de465bacc012f7f23e11d916d7a5161953158aa` |
| `comfy/sd.py` | `3b71a1a71a78ee327c24201f8d522393eb111264b3569d8b3a24bd9149d77f4f` |
| `comfy_extras/nodes_edit_model.py` | `3773fd748c404758ee36a3bac24cfea6e10c1b9990fa388cc440c56db1dc6a4a` |
| `comfy_extras/nodes_custom_sampler.py` | `913d776b5e696c70b77b8184f2af504533fbff2fad62a05cef4ecba87975f0bf` |

## Existing evidence that should have prevented the repeat

The [older head/body study](head-body-proportion-v1.0.4-evaluation.md) already records
an oversized head despite a .7756 identity score, followed by failed prompt/crop-size
corrections. It separated torso and face evidence for one different Solo workflow;
that result does not transfer to UMO's trained two-input semantics or prove a Group fix.
The [Krea2 lounge comparison](krea2-vs-flux2-lounge-identity-edit-evaluation-2026-08-25.md)
likewise records smoother skin and stiffer expression despite improved angle-matched
identity. These are prior warnings about the exact acceptance mistake, not permission
to retry the closed recipes.

## One relevant research check, without a build

The [AnyPhoto paper](https://arxiv.org/html/2603.14770v1) describes trained spatial
face conditioning, identity modulation and reference replacement intended to reduce
copy-paste artifacts. Its limitations explicitly include small-face blur and head/body
incompatibility, plus unstable identity assignment when reference and requested person
counts differ. It is therefore not evidence of a ready solution for this Group case.
The inspected paper and targeted author/title/GitHub/Hugging Face searches did not
establish an author-released runnable model. This is a bounded release check, not
proof that no release exists. No implementation or download is admitted from it.

## Consequence

The unresolved task is natural proportions and face/scene integration together with
identity. A higher similarity score, repaired display sizing or another image-guidance
value does not answer it. Keep this UMO recipe closed. Any prospective replacement
must have a released, compatible conditioning mechanism addressing those visual
failures and still pass the original genuine-reference and bystander checks. No
replacement is admitted by this diagnosis; general Group and stronger High remain
unfinished, with all unique assets retained for now.
