# SafetyBox Roadmap

Milestones are sequential unless an ADR documents a justified change. Completion means meeting exit criteria, not merely creating files.

| Milestone | Objective | Deliverables | Exit criteria |
|---|---|---|---|
| M0 — Research specification | Establish traceable scope and evaluation design. | Governance, research, architecture, threat, experiment, and ADR documents. | IDs are consistent; links validate; open assumptions are explicit; implementation scope is approved. |
| M1 — Deterministic reference monitor core — Implemented | Establish a minimal fail-safe authorization boundary. | Typed interfaces, policy decision path, focused tests. | Met for the in-process `ReferenceMonitor` API: `INV-001`, `INV-002`, and authorization failure have executable tests; direct tool references remain outside this abstraction. |
| M2 — Task contracts and capability enforcement — Implemented | Enforce task- and resource-scoped authority. | Immutable task contract, explicit action/resource capabilities, deterministic evaluator, and focused tests. | Met only for the in-process logical model: task/action/resource scope and non-expansion tests pass; no contract schema, capability registry, or filesystem/shell adapter exists yet. |
| M3 — Canonical event and audit system — Implemented | Produce ordered, attributable, explainable records. | Immutable in-process event schema, per-session sequencing, ReferenceMonitor audit emission, and in-memory audit sink. | Met for the single-process in-memory `ReferenceMonitor` model: requests map to session/task IDs, decision rule IDs are recorded, ordering and failure semantics are unit-tested. Durable provenance remains future work. |
| M4 — Threat scenario simulator — Implemented | Reproduce controlled benign and adversarial action requests. | Immutable deterministic scenario runner, harmless in-memory tools/world, M3-linked raw evidence, starter TS corpus, and benign controls. | Met for the single-process logical simulator: declared step expectations, blocked/effect distinction, audit linkage, and semantic replay are tested. It is not a benchmark, real sandbox, or trajectory detector. |
| M5 — Trajectory monitoring | Evaluate stateful signals across action sequences. | Rule-based trajectory monitor and sequence fixtures. | At least one registered experiment compares action-only and trajectory-aware policies. |
| M6 — Risk and capability degradation | Evaluate graduated containment. | Experimental state machine, degradation rules, recovery/approval protocol. | Transitions are deterministic and audited; weights, if any, are empirically calibrated. |
| M7 — Benchmark suite | Create a versioned benign/adversarial task corpus. | Benchmark manifests, tasks, scoring protocol, data cards. | Coverage and denominators are documented; licensing and contamination checks are complete. |
| M8 — LLM-monitor baseline | Add an optional comparison monitor outside the deterministic core. | B3 adapter, prompts, cost/token capture, failure handling. | Runs are reproducible where provider controls permit; deterministic enforcement has no dependency on B3. |
| M9 — Cross-model/framework evaluation | Test portability and generalization. | Multiple model/provider and framework adapters with matched protocols. | Comparison matrix has preregistered selection criteria and known confounders. |
| M10 — Ablation studies | Attribute effects to system components. | Registered ablations and analysis scripts. | Each ablation changes one declared factor and reports uncertainty. |
| M11 — Paper experiments | Execute the frozen primary evaluation. | Finalized experiment manifests, immutable results, analysis, claim updates. | Planned trials complete; deviations are logged; claims trace to evidence. |
| M12 — Artifact/reproducibility release | Package a reviewable research artifact. | Versioned code, data or retrieval instructions, environment lock, artifact guide. | Independent clean-environment reproduction succeeds and limitations are documented. |

Dates are intentionally omitted until staffing, implementation scope, and experimental resource constraints are known.
