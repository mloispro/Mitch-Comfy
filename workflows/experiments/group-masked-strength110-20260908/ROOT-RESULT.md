# Strength1.10 improves likeness, but does not fix Group

Completed one controlled refinement on September8. Reject this recipe for
production: the main identity remains insufficient under the declared checks,
and readable partial fifth-person preservation still fails. The run itself,
native guards, complete graph attribution and independent monitoring all pass.
No production workflow changed. All earlier evidence remains intact.

## Measured result

Only character-hook strength0.90 to1.10 and the save prefix changed. Both use
seed8675412,832x1216,30Euler/CFG4, the same native masks, references and models.
The correct central navy-suited man was selected geometrically before scoring,
then root confirmed index0 on the saved scene-selection overlay. Native face
76.4474x106.4948px; no larger-face/framing substitution.

| Diagnostic | Previous0.90 | New1.10 | Fixed requirement |
| --- | ---: | ---: | --- |
| Main centroid | .5225072503 | .5556934476 | >=.55; new passes this component |
| Mean of six genuine comparisons | .4507673730 | .4793970635 | Descriptive |
| Weakest genuine comparison | .3565687537 | .4005086422 | >=.5533463955; fails |
| Maximum bystander-to-identity | .0705500022 | .0656470135 | <.42; passes |
| Maximum bystander-to-main | .1853 | .1746 | <.50; passes |
| Maximum distinct bystander pair | .2586 | .2348 | <.72; passes |

Centroid gain .0331861973; weakest gain .0439398885. All six improve, but all six
remain below the unchanged conservative floor. New raw scores:

- val01 surf: .4005086421966553
- val02 mirror: .48546597361564636
- val03 navy: .5341733694076538
- val04 window: .4578324854373932
- val05 balcony: .4954531490802765
- val06 car: .5029487609863281

These are similarity diagnostics, not probabilities. `near_match` is not an
identity lock. Both blind full-size/thumbnail reviews preceded scoring. They
found plausible closed lips, main arms/hands/glass contact and distinct principal
bystanders, but uncertain fine likeness and no sufficiently readable partial
fifth person. Root also finds the face overly polished/smooth relative to the
genuine photographs. Both flag changed blonde hand contact. No clear halo or
gross new main limb defect is demonstrated.

## What this establishes and what it does not

The targeted strength increase has a measurable effect, but not a sufficient
one. Pixel comparison is nonzero: whole-frame mean absolute channel difference
.984758/255; main-face rectangle5.233321/255. This is not proof of exact internal
weight behavior or photographic improvement. No additional strength/seed sweep
or postprocessing rescue is justified by this bounded result.

Regional output mixing still shares full-frame latents; it does not isolate
attention. The face interior was already mask1.0. This experiment does not prove
that mask geometry, strength alone, or a single implementation defect explains
the remaining identity deficit. The prompt omits explicit preservation of the
edge person, although the guide retains it; that is a separate known source-
description omission, not a demonstrated cause or an identity fix.

The all-six floor is a conservative experimental guard, not a universal production
law. The existing genuine-only77px study shows occasional marginal crossings,
but not losses comparable to this .4005 weakest score. No post-hoc threshold
change was made. Existing global1.00 and2.28MP holdouts, raw-photo Base9B identity
editing and Krea2 IdentityEdit trials do not supply a proven reliable replacement.
Their failures and different evaluation cohorts remain preserved.

## Runtime and reproducibility

- Prompt1cb5987f-0cfb-4106-b131-fe410e7f56f7; clientbc1dbe9a-4099-4fd8-865d-6a56dde09972.
- Worker338.904seconds including loading;338.904 vs334.218 is not a general
  speed comparison across fresh lifetimes/cache states.
- Graph SHA DFE5EDBF8205188C6DA053FE74C747A234D050DA0889D44017A610ACE8657CD1.
- Native and copied PNG SHA939A0714A8EC4443B6D4F78E005EE2BACF731C601D30AB5049146CF7F0A0EC82.
- Evaluation comparison SHA C109B854CD4D48EABAC88371EFA4FF9F9896D1FD7B2193B76708DF7AC179C728.
- All36 executing events in exact order; both native entry/return guards and
  independent terminal observer pass. Full graph/PNG/ownership attribution
  verified before scoring and reverified by CPU-only scoring.
- 449 memory samples: minimum host17.90673065GiB/commit45.00217056GiB;
  largest sample gap.794155seconds.294 exact desktop checks passed. These are
  sampled cooperative safeguards, not guaranteed prevention of every transient OOM.
- Root independently passed33 PowerShell +18 runtime/desktop +9 evaluator CPU
  tests. An independent saved-run audit corroborated runtime and ownership.
- Owned37248/trampoline51160 stopped06:47:25.0839486Z; stop receipt
  SHA7F6BCFE461BDE2D21833C55A6A202E5C7B39AB1FB36309658D523997B11CB342.
  Both production workers were preserved; both GPUs subsequently idle.

The initial admission was refused before any POST because root serialized process
creation timestamps through PowerShell automatic date conversion. Exact same-
instant but different strings correctly failed the strict comparator. Rejected
approval and entire unsubmitted attempt are under pre-submit-refusals/timestamp-format.
Root restored exact recorded strings, reran the unchanged validator, and submitted
the first and only image. No runtime guard, threshold or payload was changed.

## Remaining input / next substantive work

The September8 recheck finds the same55 top-level local photographs, all matching
the prior discovery hashes, and no files in the V6 intake. The preserved training
audit identifies missing true-profile and usable body coverage: six profile
photographs (two training plus one independent validation per side) and two clear
full-/three-quarter-body training photographs from distinct sessions. Existing
three-quarter face views are already adequate. See the preserved
[photo audit](../../../work/flux2-klein9b-identity-v6-r32-dop/EXISTING-PHOTO-AUDIT.md).

An improved-data training experiment is the recommended substantive next avenue,
not a promised cure. No new training job, model download, photo upload or purchase
was initiated. New photographs and a separately approved training plan are needed
before reviving that shelved route. The useful source-preserving Upgrade options
and qualified Solo results remain unchanged; the full9B suite is not finished.

[Exact diagnostics](evaluation-pilot/comparison.json) ·
[Root blind review](ROOT-VISUAL-REVIEW.md) ·
[Independent blind review](INDEPENDENT-VISUAL-REVIEW.md)

![Actual1.10 Group test](C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/group-masked-strength110-20260908/runs/ready-amber-hook-pilot/group-amber-hook-s110-seed8675412_00001_.png)
