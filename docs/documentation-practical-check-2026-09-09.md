# Practical documentation check

Purpose: establish that the guides support correct development decisions, and distinguish that
from an unmeasured claim about total development speed. These are informed walkthroughs by the
documentation author, not blind or independently timed before/after trials.

| Representative question | Route and source verification | Outcome |
| --- | --- | --- |
| Hair polish touches neck: where should a regression investigation start? | ARCHITECTURE identifies ParseNet hair13/neck17; TESTING links the actual mask-entry-point test; code uses class13 in `build_semantic_hair_mask` | Correct implementation/test found. The existing test mocks parser logits while exercising production crop/normalization/resize; it is not a live parser/image validation |
| Why can a named Solo card ignore a manually selected reference profile? | ARCHITECTURE points to the resolver and Custom helper. `resolve_identity_profile` returns the preset's profile for named cards and the requested profile for Custom | Correct explanation without changing the generator or running an image. The UI suite covers helper conversion and profile retention |
| What optimization has concrete evidence without changing image generation? | OPTIMIZATION points to the raw-feature-reuse pilot and Group/Upgrade replay. Saved pilot receipt reports exact raw/report parity and 3→1 analyzer constructions | A supported future implementation candidate was retrieved. The old timing is one CPU observation, not proof documentation made this task faster |

Twelve existing hair/preset Python tests passed with the available plain `python` runtime,
and the visual-scene UI suite passed. The documented Comfy Python executable initially failed
to launch its uv child in the sandbox (permission denied); the alternative runtime passed the
CPU-only tests. No worker or dependency was changed. This is not a Comfy-runtime validation.

## Real issue found and fixed

The initial freshness check detected eight added/changed files in the separately progressing
Group-cache experiment. None were already watched by the current-status source review.
In particular, a new visual review and confirmation plan superseded its earlier progress-only snapshot.
Regenerating an index alone would not have required correcting that current conclusion.

`project-docs.py` now supports optional future-evidence globs. Current status, decisions and
optimization guides watch this experiment's Markdown, pair comparison receipts and prospective
release receipt. The new regression test starts with absent evidence, creates result/release files,
and confirms guide review remains required even after index refresh. Existing required `sources`
still fail if missing. Eight documentation-tool tests pass.

The three current guides were updated to the recorded initial-pair outcome and the unproven
confirmation/release status. No image acceptance was newly adjudicated by this documentation task.

## What would establish a development-speed gain

Use matched fresh-context tasks against the same frozen code: a bug diagnosis/fix, a small feature,
and an optimization proposal. Compare the previous documentation with the maintained guides using
the same tooling and task budget; alternate equivalent tasks/order to reduce learning bias.
Do not have this already-informed author solve the same task twice and call that a fair comparison.

Record time to the correct implementation/test/evidence, total time to a verified result, search/read
volume, incorrect edits/rework and required test outcomes. Grade proposals on a supported mechanism,
awareness of failed approaches, a falsifiable prediction and a bounded acceptance test. Separate
navigation time from implementation, GPU generation and manual image review.

Accept a speed improvement only when time to verified results falls while correctness and required
checks remain at least as good. A smaller first pilot gives preliminary evidence; consistency needs
additional tasks. These future trials have not been run or scheduled by this walkthrough.
