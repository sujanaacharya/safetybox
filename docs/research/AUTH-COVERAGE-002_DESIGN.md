# AUTH-COVERAGE-002 benchmark replacement design

**Design identity:** `AUTH-COVERAGE-002-DESIGN@1`

**Status:** preregistration design; no corpus, protocol, runner, or result is frozen by
this document

**Predecessor disposition:** `AUTH-COVERAGE-001-FINAL-PRE-RUN-GATE@1` returned
`BLOCKED_BENCHMARK_LEAKAGE`

| Predecessor record | Frozen value |
|---|---|
| protocol | `AUTH-COVERAGE-001-PROTOCOL@1` |
| corpus | `AUTH-COVERAGE-001-CORPUS@1` |
| reviewed freeze SHA | `fb894b2b5631632456f84884c64fc14aff40a536` |
| final gate | `AUTH-COVERAGE-001-FINAL-PRE-RUN-GATE@1` |
| gate decision | `BLOCKED_BENCHMARK_LEAKAGE` |
| final pushed gate SHA | `66adfb556fe60930e5213f76cf7a2f3e6cec8fc4` |

## Purpose

AUTH-COVERAGE-002 is the clean replacement for AUTH-COVERAGE-001. It will measure whether
the production authorization path distinguishes authorized from unauthorized filesystem
and process requests under task, action, resource, capability, and compound-operation
pressure. It is an authorization benchmark, not evidence of effect mediation, real-effect
correctness, authenticated identity binding, or global agent safety.

AUTH-COVERAGE-001 must never be reported as valid held-out evidence. Its frozen methodology,
formal artifacts, and failure analysis remain useful research evidence, but its public ID
construction reconstructs labels, its held-out cases were exercised by frozen production-
conformance tests, and its run path cannot provide complete reconstructable raw evidence.
The 002 corpus therefore MUST be newly generated. Relabeling, re-IDing, or re-splitting the
001 held-out cases cannot restore a held-out claim.

## Research question and bounded claim

**RQ:** Under a frozen logical authorization specification, how reliably does the frozen
SafetyBox production authorization path preserve legitimate filesystem/process authority
and reject requests outside the supplied task-scoped authority?

The strongest possible result is bounded to conformance within the frozen specification,
corpus, production implementation, and one-shot execution. Even a perfect result would not
show that every protected primitive is mediated or that an allowed operation caused the
intended real effect.

## Non-negotiable validity properties

The benchmark is not eligible to run until all of these properties have executable gates:

1. Runtime scenario IDs are uniformly random opaque values independent of labels and all
   scenario semantics.
2. DEV, VALIDATION, and HELD_OUT are separate artifacts with group-preserving allocation.
3. No production test, regression, tuning job, baseline, or oracle-debugging path can load
   or execute HELD_OUT.
4. The canonical runner and its lifecycle are frozen and validated before corpus freeze.
5. The production component receives only request, contract, capabilities, and tool inputs.
6. Every raw prediction is sufficient to reconstruct the exact authorization input and
   output, but contains no expected label or label-derived metadata.
7. Prediction exposure is durably registered before production evaluation and raw output
   is durably appended after every evaluation.
8. Scoring cannot begin until the raw journal is complete, sealed, and independently
   verified.
9. Error states, strata, denominators, and report queries are frozen as executable
   contracts before the one-shot run.
10. Any exposure followed by an incomplete run permanently yields
    `PARTIAL_AFTER_PREDICTION_EXPOSURE`; it never authorizes a restart.

## Artifact and trust separation

The implementation phase MUST create separately checksum-covered artifacts. Names below
describe roles rather than pre-allocating paths or freezing schemas.

| Artifact | Contents | May load HELD_OUT? | May load labels? |
|---|---|---:|---:|
| construction workspace | templates, seeds, semantic metadata, oracle inputs | construction only | yes |
| runtime split package | scenario UUID and authorization inputs | canonical runner only for authorized split | no |
| analysis package | family, difficulty, pair/group membership, claim tags | scorer after raw seal | yes |
| sealed labels | expected final and component decisions | scorer only | yes |
| canonical runner | runtime validation, production invocation, durable capture | only during authorized one-shot run | no |
| raw prediction journal | reconstructed input, observed decisions, explanations, provenance | produced during run | no expected labels |
| exposure ledger | reservations and exposure lifecycle | yes | no |
| scorer | raw/label join and frozen metric queries | only after raw seal | yes |

