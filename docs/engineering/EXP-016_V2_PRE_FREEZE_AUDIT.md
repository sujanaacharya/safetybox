# EXP-016 Protocol@2 pre-freeze audit

**Audit ID:** `EXP-016-V2-PRE-FREEZE-AUDIT@1`

**Input SHA:** `97cf8bfc7bc196fc8c7704ba924ee7dae34efc9a`

**Date:** 2026-09-25

**Decision:** `FREEZE_READY`

## Scope and integrity

This audit covers governance and experiment-side specification only. No held-out scenario,
label, prediction, native child invocation, ProcessAdapter held-out invocation, or
`results/EXP-016` artifact was created. The existing Protocol@1, process implementation,
monitor, native helper, reachability oracle, EXP-015 artifacts, and results remain unchanged.

Protocol@1 is retained as `VALID_BUT_INSUFFICIENT_FOR_CORPUS_AUTHORSHIP`.
Protocol@2 is a prospective successor for future corpus work; it promotes no claim and
leaves RTM at RTM-1.

## Defect resolution

| Defect | V2 resolution | Mechanical evidence |
|---|---|---|
| Empty frozen family registry | Definition-only registry plus separate population model | Positive disposable join leaves definitions byte-equivalent |
| Frozen scenario count zero | `frozen_corpus_count=null` in `PLANNED` and `MATERIALIZED` | Planned zero-current-state accepted; frozen zero rejected |
| Strict-prefix spawn failure rejection | Typed partial-order lifecycle | Same truthful state rejected by v1 and accepted by v2 |
| Adapter-shaped direct control | Independent direct lifecycle with adapter fields `NOT_APPLICABLE` | Direct success accepted; fabricated adapter fields and route confusion rejected |

## Lifecycle coverage

Synthetic raw observations cover exit-zero success, executable rejection, cwd rejection,
preaudit attempted failure, confirmed-no-child spawn failure, indeterminate spawn, nonzero
exit, signal, timeout, capture failure, terminal-audit failure, authorization denial,
authorization failure, and direct-control success.

Invalid tests reject child creation without successful spawn, child completion without
creation, spawn without successful adapter prerequisites, direct controls with adapter
state, mismatched route/dispatcher, invalid repeat cardinality, and family-route mismatch.
Unknown child/effect state remains `INDETERMINATE`.

## Population, scoring, and joins

The planned total is 120; exact family counts and membership remain `NOT_YET_FROZEN`.
Family definitions contain all 20 canonical families and no scenario IDs. Every metric has
explicit route applicability and requires a positive denominator. Zero is
`NOT_EXERCISED`, negative cardinality is invalid, and `NOT_APPLICABLE` is excluded rather
than passed.

Requirement and threat mappings are definition-level only until future membership freezes.
REQ-035, REQ-047, and REQ-061 remain explicitly unclaimed. Network, descendants, process
trees, TOCTOU, shell routes, resource exhaustion, privilege, authenticated identity, and
broader inherited-descriptor behavior remain non-evaluated boundaries. The repeat
normalization projection is unchanged from v1.

## Raw/production separation

The raw record contract contains route and observed production/runner facts but prohibits
expected lifecycle, family, denominator, repeat, requirement, threat, and prediction fields.
The independent v2 oracle imports no `safetybox.process` implementation. Production code is
not changed; lifecycle derivation occurs after raw completion and before scoring-label join.

## Adversarial review

| Attack question | Result |
|---|---|
| Can terminal audit require impossible earlier success? | No; only an applicable terminal outcome is required, and spawn-failure regression passes. |
| Can a child exist without successful spawn? | Rejected. |
| Can DIRECT_CONTROL satisfy adapter metrics? | No; metric routes are disjoint where semantics differ. |
| Can failed spawn look not attempted? | No; statuses are distinct. |
| Can unknown become false? | No; indeterminate spawn/child/effect has a dedicated valid path. |
| Can planned, materialized, and frozen counts be confused? | No; transition invariants and null frozen count are tested. |
| Can definitions mutate when instances are added? | Synthetic positive population leaves definitions unchanged. |
| Can an empty corpus pass? | No; all metrics and overall success require positive applicable denominators. |
| Can route mismatch be hidden? | No; family route, runtime route, and adapter-used observation must agree. |
| Can `NOT_APPLICABLE` score as pass? | No; it is excluded and non-passing. |
| Can terminal failure become authorization failure? | No; registered paths and typed terminal fields are distinct. |
| Can the model hide indeterminate effects? | No; coercion is a contract failure. |

No unresolved validity blocker was found.

## Known limitations

- This is infrastructure evidence, not held-out execution evidence.
- Direct controls currently register only the intended successful boundary-control path.
- Future runner completeness and raw/label process isolation must be audited at corpus and
  pre-run freeze.
- Exact family counts, scenario membership, and denominators are intentionally deferred to
  pre-authorship corpus design freeze.
- The unchanged physical oracle still requires corpus-side supplemental checks for effective
  cwd permissions, mount executability, loader availability, isolated invalid-fixture
  defects, and the distinct ignore-TERM smoke class.
- The frozen helper observes only its registered selected environment keys; no broader
  environment-absence claim is permitted.

## Validation record

| Gate | Result |
|---|---|
| Focused v2 tests | 26 passed |
| Applicable full pytest | 673 passed, 2 frozen EXP-015 pre-run lifecycle nodes deselected |
| Coverage | 94% overall; v2 lifecycle module 90% |
| Ruff | PASS |
| mypy strict `src` | PASS, 69 source files |
| JSON parsing | PASS |
| `git diff --check` | PASS |
| EXP-015 raw checksums | PASS |
| EXP-016 helper checksums | PASS |
| Historical v1 byte-integrity regression | PASS |
| V2 checksum manifest | GENERATED_AND_VERIFIED_BEFORE_COMMIT |

The two exact EXP-015 deselections are the established post-run lifecycle dispositions for
the frozen pre-run absence/import-isolation assertions. The remaining fresh-process
negative isolation gate passed. No EXP-015 file was modified.

## Freeze decision

Every Protocol@2 governance condition is satisfied. V2 is freeze-ready as experiment
infrastructure only. This decision does not authorize held-out execution or claim promotion.
