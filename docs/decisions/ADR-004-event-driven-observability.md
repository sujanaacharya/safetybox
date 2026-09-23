# ADR-004: Event-Driven Observability

Status: Accepted

Date: 2026-09-23

## Context

Single requests cannot represent cumulative limits, causal chains, repeated probing, or multi-step trajectories. Research evidence also requires attributable, ordered observations rather than model narratives.

## Decision

Represent runtime observations, decisions, state transitions, and results as canonical immutable events with session-local monotonic sequence numbers and correlation/causal identifiers. Trajectory monitoring and audit consume the same committed event semantics, with separate storage/availability responsibilities.

## Alternatives Considered

- Unstructured component logs.
- Current-state snapshots without an ordered history.
- Wall-clock timestamps as the sole ordering mechanism.

## Consequences

### Positive

- Supports deterministic replay, trajectory policies, provenance, and experimental analysis.
- Makes missing or contradictory lifecycle steps testable.

### Negative

- Requires schema evolution, sequencing, redaction, retention, and backpressure design.
- High-volume telemetry adds storage and performance overhead.

### Risks

- Ordering mistakes can cause incorrect enforcement state.
- Sensitive payloads may leak through poorly designed audit records.

## Research Impact

This decision enables RQ-08 and time-to-detection/containment measurement. EXP-003 and EXP-009 must distinguish committed event order from wall-clock timing.
