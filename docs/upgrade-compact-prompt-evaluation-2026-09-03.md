# Compact native High experiment — research gate, not production

## Why this test, and what it can prove

The previous goal turn made progress: it diagnosed partially suppressed eye
controls, rejected excessive squint/warmth, and validated a no-narrowing component
on three corrected bases. It did not establish stronger overall beauty or a shared
native generation policy. Do not restart those closed parameter sweeps.

The latest inventory confirms that the existing native four-reference generation
already introduces source-expression/cheek/under-eye differences before CPU High.
Adding more local small remaps has not solved the requested appearance. The next
bounded experiment therefore returns to native generation without adding a stage.

Actual installed Klein tokenization (`prompt-budget-audit.json`) gives 772 tokens
for production canyon,533 for house and956 for the earlier native High. Comfy's
`comfy/text_encoders/flux.py` sets maximum length99999999 and minimum512; the full
prompt remains present. **There is no demonstrated512-token truncation bug here.**

[BFL's Qwen3Embedder](https://github.com/black-forest-labs/flux2/blob/main/src/flux2/text_encoder.py)
uses `MAX_LENGTH=512` and truncates/pads to that length. The installed AI-Toolkit
Flux2 Qwen embedding implementation also defaults to512. This is an implementation
difference, not proof that longer Comfy prompts cause the observed defects, nor
proof of the base model's complete training sequence distribution.

`compact-native-high-prompt.txt` uses292 nonpad tokens including chat template and
is padded to512. It retains four distinct roles and both trained triggers. It
condenses rather than appends the beauty/edit request. This is one **prompt-policy**
change, not a pure token-length experiment: wording/order also change. Any result
must not be attributed solely to512-token alignment.

## Conditioning and exact compatibility

Use the existing `run-upgrade-reference-ablation.ps1`, `ReferenceMode=four`, author
native-reference layout. Trace each unchanged input:

1. Original canyon source -> bicubic1MP -> full Flux2 VAE -> first ReferenceLatent
   on positive AND negative CFG conditioning: edit-source/composition/pose/expression.
   Its identity influence is not isolated; it is not a genuine scoring reference.
2. Original face-free Canny guide -> nearest-exact.5MP -> VAE -> second reference:
   composition geometry, not trained identity/expression control.
3. Protected genuine identity portrait -> nearest-exact.5MP -> VAE -> third reference:
   explicit identity image, in addition to the learned character LoRA.
4. Protected isolated genuine hair material -> bicubic.1MP -> VAE -> fourth reference:
   hair texture/style, not a substitute identity anchor.

The established genuine-photo-trained rank32 V3 step1600 **Klein Base9B** character
LoRA remains at.9, Smartphone Snapshot v13 Base9B at.25. Qwen3-8B text encoder,
full Flux2 VAE, fp8_e4m3fn model loading,50Euler steps, Flux2Scheduler, CFG4,
seed8675412,1024x1024, empty Flux2 latent, Turbo OFF and no postprocess remain fixed.
No portrait swaps, new weights, masks, crop, source-latent initialization, upscaler,
restoration, extra model pass or changed GPU lock. RTX3090/8188 only.

Identity is predicted from the documented character-training mechanism and genuine
native reference, not from a prompt or generic img2img signal alone. Existing local
config/provenance and raw four-reference scores provide task-specific evidence;
recognizability still requires genuine-reference scores and visual inspection.

Primary sources rechecked:

- [Base9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
  documents undistilled native multi-reference editing and the author implementation.
- [BFL character LoRA training](https://docs.bfl.ai/flux_2/flux2_klein_training)
  supports the genuine-trained character mechanism; it does not promise identity lock.
- [BFL editing guidance](https://docs.bfl.ai/guides/prompting_editing_single_reference)
  recommends explicit edits and retained invariants, not an assurance that every
  geometry/appearance requirement will be honored simultaneously.

The runner checks live nodes/models, actual protected weight hashes and both GPUs/
queues before submission. Clear only our completed job's cached models when queues
are empty and latest history proves ownership; never interrupt GPU work or use4070
against Upgrade's explicit lock.

## Acceptance and refinement limit

Compare the native output to source, original raw/Low and the earlier long native
High, using six genuine held-out photos (source is not in this scoring set). Inspect
at native size and thumbnail for recognizable identity, appealing closed-lip smile,
eye focus, head direction/forehead, cheek fullness, clear natural skin, real hair,
whole-frame integration and detailed background. No postprocess may hide native
failures. A stronger edit with a modest score tradeoff can be useful per Mitch's
preference, but generic faces, teeth, pose drift or rendered skin are not success.

At most one controlled refinement after diagnosing this first result. If it fails,
preserve and label it before another mechanism. No production promotion or universal
three-photo claim follows from a single successful canyon image.

## Submission and structural verification

Submitted canyon as `12e63367-4d00-4160-b37b-5942b27002cc`, port8188. The owned
previous job `d0f658bf-5550-4a08-8bb4-5073640bd79f` was terminal and both queues were
empty before its cached weights were released.3090 memory was rechecked at1134MiB
before the normal protected-hash/node/model preflight;4070 remained untouched.

`compact-native-high-canyon/prompt-only-change-audit.json` proves that the submitted
graph differs from the older native High only at `6.text` and `27.filename_prefix`.
All four reference records and verified model hashes are identical. The first
comparison flagged a missing legacy convenience phone-strength field; direct node3
inspection confirmed.25 in both. The comparator now validates a present convenience
field against the actual graph and always compares that graph exactly. Four tests
pass, including rejection of changed actual strength, contradictory metadata, seed
or reference changes. This is not a relaxed generation setting.

This section records submission, not completion. Read live history for status and
inspect the executed PNG/audit before claiming an image result.

## First native result: rejected

The run completed successfully in400.153s. Executed PNG metadata matches the saved
graph and reference hashes. `compact-native-high-canyon/evaluation/audit.json`
records genuine-reference likeness .756429 versus old raw .751794. This passes the
numeric identity diagnostic, **not** the requested result: mouth opening .123106
versus .035 maximum, clearly visible teeth, source pose drift8.810747 degrees and
much softer background. Full-size and thumbnail review reject it before polish.
The 512-token-sized condition is therefore not sufficient to fix High; no causal
claim that prompt length caused the earlier failures is supported.

## One controlled negative-conditioning refinement

The original and compact High both produce a broad toothy smile despite positive
closed-lip instructions. Before another prompt sweep, inspect the actual native
Base CFG path. Local `comfy.samplers.cfg_function` computes uncond + cfg*(cond-uncond),
and `CFGGuider` passes both branches at4.0; this is not distilled embedded guidance.
All four native references remain on **both** branches.

There is an important source caveat: [BFL's general help](https://help.bfl.ai/articles/7734566352-does-flux-2-support-negative-prompting)
says FLUX.2 does not support negative prompts. Do not market this as a BFL-endorsed
feature. However, the author-maintained [DiffSynth Flux2 implementation](https://github.com/modelscope/DiffSynth-Studio/blob/main/diffsynth/pipelines/flux2_image.py)
has separate Qwen3 positive/negative embeddings and actual CFG, and its
[exact Base9B example](https://github.com/modelscope/DiffSynth-Studio/blob/main/examples/flux2/model_inference/FLUX.2-klein-base-9B.py)
uses the compatible base model. Together with the inspected local math this supports
one **experimental** numerical test, not guaranteed semantic suppression.

Keep the compact positive prompt, all models/references,50steps,CFG4,seed and size
identical. Change only the formerly empty negative text to
`compact-native-high-negative.txt`, targeting observed teeth/head-angle/cheek/crease/
freckle/background failures. No new nodes, sampler modifications, LoRAs or installs.
Identity remains the same genuine character LoRA plus portrait, not this negative text.
Verify a graph diff of only `7.text` and output prefix. Default runner behavior still
uses an empty negative, so this does not modify production or earlier recipes.

This is the one controlled refinement for the compact-native experiment. Evaluate
raw output before any finish. If it still fails, close this route; do not start a
negative-strength/CFG/wording grid. All3 and production acceptance remain required.

### Refinement submission and checks

Submitted `ef7fce54-a1b5-4351-8175-2fa721b10a23` (number34), using the same
positive text and native four-reference graph. Both GPUs/queues were idle before
releasing only the completed compact experiment's cache;3090 memory fell to1127MiB.
The first protected-file hash preflight was denied access to the VAE and terminated
before submission. The approved retry completed all protected hash checks and
submitted exactly once. It did not bypass a model/provenance check.

`compact-native-high-negative-canyon/negative-only-change-audit.json` proves that
only `7.text` and `27.filename_prefix` changed. The standalone graph comparator
has five passing tests, including explicit negative-branch selection and rejection
of simultaneous positive changes. The misplaced reference-mutation test was moved
back into its own seed/reference check. Eight existing attractiveness/reporting
tests also pass. These are code/provenance checks, not image acceptance.

The exact DiffSynth Base9B example was read in full: both generation and native edit
use50steps/CFG4. It does not itself demonstrate a nonempty negative prompt; the
experimental rationale is the separate negative branch in its pipeline and local
Comfy CFG implementation. The BFL support caveat above remains applicable.

### Refinement result: visibly stronger, not accepted

The job completed successfully in400.040s, output
`ComfyUI/output/upgrade-source-faithful/compact-native-high-negative-canyon/raw_00001_.png`,
SHA256 `079cede4fb0cbd07a28c9e065cffcf24334911d81905e3996a6b17d068feae5a`.
The evaluation verified the executed PNG graph and reference hashes, then scored
six independent genuine photographs locally. No postprocess was applied.

| Diagnostic | Compact positive only | Same positive + negative |
| --- | ---: | ---: |
| Genuine-reference centroid similarity |0.756429|0.422163|
| Source pose maximum error, degrees |8.810747|0.976511|
| Mouth opening ratio |0.123106|0.004329|
| Source mouth-coordinate error |0.103722|0.005341|

Compared with the old raw0.751794, the refinement loses0.329631 likeness. Against
individual genuine references it scores0.268–0.397. This is substantially more than
the modest likeness tradeoff Mitch accepted, not merely a rounded0.70 near miss.
The score is diagnostic, not a measure of beauty or proof of the source's genuineness.

Full-size, face-crop and thumbnail review: no visible teeth; head angle and closed,
asymmetric smile now follow the source substantially better; the background is
more readable than the positive-only experiment. Eyes/brows, cheek contour and
skin presentation are clearly different from Low. The face also becomes much more
source-like, with less of the likeness seen in the genuine portrait/old raw. Skin
is cleaner but still somewhat uniform. These gains do not establish an acceptable
recognizable-Mitch High. Maximum source-relative eye-coordinate error0.027111 also
requires review; do not claim exact gaze preservation from the pose/mouth passes.

Conclusion: nonempty native negative conditioning has a large effect in this one
fixed-seed test, but does not meet the combined appearance/identity requirement.
Which individual negative term caused the tradeoff has not been isolated. This
closes the compact-positive/one-negative-refinement experiment; no wording/CFG/
strength grid, additional photos, or production promotion was queued. Present the
comparison as an unaccepted stronger-edit boundary for Mitch's visual judgment,
not a fixed High. A subjective likeness decision is needed before treating this
direction as useful; all-three-photo and end-to-end verification remain outstanding.

Both queues were empty at handoff;4070 was untouched. Production main node, High,
Low, gaze module, frontend extension and public workflow hashes remain unchanged.
The five graph tests, eight existing attractiveness/reporting tests, PowerShell
parser and `git diff --check` pass (only existing LF/CRLF notices in unrelated files).
