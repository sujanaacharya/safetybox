# ADR-003: Provider-Neutral Design

Status: Accepted

Date: 2026-09-23

## Context

Model providers and agent frameworks expose different tool-call formats, identities, and lifecycle hooks. Binding core policy semantics to one provider would limit comparisons and make safety behavior change with integration technology.

## Decision

Define canonical requests, events, task contracts, capabilities, decisions, and adapter conformance independently of any model provider or agent framework. Provider/framework integrations terminate at adapters and may not redefine core authorization semantics.

## Alternatives Considered

- Build directly around one provider SDK.
- Adopt one agent framework's native tool/policy model as canonical.
- Maintain separate policy engines per framework.

## Consequences

### Positive

- Enables matched cross-model/framework evaluation.
- Limits provider dependencies in the trusted core.

### Negative

- Canonicalization may omit framework-specific features or require extensions.
- Adapter correctness and equivalence become significant engineering burdens.

### Risks

- Superficially normalized requests may retain unequal observability or semantics.
- Lowest-common-denominator design could weaken controls.

## Research Impact

RQ-05 and EXP-006 evaluate bounded portability. Results must distinguish core decision invariance from adapter and end-to-end task outcomes.
