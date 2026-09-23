# Glossary

| Term | Canonical meaning |
|---|---|
| Agent | The protected autonomous or semi-autonomous system requesting actions. It is not part of the trusted enforcement base. |
| Agent adapter | Framework-specific translation between agent tool calls and canonical SafetyBox requests/events. |
| Approval | An explicit decision by an authorized external principal permitting a pending action. |
| Capability | Task-scoped authority for an actor to perform an action on a resource under constraints, duration, and conditions. |
| Containment | Reduction or removal of external effects available to a suspicious session. |
| Deterministic core | Enforcement functions whose output is reproducible from the same normalized inputs, state, policy version, and engine version. |
| Enforcement controller | Component that turns evaluated decisions and state into forwarding, restriction, pause, quarantine, or termination actions. |
| Event | Canonical, ordered record of an observed request, decision, state transition, or external result. |
| External action | An operation with effects outside the agent's internal computation, including tool, file, shell, network, API, or database operations. |
| Policy | Versioned deterministic rules mapping normalized context to a decision and explanation. |
| Provenance | Lineage connecting actions and evidence to task, session, policy, software, inputs, and causal events. |
| Reference monitor | Mediation boundary intended to observe and authorize every privileged external action before execution. |
| Risk state | Experimental runtime state summarizing policy-relevant behavioral concern; not a validated measure of agent intent. |
| Safety invariant | A desired property that must later be verified against implementation and deployment assumptions. |
| Task contract | Versioned declaration of goals, prohibitions, capabilities, scopes, limits, approvals, and termination conditions for one task. |
| Trajectory | Ordered sequence of events considered jointly rather than as isolated actions. |
| Trust state | Operational label controlling restriction level; it is not a moral or scientifically validated assessment. |
