# ADR-005: Task-Scoped Capabilities

Status: Accepted

Date: 2026-09-23

## Context

Tool-level allowlists grant broad authority: permission to use a filesystem or database tool does not define which path, operation, row, duration, or purpose is acceptable. Persistent broad credentials increase the effects of prompt injection or compromise.

## Decision

Derive effective authority from versioned task contracts and capabilities binding actor, action, resource, scope, constraints, duration, and conditions. The contract sets a maximum-privilege ceiling. Runtime authority may be attenuated or revoked, but cannot silently expand.

## Alternatives Considered

- Global tool allowlists.
- Role-based permissions not specialized to the current task.
- Let the agent request and self-approve new permissions.

## Consequences

### Positive

- Makes least privilege and blast radius explicit and measurable.
- Supports resource-level decisions and graduated containment.

### Negative

- Contract creation and resource canonicalization are difficult.
- Overly narrow contracts can reduce benign completion and increase approvals.

### Risks

- Alias, delegation, or TOCTOU errors can escape apparent scope.
- A malicious authorized task issuer can still grant harmful authority.

## Research Impact

This decision motivates RQ-03 and RQ-09, EXP-004 and EXP-010, and the tool-allowlist/capability ablations. Blast-radius reduction remains an untested hypothesis.
