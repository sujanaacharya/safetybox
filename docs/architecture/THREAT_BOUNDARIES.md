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
    Context[Externally supplied TaskContext]
    FutureMonitor[Future M5.1 monitor]
  end
  subgraph P[Privileged environment]
    Adapters[Sandbox/tool adapters]
    Resources[OS, files, network, APIs, database]
  end
  Agent --> Intercept
  Content --> Agent
  Intercept --> Policy --> Controller --> Adapters --> Resources
  Controller --> Audit
  Context -. semantic input only .-> FutureMonitor
```

## Boundary assumptions

- The agent cannot reach privileged resources except through controlled adapters.
- Agent identity, session/task binding, contract/policy sources, and approval identities are authenticated.
- The host and isolation mechanisms enforce separation from policy, audit, and controller state.
- Adapters correctly bind authorization to actual operations and accurately report outcomes.
- External tools and their outputs may be compromised; their internal effects may be only partly observable.
- Trusted context authorities and immutable references are assumed authentic outside
  the current in-process model. Agent self-report is explicitly untrusted and cannot
  construct accepted semantic declarations.

`TaskContext` is outside the authorization path. Even valid trusted semantic context
cannot grant authority absent from `TaskContract`; compromised or incorrect context
can mislead future interpretation but cannot expand M2 capabilities through M5.1-A.

Violating these assumptions can invalidate prevention claims. They must be tested where feasible and disclosed otherwise. SafetyBox does not replace host hardening or cryptographic identity systems.
