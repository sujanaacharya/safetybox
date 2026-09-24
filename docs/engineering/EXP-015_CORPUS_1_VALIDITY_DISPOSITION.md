# EXP-015 Corpus@1 Validity Disposition

**Disposition ID:** `EXP-015-CORPUS-1-VALIDITY-DISPOSITION@1`
**Date:** 2026-09-24
**Governance HEAD at audit:** `22cd5562d7a5d1be3b56706a2adad2c54d7609c6`
**Protocol / implementation / corpus freezes:** `1b1d22eaded580e9b6f6311bf0e3a8145002e98d` / `12c585a9830436d8a88d356cfecbdff132b55487` / `ba433ee21e66813ac30d966bf2f4880bb3897f53`

## Disposition

`EXP-015-CORPUS@1` is **`INVALID_AS_FROZEN`** and is retired as
**`RETIRED_PRE_EXPOSURE_INVALID_RUNTIME_MATERIALIZATION`**. Preserve it in place,
including its original freeze commit, as an auditable failed corpus design. It must not
be silently repaired, run, or relabelled as a valid registered corpus.

`EXP-015-RUN-001` is **`NOT_STARTED_UNSPENT`**. No canonical evaluation occurred:
there was no held-out `ProcessAdapter` invocation, prediction exposure, raw record, or
`results/EXP-015` directory. The audit read frozen corpus artifacts, including the
separate labels solely to reconcile metadata; it did not load labels into a runner or
join them to any prediction. Prediction exposure count and adapter exposure count are 0.

The frozen adapter has **`NO_PREDICTION_CONTAMINATION`**. A future author knows this
design failed (authoring-knowledge contamination only), but no adapter behavior was
exposed. A newly held-out `EXP-015-CORPUS@2` remains permissible if authored without
adapter execution, prediction access, or tuning.

## Reproduction and pair reconciliation

The worktree was clean at audit start and `results/EXP-015` was absent. The protocol,
implementation `src/`, and corpus tree were byte-identical to their stated freezes.
The corpus has 120 scenario objects, all with the same fixture declaration:

```json
{"type":"heldout_probe","mode":"frame"}
```

| Artifact | Frozen fact |
|---|---|
| `manifest.yaml` | `pair_count: 22`, `strong_pair_count: 16` |
| `PAIR_AUDIT.md` | 22 declared pairs; 16 strong authority-only pairs |
| `labels.json` | 42 non-null `pair_id` entries across 26 distinct IDs |
| `build_corpus.py` | creates 32 two-member `PAIR-01`–`PAIR-16` references, four singleton `PAIR-B` references, and six singleton `REPEAT` references, while hard-coding 22/16 in the manifest |
| `scenarios.json` | contains no pair registry or pair metadata |

The historical “42 pair metadata entries” means **42 scenario-level label references**,
not 42 pairs. The manifest-declared frozen count is 22, but it is not mechanically
supported by a canonical registry. There is no internally coherent authoritative pair
definition. This is **`MULTIPLE_PAIR_DEFINITIONS`** (with reporting/generation defects),
not evidence for 42 pairs. Future references may call 22 “manifest-declared,” never
“verified pairs.”

## Runtime self-sufficiency audit

Every runtime scenario must contain every non-label fact needed to deterministically
materialize its initial state and request. A materializer may use the request, explicit
fixture/helper specifications, and explicit failure injection. It must not use labels,
expected authorization/validation/terminal class, quality tags, pair classification,
scenario-ID semantics, or hidden lookup tables keyed by them.

This is already required by the frozen protocol: it says runner-private state may not
fill gaps, prohibits a corpus-specific runtime branch, requires paired cases to fix
fixture state, and joins labels/expected terminals only after raw-record persistence.
Protocol impact is **`PROTOCOL_ALREADY_REQUIRED_IT`**. A Corpus@2 schema convention can
make this mechanically testable; no frozen protocol semantic change is needed.

| Classification | Count |
|---|---:|
| `SELF_CONTAINED_EXECUTABLE` | 0 |
| `UNDER_SPECIFIED` | 120 |
| `AMBIGUOUS` | 0 |
| `CONTROL_ONLY` | 0 |

The common fixture does not describe a helper path/object, executable mode, cwd object,
parent environment, helper behavior, marker/sentinel, failure seam, or direct-control
route. Supplying these from an ID, label, family, expected terminal, pair metadata, or
runner-private table is prohibited hidden evaluation state. The six intended PMED
boundary controls have no runtime route declaration and are under-specified too.

All 16 validation cases (`PMH-015-073`–`PMH-015-088`) are `UNDER_SPECIFIED`. Labels say
`REJECTED`, but no runtime record distinguishes missing, symlink, directory,
non-regular, non-executable executable states or missing, symlink, non-directory cwd
states. All 12 execution failures (`PMH-015-089`–`PMH-015-100`) are also
`UNDER_SPECIFIED`: labels assign nonzero, timeout, signal, or indeterminate behavior,
but runtime data specifies no exit code, sleep, signal, helper mode, injection stage, or
injection mode. Corpus@1 is therefore not partly valid: it is **`INVALID_AS_FROZEN`**.

