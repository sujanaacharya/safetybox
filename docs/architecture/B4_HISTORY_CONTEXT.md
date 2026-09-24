# B4 History Context

`B4-HISTORY-CONTEXT@1` is the immutable trusted companion schema consumed by
`B4-BOUNDED-CONTEXT-TRAJECTORY@1`. It adds no field to frozen `TaskContext` v1 and has
no authorization meaning. A companion binds to one `task_id` and to a deterministic
SHA-256 semantic reference of the complete immutable `TaskContext`.

## Top-level schema

`B4HistoricalConstraints` contains the schema and constraint identifiers, task binding,
TaskContext reference, four explicit dimension-applicability declarations, role groups,
aggregation scopes, role-combination constraints, semantic-event bindings, phase
definitions and transitions, finalization constraints, and fallback-progression
constraints. Every caller-owned iterable is copied to a tuple or `frozenset`.

Each dimension must occur exactly once as `REQUIRED` or `NOT_APPLICABLE`:

- `ROLE_COMBINATION`
- `PHASE_TRANSITION`
- `FINALIZATION`
- `FALLBACK_PROGRESSION`

An omitted entry is invalid. A required dimension with absent or incompatible
declarations produces an `INSUFFICIENT_CONTEXT` finding. `NOT_APPLICABLE` is an
explicit trusted statement, not an inference from an empty tuple.

## Trust boundary

Every applicability entry and declaration carries the frozen M5.1-A `ContextSource`.
The implementation accepts exactly the authorities for which
`ContextAuthority.is_trusted` is true and rejects `AGENT_SELF_REPORT`. In the frozen
M5.1-A enum these are `TASK_CONTRACT`, `SYSTEM_POLICY`, `RESOURCE_REGISTRY`, and
`TOOL_ADAPTER`; B4 does not modify that enum to add another authority. This is an
in-process trust boundary, not issuer authentication or cryptographic integrity.

## Declaration types

`RoleGroup` maps an opaque group ID to a non-empty resource-role and/or data-role set.
`AggregationScope` declares opening and closing semantic events plus the groups tracked
inside the scope. `RoleCombinationConstraint` identifies the scope and outcome event,
the finite role/group universes projected at that outcome, and a non-empty set of
allowed exact `RoleCombination` values. Group and role spellings never select code
paths.

`SemanticEventBinding` is a conjunction over exact action ID and optional matched
resource role, data role, destination, action purpose, or outcome ID. These fields come
from the observation and frozen M5.1-B interpretation. Zero matches means the
observation is outside semantic-event applicability; multiple matches produce
`INSUFFICIENT_CONTEXT` and are never resolved by precedence.

`PhaseDefinition` maps events to one opaque phase and may mark that phase initial or
terminal. Events cannot belong to multiple phases. `PhaseTransition` is a directed
edge. Exactly one initial phase is required when phase transitions are applicable;
same-phase continuation needs no self-edge.

`FinalizationConstraint` names the trusted event establishing finalization, the opaque
outcome ID, phases closed by that event, and the exact semantic events allowed after
finalization. An empty exception set is an explicit declaration that no closed-phase
event is excepted. Finalization does not terminate a task or session.

`FallbackProgressionConstraint` links one frozen M5.1-A fallback behavior to a finite
candidate tuple. Each `FallbackCandidate` binds an opaque candidate ID to a canonical
resource scope and matched resource role. The declaration includes directed candidate
edges, a per-episode positive maximum, optional paired termination condition/event,
restart policy, cycle policy, and either `ORDERED` or `EXPLICIT_TRANSITIONS` mode.
`ORDERED` means adjacent tuple entries define the edges; otherwise the declared edge set
is authoritative.

## Validation and revision limits

Construction rejects unsupported schema versions, whitespace-bearing identifiers,
duplicates, unknown cross-references, empty combination allow-lists, ambiguous phase
membership, malformed fallback candidates, and untrusted provenance. Some incomplete
but structurally representable required dimensions remain constructible so the monitor
can emit the preregistered abstention.

`task_context_reference()` canonically serializes the immutable dataclass graph and
hashes it. A mismatch is detectable and yields `INSUFFICIENT_CONTEXT` for required
dimensions. B4 cannot detect a declaration that is internally consistent but stale
relative to an unrepresented real-world task, and declaration consistency never proves
freshness or safety.

Descriptions and resource contents are never parsed. The schema expresses observed
roles and ordered semantic relations, not payload lineage or causal transfer.
