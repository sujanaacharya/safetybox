# EXP-016 corpus-authorship contract disposition

**Disposition ID:** `EXP-016-CORPUS-AUTHORSHIP-DISPOSITION@1`

**Date:** 2026-09-25

**Input freeze:** `97cf8bfc7bc196fc8c7704ba924ee7dae34efc9a`

## Decision

`EXP-016-PROTOCOL@1` is `VALID_BUT_INSUFFICIENT_FOR_CORPUS_AUTHORSHIP`.
It remains immutable historical evidence. It is not erased, rewritten, or interpreted as
having authorized a corpus.

`EXP-016-CORPUS@1` is:

- `NOT_AUTHORED`
- `NOT_FROZEN`
- `NOT_EXPOSED`

Held-out scenario count, held-out ProcessAdapter executions, and prediction exposure all
remain zero. `results/EXP-016` remains absent.

`EXP-016-PROTOCOL@2` is a prospective governance successor for future corpus authorship.
Versioning is scientifically clean because adversarial review found the inconsistencies
before any held-out input, execution, label exposure, or prediction existed.

## Root causes

### Definition/population conflation

The v1 family registry was both the only family definition registry and a frozen empty
instance registry. The v1 scorer likewise froze `held_out_scenario_count=0`. A later
nonempty corpus could not populate either artifact without rewriting history.

V2 separates immutable family definitions from separately frozen future corpus membership.
Before authorship, `frozen_corpus_count` is null/`NOT_YET_FROZEN`; zero describes only the
current number of materialized instances.

### Strict-prefix lifecycle error

V1 assumed every reached stage formed one success prefix. That model rejects a truthful
confirmed-no-child spawn failure: authorization and validation pass, preaudit commits,
spawn is attempted and fails, no child exists, and `EXECUTION_FAILED` nevertheless commits.

V2 uses typed statuses and route-aware partial-order dependencies. Terminal audit depends
on an applicable adapter terminal outcome, not on successful child creation or completion.

### Route-model conflation

V1 used an adapter-shaped funnel for `DIRECT_CONTROL`. A direct control deliberately has no
TaskContract authorization, ProcessAdapter validation, ProcessAuditEnvelope, or adapter
terminal audit.

V2 records these fields as `NOT_APPLICABLE`, requires `adapter_used=false`, and models only
direct route selection, direct spawn, child creation/completion, and direct observation.

## Production disposition

Review of `monitor.py`, ProcessAdapter, process audit bridging, primitive observations, and
failure classification found no separate production defect. No production file changes.
The correction is downstream:

`raw observations -> experiment lifecycle derivation -> scoring`

EXP-015 is not reinterpreted. RTM remains RTM-1, and no SafetyBox claim is promoted.

## Supersession

| Historical identity | Prospective successor | Scope |
|---|---|---|
| `EXP-016-PROTOCOL@1` | `EXP-016-PROTOCOL@2` | Future corpus governance only |
| `EXP-016-FAMILY-REGISTRY@1` | `EXP-016-FAMILY-REGISTRY@2` | Definitions only |
| `EXP-016-SCORING-CONTRACT@1` | `EXP-016-SCORING-CONTRACT@2` | Schema and derivation rules |
| v1 strict stage funnel | `EXP-016-REACHABILITY-MODEL@2` | Route-aware lifecycle model |
| v1 route declaration | `EXP-016-ROUTE-CONTRACT@2` | Independent route semantics |

All v1 files remain at their original paths and checksums.
