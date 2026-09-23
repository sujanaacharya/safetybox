# Glossary

| Term | Canonical meaning |
|---|---|
| Agent | The protected autonomous or semi-autonomous system requesting actions. It is not part of the trusted enforcement base. |
| Agent adapter | Framework-specific translation between agent tool calls and canonical SafetyBox requests/events. |
| Approval | An explicit decision by an authorized external principal permitting a pending action. |
| Capability | Task-scoped authority for an actor to perform an action on a resource under constraints, duration, and conditions. |
| Containment | Reduction or removal of external effects available to a suspicious session. |
| Context source | Authority and immutable reference from which a trusted semantic declaration originated. |
| Data-flow constraint | Declared permitted logical relationship among resource roles, a derived data role, a destination purpose, and action purposes; not byte-level lineage. |
| Data role | Lightweight logical class or purpose of information declared by trusted context. |
| Deterministic core | Enforcement functions whose output is reproducible from the same normalized inputs, state, policy version, and engine version. |
| Destination constraint | Task-scoped declaration of a legitimate outbound action/destination relationship and its permitted semantic roles and outcomes. |
| Enforcement controller | Component that turns evaluated decisions and state into forwarding, restriction, pause, quarantine, or termination actions. |
| Event | Canonical, ordered record of an observed request, decision, state transition, or external result. |
| External action | An operation with effects outside the agent's internal computation, including tool, file, shell, network, API, or database operations. |
| Fallback pattern | Bounded trusted declaration of expected repeated-access, compatibility, migration, or diagnostic behavior. |
| Policy | Versioned deterministic rules mapping normalized context to a decision and explanation. |
| Provenance | Lineage connecting actions and evidence to task, session, policy, software, inputs, and causal events. |
| Reference monitor | Mediation boundary intended to observe and authorize every privileged external action before execution. |
| Resource role | Trusted mapping from a canonical resource scope to its semantic role and optional data role. |
| Risk state | Experimental runtime state summarizing policy-relevant behavioral concern; not a validated measure of agent intent. |
| Safety invariant | A desired property that must later be verified against implementation and deployment assumptions. |
| Task contract | Versioned declaration of goals, prohibitions, capabilities, scopes, limits, approvals, and termination conditions for one task. |
| Task context | Immutable, versioned trusted semantic declarations used to interpret actions relative to a task; it grants no authority. |
| Task purpose | Structured externally declared identifier for why a task exists, optionally accompanied by a human-readable description. |
| Allowed outcome | Structured identifier for a legitimate task result declared in task context. |
| Trajectory | Ordered sequence of events considered jointly rather than as isolated actions. |
| Trust state | Operational label controlling restriction level; it is not a moral or scientifically validated assessment. |
