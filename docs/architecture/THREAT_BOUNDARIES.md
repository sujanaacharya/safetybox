# Architectural Threat Boundaries

This view complements the canonical threat-model [Trust Boundaries](../threat-model/TRUST_BOUNDARIES.md) by locating controls in the architecture.

```mermaid
flowchart TB
  subgraph U[Untrusted / variably trusted]
    Agent[Protected agent]
    Content[Prompts, retrieved content, tool output]
  end
  subgraph T[SafetyBox trusted enforcement base]
    Intercept[Interception]
    Policy[Policy + capability evaluation]
    Controller[Controller]
    Audit[Integrity-critical audit path]
  end
  subgraph P[Privileged environment]
    Adapters[Sandbox/tool adapters]
    Resources[OS, files, network, APIs, database]
  end
  Agent --> Intercept
  Content --> Agent
  Intercept --> Policy --> Controller --> Adapters --> Resources
  Controller --> Audit
```

## Boundary assumptions

- The agent cannot reach privileged resources except through controlled adapters.
- Agent identity, session/task binding, contract/policy sources, and approval identities are authenticated.
- The host and isolation mechanisms enforce separation from policy, audit, and controller state.
- Adapters correctly bind authorization to actual operations and accurately report outcomes.
- External tools and their outputs may be compromised; their internal effects may be only partly observable.

Violating these assumptions can invalidate prevention claims. They must be tested where feasible and disclosed otherwise. SafetyBox does not replace host hardening or cryptographic identity systems.
