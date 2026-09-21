# Native identity-portrait detail probe

Status: native pilot completed and rejected as stronger High. No resolution sweep
or production change.

The current four-reference base preserves strong identity and detailed scenes,
but replaces the source's preferred eye/brow/expression presentation. Removing
the portrait entirely, changing its photograph, adjusting character-LoRA weight,
and multiple text changes have already failed or provided inadequate results.
The saved native experiment inventory shows portrait resolution fixed at 0.5 MP;
those tests do not isolate how much detailed portrait information is supplied.

Test one reduced-detail portrait at 0.1 MP. This is not an attention-weight or
identity-strength knob: it changes the portrait's encoded visual detail and
latent-token layout. The prediction is that less portrait detail may allow more
source expression to survive while the same genuine-trained identity LoRA and
retained portrait still provide likeness. That prediction is unproven.

## Conditioning and exact compatibility

Use the existing native four-reference runner expanded from the freshly audited
public house output, not a new model or guessed node graph:

1. Original source -> bicubic 1 MP -> full Flux2 VAE -> first reference latent.
2. Same face-free edge guide -> nearest-exact 0.5 MP -> VAE -> second reference.
3. Same genuine identity portrait -> nearest-exact **0.1 MP instead of 0.5 MP**
   -> VAE -> third reference.
4. Same genuine isolated hair crop -> bicubic 0.1 MP -> VAE -> fourth reference.

All references retain their order on both CFG branches. Identity support is the
same genuine-photo-trained Base9B V3 step-1600 LoRA at 0.9 plus the actual genuine
portrait, not the geometry guide or hair style input. The original source's own
identity influence is not isolated or proven absent.

[BFL's model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
and [official repository](https://github.com/black-forest-labs/flux2) support native
single/multi-reference editing; the [training guide](https://docs.bfl.ai/flux_2/flux2_klein_training)
supports Base character LoRAs. These establish the model/adapter mechanism, not
a guarantee that the reduced portrait will improve beauty. The exact 0.1 MP
portrait setting is experimental, not an author-recommended identity setting.

The shipped `image_flux2_klein_image_edit_9b_base.json` single-reference subgraph
`7b34ab90-36f9-45ba-a665-71d418f0df18` was re-read including links. Its source
scaler -> VAE -> positive/negative ReferenceLatent topology is retained and
extended by the already-established four-role chain. The installed
`nodes_edit_model.py` appends latent samples exactly as the public wrapper does.
The installed ImageScaleToTotalPixels with resolution_steps=1 uses the same
1024-squared area, rounding and common_upscale implementation as the wrapper.

Keep Base9B BF16 model file with existing FP8 load mode, Qwen3-8B FP8-mixed encoder,
full Flux2 VAE, compatible Smartphone Snapshot v13 at 0.25, 50 Euler steps,
Flux2Scheduler, CFG 4, seed 8675416 and native 1680x1008 output. Phone on, Turbo
off; no negative-prompt change, mask, restoration, upscaler, extra lighting or
polish stage. Do not mix the separate CodeFormer experiment into this test.

Protected model/image hashes and live node/model availability are checked again
at submission. GPU is locked to 3090/8188; inspect both GPUs, all known queues,
Forge and free host RAM, require 32 GiB available, and preserve other work.
No cache release, worker restart, download or dependency change is required.

## Control and acceptance

The control manifest is an expanded equivalent of the verified public job
`52348431-764b-407b-bc74-8da6c055ca66`; that exact expanded control graph has not
itself been rendered. Its prompt and all four resized dimensions must agree with
the actual public report. Candidate graph changes only node121.megapixels and
the save destination. Do not claim pixel-exact control equivalence without a
separate reproduction if a positive result depends on it.

Evaluate raw output against the original source, actual Low and audited raw:
noticeable retention of flattering source eyes/brows/closed-lip expression,
recognizable identity against six genuine EXIF-oriented photos, reduced rather
than inflated cheeks, correct head direction/forehead/pupil focus, detailed
background and coherent texture at native size and thumbnail. Similarity is a
diagnostic, not sole acceptance. At most one controlled resolution refinement
after diagnosis; no grid or seed rolling. A successful house pilot still needs
the same recipe on canyon and a genuine third plus actual public integration.

Artifacts: `work/upgrade-source-faithful-20260903/portrait-detail-house-control-prepared/`
and the separately submitted candidate directory. Production remains unchanged.

## Completed pilot

Job `ff61023b-21bd-4b3d-a02a-6d3b40ff7373` completed on3090/8188 in438.936seconds.
Executed PNG graph and every reference hash match the prepared candidate.
The native full image, source/actual-Low/candidate face and thumbnail sheets,
and raw/candidate face comparison were reviewed. Detailed siding and branches
remain, but the tense brow, hooded eyes, fuller cheeks and serious expression
are still too Low-like. Speckled/coarse skin and bundled hair also persist.
Lips remain closed without visible invented teeth; no obvious new halo is seen.

Six genuine EXIF-correct reference similarity is0.726706, actual public Low
0.739620 and raw0.779115. Source-pose maximum difference is3.326439degrees;
closed-mouth opening ratio0.001042. These are diagnostics, not the reason alone
for rejection: the user permits a modest likeness tradeoff for a genuinely
stronger beauty result, but this candidate does not supply that benefit.

Candidate SHA256 `F6B285384FC515CEEB4406CD69EAE7F20FF13A108AD777E6C8065FF123CF4D20`.
Audit SHA256 `A9E68A7140D7B7CC67FFDA1DE5BE658AD32E07C150EF93FB0C6DB30BE13424D9`.
Artifacts are under `portrait-detail-house-010/`, including terminal history,
evaluation and explicit `review.json`. No expanded-control reproduction is
needed for this negative visual finding; no equivalence claim is added.
