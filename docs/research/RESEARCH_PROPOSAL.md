# Research Proposal

## 1. Motivation

Autonomous agents can translate model outputs into consequential file, shell, network, database, and API actions. Safety mechanisms controlled by the same agent may fail under prompt injection, model error, compromised context, or deliberate evasion. SafetyBox investigates whether an independently controlled mediation layer can constrain those external effects using explicit, inspectable rules.

## 2. Problem statement

The central question is whether an external deterministic runtime can detect, prevent, and contain unauthorized or task-deviating behavior without relying primarily on another LLM as the safety judge. The system must mediate privileged actions before execution, scope authority to a declared task, preserve evidence, and expose predictable failure behavior.

## 3. Research gap

Relevant fields provide guardrails, reference-monitor principles, capability security, sandboxing, policy engines, runtime verification, anomaly detection, provenance, and LLM judging. The proposed research tests their combination for tool-using agents under a provider- and framework-neutral event model. This is a proposed gap framing, not a novelty claim; it must be revised after a verified literature review in [Related Work](RELATED_WORK.md).

## 4. Proposed architecture

SafetyBox is designed as an external reference monitor. An agent adapter converts framework-specific requests into canonical actions. An interception layer ensures requests reach a capability registry and deterministic policy engine before a controller can forward them. Ordered events feed audit/provenance storage and an experimental trajectory/risk subsystem. The controller may allow, deny, limit, request approval, degrade capabilities, pause, quarantine, or terminate. Semantic models may later supply an auxiliary signal, but fundamental authorization cannot depend on them. See [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md).

## 5. Core research questions

The ten questions in [Research Questions](RESEARCH_QUESTIONS.md) cover prevention, early detection, containment/utility, overhead, portability, deterministic-versus-LLM monitoring, deterministic blind spots, trajectory value, prompt-injection blast radius, and evasion robustness.

## 6. Hypotheses

The preregistration candidates in [Hypotheses](HYPOTHESES.md) predict strong enforcement for explicitly represented violations, incremental value from trajectory monitoring and graduated restriction, lower deterministic-policy overhead than LLM monitoring, portability under canonical adapters, and residual semantic blind spots. They are untested.

## 7. Intended evaluation methodology

Evaluation will use versioned benign and adversarial task suites, explicitly enumerated threat scenarios, matched trials across baselines, and immutable run metadata. Primary outcomes include unsafe-action execution, attack prevention, false positives/negatives, task completion, latency, resource cost, and repeated-run decision consistency. Experiments will separate policy expressiveness from implementation correctness and compare action-level with trajectory-level checks. Statistical methods, sample sizes, uncertainty reporting, and stopping criteria will be preregistered per experiment rather than invented after observation.

## 8. Expected contributions

Candidate contributions are: a provider-neutral task/capability vocabulary; a deterministic reference-monitor architecture; a canonical event and provenance model; a catalog of agent-specific threat trajectories; and a reproducible comparative evaluation protocol. Whether these are novel or effective remains subject to literature review and experiments.

## 9. Limitations

Deterministic controls can only reason over represented, observable behavior. They may miss harmful semantic intent, misuse through authorized channels, side channels, compromised enforcement hosts, and effects hidden inside tools. Adapter completeness and policy quality may dominate outcomes. LLM baselines introduce nondeterminism and provider drift. Benchmarks may not reflect deployed environments.

## 10. Ethical considerations

Threat research can expose operational misuse patterns. Scenario data should minimize real credentials and external targets, use isolated resources, and apply staged disclosure to discovered vulnerabilities. Dataset collection must address privacy, licenses, and contamination. Reports must include utility costs and disparate operational impacts, not only attack detection. Human approval paths must avoid presenting automation as infallible.

## 11. Reproducibility strategy

Every reported run will record code SHA, software and schema versions, environment, model/provider details, task contract, policy set, scenario, trial, and results. Artifacts will be checksummed; finalized results will be immutable; analysis will be scriptable; nondeterministic inputs will be disclosed; and repeated-run consistency will be measured. See [Reproducibility](../experiments/REPRODUCIBILITY.md).

## 12. Potential publication directions

Possible directions include a systems-security paper on reference mediation and containment, an empirical AI-safety paper comparing monitoring approaches, or a reproducibility/benchmark artifact. Venue selection and claim scope will follow literature review and pilot evidence; no publication claim is predetermined.
