# EXP-016 route semantics v2

**Contract:** `EXP-016-ROUTE-CONTRACT@2`

## ADAPTER

The adapter route requires an observed generic `ProcessAdapter` dispatch. Authorization,
executable and cwd validation, preaudit, spawn, child/capture evidence, and terminal audit
are modeled according to their observed applicability. Adapter audit ordering,
authorization correctness, validation truthfulness, and adapter audit truthfulness use only
this route.

## DIRECT_CONTROL

The direct route uses the independent native runner with `shell=false` and requires an
observed `adapter_used=false`. Its lifecycle is limited to route selection, direct spawn,
child creation, child completion, and direct observation.

TaskContract authorization, ProcessAdapter validation, preaudit, ProcessAuditEnvelope, and
adapter terminal audit are `NOT_APPLICABLE`. They are neither false nor missing successes.
Any populated adapter field or observed adapter dispatch is route confusion and fails the
control.

The direct-control boundary metric uses only `DIRECT_CONTROL`. Adapter audit metrics use
only `ADAPTER`. Argv, output, and selected-environment observations may be compared across
routes only through separately route-aware denominators.

`NOT_APPLICABLE` is excluded from a metric denominator and cannot count as `PASS`.
