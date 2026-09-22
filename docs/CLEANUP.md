# Preservation and cleanup decisions

Reviewed September 21, 2026. Mitch asked to finish identifying unfinished work before
deleting its dependencies, then authorized the recommended next steps. The chosen scope
is a recoverable local checkpoint followed by removal of verified redundant staging
copies. The first checkpoint retained everything; the subsequent authorized cleanup
removed exactly twelve duplicate weights after dependency review and fresh hashes.
That duplicate-removal stage performed no generation, training, worker restart, upload
or experiment retirement. A later validation pass ran one authorized Upgrade image
and completed the actual gallery check; see the updated dispositions below.
Current image acceptance remains in [STATUS](STATUS.md). The [September 21 closeout](validation-closeout-2026-09-21.md)
records the completed validation/disposition pass and its remaining feature limits.

## Retain and finish deliberately

| Route | Disposition | Next useful action / stopping point |
| --- | --- | --- |
| Qwen 2.1 Group first image | Keep three verified weights (16.10GiB), isolated runtime and rejected evidence | [Completed pilot](../work/group-qwen21-pilot-20260921/RESULT.md) fails face integration before scoring, so no refinement follows. Both private services are stopped. [Two old HTTP partials](../work/group-qwen21-pilot-20260921/partial-prefix-check.json) match complete-file prefixes byte-for-byte:1.914GiB of redundant staging data, still retained. No production change or unique-weight deletion follows this image failure. |
| Original production and the three Production Speed workflows | Keep all dependencies and saved fallbacks | The [Speed release](../work/production-speed-rollout/RESULTS.md) is complete for its three recipes. Do not rerun its confirmation pairs as unfinished work. |
| Solo public presets | Source comparison complete; retain controls and use accepted Speed Cocktail for its exact case | [Comparison](solo-cocktail-comparison-2026-09-21.md) found differences in references, surrounding prompt and diffusion precision, without isolating the cause. No blanket original-card fix follows. Other scenes retain their [coverage qualifications](../work/9b-readiness-resume-20260907/COVERAGE-MATRIX.md). |
| Source-preserving Upgrade | Second genuine-source check complete; retain both controls and new result | [Balcony test](../work/upgrade-generalization-20260921/RESULT.md) passes the fixed visual/source-excluded gates. Coverage is now two genuine photos, not universal enhancement or stronger High. |
| Stronger High | Hold all unique weights and evidence; no repeat grids | The [native/BeautyGRPO work](upgrade-high-resume-2026-09-07.md) and [explicit-feature refinement](upgrade-high-explicit-features-2026-09-07.md) did not achieve the requested improvement. Require a changed, supported mechanism before another experiment; do not declare High complete. |
| LaTo | Hold the full 47.715 GiB of candidate weights | The [predictor failure](../work/9b-readiness-resume-20260907/lato-compat/ROOT-FINAL-PREDICTOR-RESULT.md) closes its tested source/recipe. Later image stages are unexecuted. [Disposition review](../work/final-validation-20260921/DISPOSITION.md) confirms external-landmark driving is a distinct supported possibility, but has no admitted geometry for this case. Retain assets; do not advance failed predictor points. |
| PerformRecast | Hold five new isolated checkpoints, 0.941GiB | [Zero-motion test](../work/high-performrecast-gate-20260921/RESULT.md) passes runtime/likeness but fails native detail. No expression trial or production installation. Preserve this bounded failure; it does not finish stronger High or authorize deleting unique weights. |
| MirrorPPR | Conditional research candidate; no model assets downloaded | [Source/release gate](../work/high-mirrorppr-gate-20260921/RESULT.md) does not establish full High capability in the inspected public Face release. Await author-supported full-task evidence and compatibility admission; this source-only finding neither fails an image nor finishes High. |
| UMO Group | Keep one new released adapter and its exact-value Comfy conversion; close the tested recipe | Both serializations total 1,307,517,672 bytes (1.218GiB); existing base assets are reused. [Mitch rejects the pair](group-umo-visual-rejection-2026-09-21.md) for oversized-looking head proportions and an unnatural, pasted-on face. Earlier favorable geometry wording is superseded. Preserve this failure; no unique model deletion follows. |
| General Group likeness | Hold identity models, genuine references and failed/accepted controls | Regional routing/text and the newer [visually rejected UMO pair](group-umo-visual-rejection-2026-09-21.md) are closed for their tested recipes. Higher likeness diagnostics do not repair proportions or integration. No further sweep, model download or new character training follows from this correction or cleanup. |
| VOSR | Completed study; retain 6.494 GiB for local reproducibility | The [completed enhancement study](../work/fast-detail-20260903/RESULTS.md) did not justify promotion. Preserve results; do not repeat the same enhancement recipe. |
| USO / WithAnyone 1.0 / PuLID | Tested routes closed; installed assets retained | [Screening results](identity-candidate-screening.md) establish bounded rejection, not failure of every future model/version. [Dependency audit](../work/final-validation-20260921/DISPOSITION.md) found installed optional PuLID/core USO consumers and historical runners. Retain unique assets/shared encoders; dormant does not mean redundant. |
| St. Barts final image | Keep final PNG, original, masks, background and composition code | [Exact-foreground correction](../work/st-barts-exact-foreground-20260920/RESULT.md) is complete for pose preservation with qualified likeness. [Actual gallery interaction passed](../work/st-barts-gallery-check-20260921/RESULT.md); text-conditioned generation does not inherit exact pose preservation. |

