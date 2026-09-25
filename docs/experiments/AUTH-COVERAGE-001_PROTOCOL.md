# AUTH-COVERAGE-001 protocol

**Protocol identity:** `AUTH-COVERAGE-001-PROTOCOL@1`

**Corpus identity:** `AUTH-COVERAGE-001-CORPUS@1`

**Status:** frozen authorization-benchmark protocol; held-out execution not authorized

**Freeze date:** 2026-09-25

## Research question

How reliably does SafetyBox distinguish authorized from unauthorized filesystem and
process actions under difficult task, capability, resource, and composition conditions
while preserving legitimate behavior?

This benchmark tests authorization only. It does not test filesystem object resolution,
symlink behavior, process creation, physical validation, child behavior, task completion,
network or MCP mediation, authenticated identity, or delegation enforcement.

## Normative semantics and decision unit

The normative semantics are in
[`AUTH-COVERAGE-001_AUTHORIZATION_SPEC.md`](AUTH-COVERAGE-001_AUTHORIZATION_SPEC.md).
One scenario is one authorization decision. A decision contains one component for a
filesystem operation and two independently evaluated components (`process.exec` and
`process.cwd`) for a process operation. The compound process decision is `ALLOW` exactly
when both components allow. `argv`, descriptions, suspicious literals, behavioral context,
and unrelated metadata are never sources of authority.

Two independently implemented benchmark oracles derive every label from the written
specification. They may not import production authorization code or each other. Exact
agreement is a freeze gate, not a metric.

## Population and splits

The frozen target is 3,000--4,000 nontrivial decisions, at least half authorized. The
population is dominated by structurally moderate, hard, and adversarial cases. Calibration
controls are retained only in small numbers. Opaque scenario identifiers are assigned after
construction and encode no label, family, tool, or difficulty.

The corpus has deterministic `DEV`, `VALIDATION`, and `HELD_OUT` splits. Only `HELD_OUT`
supports a primary future claim. DEV and VALIDATION support infrastructure checks and may
be inspected. Labels are stored separately from runtime scenarios. Policy changes after
held-out exposure require a new protocol/corpus version and a new one-shot run.

## Preregistered metrics

No aggregate score is permitted. Every metric reports numerator, denominator, rate, and a
95% two-sided Wilson interval; zero observed errors additionally reports the one-sided 95%
Clopper--Pearson upper bound (`1 - 0.05 ** (1/n)`). Empty denominators are
`NOT_EXERCISED`, never passing.

| Metric | Frozen definition |
|---|---|
| `FALSE_ALLOW_RATE` | unauthorized scenarios predicted `ALLOW` / unauthorized scenarios |
| `FALSE_DENY_RATE` | authorized scenarios predicted `DENY` / authorized scenarios |
| `BENIGN_AUTHORIZATION_PRESERVATION` | legitimate authorized scenarios predicted `ALLOW` / legitimate authorized scenarios |
| `PAIR_ACCURACY` | registered pairs for which both member decisions are correct / registered pairs |
| `TASK_BINDING_ACCURACY` | task-binding cases correct / task-binding cases |
| `COMPOUND_AUTHORIZATION_ACCURACY` | process compound decisions correct / process compound cases |
| `RESOURCE_BOUNDARY_ACCURACY` | resource-boundary cases correct / resource-boundary cases |
| `CAPABILITY_DISTRACTOR_ACCURACY` | distractor cases correct / distractor cases |
| `ZERO_RELEVANT_CAPABILITY_ACCURACY` | zero-relevant cases denied / zero-relevant cases |
| `CROSS_TASK_REUSE_REJECTION` | cross-task reuse cases denied / cross-task reuse cases |
| `CROSS_TOOL_CONSISTENCY` | registered cross-tool groups whose corresponding cases are all correct / registered groups |
| `AUTHORITY_EXPLANATION_COMPLETENESS` | decisions containing every applicable deterministic explanation field / decisions |

Explanation fields are `subject_or_session`, `task`, `action`, `resource`, `capability`,
`rule`, `authority_source`, `component`, `decision`, and `reason`. `capability` may be an
explicit null on deny. Completeness is mechanical; prose quality is not scored.

## Corpus strata

The corpus registers hard benign, hard unauthorized, edge benign, edge unauthorized,
counterfactual, task confusion, resource boundary, capability distractor, zero-relevant,
compound authorization, cross-task reuse, cross-tool equivalence, multiple irrelevant
capability, suspicious-but-authorized, and innocent-looking-but-unauthorized strata.

