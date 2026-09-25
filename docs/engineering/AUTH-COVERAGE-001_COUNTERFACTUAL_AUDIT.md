# AUTH-COVERAGE-001 counterfactual audit

**Audit ID:** `AUTH-COVERAGE-001-COUNTERFACTUAL-AUDIT@1`

**Scope:** frozen scenario and pair-registry structure only

**Held-out predictions:** not loaded or executed

## Purpose

This audit distinguishes a registered pair from an actual one-dimension
counterfactual. Pair membership alone is not evidence of counterfactual quality.
The independent audit implementation is
`experiments/AUTH-COVERAGE-001/audit/audit_core.py`; it imports neither corpus
oracle nor production authorization code.

## Frozen method

For each registry entry, the auditor:

1. resolves both opaque scenario IDs against `corpus/scenarios.json`;
2. recursively flattens both runtime-visible scenarios to RFC 6901-style JSON
   Pointer leaf paths;
3. ignores only `/scenario_id`;
4. computes the exact set of differing leaf paths, including array-length
   sentinels;
5. compares that set with `differing_paths`; and
6. assigns quality independently of the registered `strength`.

`STRONG` requires exact equality between actual and declared differing paths and
paths consistent with the named single authority dimension. Capability-presence
swaps and multi-capability splitting remain `MODERATE` even with exact path
registration because they intervene on multiple authority-object leaves.
`MODERATE` also includes cases where undeclared differences remain authority-
relevant but the pair is not a clean one-dimension intervention. `WEAK` includes
unexplained non-authority differences, missing operands, an empty intervention,
or invalid metadata.

The audit reports both registered and independently derived counts, all
disagreements, and counts by changed dimension. Freeze requires no invalid pair
and exact registered/derived strength agreement. No pair is silently upgraded.

## Authority dimensions

The registry may name `TASK_BINDING`, `ACTION_BINDING`, `EXEC_RESOURCE`,
`CWD_RESOURCE`, `FILESYSTEM_RESOURCE`, `CAPABILITY_PRESENCE`,
`CAPABILITY_SCOPE`, `COMPOUND_SUBDECISION`, `CROSS_TASK_REUSE`, or a frozen
future-compatible equivalent. Multiple leaf changes are permitted only when they
are the declared representation of one authority intervention, such as insertion
of one complete capability. Their exact leaf paths must still be registered.

## Interpretation limits

Exact structural matching shows that the pair changes only what the registry
declares. It does not by itself prove realism, semantic importance, production
correctness, or external authorship. Pair accuracy is later computed only after a
sealed raw prediction file exists and requires both pair members to be correct.

## Frozen result

**Result: PASS.** The canonical registry contains 1,800 pairs: 1,420 `STRONG`,
380 `MODERATE`, and zero `WEAK`. Independent derivation reproduced those counts
exactly, with zero invalid pairs and zero registered/derived disagreements. All
pair members remain in the same split. The largest dimensions are capability
presence (300), cross-task reuse (200), task binding (180), capability scope
(180), and filesystem resource (180); every registered dimension remains visible
in the machine-readable report.

The numeric result is frozen in
`experiments/AUTH-COVERAGE-001/audit/audit_report.json`. This construction audit
did not create a held-out prediction file.