No unresolved route is silently marked complete or retired to obtain disk savings.
The Solo public-versus-accepted-recipe source comparison is complete; use the
existing accepted Cocktail handoff. The bounded second-source Upgrade test and
actual gallery check are now complete. [Final dependency/disposition review](../work/final-validation-20260921/DISPOSITION.md)
retains 54.654 GiB of unique weights; no further redundant weight was established.
High and broader Group remain unresolved features, with their dependencies retained.
This is cleanup readiness with explicit keep decisions, not full-suite image acceptance.

## What the disk audit actually established

[Full read-only model audit](../work/cleanup-checkpoint-20260921/model-audit.json),
[audit source](../work/cleanup-checkpoint-20260921/audit_models.py).

The inventory covered 27 weight files across the four previously suggested candidate
roots. Twelve files, totaling **61.638 GiB**, have a full SHA256-identical installed
copy under `C:/projects/AI-Tools/ComfyUI/models`. The inventory records both exact paths,
sizes, hashes and distinct-file status. It neither writes models nor proves that the
download-side path is unused.

| Candidate location | Weight size | Current decision |
| --- | ---: | --- |
| `.downloads/models` | 30.404 GiB before cleanup | Removed eight duplicate weights totaling 29.958 GiB; retained the unique USO adapter and all other files. |
| `work/upgrade-high-20260907/models` | 31.680 GiB before cleanup | Removed four duplicate weights; retained download receipts/configuration and every installed copy. BeautyGRPO runners use installed paths. |
| `work/9b-readiness-resume-20260907/lato-compat/models` | 47.715 GiB | Hold; no identical installed copy was established by this audit. |
| `work/fast-detail-20260903/vosr-runner/assets` | 6.494 GiB | Hold; no identical installed copy was established by this audit. |

The subsequent [dependency review](../work/duplicate-cleanup-20260921/DEPENDENCIES.md)
checked active, dynamic and frozen consumers. No inference consumer of the twelve
staging weight paths was found in the inspected project/Comfy scope. A dry run and
the removal pass each verified full SHA256 and size on both sides. The removal pass
held installed copies protected from writes/deletion and required staging files to
be unused. Exact regular files were removed; no directory or hardlink replacement.

