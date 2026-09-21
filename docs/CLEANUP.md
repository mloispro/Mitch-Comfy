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
| Original production and the three Production Speed workflows | Keep all dependencies and saved fallbacks | The [Speed release](../work/production-speed-rollout/RESULTS.md) is complete for its three recipes. Do not rerun its confirmation pairs as unfinished work. |
| Solo public presets | Source comparison complete; retain controls and use accepted Speed Cocktail for its exact case | [Comparison](solo-cocktail-comparison-2026-09-21.md) found differences in references, surrounding prompt and diffusion precision, without isolating the cause. No blanket original-card fix follows. Other scenes retain their [coverage qualifications](../work/9b-readiness-resume-20260907/COVERAGE-MATRIX.md). |
| Source-preserving Upgrade | Second genuine-source check complete; retain both controls and new result | [Balcony test](../work/upgrade-generalization-20260921/RESULT.md) passes the fixed visual/source-excluded gates. Coverage is now two genuine photos, not universal enhancement or stronger High. |
| Stronger High | Hold all unique weights and evidence; no repeat grids | The [native/BeautyGRPO work](upgrade-high-resume-2026-09-07.md) and [explicit-feature refinement](upgrade-high-explicit-features-2026-09-07.md) did not achieve the requested improvement. Require a changed, supported mechanism before another experiment; do not declare High complete. |
| LaTo | Hold the full 47.715 GiB of candidate weights | The [predictor failure](../work/9b-readiness-resume-20260907/lato-compat/ROOT-FINAL-PREDICTOR-RESULT.md) closes its tested source/recipe. Later image stages are unexecuted. [Disposition review](../work/final-validation-20260921/DISPOSITION.md) confirms external-landmark driving is a distinct supported possibility, but has no admitted geometry for this case. Retain assets; do not advance failed predictor points. |
| General Group likeness | Hold identity models, genuine references and failed/accepted controls | The [masked refinement](../workflows/experiments/group-masked-strength110-20260908/ROOT-RESULT.md) is closed. A future mechanism must address main likeness and preservation of all other people. No further strength sweep or new character training follows from this cleanup. |
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

This is a same-drive recovery snapshot, not protection against losing the computer or
disk. No external backup destination has been selected and nothing was uploaded.
The large installed/held models remain only where they already existed unless another
backup exists independently; this archive does not claim to back them up.

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
