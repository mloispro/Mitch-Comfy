# Preservation and cleanup decisions

Reviewed September 21, 2026. Mitch asked to finish identifying unfinished work before
deleting its dependencies, then authorized the recommended next steps. The chosen scope
is a recoverable local checkpoint and a dependency inventory. No new generation,
training, worker restart, upload, model deletion or experiment retirement is part of
this checkpoint. Current image acceptance remains in [STATUS](STATUS.md).

## Retain and finish deliberately

| Route | Disposition | Next useful action / stopping point |
| --- | --- | --- |
| Original production and the three Production Speed workflows | Keep all dependencies and saved fallbacks | The [Speed release](../work/production-speed-rollout/RESULTS.md) is complete for its three recipes. Do not rerun its confirmation pairs as unfinished work. |
| Solo public presets | Pursue a bounded source comparison first; retain controls | Compare the [failed public Cocktail](../work/9b-readiness-resume-20260907/public-cocktail-parity/ROOT-RESULT.md) with the accepted Speed graph. Select one explained difference before any future image test. Other scenes retain their [coverage qualifications](../work/9b-readiness-resume-20260907/COVERAGE-MATRIX.md). |
| Source-preserving Upgrade | Retain Quality50 and Turbo8 controls; wider use remains open | A later bounded check on additional genuine sources must preserve source fidelity and use a source-excluded likeness cohort. The one-source Speed pass is not general approval. |
| Stronger High | Hold all unique weights and evidence; no repeat grids | The [native/BeautyGRPO work](upgrade-high-resume-2026-09-07.md) and [explicit-feature refinement](upgrade-high-explicit-features-2026-09-07.md) did not achieve the requested improvement. Require a changed, supported mechanism before another experiment; do not declare High complete. |
| LaTo | Hold the full 47.715 GiB of candidate weights | The [predictor failure](../work/9b-readiness-resume-20260907/lato-compat/ROOT-FINAL-PREDICTOR-RESULT.md) closes its tested source/recipe. Later image stages are unexecuted. Decide whether a separately justified author-supported alternative is worth pursuing before retiring unique assets. |
| General Group likeness | Hold identity models, genuine references and failed/accepted controls | The [masked refinement](../workflows/experiments/group-masked-strength110-20260908/ROOT-RESULT.md) is closed. A future mechanism must address main likeness and preservation of all other people. No further strength sweep or new character training follows from this cleanup. |
| VOSR | Hold unique weights pending an explicit retirement decision | The [completed enhancement study](../work/fast-detail-20260903/RESULTS.md) did not justify promotion. Preserve results; do not repeat the same enhancement recipe. |
| USO / WithAnyone 1.0 / PuLID | Tested routes closed; installed assets retained | [Screening results](identity-candidate-screening.md) establish bounded rejection, not failure of every future model/version. Audit shared encoders and installed optional nodes before removing a unique installed dependency. |
| St. Barts final image | Keep final PNG, original, masks, background and composition code | [Exact-foreground correction](../work/st-barts-exact-foreground-20260920/RESULT.md) is complete for pose preservation with qualified likeness. Actual gallery interaction remains unchecked; text-only generation does not inherit exact pose preservation. |

No unresolved route is silently marked complete or retired to obtain disk savings.
The next development priority is the Solo public-versus-accepted-recipe source
comparison, followed by bounded Upgrade generalization. High and broader Group
remain explicit research holds until a supported next mechanism is identified.

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
| `.downloads/models` | 30.404 GiB | 29.958 GiB verified duplicate copies; remaining USO adapter retained. Preserve all paths until direct, dynamic and frozen-runner dependencies are checked. |
| `work/upgrade-high-20260907/models` | 31.680 GiB | All four weights have identical installed copies. The BeautyGRPO runner loads installed paths from its receipt, but that alone is not a complete historical-path audit. Retain copies for now. |
| `work/9b-readiness-resume-20260907/lato-compat/models` | 47.715 GiB | Hold; no identical installed copy was established by this audit. |
| `work/fast-detail-20260903/vosr-runner/assets` | 6.494 GiB | Hold; no identical installed copy was established by this audit. |

These are logical file sizes, not a promise of physical space recovery. No files were
deleted or replaced with hardlinks. Before any future removal, recheck bytes and all
consumers of the exact path, preserve restoration information, and retain at least one
verified copy. Do not remove an entire `work` directory based on its total size.

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
in the archive manifest. All original files remain in place. Source/configuration and
curated gallery assets are preserved separately by a local Git checkpoint.

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
all-preset photo acceptance or the unperformed browser-interaction check. Engine files
and production workflow JSON are unchanged by this cleanup.

The checkpoint also checks Git's staged bytes, not only the working files. Default
newline conversion initially changed both pinned gallery text files and 98 frozen
experiment files in the index. Narrow [.gitattributes](../.gitattributes) rules preserve
those exact bytes and the archived reference-policy snapshot. The evaluated cache
module/test retain their existing EOF padding; only that whitespace diagnostic is
waived for those two files. No runtime source was reformatted to make an integrity
check pass.
