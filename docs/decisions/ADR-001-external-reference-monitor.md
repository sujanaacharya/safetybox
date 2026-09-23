# ADR-001: External Reference Monitor

Status: Accepted

Date: 2026-09-23

## Context

An agent can be mistaken, prompt-injected, compromised, or motivated to evade controls. Controls implemented only inside the protected agent share its failure domain. SafetyBox requires an independently governed place to authorize privileged effects.

## Decision

Place SafetyBox as an external reference-monitor boundary between agent requests and privileged resources. When interception is enabled, the agent must not retain a direct privileged path to tools, files, shell, network, APIs, or databases. Every privileged request is mediated before execution and attributed to a task/session.

## Alternatives Considered

- Agent self-enforcement through system prompts or planning rules.
- Post-execution log analysis without preventive mediation.
- Tool-specific controls with no shared authorization boundary.

## Consequences

### Positive

- Separates policy authority from the protected agent.
- Enables pre-execution denial and consistent audit semantics.
- Creates a testable complete-mediation requirement.

### Negative

- Requires adapter coverage and deployment isolation.
- Adds latency, operational complexity, and a control-plane dependency.

### Risks

- A bypass, confused adapter, or compromised enforcement host invalidates relevant guarantees.
- “External” may be overstated unless deployment topology is verified.

## Research Impact

This decision motivates RQ-01, RQ-02, and EXP-002. Prevention claims must test tool-side execution and disclose complete-mediation assumptions.
