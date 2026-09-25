# AUTH-COVERAGE-002 raw-first execution protocol

**Protocol:** `AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1`  
**Substrate:** `AUTH-COVERAGE-002-EXECUTION-SUBSTRATE@1`  
**Status:** preregistered and frozen before corpus authorship  
**Held-out scenarios authored:** **0**  
**Held-out prediction exposures:** **0**

## Scope and scientific boundary

This protocol freezes the instrument that will later measure production authorization. It
does not create a corpus, labels, or an AUTH-COVERAGE-002 empirical result. The production
policy remains benchmark-agnostic; the research wrapper calls the normal public
`TaskContractPolicy.authorize` path and never adds benchmark rules to that policy.

The canonical runner sees only an opaque correlation ID, tool class, request/session/actor
fields, contract identity and description, the complete capability sequence as received,
and ordered compound component requests. It rejects expected decisions, family,
difficulty, pair, oracle, authority-distance, error-class, scoring-class, and split-
derivation fields. Split identity exists only in the sealed package/run manifests and
ledger binding.

## Frozen identities

| Instrument | Identity |
|---|---|
| production runner | `AUTH-COVERAGE-002-RUNNER@1` |
| generic exposure ledger | `AUTH-COVERAGE-EXPOSURE-LEDGER@1` |
| raw schema | `AUTH-COVERAGE-002-RAW-SCHEMA@1` |
| state machine | `AUTH-COVERAGE-002-RUN-STATE-MACHINE@1` |
| error taxonomy | `AUTH-COVERAGE-002-ERROR-TAXONOMY@1` |
| metric contract | `AUTH-COVERAGE-002-METRIC-CONTRACT@1` |

No corpus identity or held-out label identity is allocated by this freeze.

## One-shot execution

The run manifest binds protocol, corpus/split package checksums, exact ordered scenario
IDs, a canonical authorization-input digest for every scenario, production Git SHA and
source checksums, policy/TaskContract/spec versions, runner version/checksum, raw and ledger
versions, environment metadata, and sequential order. Package manifests have an exact
label-free schema; the corpus manifest must physically reside in the validated runtime-only
directory.

For each scenario the exact durable order is:

1. validate the runtime object and its frozen canonical input digest;
2. append and fsync `RESERVED`;
3. immediately before production, append and fsync `STARTED`;
4. durably cross `RUNNING_EXPOSED`;
5. consume the in-process single-use permit and invoke production once;
6. serialize the complete raw record, append, flush, and fsync it;
7. append and fsync `COMPLETED`, or truthfully record `FAILED_AFTER_CALL`.

`STARTED`, not reservation, is the conservative prediction-exposure boundary. A crash
after reservation but before `STARTED` is `RESERVED_NOT_EXPOSED`. Any uncertainty after
`STARTED` is exposed. A raw-write failure cannot restore an unexposed state or permit a
retry. The held-out ledger reservation atomically binds the entire experiment/corpus/
split/component scope to its first run ID, closing the two-run zero-gate race.

The canonical entry point is `scripts/run_auth_coverage_002.py`. It requires a fresh
output set, requires the runtime inventory to equal exactly the four frozen files (run
manifest, runtime binding, corpus binding, and scenario array), installs the scoring/oracle
import and ordinary-file audit gates,
sets the canonical-process attestation, consumes frozen order sequentially, and seals raw
evidence. A new runner object refuses an already-exposed held-out run and terminalizes an
interrupted active run; it never silently resumes.

## Failure and partial-run semantics

The deterministic lifecycle is:

```text
CREATED -> READY -> RUNNING_UNEXPOSED -> RUNNING_EXPOSED
RUNNING_EXPOSED -> COMPLETED_RAW -> SEALED_RAW -> SCORING -> COMPLETE
RUNNING_UNEXPOSED -> ABORTED_BEFORE_PREDICTION
RUNNING_EXPOSED -> PARTIAL_AFTER_PREDICTION_EXPOSURE
eligible nonterminal states -> INVALID (only registered transitions)
```

All unregistered transitions fail before mutation. `PARTIAL_AFTER_PREDICTION_EXPOSURE`,
`ABORTED_BEFORE_PREDICTION`, `INVALID`, and `COMPLETE` are terminal. Partial runs receive a
non-scorable partial raw manifest anchoring the available raw bytes, an immutable
point-in-time ledger snapshot and durable head/count anchor, run metadata, and state.
Sealing is idempotently recoverable
from `COMPLETED_RAW`; recovery revalidates all raw/ledger/provenance joins and never calls
production.

Reconciliation compares state, ledger, and raw evidence under the same exclusive run lock.
It may append a before-call terminal event, conservatively append `FAILED_AFTER_CALL`, or
recover `COMPLETED` from already durable raw evidence. It never creates or repeats a
prediction.

## Raw seal and scoring

Complete sealing requires exact scenario membership/order; contiguous raw sequence;
reconstructable inputs; full implementation provenance; one `STARTED` per prediction;
exact exposure binding; and a `COMPLETED` event cross-linked to each raw record digest and
sequence. The raw manifest binds record count, raw checksum, immutable ledger-snapshot
checksum, ledger-snapshot anchor checksum/head/count, run-metadata checksum, and
run-manifest digest. Every raw digest and sequence is independently cross-linked to its
hash-chained `COMPLETED` event, so coordinated raw and raw-manifest edits still fail.

Only `SEALED_RAW` enters scoring. `scripts/score_auth_coverage_002.py` is a fresh analysis
process with no production-authorizer entry point. It independently verifies the seal,
then loads labels, pairs, and cross-tool metadata. Output binds raw, label, pair, cross-tool,
analysis-package, metric-contract, scorer-source, and scoring-adapter digests. An interrupted
`SCORING` state cannot restart; the next attempt marks the run `INVALID` while preserving
the sealed raw package.

## Frozen research invariants

- `AUTH002-RUN-INV-001`: no held-out production call without durable reservation and
  `STARTED`.
- `AUTH002-RUN-INV-002`: a production call implies prediction exposure.
- `AUTH002-RUN-INV-003`: an exposed scenario/run cannot be canonically rerun.
- `AUTH002-RUN-INV-004`: scoring requires verified `SEALED_RAW`.
- `AUTH002-RUN-INV-005`: execution cannot import or physically package expected labels.
- `AUTH002-RUN-INV-006`: every raw record reconstructs the production input digest.
- `AUTH002-RUN-INV-007`: one run uses one complete production implementation identity.
- `AUTH002-RUN-INV-008`: complete and partial raw seals detect later mutation.

## Security boundary

The ledger is scientific governance, not a production security boundary. Advisory locks,
append-only conventions, hash chaining, and a separately durable head/count anchor detect
accidental or non-coordinated replacement and enforce one-shot behavior among participating
tools. A fully privileged attacker who replaces the ledger, anchor, code, and freeze
manifest together is outside the claim.
