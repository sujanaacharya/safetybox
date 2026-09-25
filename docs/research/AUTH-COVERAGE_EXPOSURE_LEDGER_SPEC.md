# Authorization benchmark exposure ledger specification

**Specification identity:** `AUTH-COVERAGE-EXPOSURE-LEDGER-SPEC@1`

**Status:** reusable research-infrastructure design; not implemented

## Purpose

The exposure ledger is the authoritative append-only record of benchmark production
evaluation attempts. Its central rule is conservative:

> Once a production prediction is reserved, the scenario is treated as exposed whether or
> not the call completed or its output was persisted.

The ledger would have made the AUTH-COVERAGE-001 zero-exposure contradiction visible:
production-conformance tests evaluated HELD_OUT even though no result package existed.
AUTH-COVERAGE-001 remains `BLOCKED_BENCHMARK_LEAKAGE` and cannot become valid held-out
evidence. This facility applies prospectively; it does not rewrite historical provenance.

The ledger is reusable across authorization benchmarks. It is not a label store, result
scorer, audit log for ordinary application activity, or proof that uninstrumented code did
not run.

## Terminology

- **Prediction exposure:** a production component is invoked on a benchmark scenario, or a
  durable reservation is created immediately before such invocation. Reservation is
  deliberately counted even if invocation cannot later be proved.
- **Purpose:** why the evaluation was requested, such as `DEV_TEST`, `VALIDATION_REHEARSAL`,
  `HELD_OUT_CANONICAL`, `BASELINE`, or `ORACLE_DEBUG`.
- **Production component:** the exact registered policy/evaluator entry point being measured.
- **Reservation:** the irreversible pre-invocation event that consumes one attempt.
- **Prediction journal:** experiment-local raw input/output evidence. It is distinct from,
  and cross-linked to, this ledger.
- **Checkpoint:** an immutable digest commitment to a ledger prefix.

Reading a scenario without invoking a production decision component is access, not
prediction exposure; access controls should record it separately. Oracle execution is also
not production exposure, but its purpose and component type must be explicit so it cannot
masquerade as production. Any ambiguous component classification fails closed as production
exposure.

## Security and scientific properties

The design MUST provide:

1. append-only, durable, ordered events;
2. reservation committed before every registered production call;
3. exact experiment/corpus/split/scenario/component/implementation attribution;
4. one-attempt enforcement for one-shot tuples;
5. concurrent-writer serialization without duplicate sequence numbers;
6. detection of mutation, deletion, insertion, reordering, and truncated suffixes;
7. reconciliation with experiment-local raw prediction journals;
8. purpose-based denial of HELD_OUT in tests, tuning, debugging, and rehearsal;
9. no expected labels or correctness fields; and
10. queryable evidence for a mechanical zero-exposure gate.

The ledger cannot prove completeness while direct calls can bypass it. Therefore each
benchmark must register its production entry points, deny direct benchmark invocation,
and test that all authorized routes require a valid ledger reservation token.

## Logical event schema

Every event has the following required envelope:

| Field | Meaning |
|---|---|
| `schema_id` | exact ledger schema version |
| `event_id` | cryptographically random globally unique event identifier |
| `sequence` | globally monotonic committed event number |
| `event_type` | closed enumeration defined below |
| `recorded_at_utc` | trusted UTC recording timestamp |
| `writer_id` | registered ledger writer identity/version |
| `experiment_id` | experiment or benchmark identity |
| `protocol_id` | protocol version |
| `corpus_id` | corpus version |
| `split` | `DEV`, `VALIDATION`, `HELD_OUT`, or registered equivalent |
| `scenario_id` | opaque scenario identifier |
| `scenario_input_digest` | digest of label-free runtime input |
| `production_component` | stable component/entry-point identity |
| `implementation_sha` | exact tested implementation revision |
| `execution_purpose` | closed purpose enumeration |
| `run_id` | one-shot run identity or development run identity |
| `run_authorization_id` | trusted authorization for this execution |
| `reservation_id` | stable ID linking the pre-call reservation and later events |
| `process_identity` | host/container/process receipt digest, not a mutable display name |
| `raw_record_locator` | null until a raw record is committed |
| `raw_record_digest` | null until a raw record is committed |
| `outcome` | lifecycle outcome, never expected correctness |
| `previous_event_digest` | digest of the immediately preceding committed event |
| `event_digest` | digest of canonical event bytes |

The ledger MAY store tool class for operations reporting. It MUST NOT store expected final
or component labels, family, difficulty, pair identity, oracle decisions, correctness,
false-allow/false-deny status, or any label-derived value. Observed production decisions
belong in the raw journal; if duplicated in the ledger, only a digest may be retained.

## Closed event and purpose vocabularies

Version 1 event types are:

- `RUN_AUTHORIZED`: trusted gate authorizes a precisely identified run;
- `RUN_STARTED`: runner identity and environment are bound;
- `PREDICTION_RESERVED`: durable pre-invocation exposure boundary;
- `RAW_PREDICTION_COMMITTED`: raw record was synced and cross-linked;
- `PREDICTION_FAILED_AFTER_RESERVATION`: invocation or capture did not commit a valid raw
  record;
