# Audit and Provenance

## Objectives

Audit answers what was requested, what was decided, why, which state and versions governed the decision, whether execution occurred, and what result was observed. Provenance links these records to tasks, sessions, contracts, policies, software, adapters, experiments, and source artifacts.

## Implemented in M3

`ReferenceMonitor` emits immutable ordered lifecycle events through an `AuditRecorder`, which owns per-session sequencing and delivers to an `AuditSink`. `InMemoryAuditSink` is the supplied test sink and returns tuple snapshots rather than its mutable internal collection. Authorization events preserve the structured policy decision and responsible `rule_id`.

M3 fails closed when a required audit event cannot be recorded before tool execution: `AuditFailure` is raised and the tool is not invoked. A failure while attempting a terminal event after an invoked tool cannot undo that side effect; it raises `AuditFailure` with an indeterminate execution-status boundary. This research-prototype choice is not a universal deployment policy.

## M4 scenario linkage

M4 creates one `ActionRequest` per ordered scenario step. Its deterministic request ID is `<scenario_id>:<step_id>` and is also the M3 correlation ID. `ScenarioResult` returns the existing M3 events rather than a duplicate event stream; event UUIDs and timestamps remain M3 observational metadata.

## Future minimum decision record

- event/session/task/correlation identifiers and sequence number;
- normalized actor, action, resource, and governed argument reference;
- contract, capability snapshot, policy set, schema, engine, and adapter versions/hashes;
- enforcement outcome, reason code, matched rule IDs, limits, and state transition;
- authoritative timestamps and execution/result status;
- approval identity/scope where applicable;
- redaction classification, integrity metadata, and causal links.

## Integrity and confidentiality

Durable storage, cross-process ordering, distributed tracing, append-only or tamper-evident storage, cryptographic integrity, automatic experiment provenance, and redaction guarantees are not implemented. Audit integrity is not useful if logs disclose secrets, so payload minimization, structured redaction, access control, encryption, and retention/deletion policy remain required.

## Future research provenance

Experiment outputs link to code SHA, configuration and policy hashes, benchmark/task versions, event ranges, analysis code, environment metadata, and checksums. Finalized result files are immutable under [Project Governance](../PROJECT_GOVERNANCE.md). Corrections retain the original and add a linked successor.

An explanation is evidence-backed only when it derives from evaluated facts and rules; agent or LLM rationales are separately labeled unverified content.
