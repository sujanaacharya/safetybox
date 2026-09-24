# EXP-013-CORPUS@1

`EXP-013-CORPUS@1` is the candidate held-out counterfactual multi-step corpus for the
frozen EXP-013 protocol. It contains 96 immutable scenarios:

- 80 primary scenarios: 40 history-required trajectory positives and 40 matched hard
  negatives;
- 40 complete strong counterfactual pairs;
- 8 partial-context controls; and
- 8 stale-context controls.

The six primary families are MS-A role accumulation, MS-B cross-source grouping, MS-C
ordered phase transitions, MS-D post-finalization collection, MS-E fallback
progression, and MS-F cross-phase interleaving. Every family has at least six complete
pairs. Primary pair members share the exact `TaskContext`, exact
`B4HistoricalConstraints`, local observation-evidence multiset, task category, and
context schema versions. The intended difference is an ordered or grouped historical
relationship.

## Files and isolation

`src/safetybox/experiments/exp013_corpus.py` contains experiment-only immutable input
definitions. Its runtime scenario objects contain no label, family, pair membership, or
rationale. `labels.yaml` is evaluator-side data and must not be passed to a detector.
`manifest.yaml` records frozen references and counts.

The module imports the frozen history-context schema and reference/validation helpers.
It imports neither B4 monitor code nor B4 rules. Corpus tests may execute frozen B2 for
the protocol-permitted parity audit. They do not execute B4.

## Primary qualification

All primary observations evaluate locally as `CONTEXT_CONSISTENT`. Every primary pair
reduces to `NEGATIVE` under frozen B2. Removing order, grouping, accumulated state,
phase state, finalization state, or fallback episode structure removes the declared
ground-truth distinction. See `COUNTERFACTUAL_PAIRS.md` and `B2_PARITY_AUDIT.md`.

## Controls

Partial-context controls intentionally require one history dimension while omitting its
supporting declaration. They are secondary abstention controls and are excluded from
primary TP/FP denominators.

Stale controls have two separate axes. Four carry a detectable TaskContext reference
mismatch and expect declaration-relative insufficient context. Four are internally
consistent with trusted declarations that are semantically stale relative to the
represented current task; their declaration-relative outcome remains consistent while
current-task truth is recorded separately. These cases do not define detector failure
when freshness is unrepresented.

## Audit boundary

The static audit uses deterministic contingency tables only; no model is trained. The
B2 audit is the sole detector prediction audit performed before corpus freeze. No B4,
M5.1-C, EXP-013 final evaluation, result directory, predictions, or performance metrics
are included.

The corpus remains a candidate until committed under the frozen references. A freeze
recommendation is recorded only after all checks in `FREEZE_CHECKLIST.md` pass.
