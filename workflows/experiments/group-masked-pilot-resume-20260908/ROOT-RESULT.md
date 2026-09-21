# Group masked pilot — completed, image rejected

The remaining pilot actually ran to completion on September8. Runtime and
ownership checks pass; photo acceptance fails. This is no longer an unsubmitted
RAM-blocked experiment. No production workflow was promoted or changed.

## Result

The regional identity treatment greatly reduced bystander similarity in this
one pair, but weakened the main identity. The selected central man is index0,
visually confirmed by the scene-selection overlay at bbox
(383.6488,487.1934,460.0754,593.5444). Selection was geometric before scoring,
not the largest face or best identity score. All three full bystanders were
detected and remain outside the main index.

| Diagnostic | Earlier all-white control | New person-mask pilot | Requirement |
| --- | ---: | ---: | --- |
| Main centroid likeness | .6136325002 | .5225072503 | >=.55 — pilot fails |
| Weakest genuine-reference comparison | .4577103853 | .3565687537 | .5533463955 floor — both fail |
| Maximum bystander-to-genuine likeness | .3802 | .0706 | <.42 — pilot passes |
| Maximum bystander-to-main likeness | .5051 | .1853 | <.50 — pilot passes |
| Maximum distinct bystander-pair likeness | .4354 | .2586 | <.72 — pilot passes |

The same six genuine photographs and unchanged calibration were used. Every
main-reference comparison declined; all six pilot values are below the floor:
val01 .35656875371932983; val02 .45176178216934204;
val03 .517468273639679; val04 .45188236236572266;
val05 .4732408821582794; val06 .45368218421936035.
Mean .4507673730452855. `near_match` is not a pass or identity lock.
These are similarity diagnostics, not probability percentages.

Both blind native/thumbnail reviews were completed before scoring. The main
man, four principal people, own arms/hands and glass contact look broadly
plausible; the skin is smoother/more polished than the genuine photographs.
Neither review accepts preservation of the readable partial fifth person at
the right edge: at most ambiguous tiny edge slivers remain where the source has
a substantial visible torso. Root also flags the blonde's separated hands
instead of the original folded lap contact. No obvious head seam/halo was found.
These failures are not waived by low bystander similarity.

## Actual run and safety evidence

- Prompt `df911670-57ed-4bc5-b982-a2bbe057b975`; client
  `2e1167a8-46f7-4542-bb3d-21a318605f8c`.
- One832x1216 image, seed8675412, frozen36-node graph
  EB6AEF903DB72BE0E8CED5389EFB1C01E08E586B76C611CF3665796C05EFA76A.
  No recipe, model, mask, sampling or resource-threshold changes.
- 334.218 worker seconds, including loading. Both native guards returned and
  all36 execution events passed. Independent observer terminal: success.
- 444 host/commit samples, maximum gap .774364seconds. Lowest host17.02055GiB;
  lowest commit headroom45.01652GiB, above unchanged12/10 floors.283 exact
  desktop-lifetime observations passed. These are not continuous GPU-peak
  measurements or hard pre-OOM guarantees.
- Exact owner55636 and trampoline48604 stopped at06:11:48.3313207Z. Both
  production workers52720/19552 retain their original lifetimes and empty queues.
  Stop receipt SHA BBBDB52FED8492E66DFB35F00C8F8EE5236F4800B8BCDB9C9B03F87C4B55ABD2.
- Original193 historical/18 fresh pins plus11 desktop supplement pins remain.
  Root independently passed33 original/19 supplemental PowerShell checks,
  original6 native-runtime tests and10 desktop tests in actual Comfy Python.
  Final independent run of all24 Python tests (6 native,10 desktop,8 evaluator)
  and19 supplemental PowerShell checks passed after result documentation; all
  original and supplemental pins still verify.

The first verify-only call used default-sandbox miniconda and refused a Windows
Python path-alias comparison. The two paths are the same file in the documented
read-authorized Comfy environment; the original pinned evaluator then passed
full actual verification unchanged. No evaluator alias bypass, score waiver or
image retry was added. CPU-only scoring also reverified actual provenance.
Its saved comparison SHA is BB06BCD70C9D1FDC83F4D12865075AA8C277BC566F9058F1EC11F5F0A4D14101.

## Decision and mechanism diagnosis

Reject this recipe for use. The test establishes that regional mixing can reduce
these bystander similarities; it does not establish sufficient identity retention.
The known mechanism mixes denoising outputs, not identity-token attention, and
both branches share the evolving full-frame latent. It is therefore unsurprising
that changing identity conditioning outside the person also changes his final
face. That is a mechanism-consistent interpretation, not a proved attribution
of every pixel or a guarantee that a higher LoRA strength would repair it.

A read-only native-mask check rules out simply omitting the main facial features:
the interior feature rectangle(395,505)-(451,580) is uniformly1.0, and the detected
main-face rectangle has mean .999342/minimum .74902 at its boundary. All three
bystander face rectangles are uniformly0. This checks the saved native mask,
not token attention or a mathematical guarantee about resized latent boundaries.

The old control's automated monitor failed and its image remains an image-only
comparator. Different worker lifetimes/cache context prohibit a matched-speed
claim. Neither image passed the full six-reference floor. Do not reuse either
as a successful identity control or declare all Group layouts fixed.

No rescue seed, strength sweep, sharpening, restoration, head paste or further
render was performed. Future work needs a separately justified identity-retention
test; upscaling cannot make this failed identity/source-preservation test pass.
The already validated source-preserving Upgrade options remain separate and
unchanged. This bounded experiment is complete; the full9B suite is not ready.

[Raw photo](runs/ready-amber-hook-pilot/group-amber-hook-pilot-seed8675412_00001_.png)
· [Exact diagnostics](evaluation-pilot/comparison.json)
· [Root pre-score review](ROOT-VISUAL-REVIEW.md)
· [Independent blind review](INDEPENDENT-VISUAL-REVIEW.md)
· [Python alias evidence](ALIAS-EVIDENCE-20260908.json)

![Rejected Group pilot](C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/group-masked-pilot-resume-20260908/runs/ready-amber-hook-pilot/group-amber-hook-pilot-seed8675412_00001_.png)
