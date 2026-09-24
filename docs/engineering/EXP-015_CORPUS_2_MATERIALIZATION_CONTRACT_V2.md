# EXP-015 Corpus@2 Materialization Contract v2

`materialize(runtime_scenario, temp_root) -> MaterializedScenario` validates only
runtime structure then creates declared fixture objects. It never executes a child,
invokes `ProcessAdapter`, evaluates authorization, reads labels/pairs/manifests, or uses
an ID-driven table. It preserves `request.task_id` and `task_contract.task_id` verbatim
and independently; task equality cannot select fixture or helper behavior.

`MaterializedScenario` carries `EXP-015-RUNTIME-SCHEMA@2` and
`EXP-015-MATERIALIZER@2` provenance. Its label-free raw-record provenance requires
`request_task_id` and `contract_task_id` (plus scenario/schema/materializer IDs). Raw
records must not store an expected task-match outcome.

```text
runtime scenario -> materializer v2 -> ProcessRequest(request.task_id)
                                  + TaskContract(contract.task_id)
                  -> generic executor -> raw result
```

The runner has no task-binding intervention. An independently implemented authorization
oracle receives contract, request task ID, exec action/resource, and cwd action/resource
as separate inputs. It can derive a task-binding denial without importing or executing
the production authorizer.

The materializer imports only the standard library and v2 schema infrastructure. It has
no imports of process adapter/validation/canonicalization internals, authorization,
labels, scoring, pair registry, or manifest code. Future authoring materializes every
record twice in fresh roots and compares normalized fixture state before any adapter
execution.

`session_id` and `actor` remain required opaque provenance fields. The schema does not
bind either to a task contract, because the frozen contract has no authenticated
session/actor/issuer/deployment model. This unresolved identity limitation is documented,
not silently solved by schema validation.