The [completed result](../work/duplicate-cleanup-20260921/RESULT.md),
[removal receipt](../work/duplicate-cleanup-20260921/removal.json) and
[post-cleanup snapshot](../work/duplicate-cleanup-20260921/after.json) record
**66,183,721,828 logical bytes removed (61.638 GiB)**. Observed volume free space rose
by **61.628 GiB**, to **792.464 GiB**; other disk activity can affect that measurement.
All 64 loader dropdown sets were unchanged. Metadata for 145 installed files and
15 unique candidate weights was unchanged; all 31 retained files in the two staging
roots matched their pre-cleanup hashes. The 53 pinned evidence files and 25 active
baseline artifacts also passed. These are integrity/API checks, not new image acceptance.

The versioned [restore manifest](../config/duplicate-model-cleanup-20260921.json)
records every removed path, retained source, size, SHA256 and original timestamp.
Copying a retained source back can restore an old staging path without a download;
verify its hash and never overwrite an unexpected destination. The installed weights
are the surviving copies, so Git and the evidence archive do not replace model backup.
Any further removal requires a separate exact-path/dependency review; an entire `work`
directory must not be removed based on its size.

## Recovery coverage

The local snapshot is `local/preservation-checkpoint-20260921/evidence.zip` with a
[completed verification receipt](../local/preservation-checkpoint-20260921/backup-verification.json).
All **14,814 files** were read back and matched their source SHA256 values: 9,543,751,819
source bytes in an 8,681,260,671-byte archive. Its `SNAPSHOT-MANIFEST.json` lists every
entry and all 1,035 exclusion records. The [snapshot script](../local/preservation-checkpoint-20260921/snapshot.py)
records the exact collection and verification method.

Scope: project `work`, `datasets`, `comparisons`, frozen workflow experiments, the
evaluation-case catalog, and normal ComfyUI `input` and `output`. Model tensor files,
virtual environments, caches and filesystem links are explicitly excluded and listed
in the archive manifest. All archived original evidence remains in place. Source/configuration
and curated gallery assets were saved by local Git checkpoint `7582713` before cleanup.
The twelve removed weights were excluded from that archive; their installed twins remain.

The new cleanup scripts, dependency search, before/after snapshots and verification
logs are preserved separately in `local/preservation-checkpoint-20260921/duplicate-cleanup-evidence.zip`;
its [verification receipt](../local/preservation-checkpoint-20260921/duplicate-cleanup-backup-verification.json)
records entry-by-entry SHA256 checks. The original snapshot and its receipt are unchanged.

New Upgrade/gallery/disposition evidence is preserved in
`local/final-validation-20260921/evidence.zip`; its [verification receipt](../local/final-validation-20260921/verification.json)
records SHA256 readback of every archived entry. It supplements rather than replaces the earlier archives.

The subsequent [Group token-delta pilot](../work/group-token-pilot-20260921/RESULT.md)
completed its software and image checks but failed likeness/visual acceptance. Its
private worker is stopped and the evidence is saved in
`local/group-token-pilot-20260921/evidence.zip`, with a
[verified receipt](../local/group-token-pilot-20260921/verification.json).
This closes the tested recipe, not general Group or stronger High. All15 unique
candidate weights and installed dependencies remain retained; no additional deletion
is justified by this result.

This is a same-drive recovery snapshot, not protection against losing the computer or
disk. No external backup destination has been selected and nothing was uploaded.
The large installed/held models remain only where they already existed unless another
backup exists independently; this archive does not claim to back them up.

The subsequent PerformRecast evaluation adds **1,010,234,841bytes (0.941GiB)** in five
isolated model files under `work/high-performrecast-gate-20260921/models`. These are
additional to the15 older unique candidate weights (54.654GiB), not a change to the
completed duplicate-removal inventory. All are retained. Its non-model evidence is
saved in `local/high-performrecast-gate-20260921/evidence.zip`, with a
[per-entry verification receipt](../local/high-performrecast-gate-20260921/verification.json).
The snapshot excludes these models explicitly. This pass deletes nothing and leaves
the public Comfy worker running; useful stronger High and general Group remain unresolved.

