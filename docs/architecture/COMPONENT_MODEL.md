# Component Model

The [System Architecture](SYSTEM_ARCHITECTURE.md) owns the component list. This document specifies responsibility and trust separation.

| Component | Accepts | Produces | Must not do |
|---|---|---|---|
| Task Contract loader | Authenticated, versioned contract | Validated canonical contract | Infer undeclared authority from agent text |
| Task Context loader (future) | Authenticated versioned semantic declarations | Immutable validated `TaskContext` | Grant capabilities, infer roles from text, or trust agent self-report |
| Agent Adapter | Framework request/response | Canonical request/events | Execute tools or weaken scope |
| Interception Layer | Canonical request and session identity | Mediation transaction | Permit bypass or pre-authorization side effects |
| Capability Registry | Contract grants, revocations, time/state | Effective capabilities | Expand authority without authorized grant event |
| Policy Engine | Normalized request, state, versioned rules | Decision, matched rules, explanation | Invoke tools or mutate evidence |
| Event subsystem | Candidate canonical events | Ordered committed events | Accept agent-controlled sequence/timestamps as authoritative |
| Context Evaluator | One completed observation, trusted `TaskContext`, optional structured metadata | Immutable reason-coded `ContextEvaluation` | Authorize, retain trajectory history, infer natural-language semantics, or emit findings |
| Context-Aware Trajectory Monitor | Ordered completed observations, trusted task context, M5.1-B evaluations | Immutable context-aware findings and bounded snapshots | Authorize, execute, contain, infer payload lineage, or treat missing context as benign |
| Trajectory Monitor | Ordered canonical events, deterministic trajectory rules | Immutable findings and explanations | Directly execute external actions, authorize requests, or mutate task authority/capabilities |
| Risk/Trust Engine | Defined signals and transition policy | State transition proposal | Treat an opaque score as fact about intent |
| Enforcement Controller | Policy/capability/risk decisions | Applied outcome and events | Override a hard deny with advisory input |
| Approval mechanism | Pending request, bounded context | Signed/attributable decision | Grant authority beyond approver scope |
| Tool adapter/sandbox | Authorized normalized invocation | Result or execution failure event | Accept an unbound/stale authorization |
| Audit Logger | Committed events | Durable ordered record | Rewrite finalized evidence silently |
| Provenance Store | IDs, versions, hashes, causal links | Queryable lineage | Conflate unverified agent statements with observations |

## Implemented M3 boundary

M3 implements only `AuditRecorder` plus `AuditSink`/`InMemoryAuditSink` within the in-process monitor. The recorder—not producers—allocates session sequence numbers and creates immutable events. It has no concurrency, persistence, fan-out, or remote-delivery support.

## Interface discipline

Interfaces will later be typed and versioned. Requests require task/session identity, normalized action/resource, correlation identity, and a bound policy/capability snapshot. Authorization should be single-use or otherwise protected from replay. Components fail closed or enter explicitly configured safe states as documented in [Failure Modes](FAILURE_MODES.md).

The trusted computing base is intended to include the interception boundary, policy/capability evaluation, controller, adapters enforcing authorization, and integrity-critical audit path. The protected agent and arbitrary tool outputs remain untrusted.

M5 implements only an observational trajectory consumer, separate from the event recorder and enforcement path. It derives bounded session-and-task-local state from ordered canonical events and returns findings; there is no event fan-out, containment, or controller integration.

M5.1-A implements the context value model and validation. M5.1-B adds a stateless
single-observation evaluator over that model. Context objects are constructed
externally; there is no loader, agent setter, trajectory consumer, or authorization
integration. Evaluation preserves per-declaration source references and cannot emit or
suppress trajectory findings.

M5.1-C is the first trajectory consumer of `ContextEvaluation`. Its state is bounded and
isolated by session/task, and its output remains outside the enforcement path. It does
not replace or mutate M5.
