# Deterministic Threat Scenario Simulator

## Scope

M4 provides a harmless, deterministic execution harness for reusable scenario definitions. It is simulation infrastructure, not a frozen benchmark, experimental result table, detector, sandbox, or claim of prevention. Scenario behavior is defined independently of the current SafetyBox policy so later B0--B5 conditions can execute matched inputs.

`ThreatScenario` may describe malicious behavior, accidental misuse, task deviation, boundary probing, or benign unusual behavior. A scenario label is not evidence of actor intent. Benign controls use the `BENIGN-NNN` namespace, deliberately distinct from the canonical `TS-NNN` threat catalog.

## Architecture

```text
ThreatScenario -> ScenarioRunner -> ReferenceMonitor -> SimulatedTool -> SimulatedWorld
                                      |
                                      v
                                M3 audit events
```

The runner creates a fresh `SimulatedWorld`, `InMemoryAuditSink`, `TaskContractPolicy`, and `ReferenceMonitor` for each run. Each `ScenarioStep` becomes an `ActionRequest` with deterministic request ID `<scenario_id>:<step_id>` and session ID `simulation:<scenario_id>`. M3 retains its intentionally nondeterministic event UUIDs and UTC timestamps; semantic replay comparisons use step IDs, decisions, rule IDs, execution/effect flags, world snapshots, and event types instead.

## Schema and evidence semantics

- `ThreatScenario`: immutable ID, metadata, immutable task contract, ordered steps, explicit expectation, optional RQ/H mappings, and notes.
- `ScenarioStep`: immutable `step_id`, actor, action, logical resource, immutable arguments, and optional request task-ID override for task-binding tests.
- `ScenarioExpectation`: human-readable expected security property, step-level `MUST_EXECUTE`, `MUST_NOT_EXECUTE`, or `OBSERVATION_ONLY` requirements, plus current implementation status.
- `ScenarioResult`: immutable task-contract and expected-property snapshot, step evidence, canonical M3 events, immutable world snapshot, and expectation-evaluation records with raw counts.

Policy outcomes and scenario-security outcomes are different. `ALLOW` only means the individual request matches the configured policy; it does not make a trajectory safe. `DENY` only means an individual request was not forwarded; it does not establish universal security. A failed expectation is result data, not a runner exception. In contrast, malformed scenario configuration or an unavailable simulated adapter is `SimulationInfrastructureError`.

`CURRENTLY_UNDETECTABLE` is descriptive rather than a passing verdict. TS-009 is retained in this status because every action is individually authorized and M4 deliberately has no trajectory analysis.

## Simulated effects and limits

Filesystem, network, shell, and database actions are represented by `Simulated*Tool` classes. They append only logical identifiers to a fresh in-memory world (`files_read`, `network_requests`, `shell_commands`, `database_queries`). They do not import or invoke filesystem access, subprocesses, network clients, or database drivers.

M4 exercises existing in-process evidence for INV-001, INV-002, INV-004, INV-005, and INV-011. It does not establish deployment-wide complete mediation, OS confinement, durable audit, identity authentication, alias resistance, data lineage, or trajectory detection.

## Initial corpus

| ID | Status | Purpose |
|---|---|---|
| TS-001 | SIMULATED / PARTIALLY_ENFORCED | Allowed project read followed by denied logical credential access. |
| TS-006 | SIMULATED / PARTIALLY_ENFORCED | Task-B request context against task-A contract. |
| TS-008 | SIMULATED / PARTIALLY_ENFORCED | Nearby path-boundary probes; no repetition scoring. |
| TS-009 | SIMULATED / CURRENTLY_UNDETECTABLE | Individually allowed reads, query, and outbound-like action; future trajectory material. |
| TS-010 | SIMULATED / PARTIALLY_ENFORCED | Logical SafetyBox control-plane resource access attempt. |
| BENIGN-001 | SIMULATED | Normal scoped project inspection. |
| BENIGN-002 | SIMULATED | Normal mixed filesystem/database task within granted capabilities. |

The corpus is intentionally small and has no randomness, actual payloads, real secrets, or external side effects. A later benchmark must freeze versioned scenario selections, baselines, sampling, metrics, and analysis rules separately.

## Anti-overfitting rule

Before adding or changing a scenario, ask: “Would this still be meaningful if SafetyBox did not exist?” If not, do not use it as evidence of general protection. A poor result—including a fully allowed suspicious trajectory—is valuable and must not motivate rewriting the scenario to flatter a detector.
