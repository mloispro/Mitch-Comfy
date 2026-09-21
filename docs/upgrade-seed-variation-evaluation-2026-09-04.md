# Native High: one alternate-noise diagnostic

Status: completed diagnostic, not production or a three-photo solution. The preceding
goal turn made progress by measuring and closing iris/brow contrast as a stand-alone
High fix. Its normal-size beauty effect is too small. Do not repeat that contrast grid.

Fresh inventory confirms earlier V3 checkpoints were removed in the documented
September 1 cleanup. The current weights/configs do not establish overfitting. No
checkpoint reconstruction, model install, retraining or dependency change is planned.
Existing 4B rollbacks are not substituted into the 9B workflow. Two newly inspected
adapter cards do not justify installation: dx8152 Consistency names distilled 9B,
and houseofboern More Detail targets more skin/fabric/hair detail, not this combined
identity/expression/beauty requirement. Neither is installed or used here.

## Question and research gate

The previous native High comparisons fixed each scene's seed while varying controls.
That is good for parameter isolation, but has not established whether the tense
house expression is robust to noise variation. Run **one predeclared next seed**;
this is not a seed hunt, a best-of-N production policy, or a claim that all prior
failures were unlucky. No added postprocess may hide native failures.

Use `compact-native-high-negative-house/experiment.json`, SHA256
`D90422510E24CC94178FE894AD4D9D069EA1DDF091A857CF1251C1627ED1FFA4`.
Change only RandomNoise seed 8675416 -> 8675417 and the SaveImage destination.
The saved executed control PNG and reference hashes must match before submission.

Identity remains the genuine-photo-trained Base9B V3 step1600 LoRA at .9 plus
the genuine portrait in reference3. Source1 carries edit-source/composition/expression
(its identity influence is unisolated); source-derived face-free edges in reference2
carry structure; isolated genuine hair in reference4 carries material, not identity.
Each input follows LoadImage -> fixed scale -> VAEEncode -> ReferenceLatent on both
CFG branches. No style-only reference or prompt is being claimed as identity control.

Keep Base9B loaded fp8, Qwen3-8B, full Flux2 VAE, Smartphone v13 .25, 50 Euler steps,
CFG4 and 1680x1008. This retains the 1.69MP control rather than changing resolution
with seed. Turbo OFF, Phone ON, 3090/8188 locked. Existing negative text is an
experimental native-CFG condition, not a newly endorsed BFL negative-prompt feature.

[BFL training guidance](https://docs.bfl.ai/flux_2/flux2_klein_training) supports
Base-model character LoRAs and 50-step/CFG4 inference. The installed and
[author-maintained noise node](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_custom_sampler.py)
passes the seed to noise preparation. This supports a noise-only controlled test,
not a prediction of greater attractiveness. The prior author's native-edit template
adaptation and all other graph connections are reused, not invented.

## Decision rule

Freshly verify both GPU queues/devices, all live node/model names, five weight hashes
and four reference hashes. Preserve the other worker; no explicit cache free or
restart. Recheck the owned latest terminal graph and idle queues after hashing.

Evaluate the raw result against source, actual production Low and the exact native
control, using six independent genuine identity photographs. Inspect native, face
and thumbnail views for eyes/brows, closed-lip smile/no teeth, cheeks, skin spots,
hair, forehead, pose/gaze, body, background detail and integration. Scores remain
diagnostics. If the same substantive failures remain, close this noise probe without
rolling further seeds. A good individual sample would still need a coherent policy,
canyon and genuine-third verification, integration and end-to-end validation.

## Submitted run

Job `adfcbb9f-0626-4474-8bca-d1bae6032958`, queue number47, was accepted by8188
with no node errors. Experiment folder:
`work/upgrade-source-faithful-20260903/native-high-seed-probe-house`.
All model/reference hashes and both idle-queue checks passed. The latest owned
terminal RefControl job's graph matched its saved manifest; no cache was freed.
The graph-difference check allows only `20.noise_seed` and `27.filename_prefix`.
Five regression tests pass.

The first preflight stopped before creating the experiment folder or submitting:
the historical control lacks a convenience baseline-report hash. The runner now
uses the independently recorded exact house report pin
`2F681509A799DA00A38E4A40825BA0891C72110DC324E4863B47BC6EF791859C`
for that hash-pinned legacy control only. Altered report bytes or contradictory
present metadata still fail. The second preflight submitted exactly once; no
uncertain POST was retried. This section is submission evidence, not image acceptance.

## Completed result and decision

Live history reports successful completion of the exact submitted job in499.65s.
Native output:
`C:/projects/AI-Tools/ComfyUI/output/upgrade-source-faithful/native-high-seed-probe-house/raw_00001_.png`
SHA256 `b34e11743914a05015a8e6f8b438709c673cea6cc828a00244097c4e32b968f4`.
The CPU evaluator verified its executed graph/reference hashes and compared it
with all six genuine held-outs. No postprocess was applied. A second comparison
check verified unchanged source, raw, actual Low, genuine scoring references and
the exact two-field graph diff before building the four-column A/B sheets.

| Diagnostic | Seed8675416 control | Seed8675417 probe |
| --- | ---: | ---: |
| Genuine-reference likeness | .741355 | .695566 |
| Source maximum pose error, degrees | 2.198845 | .929035 |
| Mouth opening ratio | .005476 | .001914 |
| Source normalized mouth-corner error | .014931 | .022210 |
| Largest source eye-coordinate component error | .044975 | .080856 |

The eye figure combines horizontal/vertical local coordinates, not a degree-of-
gaze estimate. Probe horizontal errors alone are .033535 and .028768. The mouth
is visibly closed, with no invented teeth. The existing numeric likeness gate
fails (.695566 vs raw .779115); do not round it into a pass. However, Mitch allows
a stronger beauty edit with a modest likeness tradeoff, so that gate alone is
not the acceptance decision. Recognition/appearance still require human review.

Native-size, face-crop and thumbnail review: the alternate noise makes a noticeable
change, not merely the same Low face again. Eyes/brows are better defined and the
overall presentation is more source-like than production Low. Face fullness is
less pronounced than Low, but matching Mitch's actual preferred appearance is not
established. Frown lines/skin marks remain, highlighted hair has regular bundled
strands, and the background remains strongly softened instead of the requested
PhoneON detail. Clothing/body/scene remain broadly coherent without an obvious
face-paste boundary, but this is not an unchanged-background or exact-gaze result.

Decision: **not a complete High fix and not promoted**. Noise affects the beauty/
likeness tradeoff substantially; this single comparison does not establish a
reliable seed-selection policy. No more seed rolling follows this diagnostic.
The four-column face comparison was shown to Mitch with a nonblocking question
about whether the rightmost face is a useful beauty/likeness direction, explicitly
excluding neither background nor texture from the eventual full goal. No answer
or approval is assumed. Canyon, genuine-third and end-to-end production acceptance
remain outstanding. Goal remains active; no repeated-blocker condition exists.

Both live queues were empty after completion. The 3090 cache was retained and the
4070 was untouched. No production files, defaults, model files or dependencies
changed. Five seed/provenance tests, syntax checks and `git diff --check` pass.
