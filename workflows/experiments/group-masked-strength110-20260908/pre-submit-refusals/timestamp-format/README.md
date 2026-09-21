# Pre-submit refusal: root approval serialization

No prompt was submitted: terminal prompt_id null, empty live history and queues.
The initial root approval was assembled using PowerShell automatic date parsing,
which normalized creation timestamps to local-offset strings. These denote the
same instants but violated the intended exact six-field string check. The guard
correctly refused. This is a root record-formatting error, not an image/model
failure and not a reason to relax the comparator.

Root retained the rejected approval and entire unsubmitted attempt, and restored
the exact creation strings from the previously individually reviewed evidence.
A literal comparison now passes all22 desktop lifetimes and both parents. No
runtime, payload, resource threshold, expiry, PID or other identity field changed.
The same still-ready owned worker may receive its first and only prompt after
all preflight checks pass again. This is not an inference retry.
