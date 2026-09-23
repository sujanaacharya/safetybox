# Audit and Provenance

## Objectives

Audit answers what was requested, what was decided, why, which state and versions governed the decision, whether execution occurred, and what result was observed. Provenance links these records to tasks, sessions, contracts, policies, software, adapters, experiments, and source artifacts.

## Minimum decision record

- event/session/task/correlation identifiers and sequence number;
- normalized actor, action, resource, and governed argument reference;
- contract, capability snapshot, policy set, schema, engine, and adapter versions/hashes;
- enforcement outcome, reason code, matched rule IDs, limits, and state transition;
- authoritative timestamps and execution/result status;
- approval identity/scope where applicable;
- redaction classification, integrity metadata, and causal links.

## Integrity and confidentiality

Append-only behavior, hashing/signing, durable storage, rotation, and external anchoring are deployment choices to evaluate; none is currently implemented. Audit integrity is not useful if logs disclose secrets, so payload minimization, structured redaction, access control, encryption, and retention/deletion policy are required. Redaction rules themselves must be versioned and must preserve evidence needed for declared metrics.

## Research provenance

Experiment outputs link to code SHA, configuration and policy hashes, benchmark/task versions, event ranges, analysis code, environment metadata, and checksums. Finalized result files are immutable under [Project Governance](../PROJECT_GOVERNANCE.md). Corrections retain the original and add a linked successor.

An explanation is evidence-backed only when it derives from evaluated facts and rules; agent or LLM rationales are separately labeled unverified content.