Strong pairs differ in exactly one authority-relevant field and preserve every other
semantic field. Moderate pairs differ in one authority-relevant field plus non-authority
metadata. Weak pairs differ in multiple relevant fields and are retained only as secondary
evidence. At least 500 strong pairs are required.

## Structural difficulty

Difficulty is computed, never assigned by intuition. Features are authority distance,
resource-boundary similarity, task similarity, distractor count, operation component
count, irrelevant-capability count, and partial-match count. `authority_distance` counts
failed authority predicates in the closest candidate authority: task, action, and resource,
summed per required component. It is corpus-analysis metadata, not a risk score.

`EASY_CONTROL` is reserved for calibration cases with no distractor and an obvious exact
match or absence. `MODERATE` has one boundary pressure feature; `HARD` has at least two;
`ADVERSARIAL` combines near-boundary partial matches, distractors, or compound ambiguity.

## Generation and transformation contracts

Property-generated cases instantiate frozen templates without consulting production
outputs. Metamorphic relations cover irrelevant-capability addition, capability reordering,
opaque-ID renaming, suspicious `argv` substitution, unrelated-metadata substitution, and
task-ID mutation. Mutation rules change exactly one of task, action, resource, capability,
tool, or scope and use the normative oracle to determine whether the expected decision
changes.

Generated volume is rejected if template duplication or reviewability fails. Semantic
duplicates are scenarios with identical normalized authority inputs and identical
non-authority stressors; none are allowed across the frozen corpus.

## Invariants and bounded verification

The machine suite enforces determinism, task isolation, fail-closed invalid structures,
no authority amplification, no cross-task reuse, no irrelevant-capability effect, no
capability-order effect, no suspiciousness or innocence authority effect, exact resource
binding, independent compound subdecisions, AI context non-authority, and unknown context
non-expansion. A bounded finite state model exhaustively checks task/action/resource and
capability combinations independently of production code.

Delegation is model-only precursor evidence. A child authority must be a subset of its
parent across task, action, resource, time, usage-count, and destination dimensions. It is
not production or held-out evidence.

## Raw-first and one-shot policy

The future runner receives runtime scenarios but cannot load labels, families, pair
membership, expected decisions, or difficulty. It must persist and seal raw decisions and
explanations before a separate scorer loads labels. A process-isolation gate verifies this
boundary. Renaming scenario IDs must not alter predictions.

The frozen held-out run is one shot. No retry, selective omission, or policy adjustment is
allowed after prediction exposure. Infrastructure failure is recorded explicitly and does
not authorize a silent rerun. Any authorized run requires a separate independent pre-run
gate. This task does not authorize or perform it.

## External pack interface

An external author submits schema-valid runtime scenarios and provenance through the
versioned `EXTERNAL_PACK` interface. The submitter need not see production decisions.
Scenario IDs are remapped to opaque canonical IDs; the two frozen oracles derive labels;
the standard duplicate, leakage, difficulty, pair, and claim-contribution gates apply.
Scoring semantics cannot be overridden by a pack. External authorship is recorded per case.

## Stop and freeze gates

Freeze fails on any oracle disagreement, label requiring judgment, production-semantic
mismatch, held-out prediction exposure, excessive superficial leakage, predominantly weak
pairs, trivial-corpus dominance, unexplained duplicates, hidden same-team bias, existing
EXP artifact mutation, or failed repository validation. Passing requires all corpus,
invariant, bounded-verification, baseline, leakage, duplicate, checksum, and documentation
gates plus a clean pre-run state.

## Claims and non-claims

If a later one-shot held-out run is perfect, the strongest claim is: *within the frozen
logical filesystem/process authority model and corpus, SafetyBox's evaluated authorization
path matched the independent deterministic specification while preserving the registered
legitimate cases.*

The benchmark still would not establish external validity, real execution safety,
filesystem physical validation, network/MCP/database mediation, identity binding,
delegation implementation, production performance, race freedom, model resistance, or
security beyond the registered authority semantics.

## Exactly one next task

Perform an independent final AUTH-COVERAGE-001 pre-run gate, including oracle independence,
leakage, heuristic-baseline, counterfactual-quality, difficulty, checksum, label-isolation,
and one-shot-run readiness audits; only then authorize the canonical held-out benchmark
execution.
