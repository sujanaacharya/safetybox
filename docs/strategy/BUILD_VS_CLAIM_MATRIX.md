# Build vs Claim Matrix

This matrix separates design, construction, evaluation, and claim strength. “Yes” never
means production-ready unless the production-ready column independently says yes.

| Component | Designed | Implemented | Unit tested | Held-out synthetic | Real-system evaluated | Production-ready | Claim boundary |
|---|---|---|---|---|---|---|---|
| Reference monitor | Yes | Yes, in process | Yes | Logical use in frozen synthetic studies | No | No | Authorize-before-forward behavior for the in-process protected-tool API; not complete mediation. |
| Task capability model | Yes | Yes, minimal immutable M2 | Yes | Logical task/action/resource cases | No | No | Explicit represented capability matches only; no OS identity, rich constraints, or real alias handling. |
| Audit/event lifecycle | Yes | Yes, M3 in memory | Yes | Canonical evidence used by synthetic studies | No | No | Single-process sequence and attribution; not durable or forensically complete. |
| Threat simulator | Yes | Yes, harmless logical world | Yes | EXP-009/012/013 corpora build on synthetic observations | No | No | Deterministic simulation only. |
| Sequence monitoring | Yes | Yes, M5 | Yes | Yes, EXP-009 | No | No | Registered synthetic patterns; high false positives in EXP-009 and no prevention. |
| Single-observation context | Yes | Yes, M5.1-B/B2 | Yes | Yes, EXP-012/013 | No | No | Exact structured declaration comparison; not semantic truth or real context quality. |
| History-aware B4 | Yes | Yes, frozen B4 | Yes | Yes, EXP-013 | No | No | 38/40 frozen synthetic pairs with 0/40 matched-negative FP; bounded, observational, declaration-dependent. |
| Real filesystem mediation | Yes, EXP-014 v1 | No | No | No | No | No | Proposed FMED-L1/RTM-1 adapter-routed claim only. |
| Real shell mediation | Concept only | No | No | No | No | No | No shell/interpreter/process-control claim. |
| Network mediation | Concept only | No | No | No | No | No | No socket, DNS, HTTP, rebinding, or remote-effect claim. |
| MCP mediation | Concept only | No | No | No | No | No | No MCP identity, permission, protocol, or server claim. |
| Data lineage | Gap documented | No | No | No | No | No | Ordered actions and roles do not prove causal data transfer. |
| AI scanner | Strategy concept | No | No | No | No | No | No static discovery/detection or AI-inference claim. |
| Containment/degradation | M6 design direction | No | No | No | No | No | Findings and denials are not quarantine, revocation, rollback, or recovery. |
| Production gateway | Boundary concepts only | No | No | No | No | No | No deployment-wide interception, availability, durability, scaling, or production assurance claim. |

## Discipline

Claims must cite a frozen experiment and name the tested component, boundary, evidence
level, negative evidence, and limitations. Design does not imply implementation;
implementation does not imply evaluation; a finite evaluation does not imply complete
mediation or production readiness. The [claims ledger](../research/CLAIMS_LEDGER.md)
remains the authority for repository-wide claim status.