## Fixture facts versus labels

Valid runtime facts create conditions, rather than predict outcomes:

```yaml
fixture:
  executable: {kind: symlink, path: bin/tool, target: bin/real-tool}
  cwd: {kind: directory, path: cwd/work}
  helper_behavior: {kind: exit_code, code: 17}
  failure_injection: {stage: POST_SPAWN_AUDIT, mode: RAISE}
```

Invalid runtime data includes `expected_validation: REJECT`,
`expected_terminal: FAIL_INDETERMINATE`, authorization ground truth, hard-benign or
hard-unauthorized tags, `case_family: timeout_failure`, or an ID dispatch that creates a timeout.
“Inject at POST_SPAWN_AUDIT” describes a condition and is valid; “expect fail
indeterminate” is scoring-side and is not.

## Corpus@2 corrective policy

Create `EXP-015-CORPUS@2`; do not reuse Corpus@1's identity or run. Preserve the frozen
adapter, research question, authorization emphasis, and false-allow/false-deny metrics.
Use opaque IDs, separate labels, no predictions, no adapter execution, and no tuning.

Before bulk authorship, freeze a non-held-out schema/materializer proof for normal,
missing, symlink, non-executable, and directory executable states; directory, missing,
symlink, and non-directory cwd states; nonzero exit, timeout, signal, injected failure,
and direct control. Do not execute the frozen adapter in this proof.

```yaml
scenario_id: opaque-id
route: ADAPTER_ROUTED # or DIRECT_CONTROL if protocol permits it
request: {session_id: ..., task_id: ..., request_id: ..., actor: ..., executable: ..., argv: [...], logical_cwd: ..., timeout_ms: ...}
task_contract: {task_id: ..., capabilities: [...]}
fixture:
  executable: {kind: regular|missing|symlink|directory|non_regular, path: ..., mode: ..., contents: ..., symlink_target: ...}
  cwd: {kind: directory|missing|symlink|non_directory, path: ..., mode: ..., symlink_target: ...}
  helper_behavior: {kind: exit_code|sleep|signal|frame, code: ..., duration_ms: ..., signal: ...}
  environment_parent: {variables: {...}}
  failure_injection: {stage: PRE_EXECUTION_AUDIT|POST_SPAWN_AUDIT|..., mode: RAISE|...}
  observations: {marker_paths: [...], sentinel_ids: [...]}
```

This runtime schema has no expected outcome, label, pair strength, authorization ground
truth, or quality flag. A corpus-side materializer consumes only this object to create an
isolated temporary root, helper artifact, executable/cwd objects, environment, and fault
configuration. The runner must be generic:

```text
runtime scenario -> materializer -> ProcessRequest / TaskContract -> route -> raw result
```

No ID, label, family, or expected-terminal branch is permitted. Direct controls declare
their route in the runtime object; route is an execution path, not an authorization label.

Materialize every Corpus@2 scenario at least twice before freeze, without adapter
execution, inspect each via an independent fixture oracle, then destroy it. The oracle
derives state from runtime data alone: `symlink` means `lstat` symlink; `missing` means
absence; `non_executable` means regular with no execute bit; `exit_code: 17` means the
helper configuration encodes 17.

Mechanical gates must prove that materializer imports neither labels nor scoring modules,
and that materialization/runner phases cannot open labels, pair metadata,
authorization-quality reports, or expected results before raw persistence. Validate every
fixture/helper/failure mode, prohibit hidden ID dispatch, reject exact DEV-PROC duplicates
and any exact Corpus@1 reuse retaining this invalid fixture shape.

Use one scoring-side pair registry only:

```yaml
pairs:
  - {pair_id: ..., scenario_a: ..., scenario_b: ..., changed_dimension: ..., strength: STRONG|...}
```

Generate manifest counts from scenarios, labels, and this registry; never manually type
them. Tests recompute scenario, class, quality, strong-pair, and pair counts.

Improve quality before any prediction exposure, not based on adapter behavior: target
about **60/60** authorization positive/negative, at least **32 hard benign**, at least
**32 hard unauthorized**, and at least **30 substantive strong authorization pairs**.
At least half of authorization-positive cases should be `EDGE_CASE` or `HARD_BENIGN`.
Preserve suspicious benign argv, compound/multiple-capability and task-binding cases, and
validation/execution-failure separation. Strong pairs change only authorization or task
binding while fixing fixture state. Static separability may expose fixture conformance but
must not make authorization labels trivial.

## Scientific status

This defect does not invalidate the frozen implementation. CL-011 remains `PROPOSED`;
there is no empirical EXP-015 conclusion. EXP-014 frozen evidence is untouched.
Corpus@1 remains an auditable failed design; Corpus@2 is permissible only after its
schema/materialization contract freezes and its pre-freeze gates pass.

**Exactly one next task:** Design and freeze the EXP-015-CORPUS@2 runtime scenario schema
and generic materialization contract, including self-sufficient fixture and
failure-injection specifications, before authoring the corrected held-out corpus.
