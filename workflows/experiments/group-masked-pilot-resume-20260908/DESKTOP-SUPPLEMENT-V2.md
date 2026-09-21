# Exact desktop lifetime supplement — root review required

This separate route permits explicit review of two NEW desktop lifetimes, never
a name/PID-only exception:WUDFHost39712 and AMDRSSrcExt54788. The old20 candidate,
root parent/signature evidence, all18 fresh/193 historical pins, original41GiB
admission and every phase threshold remain. No process, worker, cache, payload,
production file, historical manifest or prior approval is changed.

`fresh-v2.ps1` preserves incoming CLI arguments across the original definition
import and retains complete original command signatures. Worker argv still uses
`extra-paths-v3.yaml`; the native installed guard and guard-ready SHA still bind
original `fresh_runtime.py`. Only verification and the observer launch use
`fresh_runtime_v2.py --watch --case pilot`; its desktop function is statically
bound to `wddm_admission_v2.py`. Start/run root-approval.json must additionally
name the exact `supplement_prepared_sha256` of prepared-v2.json.

Root commands, only after source/tests/pins review:

```text
pwsh -NoProfile -File ./fresh-v2.ps1 -Action verify
pwsh -NoProfile -File ./fresh-v2.ps1 -Action capture
```

Capture creates NEW `wddm-candidate-v2.json` once; no overwrite. It reuses the
original20 capture and independently queries the exact two new children plus
their two parents with complete PID,parent,name,creation,executable,argv fields.
New children remain `matches_prior_lifetime:false` and
`review_basis:explicit_new_lifetime`. Root must inspect the actual capture and
its SHA; this preparation does not fabricate a capture or an approval.

Root then writes a separate `wddm-root-approval-v2.json`, containing:

- `approved:true`, scope`GROUP_FRESH_V2_EXACT_DESKTOP_LIFETIMES`, actual
  `candidate_sha256`, timezone-aware`issued_utc`/`expires_utc` (maximum one hour).
- Exact `supplement_prepared_sha256`, `parent_evidence_sha256`,
  `prior_candidate_sha256`, and `wddm_helper_sha256`.
- `reviewed_processes`: all22 captured rows copied exactly. Only the two new
  rows additionally require `new_lifetime_approved:true`. Any null executable
  or argv additionally requires `protected_metadata_approved:true` for that row.
- `reviewed_parents`: both exact captured parent rows. The protected services.exe
  row requires its own explicit protected-metadata approval; nulls are not
  guessed paths or proof that inaccessible executable bytes were verified.

The fresh action approval remains a separate root document with all original
worker/payload/archive/control/expiry bindings, plus the supplement SHA. Root
decides each start/run/stop command individually; nothing automatically advances.

Live observer admission retains the exact original six-field comparison and
rejects new/reused PIDs, changed argv/executable/creation/parent, missing capture,
unapproved protected nulls or expired approval. Parent lifetimes are rechecked.
The immutable per-run `wddm-approval.json` additionally records helper path/SHA and
supplement SHA, so evaluation can identify the actual helper used. Watcher/runtime
success still does not establish image identity or Group visual acceptance.

Only offline regression tests were run during preparation. No live probes,
capture/approval writes, launch, stop, queue, GPU or cache action was performed.