The generation artifact and runtime serialization MUST be separate. Removing label-only
fields from a combined object immediately before execution is insufficient isolation.
Runtime packages MUST NOT contain split names inside individual scenarios; split identity
belongs to the package manifest and exposure ledger. The runner harness may use
`scenario_uuid` for correlation, but the production authorization API MUST receive only:

- the request identity and requested components;
- the TaskContract identity and task binding;
- the complete serialized capability set;
- the tool-specific input needed to express the requested operation.

It MUST NOT receive family, difficulty, pair/group identity, expected final or component
decisions, oracle output, claim tags, authority distance, generator indices, or construction
seeds.

## Opaque identifier construction

Each scenario receives a 256-bit token from an operating-system cryptographic random number
generator, rendered in one frozen canonical encoding. Allocation is independent of label
creation, family assignment, split assignment, template position, tool, difficulty, pair
membership, and all seeds used for scenario semantics. IDs MUST NOT be hashes, keyed or
unkeyed, of bounded semantic inputs.

The ID allocator MUST:

- operate as a distinct step with no label argument and no semantic-input argument;
- reject collisions across the complete corpus and all prior 002 construction attempts;
- use a randomly permuted association table held only in the construction workspace;
- record allocator version and entropy source, but never random internal state;
- pass token, frequency, enumeration, nearest-neighbor, and public-generator attacks; and
- demonstrate that no public artifact can enumerate a bounded preimage space to recover
  labels.

Pair and group IDs are also opaque random identifiers stored only in analysis metadata.
Renaming any runtime UUID MUST leave the production prediction unchanged.

## Split construction and sealing

The benchmark uses `DEV`, `VALIDATION`, and `HELD_OUT`. Template roots, counterfactual
pairs, cross-tool groups, and other dependence groups are assigned atomically to one split.
No derived sibling may cross a split. Split membership is decided before label balance is
inspected; any permitted balancing procedure and its stopping rule must be preregistered.

The roles are:

- **DEV:** generator debugging, runner development, policy development, and exploratory
  analysis;
- **VALIDATION:** fixed pre-freeze gates, superficial leakage probes, and final runner
  rehearsal without policy tuning after results are observed;
- **HELD_OUT:** exactly one authorized production run after all freezes and an independent
  pre-run gate.

HELD_OUT is a sealed package with an access policy that rejects imports from production
tests, development regressions, policy tuning, oracle debugging, baseline training, and
interactive notebooks. The repository test suite MUST exercise synthetic runner fixtures,
DEV, or an explicitly designated rehearsal package—not HELD_OUT.

### Mechanical zero-exposure gate

Before the canonical run, a gate MUST establish all of the following mechanically:

1. The exposure ledger contains zero reservation or exposure events for the tuple
   `(AUTH-COVERAGE-002, frozen corpus, HELD_OUT, frozen production component)`.
2. No canonical run identity has previously been allocated for that corpus/split/component.
3. Tests prove HELD_OUT import denial for every registered development and test purpose.
4. Static dependency checks show the HELD_OUT package is referenced only by the canonical
   one-shot entry point and post-seal scorer.
5. The frozen run manifest, implementation SHA, runner digest, environment receipt, and
   corpus checksums agree.
6. An independent reviewer signs the gate disposition before run authorization is created.

An empty ledger is not, by itself, evidence of zero historical execution. The claim is
valid only after all benchmark production calls are forced through the ledger-enforcing
wrapper and bypass checks pass. Any evidence of an unledgered HELD_OUT production call is
a freeze blocker.

## Freeze order

AUTH-COVERAGE-002 reverses the unsafe dependency order exposed by 001:

1. Freeze normative authorization semantics and oracle-independence requirements.
2. Implement and freeze the exposure ledger interface and bypass gates.
3. Implement the canonical runner, prediction journal, state machine, raw schema, and
   scorer against synthetic fixtures and DEV-only data.
