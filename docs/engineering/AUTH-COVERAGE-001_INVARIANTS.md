# AUTH-COVERAGE-001 authorization invariants

**Registry identity:** `AUTH-COVERAGE-001-INVARIANTS@1`

**Normative specification:** `AUTH-COVERAGE-001-AUTHORIZATION-SPEC@1`

**Evidence class:** architecture/development; not held-out production evidence

## Machine-enforced registry

| Invariant | Frozen statement | Enforcement |
|---|---|---|
| `DETERMINISM` | Identical inputs return identical immutable results. | All bounded atomic states. |
| `NO_AUTHORITY_AMPLIFICATION` | Partial or attenuated authority cannot become broader authority through union or delegation. | Split-capability states and all bounded parent/child pairs. |
| `NO_CROSS_TASK_REUSE` | A contract selected for task A cannot authorize an otherwise identical request for task B. | Every atomic capability subset, action, and resource. |
| `NO_IRRELEVANT_CAPABILITY_EFFECT` | Adding a valid capability with the wrong action cannot change a decision. | Every atomic state. |
| `NO_CAPABILITY_ORDER_EFFECT` | Capability permutation preserves the decision and component rules. | Every atomic state. |
| `NO_SUSPICIOUSNESS_AUTHORITY_EFFECT` | Alarming argv/context literals cannot grant or revoke authority. | Every atomic state. |
| `NO_INNOCENCE_AUTHORITY_EFFECT` | Benign presentation cannot grant authority absent a match. | Same non-authority-data metamorphic check. |
| `EXACT_RESOURCE_BINDING` | Exact authority covers the exact resource and no tested sibling. | Every bounded task/action/resource boundary. |
| `COMPOUND_SUBDECISION_INDEPENDENCE` | Process exec and cwd are independently retained and top-level ALLOW is their conjunction. | Every bounded process state; AA/AD/DA/DD all reached. |
| `AI_CONTEXT_CANNOT_GRANT_AUTHORITY` | AI/context data does not participate in hard authorization. | Every atomic state. |
| `UNKNOWN_CONTEXT_CANNOT_EXPAND_AUTHORITY` | Unknown metadata does not participate in hard authorization. | Every atomic state. |
| `NO_OPAQUE_ID_EFFECT` | Request/contract identity rename preserves authority semantics. | Every atomic state. |
| `FAIL_CLOSED` | Malformed request, path, contract, or capability identity structure denies. | Explicit invalid-state family. |
| `ATTENUATION_PRECURSOR` | Every child capability is contained by one parent capability under the same task. | All bounded capability-set pairs. |
| `DELEGATION_CHAIN_PRECURSOR` | A root-first chain has unique IDs, exact parent links, and attenuation at every edge. | Positive and negative synthetic chains. |
| `EXPLANATION_COMPLETENESS` | Every subdecision has every mechanically required field. | Every bounded atomic state. |

## Composition interpretation

`NO_AUTHORITY_AMPLIFICATION` does not prohibit the process mediator's explicitly defined
compound composition. `process.exec` and `process.cwd` are separate required components;
each may be covered by its own complete capability. It prohibits using the action from
one capability and the resource from another to cover one atomic component, or combining
narrow parent capabilities into one broader delegated child capability.

The benchmark corpus must also instantiate these properties as counterfactual,
metamorphic, mutation, and cross-tool cases. Passing this synthetic suite alone is not a
benchmark result.

## Preserved non-claims

The registry does not establish authenticated identity/session binding, delegation in the
production system, time or usage-count attenuation, destination constraints, physical
filesystem containment, process execution safety, network/MCP/DB mediation, or
unbounded-state correctness. It cannot detect a written-specification error shared by
all same-team implementations.