- `RUN_RAW_COMPLETE`: all frozen manifest members reconcile;
- `RUN_RAW_SEALED`: immutable raw receipt and ledger checkpoint recorded;
- `RUN_PARTIAL`: exposed run ended without a complete raw set;
- `RUN_SCORED`: scorer receipt recorded, with no metric values required in this ledger; and
- `INTEGRITY_INCIDENT`: append-only record of a detected inconsistency.

Version 1 purposes are `DEV_TEST`, `DEV_EXPLORATION`, `VALIDATION_REHEARSAL`,
`VALIDATION_LEAKAGE_PROBE`, `HELD_OUT_CANONICAL`, `BASELINE`, `ORACLE_DEBUG`, and
`INDEPENDENT_AUDIT`. A benchmark-specific policy maps allowed `(split, purpose,
component_type)` combinations. For AUTH-COVERAGE-002, the only production purpose allowed
on HELD_OUT is `HELD_OUT_CANONICAL`; baselines and oracle/audit execution use non-production
component identities and cannot call the measured production entry point.

Unknown purposes, components, or event types are rejected rather than accepted as free
text.

## Reservation protocol

The production wrapper requires a single-use reservation token. Its protocol is:

1. Validate run authorization, manifest membership, split/purpose policy, component
   registration, implementation SHA, and absence of an earlier reservation for the
   one-shot key.
2. In one durable transaction, allocate the next global sequence, append
   `PREDICTION_RESERVED`, update the hash chain, and mark the reservation consumed.
3. Commit and sync that transaction.
4. Return an unforgeable, process-bound token to the wrapper.
5. Invoke production exactly once. The wrapper rejects missing, reused, expired, or
   mismatched tokens.
6. Atomically sync the experiment's raw record.
7. Append `RAW_PREDICTION_COMMITTED` with the raw locator and digest, or append
   `PREDICTION_FAILED_AFTER_RESERVATION` if a controlled failure path remains available.

The reservation itself establishes exposure. No event can cancel it. A crash after step 3
and before step 5 may overcount exposure, which is scientifically conservative. A crash
after production invocation cannot undercount it. On recovery, an unmatched reservation is
reported as exposed with missing raw evidence and the run becomes
`PARTIAL_AFTER_PREDICTION_EXPOSURE`.

The unique one-shot key is at least `(protocol_id, corpus_id, split, scenario_id,
production_component, implementation_sha, execution_purpose=HELD_OUT_CANONICAL)`. A second
reservation conflicts before production is called. Changing `run_id` does not evade this
constraint.

## Durable storage and concurrency

The reference implementation SHOULD use a local transactional database with WAL or an
equivalent single-writer append service. Required semantics, rather than a database brand,
are normative:

- `sequence` allocation, uniqueness checks, event append, and chain-head update occur in
  one serializable transaction;
- the transaction is durably synced before the production wrapper receives a token;
- update and delete operations on committed events are denied by schema and application
  policy;
- concurrent writers either serialize successfully or receive a conflict before invoking
  production;
- a unique constraint prevents multiple HELD_OUT reservations for one one-shot key;
- idempotency is allowed only for resubmitting the byte-identical event ID after uncertain
  network acknowledgement; it cannot allocate a new reservation;
- unsupported filesystems or deployments without reliable locking/sync semantics fail the
  pre-run environment gate; and
- backup/replication never becomes a second writable authority.

AUTH-COVERAGE-002 version 1 executes predictions serially even though the ledger supports
concurrent experiments. This keeps scenario order and partial-prefix interpretation simple.

## Integrity and checkpointing

Canonical event encoding and domain-separated SHA-256 (or a frozen stronger successor)
bind each event to its predecessor. Hash chaining detects edits, insertions, and reorderings,
but a chain alone cannot detect deletion of its suffix. Therefore trusted checkpoints MUST
bind:

- ledger identity and schema;
- first and last sequence;
- event count;
- terminal event digest;
- database snapshot or canonical export digest;
- creation timestamp and checkpoint authorizer; and
- the prior checkpoint digest.

At minimum, checkpoints are emitted before run authorization, immediately after raw seal,
and with the final result package. Their digests are committed to a separate immutable
research manifest or trusted transparency location. A checkpoint failure blocks execution
or scoring. Integrity repair never deletes evidence; it appends an `INTEGRITY_INCIDENT` and
invalidates affected claims.

## Run and raw-journal reconciliation

For every frozen runtime manifest member, the reconciler requires exactly one reservation
and exactly one matching raw commit. It verifies scenario input digest, component,
implementation SHA, run identity, sequence order, raw record digest, and raw journal
cross-reference. It emits, without repairing:

- reservations without raw records;
- raw records without reservations;
- duplicate attempts;
- input or implementation mismatches;
- missing/out-of-order manifest members;
- ledger or raw hash-chain failures; and
- events after a terminal run state.