4. Freeze the error taxonomy, metric definitions, stratification queries, and lifecycle.
5. Complete runner fault injection, crash recovery, import-isolation, and process-isolation
   tests.
6. Generate a wholly new corpus; allocate opaque random IDs; assign and seal splits.
7. Produce independent oracle agreement, leakage, duplicate, pair-quality, and power audits.
8. Freeze protocol, corpus, labels, analysis metadata, production SHA, and manifests.
9. Obtain an independent final pre-run gate, including mechanical zero exposure.
10. Execute HELD_OUT once, seal raw evidence, then score in a separate process.

The corpus MUST NOT be frozen until steps 1--5 pass. Runner changes after corpus freeze
invalidate run authorization and require a new benchmark version unless the frozen protocol
explicitly classifies the change as non-semantic and an independent gate accepts it.

## Canonical execution process

There is exactly one versioned entry point from runtime package to raw journal. It launches
a label-blind process whose import allowlist excludes builders, oracles, labels, analysis
metadata, scorers, and HELD_OUT construction artifacts. The process verifies its own digest,
the production implementation SHA, the runtime package digest, and the ordered scenario
manifest before any prediction.

For each scenario in the frozen order, the runner MUST:

1. validate runtime shape without deriving truth;
2. durably append a `PREDICTION_RESERVED` exposure event and flush it;
3. invoke the registered production component exactly once;
4. construct the complete raw record in memory without consulting expected data;
5. atomically append, flush, and sync the raw record;
6. append a cross-linked `RAW_PREDICTION_COMMITTED` ledger event; and
7. advance durable run state only after both records are committed.

Reservation happens before invocation. It conservatively counts a prediction as exposed
even if the process crashes before the call. This prevents an evaluation from occurring in
the gap between output creation and exposure accounting. A reservation cannot be canceled
or reused.

Parallel HELD_OUT prediction is prohibited in version 1 of the runner. Serial frozen order
simplifies exact exposure accounting, compound explanation capture, and crash disposition.
The production component MUST NOT be reinvoked to fill a missing explanation or retry an
exception.

## Reconstructable raw prediction record

Each append-only record MUST include at least:

- schema ID, run ID, monotonically increasing sequence, previous-record digest, and record
  digest;
- opaque scenario UUID and input digest;
- tool class;
- subject and session identity;
- request task, contract identity, and contract task;
- every requested component with component name, action, resource, and tool input;
- the full ordered capability set, including capability IDs, actions, resources, scope, and
  every authority-bearing constraint represented by the frozen model;
- per-component authorization decision, matched capability or explicit null, authorizing
  rule, reason, and authority provenance;
- final decision, composition rule, and final reason;
- runner identity/version and production implementation SHA;
- process/environment receipt digest;
- monotonic order metadata plus UTC wall-clock timestamp for audit correlation; and
- exposure-ledger reservation ID and committed-event ID.

The complete record must let an independent reviewer reconstruct the exact serialized
authorization call and verify its output explanation. A digest alone is not a substitute
for any authority-bearing input. Raw records MUST NOT contain expected labels, expected
component decisions, family, difficulty, pair/group membership, claim tags, oracle fields,
or derived correctness/error classes.

## Durable journal and run state machine

The raw journal is append-only and exclusive-create. Every record is canonicalized,
length-framed or transactionally stored, hash-chained, committed atomically, flushed, and
synced before the next production call. A manifest checkpoint binds the committed prefix
length and terminal digest. Torn or unverifiable tails are preserved as evidence, never
silently truncated and resumed.

The frozen lifecycle has these terminally meaningful states:

```text
PREPARED_NOT_EXPOSED
  -> RUNNING_AFTER_PREDICTION_EXPOSURE
      -> RAW_COMPLETE_UNSEALED
          -> RAW_SEALED_UNSCORED
              -> SCORED_FINAL

PREPARED_NOT_EXPOSED -> FAILED_BEFORE_PREDICTION_EXPOSURE
RUNNING_AFTER_PREDICTION_EXPOSURE -> PARTIAL_AFTER_PREDICTION_EXPOSURE
RAW_COMPLETE_UNSEALED -> INTEGRITY_FAILURE_AFTER_PREDICTION_EXPOSURE
RAW_SEALED_UNSCORED -> SCORING_FAILURE_RAW_REMAINS_SEALED
```

