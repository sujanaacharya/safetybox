# Policy Engine

## Role

The policy engine maps a normalized request and explicit state to a decision. It does not execute tools, infer authority from agent prose, or mutate audit history. Policy language and implementation remain undecided; this document fixes behavioral requirements first.

## Inputs and outputs

Inputs include task/actor/session identity, canonical action and resource, normalized arguments, task contract version, effective capability snapshot, policy set/version, trajectory state, risk state, approval facts, limit counters, and a captured evaluation time.

Output includes an enforcement outcome, stable reason code, matched `POL-NNN` rules, human-readable explanation, applied limits, proposed state transitions, and hashes/versions sufficient to reproduce evaluation.

## Rule properties

- explicit applicability and priority;
- deterministic evaluation order;
- deny-overrides or a comparably precise conflict algorithm;
- default behavior for no match, malformed input, and evaluation failure;
- separation of hard prohibitions from advisory signals;
- no network or unrecorded mutable dependency during core evaluation;
- versioned tests for boundary cases.

Initial policy IDs will be allocated with implementation, not invented in this specification.

## Decision precedence

The exact composition algorithm requires an ADR before implementation. At minimum: terminal/quarantine state cannot be weakened; an explicit hard deny cannot be overridden by an LLM or agent suggestion; approvals are scoped and cannot exceed maximum privilege; and `ALLOW_WITH_LIMITS` only narrows. Default failure behavior is defined per operation in [Failure Modes](FAILURE_MODES.md), with privileged actions expected to fail closed.

## Explainability

An explanation must identify which normalized facts and versioned rules controlled the result. It should not expose secrets or depend on post-hoc natural-language rationalization. A replay tool should eventually be able to re-evaluate stored inputs and compare the outcome.