Any reservation means prediction exposure has begun. If reconciliation is not exact, the
canonical run cannot reach `RUN_RAW_COMPLETE`; the experiment state is
`PARTIAL_AFTER_PREDICTION_EXPOSURE` or an integrity-failure state. Missing predictions are
not imputed as denies, excluded, or rerun.

## Mechanical zero-exposure query

The pre-run gate is a versioned query over a checkpointed ledger prefix. Conceptually:

```text
count(events)
where experiment_id = target_experiment
  and corpus_id = target_corpus
  and split = HELD_OUT
  and production_component = target_component
  and event_type in {PREDICTION_RESERVED,
                     RAW_PREDICTION_COMMITTED,
                     PREDICTION_FAILED_AFTER_RESERVATION}
= 0
```

The gate also requires zero prior `RUN_STARTED` events for a HELD_OUT canonical production
run and no conflicting run authorization. The query output records predicate, checkpoint,
count, and verifier version. It passes only alongside wrapper-completeness evidence: static
entry-point registration, dynamic direct-call denial tests, purpose policy tests, and an
independent review. Absence from a ledger with bypasses is not absence of exposure.

## Access control and role separation

- Construction and scoring roles may read labels but cannot issue production reservation
  tokens.
- The runner role may read the runtime package and append ledger/raw events but cannot read
  labels or analysis metadata.
- The ledger authorizer may issue a run authorization only after a recorded independent
  gate; it cannot edit committed events.
- Development/test roles are mechanically denied production reservations for HELD_OUT.
- The reviewer reads checkpoints, manifests, and receipts but does not operate the measured
  implementation during the gate.

Credentials are short-lived and bound to purpose, corpus, split, component, implementation,
and run. Possession of scenario data is not authority to evaluate it.

## Prediction exposure ledger versus access ledger

Sealed-corpus reads should also be audited, but access and prediction exposure must not be
collapsed. A future companion access ledger may record artifact reads, exports, and label
access. This specification makes only the production-execution claim. If access records
show HELD_OUT copied into an uncontrolled environment, the independent gate may block the
run even when prediction exposure remains zero.

## Failure taxonomy

Ledger infrastructure reports at least:

- `RESERVATION_POLICY_DENIED`;
- `DUPLICATE_ONE_SHOT_RESERVATION`;
- `IMPLEMENTATION_IDENTITY_MISMATCH`;
- `MANIFEST_MEMBERSHIP_MISMATCH`;
- `DURABILITY_NOT_CONFIRMED`;
- `UNMATCHED_RESERVATION`;
- `RAW_WITHOUT_RESERVATION`;
- `RAW_DIGEST_MISMATCH`;
- `EVENT_CHAIN_FAILURE`;
- `CHECKPOINT_MISMATCH`;
- `UNREGISTERED_PURPOSE_OR_COMPONENT`; and
- `DIRECT_PRODUCTION_CALL_BLOCKED`.

These are infrastructure findings, not authorization outcomes. Fail-open behavior is
prohibited. If durable reservation cannot be confirmed, the production wrapper must not
execute.

## Required validation before use

An implementation is not trusted until tests demonstrate:

- concurrent reservation races yield exactly one winner for a one-shot key;
- process termination at every boundary around commit, sync, production return, raw append,
  and ledger cross-link produces the conservative state;
- a reserved-but-uninvoked call is still exposure;
- direct production calls without a token fail;
- DEV/VALIDATION purposes cannot be mislabeled to reach HELD_OUT production;
- mutation, deletion, insertion, reorder, truncation, checkpoint rollback, and raw-link
  substitution are detected;
- restart cannot reuse a reservation or change `run_id` to evade uniqueness;
- no schema field carries labels or label-derived metadata; and
- zero-exposure and reconciliation queries are deterministic and independently recomputed.

Tests use synthetic fixtures or DEV-only scenarios. HELD_OUT must never be used to prove
that HELD_OUT access controls work.

## Retention and publication

Ledger checkpoints and the minimal non-sensitive events supporting a published benchmark
are retained with its reproducibility package. Environment-sensitive process identities may
be committed as digests with a separately controlled mapping. Retention policy cannot
remove reservations needed to interpret one-shot exposure. Redaction creates a new derived
publication view; it does not alter the authoritative ledger.

## Limitations and non-claims

The ledger detects and prevents registered workflow violations; it does not observe an
unregistered evaluator, a copied corpus run outside the trusted boundary, or compromised
storage/authorizer infrastructure. Hashes prove consistency with committed bytes, not that
event fields were truthful. Clock time supplies correlation, not total ordering; the
transactional sequence is authoritative. The ledger does not prevent semantic label
leakage, prove oracle independence, or show authorization correctness. Those require
separate benchmark gates.

## Adoption sequence

For AUTH-COVERAGE-002, implement and adversarially test this facility before building or
freezing the corpus. Register every production authorization entry point, establish direct-
call denial, freeze purpose policies and queries, then rehearse crash behavior using only
synthetic/DEV inputs. Only after those gates pass may a new HELD_OUT corpus be sealed.
