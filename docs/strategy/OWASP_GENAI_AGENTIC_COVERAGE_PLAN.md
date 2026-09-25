# OWASP GenAI and Agentic Coverage Plan

## Status and claim boundary

This is a strategy document, not an implementation or coverage claim. It uses the
[OWASP Top 10 for LLM Applications 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)
and the
[OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
as the current taxonomies at the time of writing. OWASP describes the agentic list as a
starting framework for risks in systems that plan, act, and make decisions across complex
workflows; it is not a product certification.

SafetyBox does not claim coverage of an OWASP category. EXP-009, EXP-012, and EXP-013
are synthetic held-out evaluations of bounded deterministic primitives. EXP-014 adds
Level 4 held-out real-tool evidence only for named adapter-routed filesystem sub-properties
at FMED-L1; it is not a whole-category or deployment-wide OWASP evaluation.

Allowed roadmap statuses in this document are:

- `SUPPORTED_BY_CURRENT_EVIDENCE`: only a precisely named sub-property has repository
  evidence; the evidence level must be stated.
- `PARTIALLY_ADDRESSED`: a component can mitigate or observe part of a risk.
- `ARCHITECTURALLY_RELEVANT`: the architecture could host a control but has no sufficient
  detector/evaluation yet.
- `REQUIRES_STATIC_SCANNER`, `REQUIRES_RUNTIME_EXTENSION`, `REQUIRES_AI_ANALYSIS`, or
  `REQUIRES_DATA_LINEAGE`: a missing primitive is material.
- `OUT_OF_CORE_SCOPE`: another assurance discipline should own the core control.
- `FUTURE_RESEARCH`: an empirical question remains open.

Multiple statuses may apply because discovery, detection, prevention, mitigation, and
evidence are different dimensions.

## Coverage model

A checkbox is inadequate. Every future claim must report these dimensions separately:

| Dimension | Meaning | Allowed strength vocabulary |
|---|---|---|
| `STATIC_DISCOVERY` | inventory of relevant components, permissions, trust boundaries, and flows | none / candidate / partial / strong |
| `STATIC_DETECTION` | source/config evidence of a concrete risky construction | none / candidate / partial / strong |
| `RUNTIME_OBSERVATION` | faithful visibility of relevant actions, identities, data, and outcomes | none / simulator / adapter / system |
| `RUNTIME_DETECTION` | a specified runtime predicate detects the risk | none / candidate / implemented / evaluated |
| `PREVENTION` | an execution-side control denies or requires approval before effect | none / partial / evaluated |
| `IMPACT_MITIGATION` | containment, budgets, revocation, rollback, or blast-radius reduction | none / architectural / implemented / evaluated |
| `AUDITABILITY` | reconstructable evidence, provenance, rule/reason IDs, and versions | none / partial / strong |
| `EVIDENCE_QUALITY` | highest evidence level defined below | Level 0–5 |

A category can be strong in auditability and weak in prevention, or strong in static
discovery and absent at runtime. “Covered” must never collapse these distinctions.

## Current capability mapping

| SafetyBox component | Security property | Evidence boundary |
|---|---|---|
| `ReferenceMonitor` | execution-side authorization / complete-mediation research primitive | Level 2 unit evidence alone; reused by `FS-ADAPTER@1` in EXP-014 Level 4 named filesystem sub-properties, without complete-mediation evidence |
| `TaskContract` | task-scoped authority declaration | deterministic policy model, not an intent oracle |
| `Capability` | action/resource privilege scoping | implemented and unit tested; EXP-014 supplies named FMED-L1 real-tool evidence, while real deployment and bypass resistance remain absent |
| M3 audit/provenance | reconstructable decisions and events | repository tests; not a SIEM or forensic completeness claim |
| M5 | bounded sequence monitoring | EXP-009 Level 3 synthetic evidence with high FP |
| `TaskContext` / M5.1 | trusted semantic context | EXP-012 Level 3 clean synthetic evidence; incorrect/stale context remains a boundary |
| B2 | history-free context comparator | frozen analytical/executable baseline |
| B4 | bounded role/order/phase/fallback reasoning | EXP-013 Level 3 synthetic evidence: 38/40 pairs, 0/40 matched-negative FP |
| `FS-ADAPTER@1` | adapter-routed task/action/path authorization, real filesystem effect gating, and in-process audit | EXP-014 Level 4 for named FMED-L1 sub-properties: 94/94 adapter scenarios; direct routes, races, real agents, and production remain outside scope |
| EXP-015 subprocess mediation | frozen direct executable/argv adapter and one-shot Corpus@2 evaluation | Level 3 exact authorization and denied-forwarding evidence under low independence; Level 2 execution semantics because all positives stopped before spawn; no shell, descendant, bypass-control, or production evidence |

These components expose potentially useful controls for OWASP risks; they do not solve a
category directly.

## OWASP LLM/GenAI 2026 mapping

`SD`, `SDet`, `RO`, `RDet`, `P`, `IM`, `A`, and `E` abbreviate the eight coverage
dimensions. “L3 sub-property” means held-out synthetic evidence exists for only the
specified SafetyBox behavior, not the entire OWASP risk.

| Risk | Strategic status | SD | SDet | RO | RDet | P | IM | A | E | Boundary / next primitive |
|---|---|---|---|---|---|---|---|---|---|---|
| LLM01 Prompt Injection | `ARCHITECTURALLY_RELEVANT`, `REQUIRES_AI_ANALYSIS`, `FUTURE_RESEARCH` | candidate | none | simulator | none | partial authority only | partial blast-radius candidate | partial | L0 | SafetyBox may constrain consequences, but does not detect injected language or prove attack origin. |
| LLM02 Sensitive Information Disclosure | `PARTIALLY_ADDRESSED`, `SUPPORTED_BY_CURRENT_EVIDENCE`, `REQUIRES_STATIC_SCANNER`, `REQUIRES_RUNTIME_EXTENSION`, `REQUIRES_DATA_LINEAGE` | candidate | none | adapter for one filesystem boundary | none | evaluated denied-retrieval gate | partial measured-channel mitigation | partial | L4 named sub-property | EXP-014 found no protected value/call in 9/9 denied filesystem retrievals across evaluated channels. No causal lineage, broad disclosure detection, process/debug-channel completeness, or real-agent evidence. |
| LLM03 Excessive Agency | `PARTIALLY_ADDRESSED`, `SUPPORTED_BY_CURRENT_EVIDENCE`, `REQUIRES_RUNTIME_EXTENSION` | candidate | none | adapter for one filesystem boundary | evaluated represented authorization | evaluated FMED-L1 filesystem prevention | task-scope mitigation | strong within tested audit | L4 named sub-property | EXP-014 adds held-out real-tool evidence for represented filesystem action/resource limits. Direct routes bypass and no real-agent or whole-risk claim follows. |
| LLM04 Supply Chain | `REQUIRES_STATIC_SCANNER`, `OUT_OF_CORE_SCOPE` | none | none | none | none | none | none | none | L0 | Needs SBOM/AIBOM, dependency/config provenance, signature and vulnerability tooling. |
| LLM05 Data and Model Poisoning | `REQUIRES_STATIC_SCANNER`, `REQUIRES_AI_ANALYSIS`, `OUT_OF_CORE_SCOPE` | none | none | none | none | none | none | none | L0 | Training/data governance and model assurance are outside the current runtime core. |
| LLM06 Unbounded Consumption | `ARCHITECTURALLY_RELEVANT`, `REQUIRES_RUNTIME_EXTENSION` | candidate | none | partial | candidate | none | budget/circuit-breaker candidate | partial | L0 | Requires cost/token/tool-call/time budgets and containment evaluation. |
| LLM07 Misinformation | `REQUIRES_AI_ANALYSIS`, `OUT_OF_CORE_SCOPE` | none | none | none | none | none | none | partial provenance only | L0 | Factuality and epistemic validation are not deterministic authority checks. |
| LLM08 Hidden Context Exposure | `REQUIRES_STATIC_SCANNER`, `REQUIRES_DATA_LINEAGE` | candidate | none | none | none | capability candidate | partial | partial | L0 | Needs discovery of prompts/memory/tool schemas plus output/data-flow tracing. |
| LLM09 Vector and Embedding Weaknesses | `REQUIRES_STATIC_SCANNER`, `REQUIRES_AI_ANALYSIS`, `OUT_OF_CORE_SCOPE` | none | none | none | none | none | none | none | L0 | Needs RAG/vector-store configuration, tenant isolation, retrieval, and poisoning analysis. |
| LLM10 Improper Output Handling | `REQUIRES_STATIC_SCANNER`, `REQUIRES_RUNTIME_EXTENSION`, `REQUIRES_DATA_LINEAGE` | candidate | none | none | none | none | none | partial | L0 | Needs source-to-sink discovery, validation/sanitization facts, and mediated sinks. |

## OWASP Agentic Applications 2026 mapping

| Risk | Strategic status | SD | SDet | RO | RDet | P | IM | A | E | Boundary / next primitive |
|---|---|---|---|---|---|---|---|---|---|---|
| ASI01 Agent Goal Hijack | `ARCHITECTURALLY_RELEVANT`, `REQUIRES_AI_ANALYSIS`, `FUTURE_RESEARCH` | candidate | none | simulator actions | none | authority boundary only | partial | partial | L0 | No prompt/goal manipulation detector; runtime policy may limit consequences. |
| ASI02 Tool Misuse & Exploitation | `PARTIALLY_ADDRESSED`, `SUPPORTED_BY_CURRENT_EVIDENCE`, `REQUIRES_RUNTIME_EXTENSION` | candidate | none | adapter for one filesystem boundary | evaluated registered filesystem misuse | evaluated FMED-L1 filesystem prevention | partial | strong within tested audit | L4 named sub-property | EXP-014 covers registered adapter-routed filesystem misuse/alias cases only. Shell, network, MCP, direct APIs, races, exploit breadth, and real agents remain absent. |
| ASI03 Identity & Privilege Abuse | `PARTIALLY_ADDRESSED`, `SUPPORTED_BY_CURRENT_EVIDENCE`, `REQUIRES_RUNTIME_EXTENSION` | candidate | none | adapter task binding | policy decisions | evaluated represented task/capability gate | scope reduction candidate | strong within tested audit | L4 named filesystem sub-property; L2/L3 elsewhere | EXP-014 includes task mismatch and scoped capabilities, but no real identity provider, authentication, credential broker, delegation, or NHI lifecycle integration. |
| ASI04 Agentic Supply Chain Vulnerabilities | `REQUIRES_STATIC_SCANNER`, `OUT_OF_CORE_SCOPE` | none | none | none | none | none | none | none | L0 | Requires component/tool/MCP inventory, provenance, signatures, and dependency intelligence. |
| ASI05 Unexpected Code Execution (RCE) | `PARTIALLY_ADDRESSED`, `REQUIRES_STATIC_SCANNER`, `REQUIRES_RUNTIME_EXTENSION` | candidate | none | frozen process adapter; zero held-out children | exact authorization evaluated | denied pre-spawn forwarding evaluated | none | attempt schema evaluated on early paths | L3 named authorization sub-property; L2 execution semantics | EXP-015 matched 120/120 same-team synthetic task/action/resource decisions and prevented 60/60 denied spawn forwards, but non-ELF fixtures left real child execution, shell grammar, descendants, sandbox boundaries, direct routes, and real exploit tests unestablished. |
| ASI06 Memory & Context Poisoning | `REQUIRES_AI_ANALYSIS`, `REQUIRES_RUNTIME_EXTENSION`, `FUTURE_RESEARCH` | candidate | none | none | none | none | none | partial | L0 | TaskContext is trusted input, not a detector for poisoned memory or context. |
| ASI07 Insecure Inter-Agent Communication | `REQUIRES_STATIC_SCANNER`, `REQUIRES_RUNTIME_EXTENSION` | candidate | none | none | none | capability candidate | none | partial | L0 | Needs agent identity, signed messages, protocol mediation, and trust-delegation semantics. |
| ASI08 Cascading Failures | `ARCHITECTURALLY_RELEVANT`, `REQUIRES_RUNTIME_EXTENSION`, `FUTURE_RESEARCH` | candidate | none | single-agent simulator | none | none | containment candidate | partial | L0 | Requires multi-agent graph, propagation telemetry, quarantine/revocation, and recovery tests. |
| ASI09 Human-Agent Trust Exploitation | `REQUIRES_AI_ANALYSIS`, `OUT_OF_CORE_SCOPE` | candidate | none | none | none | approval boundary candidate | none | partial | L0 | SafetyBox can make approvals auditable, not determine deception or human susceptibility. |
| ASI10 Rogue Agents | `ARCHITECTURALLY_RELEVANT`, `REQUIRES_RUNTIME_EXTENSION`, `REQUIRES_AI_ANALYSIS` | candidate | none | none | none | identity/authority candidate | quarantine candidate | partial | L0 | Needs agent identity, attestation, behavior baselines, revocation, and multi-agent evidence. |

## Future scanner architecture

The scanner should compile evidence for runtime enforcement; it must not become an
unreviewed authority generator.

```text
Repository
  -> Deterministic Project Discovery
  -> AST / config / dependency / agent / tool extraction
  -> AI System Graph
  -> AI Semantic Analysis
  -> Structured Evidence
  -> OWASP Evidence Engine
  -> Runtime Context Compiler
  -> human/policy approval boundary
  -> SafetyBox runtime
```

### Evidence types

- `FACT`: directly observed source/config/runtime value with location, parser, hash, and
  version.
- `DETERMINISTIC_DERIVATION`: reproducible result from facts, such as a call edge, granted
  scope, or source-to-sink path under documented semantics.
- `AI_INFERENCE`: probabilistic interpretation with model/prompt/version, confidence,
  alternatives, and supporting facts.
- `HYPOTHESIS`: unverified security proposition queued for testing.
- `AUTHORITY`: approved policy/context value issued by a trusted human/system process.

Only `AUTHORITY` may grant or expand runtime permission. Facts and deterministic
derivations may enforce existing authority. AI inference may propose context or findings,
but it cannot silently become authority.

### Deterministic discovery

Candidate extractors include language/package manifests, AST call sites, framework agent
definitions, prompts, tool registries, MCP configuration, endpoints, credentials
references, stores, datasets, model providers, policies, deployment manifests, and
logging paths. Each extractor must report unsupported languages/config forms and retain
file/line/hash provenance.

### AI semantic analysis

AI can interpret tool purpose, data sensitivity, likely roles, task workflows, suspicious
architectural patterns, and candidate `TaskContext`. Its output must use a schema that
separates observations from inference and requires deterministic or human validation
before runtime trust.

### OWASP evidence engine

The engine should map individual evidence records to risk sub-properties and coverage
dimensions. It must report both supporting and missing evidence, distinguish vulnerability
presence from attack success, and attach the evidence level. It must never emit a bare
“OWASP covered” boolean.

## AI role boundary

### AI for understanding. Determinism for authority.

AI may:

- interpret repositories and task descriptions;
- infer candidate semantic roles and system-graph relations;
- identify suspicious architectural patterns;
- propose `TaskContext` and B4 declarations for approval;
- analyze trajectories and explain deterministic findings; and
- prioritize hypotheses and missing evidence.

AI may not:

- grant itself authority or add a capability;
- expand a `TaskContract`;
- bypass deterministic denial;
- silently convert an inference into trusted context;
- alter evidence provenance; or
- execute protected tools merely because it recommends an action.

Any AI-proposed context must preserve the source facts, inference provenance, reviewer or
issuer, approval event, version, and expiry/revision behavior.

## AI system graph

The conceptual graph may contain:

`Agent`, `Model`, `Prompt`, `Tool`, `MCPServer`, `API`, `Database`, `VectorStore`,
`Dataset`, `File`, `Secret`, `ExternalService`, `Policy`, `Task`, and `Capability`.

Candidate edges include:

`CAN_CALL`, `READS`, `WRITES`, `RETRIEVES_FROM`, `SENDS_TO`, `DEPENDS_ON`,
`AUTHENTICATES_WITH`, `PRODUCES`, `CONSUMES`, `AUTHORIZED_FOR`, and
`OBSERVED_ACCESS`.

Each node/edge must carry evidence type, source location or runtime event, confidence
where applicable, version, and trust authority. Conflicting static and runtime edges must
coexist rather than being overwritten. Graph storage and query implementation are out of
scope for this document.

## Static, runtime, and hybrid findings

- `STATIC`: established entirely from repository/config facts or deterministic
  derivations. Example: an LLM-output value directly reaches a subprocess call without a
  visible validation boundary.
- `RUNTIME`: established entirely from mediated execution evidence. Example: an agent
  exceeds a declared fallback progression.
- `HYBRID`: needs both scanner context and runtime events. Example: static discovery marks
  a resource as sensitive and an external destination as untrusted; runtime observes the
  agent access that resource before sending to that destination.

Hybrid findings are strategically important because static analysis can name assets and
potential paths while runtime can establish which operations occurred. They still must
not claim causal data transfer unless lineage evidence connects the values.

## Data-lineage gap

SafetyBox currently reasons about observed role, grouping, phase, and order relationships.
B4 explicitly records `logical_lineage_available=false` for the evaluated findings. Event
order does not prove that bytes or fields obtained from one resource influenced a later
payload.

Future sensitive-information-disclosure and output-handling claims require a data-lineage
milestone. Candidate research layers are adapter-emitted field/value provenance,
structured transformation IDs, taint or information-flow tracking at selected boundaries,
cryptographic/content references where safe, and conservative unknown-lineage states.
Lineage itself must be bounded, privacy-aware, and evaluated with counterfactual cases
where order is identical but actual flow differs.

## OWASP evidence standard

| Level | Required evidence | Permitted wording |
|---|---|---|
| Level 0 | architecture or threat-model relevance only | “architecturally relevant to…” |
| Level 1 | detector/control implemented with versioned semantics | “implements a candidate control for…” |
| Level 2 | unit and adversarial component tests | “unit-tested for specified cases…” |
| Level 3 | preregistered held-out synthetic evaluation with positives, matched negatives, FP measurement, and frozen artifacts | “supported on named synthetic benchmark…” |
| Level 4 | real-system evaluation with real tools/agents, bypass/failure analysis, and operational metrics | “evaluated on named real systems…” |
| Level 5 | external replication or design-partner evidence under a documented protocol | “replicated/observed by…” |

Every claim must name the risk sub-property, coverage dimensions, detector/control
version, benchmark/system, level, negative evidence, and limitations. A Level 3 result for
runtime detection cannot be presented as Level 3 prevention or whole-category coverage.

## Future security benchmark program

A governed future family may use the naming pattern `OWASP-SB-001` through
`OWASP-SB-NNN`; this document does not allocate an ID. Governance should require each
registration to state:

- taxonomy/version and exact risk sub-property;
- static, runtime, or hybrid condition;
- attack-success and detection outcomes as separate variables;
- positive cases and matched hard negatives;
- counterfactual pairs where one intended security variable changes;
- preregistered metrics, thresholds, stopping rules, and exclusions;
- false-positive and abstention measurement;
- mitigation/prevention evaluation where claimed;
- context correctness, staleness, and issuer assumptions;
- real versus synthetic evidence level; and
- frozen code, corpus, labels, raw records, checksums, and independent review mechanism.

## Research dependency order

1. **Real tool mediation.** Establish faithful observation and execution-side control for
   real filesystem, subprocess/shell, and HTTP/network operations.
2. **Real agent harness and bypass testing.** Exercise complete mediation, normalization,
   failures, and audit reconstruction across at least one real agent stack.
3. **MCP interception and identity/provenance.** Add protocol-aware calls, servers,
   credentials, and trust boundaries.
4. **Data lineage.** Connect selected input/resource values to outputs conservatively.
5. **Noisy/incorrect context research.** Evaluate context compilers, issuer errors, and
   stale-but-consistent declarations.
6. **Longer-horizon and containment research.** Test eviction, summary semantics,
   budgets, restriction, revocation, and recovery.
7. **AI project scanner.** Build discovery and graph compilation once runtime schemas and
   evidence needs are grounded in real adapters.

This ordering favors scientific dependency over product breadth. A broad scanner built
first would generate architecture findings without validating SafetyBox's strongest
current differentiator: mediated runtime authority and history-aware behavior.

## Recommended implementation progression

1. real filesystem adapter;
2. real subprocess/shell adapter;
3. HTTP/network adapter;
4. MCP interception;
5. Python SDK;
6. real agent harness; and
7. AI project scanner.

No item is implemented by this plan.