Once the first reservation is durable, any premature termination, exception, timeout,
missing output, journal failure, order mismatch, or integrity ambiguity yields
`PARTIAL_AFTER_PREDICTION_EXPOSURE` (or the more specific post-exposure integrity state).
The exposed corpus/run combination is consumed. It cannot return to a pre-exposure state.

A genuine pre-exposure infrastructure failure may be repaired only if the ledger proves no
reservation exists and a new independent run authorization is issued. It is not a retry of
an exposed run.

## One-shot semantics and prediction ledger

The one-shot unit is the tuple of protocol, corpus, split, production component identity,
production implementation SHA, and run authorization. Exactly one prediction attempt per
HELD_OUT scenario is permitted. Bad results remain results. Selective omission, replay,
reordering, exception retry, explanation repair by reevaluation, and policy modification
after exposure are prohibited.

Two linked durable structures serve different purposes:

- the **exposure ledger** records that evaluation was reserved or may have occurred, even
  if no output survived; and
- the **raw prediction journal** records the actual input/output evidence when capture
  succeeded.

Their IDs and digests cross-reference each other. Reconciliation reports reservations with
no raw record, raw records with no reservation, duplicate scenario attempts, sequence
gaps, and mismatched implementation identities. Any mismatch blocks scoring; it is not
converted to `DENY` and not removed from the denominator.

The generic exposure-ledger design is specified in
[`AUTH-COVERAGE_EXPOSURE_LEDGER_SPEC.md`](AUTH-COVERAGE_EXPOSURE_LEDGER_SPEC.md).

## Raw-first scoring barrier

Scoring is a separate executable and process. Before it may import any label or analysis
artifact, an independent sealing step MUST verify:

- the run is `RAW_COMPLETE_UNSEALED`;
- scenario UUIDs equal the frozen ordered manifest exactly, with no missing or duplicate
  values;
- every input digest recomputes from the fully stored raw input;
- journal sequence and hash chain are intact;
- ledger reservations and raw commits reconcile one-to-one;
- runner, production SHA, environment, protocol, and corpus identities are constant;
- all required explanation and provenance fields are present; and
- no expected or analysis-only field appears in raw data.

The sealer then writes an immutable receipt containing raw digest, terminal chain digest,
record count, manifest digest, ledger checkpoint, and validation result. Only a fresh
scorer process receiving that receipt may load labels, pairs, families, or difficulty.
The scorer has no import or execution path back to production authorization. Failed scoring
may be repaired against the same sealed raw bytes; production predictions may not be rerun.

## Frozen error taxonomy

The implementation MUST encode the following categories as a versioned machine-readable
enumeration before corpus freeze. Categories are dispositions, not authorization decisions.
None may be silently mapped to `ALLOW` or `DENY`.

| Phase | Required category | Disposition |
|---|---|---|
| before exposure | `STARTUP_FAILURE_PRE_EXPOSURE` | terminal attempt; new authorization only after zero-exposure proof |
| before exposure | `INVALID_RUNTIME_INPUT_PRE_EXPOSURE` | corpus/freeze failure |
| evaluation | `PRODUCTION_EXCEPTION_AFTER_EXPOSURE` | partial exposed run |
| evaluation | `PRODUCTION_TIMEOUT_AFTER_EXPOSURE` | partial exposed run |
| capture | `RAW_PERSISTENCE_FAILURE_AFTER_EXPOSURE` | partial exposed run |
| capture | `INCOMPLETE_EXPLANATION_AFTER_EXPOSURE` | partial exposed run; no reevaluation |
| reconciliation | `MISSING_RAW_FOR_RESERVATION` | partial exposed run |
| reconciliation | `RAW_WITHOUT_RESERVATION` | integrity failure |
| reconciliation | `DUPLICATE_SCENARIO_ATTEMPT` | one-shot violation |
| reconciliation | `ORDER_OR_SEQUENCE_MISMATCH` | integrity failure |
| sealing | `RAW_CHAIN_OR_DIGEST_FAILURE` | integrity failure |
| scoring | `LABEL_JOIN_FAILURE` | scoring failure; raw remains sealed |
| scoring | `UNREGISTERED_STRATUM_VALUE` | scoring-contract failure |
| scoring | `EMPTY_REQUIRED_DENOMINATOR` | `NOT_EXERCISED`; cannot pass claim gate |
| correctness | `MATCH` | correct prediction |
| correctness | `FALSE_ALLOW` | unauthorized expected, observed allow |
| correctness | `FALSE_DENY` | authorized expected, observed deny |

