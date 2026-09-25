# SafetyBox mapping to the OWASP GenAI LLM Top 10 2026

## Status and version correction

This is a research mapping, not an OWASP certification or whole-category coverage claim.
It is separate from the Agentic Top 10 mapping because model/application risks and
agentic-effect risks have different mechanisms and evidence requirements.

The current official edition is **2026**, not 2025. The official OWASP publication page
is dated 2026-08-03, and OWASP's official source repository identifies the 2026 release
as current and the 2025 directory as the previous release. The 2026 edition renumbers
most entries and adds `LLM08:2026 Hidden Context Exposure`; therefore stale 2025 IDs must
not be reused as if they named the same categories.

## Source metadata

| Field | Value |
|---|---|
| Framework | OWASP Top 10 for Large Language Model Applications |
| Edition | 2026 |
| Official publication-page date | 2026-08-03 |
| Official publication | [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) |
| Canonical source repository | [GenAI-Security-Project/GenAI-LLM-Top10](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10) |
| Version-specific archival DOI | [10.5281/zenodo.22109015](https://doi.org/10.5281/zenodo.22109015) |
| SafetyBox mapping date | 2026-09-25 |

The risk summaries are concise paraphrases of the official list. The official repository
lists the current order as Prompt Injection, Sensitive Information Disclosure, Excessive
Agency, Supply Chain, Data and Model Poisoning, Unbounded Consumption, Misinformation,
Hidden Context Exposure, Vector and Embedding Weaknesses, and Improper Output Handling.

## Scope and classification

Each entry receives one primary fit classification:

| Classification | Meaning |
|---|---|
| `STRONG_NATURAL_FIT` | Task-scoped deterministic authorization and effect mediation directly address a material mechanism. |
| `PARTIAL_FIT` | SafetyBox can control a meaningful subset but requires major complementary controls. |
| `DETECTION_ONLY` | SafetyBox may host or consume findings but has no natural deterministic prevention control. |
| `IMPACT_MITIGATION_ONLY` | SafetyBox can bound some effects without detecting or preventing the underlying model/application risk. |
| `ARCHITECTURALLY_RELEVANT` | The architecture has a relevant trust boundary or future extension, but evidence/control is absent. |
| `OUT_OF_SCOPE` | The primary assurance problem belongs elsewhere. |

The categories are not forced into SafetyBox's scope. `AUTH-COVERAGE-001` is excluded as
held-out evidence because its final gate is `BLOCKED_BENCHMARK_LEAKAGE`.

## Evidence dimensions and levels

| Dimension | Meaning |
|---|---|
| `STATIC_DISCOVERY` | Inventory or source/config discovery of relevant components, data, permissions, and flows |
| `RUNTIME_OBSERVATION` | Faithful observation of requests, model/tool boundaries, primitive calls, and effects |
| `DETECTION` | A specified predicate for the named risk |
| `PREVENTION` | A trusted control prevents the named condition or protected effect |
| `IMPACT_MITIGATION` | Scope, isolation, budgets, revocation, rollback, or blast-radius reduction |
| `AUDITABILITY` | Reconstructable model/context/request/authority/decision/effect provenance |
| `EVIDENCE_QUALITY` | Highest maturity for the exact subclaim |

Evidence levels are: `0` architecture only; `1` implemented; `2` unit/development
tested; `3` preregistered held-out synthetic; `4` real-system/real-tool; `5` external or
design-partner. A component result does not transfer to an entire LLM risk.

## Current 2026 mapping

| OWASP ID | Threat | Primary fit | SafetyBox relevance | Current evidence | Experiment / next milestone | Explicit non-claim |
|---|---|---|---|---|---|---|
| LLM01:2026 | Prompt Injection | `IMPACT_MITIGATION_ONLY` | External task authority can remain unchanged when prompts alter model behavior; mediated effects may be bounded. | L0 prompt-injection mitigation; L2 authority separation; L4 only for named filesystem effects. | Pair clean/injected prompts in ASI01 family with constant authority and real effect observation. | Does not detect, remove, or solve prompt injection. |
| LLM02:2026 | Sensitive Information Disclosure | `PARTIAL_FIT` | Read and send capabilities, destinations, and mediated retrieval/egress can limit some disclosures; provenance may support audit. | L4 named denied filesystem retrieval channels only; no data lineage or egress coverage. | Network mediator plus read-to-send lineage benchmark. | No general confidentiality, noninterference, or complete-channel claim. |
| LLM03:2026 | Excessive Agency | `STRONG_NATURAL_FIT` | Least-authority TaskContracts, per-effect authorization, and mediators directly constrain actions and resources. | L4 named FMED-L1 subproperties; L3 process authorization/denied forwarding; no whole-risk evidence. | `AUTH-COVERAGE-002`, EXP-016, then `UNAUTHORIZED-EFFECT-001`. | Does not prove least authority, complete mediation, or safe behavior inside granted scope. |
| LLM04:2026 | Supply Chain | `PARTIAL_FIT` | Registered tool identity, signatures, provenance, and containment could reduce downstream impact. | L0 supply-chain control. | Tool/MCP identity and provenance spec; component substitution tests. | Does not validate models, packages, datasets, or third-party services. |
| LLM05:2026 | Data and Model Poisoning | `OUT_OF_SCOPE` | Runtime authority boundaries may limit downstream protected effects after poisoning. | L0; adjacent context non-authority interface at L2 is not poisoning evidence. | Only impact studies after context/data provenance exists. | Does not assure training, fine-tuning, model integrity, or dataset quality. |
| LLM06:2026 | Unbounded Consumption | `ARCHITECTURALLY_RELEVANT` | Future time, call-count, usage, and cost constraints could make budgets deterministic authority constraints. | L0 budgets; no consumption benchmark. | Authority V2 usage/time constraints plus loop/cost benchmark. | Does not currently prevent denial-of-wallet, token, compute, storage, or loop exhaustion. |
| LLM07:2026 | Misinformation | `OUT_OF_SCOPE` | Source/action provenance can improve audit, and authority gates may limit harmful effects of false outputs. | L0 misinformation control. | No core benchmark; integrate independent factuality controls only as untrusted evidence. | Does not establish truth, factuality, calibration, or epistemic reliability. |
| LLM08:2026 | Hidden Context Exposure | `PARTIAL_FIT` | Context and authority provenance plus read/egress mediation could limit disclosure; context must not be treated as authority. | L2 context/authorization separation; no hidden-context exposure or lineage evidence. | Hidden-context inventory and disclosure-channel benchmark after egress mediation. | Does not guarantee prompts, memory, reasoning traces, or hidden metadata remain secret. |
| LLM09:2026 | Vector and Embedding Weaknesses | `OUT_OF_SCOPE` | Tenant/task-scoped retrieval authority could gate vector-store access, but retrieval correctness and poisoning need specialized controls. | L0. | Optional retrieval mediator only after core effect milestones. | Does not secure embeddings, ranking, vector databases, RAG quality, or tenant isolation today. |
| LLM10:2026 | Improper Output Handling | `PARTIAL_FIT` | Treat model output as untrusted proposal; typed validation and sink-specific authorization/mediation can stop some executable effects. | L3 process authorization/denied forwarding; L2 execution semantics; no output-validation or source-to-sink evidence. | EXP-016 plus model-output-to-process/filesystem sink families. | Does not sanitize outputs generally or secure unmediated renderers, SQL, shells, browsers, or interpreters. |

## Evidence-dimension matrix

| ID | STATIC_DISCOVERY | RUNTIME_OBSERVATION | DETECTION | PREVENTION | IMPACT_MITIGATION | AUDITABILITY | EVIDENCE_QUALITY |
|---|---|---|---|---|---|---|---|
| LLM01 | candidate prompt/context inventory | tool requests only | none | no injection prevention; bounded authority gate | task/resource scope candidate | partial decision/effect audit | L0 risk; L4 named adjacent effect subproperty |
| LLM02 | candidate sensitive-resource inventory | L4 filesystem retrieval channels; no egress | represented denied read only | L4 denied FMED-L1 retrieval | narrow read scope | partial; no value lineage | L4 named subproperty, not disclosure category |
| LLM03 | candidate tools/capabilities | L4 filesystem; incomplete process | represented authority mismatch | L4 named filesystem; L3 denied process forwarding | task/action/resource scope | strong inside tested envelopes | L4 named subproperty |
| LLM04 | none | none for component trust | none | none for compromise | downstream containment candidate | tool version/hash absent | L0 |
| LLM05 | none | none | none | none | downstream authority ceiling candidate | no data/model provenance | L0 |
| LLM06 | candidate call/constraint inventory | partial event counts only | no budget predicate | none | budget/revocation candidate | partial action events | L0 |
| LLM07 | candidate source inventory | none for truth | none | none | mediated-effect ceiling candidate | partial source/effect provenance direction | L0 |
| LLM08 | candidate context inventory | structured context only | none | no exposure control | context non-authority at L2 | partial context/decision separation | L2 adjacent subproperty; L0 exposure |
| LLM09 | none | none | none | none | retrieval-scope candidate | none | L0 |
| LLM10 | candidate sink inventory | process early paths; filesystem effects | represented authorization/validation only | named mediated sinks only | sink scope candidate | partial request-to-sink audit | L0 risk; L3/L4 adjacent sink subproperties |

## Category analyses

### LLM01:2026 — Prompt Injection

Prompt injection manipulates model behavior through direct or indirect instructions. The
model-level distinction between data and instruction is not a SafetyBox authority source.
The natural SafetyBox contribution is consequence bounding: injected text may change a
proposal, but must not change external task authority. This becomes measurable through
clean/injected counterfactual pairs with identical TaskContracts and independent effect
observation. A successful result would support only the unauthorized-effect component
within named mediators, not prompt-injection detection or prevention.

### LLM02:2026 — Sensitive Information Disclosure

SafetyBox can contribute when disclosure requires a protected read or send effect. Exact
resource and destination capabilities, network mediation, and causal data lineage would
be required for a serious claim. EXP-014 supplies bounded evidence that registered denied
filesystem retrievals did not invoke the protected primitive or expose the protected
result through the measured caller/error/audit channels. It does not cover process,
debug, memory, model output, browser, network, timing, or other channels, and it does not
prove causal noninterference.

### LLM03:2026 — Excessive Agency

This is SafetyBox's strongest natural LLM fit. External least-authority objects and
execution-side mediation can constrain tools, actions, tasks, and resources without
depending on model compliance. The remaining scientific gap is substantial: least
authority must be compiled correctly, all relevant effect routes must be mediated, and
benign utility must remain high. Authorization accuracy, mediation bypass, unauthorized
effects, and benign completion must remain separate metrics.

### LLM04:2026 — Supply Chain

SafetyBox can eventually inventory and bind authority to exact registered tool/MCP
identities, require signed manifests, and constrain what a compromised component can do.
It is not a model, package, dataset, dependency, or artifact-assurance system. Even a
valid signature establishes identity/integrity, not benign behavior. Supply-chain
prevention remains with SBOM/AIBOM, build, signing, registry, vulnerability, and vendor
assurance systems; SafetyBox's plausible contribution is effect-side containment and
provenance.

### LLM05:2026 — Data and Model Poisoning

Training, fine-tuning, dataset governance, and model integrity are outside the core
runtime authority problem. Poisoned data or models may induce unauthorized requests, in
which case ordinary authority and mediation controls apply. That does not make those
controls poisoning defenses. The context-non-authority invariant is relevant only to the
narrow proposition that untrusted context cannot create permission.

### LLM06:2026 — Unbounded Consumption

Time windows, use counts, rate limits, token/tool-call/cost budgets, and circuit breakers
could be expressed as deterministic Authority V2 constraints. None is currently a proven
SafetyBox control. Future experiments must distinguish request denial, actual resource
consumption, cleanup, distributed fan-out, and benign completion; a call counter alone
does not prove bounded CPU, memory, network, storage, or spend.

### LLM07:2026 — Misinformation

Factuality is not an authorization property. SafetyBox may preserve source provenance,
label model assertions as untrusted, require approval for high-impact effects, or keep a
false answer from becoming an unauthorized mutation. It cannot determine general truth
with a deterministic authority check. Misinformation detection should remain a separate
model/evaluation discipline.

### LLM08:2026 — Hidden Context Exposure

The 2026 category broadens the concern beyond the old system-prompt framing. SafetyBox can
separate context provenance from authority provenance, avoid placing secrets in authority
objects, and later mediate sensitive reads and egress. It currently lacks complete context
inventory, secret classification, model-output channels, network mediation, and data
lineage. `TaskContext` being unable to grant authority is useful but is not evidence that
hidden context cannot be extracted.

### LLM09:2026 — Vector and Embedding Weaknesses

Specialized vector-store authorization, tenant isolation, ingestion integrity, retrieval
evaluation, metadata protection, and poisoning analysis are not implemented. A future
retrieval mediator could bind a query to task/tenant/index/namespace authority, but
similarity quality and embedding security remain outside SafetyBox's natural core. This
work should follow the filesystem/process flagship path rather than delay it.

### LLM10:2026 — Improper Output Handling

The trust-boundary rule is directly relevant: model output is a proposal, never executable
authority. Typed schemas, validation, and sink-specific reference monitors can stop some
unsafe outputs from becoming filesystem or process effects. EXP-015 did not demonstrate
successful real child execution, so it cannot support a general code-execution claim.
Future source-to-sink experiments must include shell, SQL, HTML/Markdown, browser, MCP,
and network sinks only when those mediators actually exist.

## Strategic summary

| Group | Categories | SafetyBox position |
|---|---|---|
| Strongest natural fit | LLM03 | Deterministic least-authority and mediated-effect research directly targets excessive agency. |
| Meaningful partial fit | LLM02, LLM04, LLM08, LLM10 | SafetyBox can control selected effect/provenance subproblems but needs egress, lineage, supply-chain, context, and sink controls. |
| Impact only | LLM01 | Bound unauthorized effects even when injection succeeds; do not claim injection detection. |
| Architecture direction | LLM06 | Deterministic budgets are plausible but unimplemented. |
| Outside natural scope | LLM05, LLM07, LLM09 | Model/data integrity, factuality, and vector/embedding assurance require distinct programs. |

## Stop conditions

Stop and narrow the claim if:

- an LLM risk is marked covered because one adjacent authorization check passed;
- a model/context detector is permitted to grant authority;
- missing network, browser, MCP, process, or direct routes are omitted from a disclosure
  or output-handling claim;
- event order is presented as causal data lineage;
- task-scoped authorization is presented as poisoning, factuality, or supply-chain
  prevention;
- the current 2026 identifier is assigned its former 2025 meaning; or
- evidence levels for authorization, mediation, effects, and attribution are collapsed.

## Permitted strongest summary

> SafetyBox is a strong natural research fit for the excessive-agency problem and a
> partial or impact-limiting fit for selected disclosure, prompt-injection consequence,
> supply-chain containment, hidden-context, and output-to-effect subproblems. It is not a
> general solution for model/data poisoning, misinformation, or vector/embedding
> weaknesses, and it currently makes no whole-category OWASP LLM claim.
