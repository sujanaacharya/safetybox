# AUTH-COVERAGE-002 partial-run semantics

`AUTH-COVERAGE-002-RUN-STATE-MACHINE@1` has an exhaustive transition table implemented in
`auth_coverage_state.py`. Tests attempt every unregistered source/target pair and require
failure without state mutation.

Before the first `STARTED`, an abandoned reservation reconciles to
`RESERVED_NOT_EXPOSED` and `ABORTED_BEFORE_PREDICTION`. After `STARTED`, every ambiguous
outcome is exposed. Missing raw becomes `EXPOSED_RAW_MISSING`; durable raw without a
completion event becomes `RAW_PRESENT_COMPLETION_EVENT_MISSING` and is completed only from
that raw record. Both post-call interruptions terminalize as
`PARTIAL_AFTER_PREDICTION_EXPOSURE`. Production is never called by reconciliation.

An interruption before even `RESERVED` terminalizes `CREATED`, `READY`, or
`RUNNING_UNEXPOSED` as `ABORTED_BEFORE_PREDICTION` without inventing a scenario attempt.
An interrupted `RUNNING_EXPOSED` run terminalizes as partial even when its most recent raw
record and completion event are individually complete; prediction execution never resumes.
Only an already durable `COMPLETED_RAW` state permits production-free seal finalization.

No canonical restart occurs at the failed scenario or at scenario one. A fresh held-out
runner detects prior run exposure, terminalizes an interrupted active state, and refuses.
Available evidence receives a partial, explicitly non-scorable manifest. Complete sealing
may be finalized idempotently after a sealing interruption from `COMPLETED_RAW`, but only
after full evidence revalidation; this is seal recovery, not prediction resumption.

All runner, sealer, reconciler, and scorer mutations share an exclusive per-run lock.
Reconciliation statuses are `CONSISTENT_COMPLETE`, `CONSISTENT_PARTIAL_AFTER_EXPOSURE`,
`INTERRUPTED_BEFORE_RESERVATION`, `RUN_INTERRUPTED_AFTER_EXPOSURE`, `RESERVED_NOT_EXPOSED`,
`EXPOSED_RAW_MISSING`, `RAW_PRESENT_COMPLETION_EVENT_MISSING`, `DUPLICATE_EXPOSURE`,
`HASH_CHAIN_INVALID`, `RUN_STATE_INCONSISTENT`, and `RAW_INVALID`.