Additional categories require a protocol version change; free-text replacement categories
are forbidden. The failure report preserves exception type/digest and phase without exposing
secrets or changing the category.

## Metrics and executable stratification

No aggregate score is permitted. At minimum, the frozen scorer separately reports
`FALSE_ALLOW_RATE`, `FALSE_DENY_RATE`, `BENIGN_AUTHORIZATION_PRESERVATION`,
`TASK_BINDING_ACCURACY`, `CROSS_TASK_REUSE_RATE`, `PAIR_ACCURACY`, and
`COMPOUND_AUTHORIZATION_ACCURACY`. Every rate includes numerator, denominator, point
estimate, a preregistered confidence interval, and a zero-error upper bound where
applicable. Infrastructure/error dispositions are reported separately and cannot improve
an authorization denominator.

Stratification is an executable contract, not a narrative promise. Before corpus freeze,
machine-readable queries MUST enumerate:

- tool class;
- expected outcome;
- DEV/VALIDATION/HELD_OUT package;
- final error category;
- registered family and conservative pair-quality class;
- structural difficulty and authority distance;
- task-binding and cross-task-reuse status;
- resource-boundary subtype;
- capability-distractor and zero-relevant-capability status;
- process compound quadrant (`AA`, `AD`, `DA`, `DD`);
- suspicious/ordinary semantic surface crossed with expected outcome;
- cross-tool group; and
- authority-explanation/provenance completeness.

Every query declares its population predicate, numerator predicate, expected nonzero
denominator, grouping unit, and whether it supports a primary or secondary claim. The
pre-freeze scorer runs every query against synthetic fixtures and DEV/VALIDATION. The
corpus audit verifies required HELD_OUT denominators without exposing labels or results to
the runner. Unknown enum values and unregistered cases hard-fail scoring.

Pair accuracy requires both members to be correct and is reported separately for strict
single-authority-dimension pairs, pairs with auxiliary non-authority changes, and weaker
diagnostic pairs. Compound accuracy reports final conjunction and both component decisions;
a correct final deny with a wrong component is not compound-correct.

## Required pre-run evidence

Run authorization requires all of the following, recorded with digests:

- independent oracle agreement and bounded formal checks;
- public-artifact ID reconstruction attack failure;
- runtime-field leakage baselines trained only on DEV and evaluated once on VALIDATION;
- duplicate/dependence audit and conservative pair-quality review;
- corpus power and denominator review for every primary stratum;
- process/import isolation and filesystem-access denial for labels and analysis metadata;
- crash fault injection after reservation, evaluation, append, flush, seal, and scoring;
- ledger/raw reconciliation and tamper tests;
- canonical runner rehearsal completed before corpus freeze;
- mechanical zero-exposure gate for HELD_OUT; and
- independent claim-pressure review preserving all non-claims.

## Stop conditions

Stop and issue a new version rather than patching the benchmark if an ID can be decoded,
any HELD_OUT production execution occurs before authorization, any expected field reaches
the runner, the runner cannot reconstruct a full input, an exposed prediction is not
durably accounted for, raw data are scored before sealing, taxonomy/strata are ambiguous,
or production semantics change after freeze. A partial exposed run is publishable failure
evidence, never a rehearsal.

## Implementation boundary

This document does not implement the corpus, ledger, runner, scorer, or policy changes.
Those artifacts require their own versioned schemas, tests, audits, freeze report, and
independent pre-run authorization. The immediate purpose is to fix dependency order and
make benchmark leakage and exposure mechanically detectable before any new held-out corpus
is allowed to support a claim.
