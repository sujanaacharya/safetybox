# ADR-002: Deterministic Core

Status: Accepted

Date: 2026-09-23

## Context

LLM safety judges can add semantic interpretation but may introduce latency, cost, provider dependence, prompt sensitivity, and nondeterministic outputs. Explicit authorization decisions should be replayable and explainable where possible.

## Decision

Fundamental capability and policy enforcement will use a deterministic core over normalized, versioned inputs and state. An LLM may later contribute an auxiliary signal, but it cannot be required for basic authorization or override a deterministic hard denial or maximum-privilege ceiling.

## Alternatives Considered

- LLM-only monitoring for all decisions.
- Agent self-classification of request safety.
- Unspecified hybrid voting without hard deterministic precedence.

## Consequences

### Positive

- Supports replay, stable reason codes, predictable failure behavior, and lower expected local decision cost.
- Keeps core operation independent of model availability.

### Negative

- Requires explicit policy representation and canonicalization.
- May miss semantic misuse that is not expressed in observable structured signals.

### Risks

- Deterministic can be mistaken for correct; bad policies produce repeatable bad decisions.
- Hidden time, concurrency, or environment inputs can undermine reproducibility.

## Research Impact

This decision creates the B2/B3/B4 comparison and informs RQ-06 and RQ-07. Lower overhead or better reproducibility remains a hypothesis to test, not a consequence assumed as evidence.