The subsequent [dual-context Group pilot](../work/group-dual-context-pilot-20260921/RESULT.md)
adds no model weights. Its structural routing checks pass, but the image fails the
fixed likeness and anatomy gates. The private worker is stopped. Both new work packages
are saved in `local/group-dual-context-pilot-20260921/evidence.zip`; the
[verification receipt](../local/group-dual-context-pilot-20260921/verification.json)
confirms63 source entries (17,388,748bytes) with per-entry SHA256 readback. The archive
is16,856,180bytes and excludes private worker runtime data and bytecode. Originals,
all20 unique candidate weights and installed dependencies remain; no deletion follows
from this failed recipe. This remains same-drive evidence recovery only.

The sole scene-text refinement likewise downloads no models and deletes nothing.
Its private worker is stopped. The new diagnosis/software/image packages are saved
in `local/group-region-text-pilot-20260921/evidence.zip`; the
[verification receipt](../local/group-region-text-pilot-20260921/verification.json)
confirms60 entries (19,647,417source bytes), all SHA256 read back, in a19,183,882-byte
archive. This supplements the earlier snapshots. The failed photograph and all
unique assets remain; stronger High and general Group are not marked complete.

The MirrorPPR source/release gate adds no model weights. Its 34 public-source/audit
files (1,112,517 bytes) are saved in `local/high-mirrorppr-gate-20260921/evidence.zip`;
the [verification receipt](../local/high-mirrorppr-gate-20260921/verification.json)
records SHA256 readback of every entry in the 209,263-byte archive. Original evidence,
all 20 unique candidate weights (about 55.595 GiB) and installed dependencies remain.
There was no generation, installation or deletion. This is same-drive recovery only.

The UMO trial adds one pretrained adapter, kept in raw and author-equivalent converted
forms under `work/group-umo-gate-20260921/models`. All20 earlier unique weights remain;
the two new serializations add1.218GiB. The source/load gate and first image are preserved
in `local/group-umo-pilot-20260921/evidence.zip`; its
[receipt](../local/group-umo-pilot-20260921/verification.json) verifies66 entries,
10,451,362source bytes in a9,884,912-byte archive. Model tensors are explicitly excluded
and retained at their source paths. Originals remain, with no production installation,
new training, upload or deletion. This remains same-drive evidence recovery only.

The sole UMO image-guidance refinement is preserved separately in
`local/group-umo-guidance3-20260921/evidence.zip`; its
[receipt](../local/group-umo-guidance3-20260921/verification.json) verifies35 entries,
9,452,728 source bytes in a9,340,508-byte archive, and verifies the parent archive hash.
Both private4070 workers are stopped. This supplement adds no model weights and deletes
nothing; neither image is promoted and neither unresolved feature is marked complete.

## Gallery baseline reconciliation

The audit found two stale active pins: the gallery manifest and JavaScript. Their current
hashes exactly match the September 20 [live manifest receipt](../work/st-barts-original-pose-20260920/live-verification.json)
and [final publication receipt](../work/st-barts-exact-foreground-20260920/publication.json).
The final PNG and thumbnail are also covered by that saved publication evidence.

The [baseline registry](../config/frozen-baselines.json) preserves the old public-surface
record and its hashes as superseded, and records the current surface separately. This
reconciles already implemented gallery behavior; it does not certify new generation,
all-preset photo acceptance. The later September 21 browser check separately passes
the card/profile/appearance/prompt interaction. Engine files
and production workflow JSON are unchanged by this cleanup.

The checkpoint also checks Git's staged bytes, not only the working files. Default
newline conversion initially changed both pinned gallery text files and 98 frozen
experiment files in the index. Narrow [.gitattributes](../.gitattributes) rules preserve
those exact bytes and the archived reference-policy snapshot. The evaluated cache
module/test retain their existing EOF padding; only that whitespace diagnostic is
waived for those two files. No runtime source was reformatted to make an integrity
check pass.

The duplicate-cleanup restore manifest also preserves its exact bytes in Git because
the executed removal script and archived receipts pin its raw SHA256. Its narrow
attribute rule prevents newline conversion from changing that audit identity.
