# EXP-016 scoring contract

**Artifact:** `EXP-016-SCORING-CONTRACT@1`

**Source of truth:**
[`scoring_contract.json`](../../experiments/EXP-016/contracts/scoring_contract.json)

## Denominators and no-vacuity rule

The scoring metadata separates:

- `AUTHORIZED_EXPECTED_TO_EXECUTE`
- `AUTHORIZED_EXPECTED_VALIDATION_REJECT`
- `AUTHORIZED_EXPECTED_FAILURE_SEMANTIC`
- `AUTHORITY_NEGATIVE_CONTROL`
- `DIRECT_CONTROL`

For every execution-semantic metric, a denominator of zero produces `NOT_EXERCISED`.
There is no empirical `PASS` without a positive denominator. This applies to argv,
environment, output, ordering, timeout, signal, child audit, benign completion, failure
seams, direct control, and repeats.

Overall success additionally requires the future corpus protocol to freeze a substantial
positive child minimum before the run. Until that number is frozen, overall execution
status is `NOT_EXERCISED`. Authorization-only evidence cannot satisfy EXP-016.

## Canonical family and reachability metadata

[`family_registry.json`](../../experiments/EXP-016/contracts/family_registry.json) is the
only family registry. Each future instance must have exactly one canonical family;
secondary tags may overlap. All family and headline counts are mechanically derived by
joining instance IDs to this registry. At this infrastructure freeze its held-out
instance list is empty and the held-out count is zero.

The preregistered
[`validation_reachability_matrix.json`](../../experiments/EXP-016/contracts/validation_reachability_matrix.json)
records expected authority, executable validation, cwd validation, spawn, child,
terminal class, and seam for every family. It is scoring metadata and must never be
copied into runtime scenario inputs.

## Truthful comparisons

Argv scoring decodes `E16A` frames and compares the ordered UTF-8 bytes exactly. No-shell
cases include literal `; rm -rf /`, `$(whoami)`, backticks, `&&`, `||`, `|`, `>`, and
`<`; a match is execution evidence, not authorization evidence.

Environment scoring decodes the child frame and demands exactly `LANG` and `LC_ALL` with
the frozen values and registered absence of `PATH`, `HOME`, and
`EXP016_PARENT_SECRET`.

Output scoring compares retained bytes, retained length, full byte count, independently
computed full-stream SHA-256, and truncation. Registered regions are empty, just below,
exactly at, just above, and comfortably above 65,536 bytes while remaining helper
bounded.

Audit scoring keeps field completeness separate from semantic truthfulness. Truth is
compared with instrumented primitive snapshots, child frames, OS return state,
an independently sampled wall-clock bracket at primitive entry and child observation,
independent hashes, marker bytes, and required-sink event order. Session-local sequence
remains ordering authority; the wall clock is corroborating evidence only. Ordering
claims require a positive spawned denominator.

## Repeat projection

`EXP-016-REPEAT-PROJECTION@1` may normalize only named ephemeral fields: temp root, PID,
timestamps, durations, event/parent IDs, and child token. Semantic argv/environment
frames, route, decision, terminal class, exit/signal/timeout state, logical cwd, marker
content, and output count/hash/truncation remain exact. Any undeclared difference fails.

Before the run the repeat set must include representatives for success, argv,
environment, nonzero exit, timeout, validation rejection, denial, and direct control.
Development proof operands cannot be reused exactly.

## Requirement, threat, and claim mapping

The machine-readable requirement mapping cites only the applicable subset of
REQ-033–062. REQ-035 is a trust assumption, REQ-047 is a descendant boundary, and
REQ-061 has no correctness threshold, so they are not claimed as tested. The threat
mapping marks network, descendants, process-tree escape, TOCTOU, shell routes, resource
exhaustion, privilege changes, identity binding, and broader descriptor inheritance as
expected boundaries/not evaluated.

All candidate claims in `candidate_claims.json` are `PROPOSED`. This freeze cannot
promote them.
