# SafetyBox mapping to the OWASP Top 10 for Agentic Applications 2026

## Status and claim boundary

This is a research-control mapping and experiment agenda. It is not an OWASP
certification, a deployment assurance statement, or a claim that SafetyBox covers any
whole OWASP category.

The organizing claim is deliberately narrower:

> SafetyBox may provide deterministic mitigation for the unauthorized-effect component
> of an agentic risk when the relevant effect is inside a named, tested mediation
> boundary.

Authorization, mediation, effect correctness, and attribution are separate evidence
domains. A correct policy decision does not prove that every effect route is mediated;
an intercepted call does not prove the resulting effect; and an audit event does not by
itself prove either. No aggregate "OWASP coverage" score is defined.

`AUTH-COVERAGE-001` contributes methodology and failure-analysis evidence only. Its final
gate is `BLOCKED_BENCHMARK_LEAKAGE`; it is not held-out evidence and is not used to raise
an evidence level in this document.

## Source metadata

| Field | Value |
|---|---|
| Framework | OWASP Top 10 for Agentic Applications |
| Edition | 2026 |
| Official publication date | 2025-12-09 |
| Official publication | [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) |
| Release context | [OWASP launch article](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) |
| SafetyBox mapping date | 2026-09-25 |

The threat summaries below are paraphrases of the official publication. The publication
defines the list as a practical starting framework for risks in autonomous systems; this
mapping does not convert that taxonomy into product certification.

The Agentic 2026 publication predates the August 2026 LLM edition and therefore contains
cross-references to `LLMxx:2025`. Those references are preserved as source history, not
silently renumbered. SafetyBox's current LLM mapping uses the separately published 2026
list and its changed identifiers; see
[`SAFETYBOX_OWASP_LLM_2026_MATRIX.md`](SAFETYBOX_OWASP_LLM_2026_MATRIX.md).

## Evidence model

Every mapped subclaim reports these dimensions independently:

| Dimension | Question |
|---|---|
| `STATIC_DISCOVERY` | Can relevant tools, resources, identities, dependencies, authority, and unmediated routes be inventoried from artifacts? |
| `RUNTIME_OBSERVATION` | Are requests, decisions, primitive invocations, effects, and outcomes faithfully observed? |
| `DETECTION` | Is there an explicit predicate that identifies the named threat or policy violation? |
| `PREVENTION` | Does a trusted execution-side control stop the named effect before it begins? |
| `IMPACT_MITIGATION` | Are scope, budgets, isolation, revocation, or recovery shown to limit harm? |
| `AUDITABILITY` | Can the effect and decision be reconstructed and tied to task-scoped authority? |
| `EVIDENCE_QUALITY` | What is the highest maturity level for the exact subclaim, not the category? |

Evidence maturity is:

| Level | Meaning |
|---|---|
| 0 | Architecture or research hypothesis only |
| 1 | Implemented |
| 2 | Unit/development tested |
| 3 | Preregistered held-out synthetic evidence |
| 4 | Real-system or real-tool evidence |
| 5 | External or design-partner evidence |

When a cell lists multiple levels, it names different subclaims. For example, `L0
ASI-specific; L4 bounded filesystem effect gate` does not promote the ASI category to
Level 4.

## Priority

Priority reflects fit with SafetyBox's deterministic authority/effect thesis and the
dependency path to credible evidence, not OWASP severity ranking.

| Priority | Categories | Rationale |
|---|---|---|
| P1 — direct near-term validation | ASI02, ASI05 | Tool and direct-process effects map most directly to existing filesystem/process mediators. |
| P1 — core thesis after benchmark foundations | ASI01, ASI06, ASI10 | These test whether changed or malicious AI behavior remains bounded by unchanged external authority. |
| P2 — architecture prerequisites | ASI03, ASI07, ASI08 | Need authenticated identity, delegation, inter-agent mediation, and graph-level propagation semantics. |
| P3 — bounded contribution | ASI04, ASI09 | SafetyBox can constrain effects and improve provenance, but supply-chain assurance and human manipulation need other disciplines. |

## Control matrix

| OWASP ID | Threat | Attack mechanism | SafetyBox control | Authorization relevance | Mediation relevance | AI-analysis relevance | Current implementation | Evidence level | Experiment | Known bypass | Next milestone | Claim status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASI01 | Agent Goal Hijack | Prompt, retrieved content, tool output, or messages redirect goals and plans. | Immutable task-scoped authority; deterministic per-effect checks. | High: changed intent must not expand authority. | High for any claim about stopped effects. | Useful for detecting goal drift, never for granting authority. | TaskContract/capability boundary exists; no goal-hijack detector or dedicated benchmark. | L0 ASI-specific; L2 authority-boundary tests; L4 only for named FMED-L1 effects. | `OWASP-AGENTIC-BENCH-001/ASI01` counterfactual goal-hijack family. | Any direct/unmediated tool route; incorrect pre-granted contract. | Freeze clean/hijacked paired scenarios after mediation baselines. | `RESEARCH_TARGET`; no ASI01 mitigation claim yet. |
| ASI02 | Tool Misuse & Exploitation | A legitimate tool is used with an unauthorized action, resource, task, combination, or payload. | TaskContract, scoped capabilities, reference monitor, effect-specific mediators. | Primary natural fit. | Primary: authorization is ineffective if the tool can be reached directly. | Can classify tool semantics or suspicious chains; cannot authorize. | Filesystem adapter evaluated; process adapter has bounded authorization/denied-forwarding evidence; network/MCP absent. | L4 named FMED-L1 subproperties; L3 process authorization/denied forwarding; no category level. | `OWASP-AGENTIC-BENCH-001/ASI02` plus `UNAUTHORIZED-EFFECT-001`. | Shell, direct OS APIs, descendants, network/MCP, races, unregistered aliases. | Complete EXP-016, then filesystem+process unauthorized-effect benchmark. | `BOUNDED_SUBPROPERTY_EVIDENCE`; no whole-category claim. |
| ASI03 | Identity & Privilege Abuse | Credentials, delegation, cached context, role inheritance, or confused-deputy flows cross identity/privilege boundaries. | Future principal/agent/session/task binding; attenuation; expiry; revocation; per-action authorization. | High, but `task_id` equality is not identity authentication. | High: credentials and effects must be bound at the actual primitive. | Can flag anomalous chains, not authenticate an identity. | Task binding and scoped capability checks exist; authenticated identity, credential broker, delegation lifecycle absent. | L0 identity claim; L4 named filesystem task-binding subproperties; L3 process task binding. | Identity-binding and cross-task/cross-principal reuse benchmark. | Forged identity input, shared credentials, inherited tokens, direct service calls. | Specify Authority V2 identities and trusted issuer/binding protocol. | `MAJOR_GAP`; task binding must not be restated as identity security. |
| ASI04 | Agentic Supply Chain Vulnerabilities | Malicious or altered models, tools, MCP servers, agents, descriptors, packages, prompts, data, or update channels enter the execution chain. | Future inventory, signed/registered tool identity, provenance, capability limits, containment. | Medium: trusted tool identity constrains what authority names. | High for containing compromised components at effect boundaries. | Useful for semantic inventory/anomaly analysis, not artifact trust. | No SBOM/AIBOM, signature validation, registry trust, or dependency scanner. | L0 category; L4 only for unrelated bounded containment subproperty. | Signed-tool substitution and compromised-tool containment scenarios after tool identity exists. | Compromised mediator/runtime, validly signed malicious tool, unmediated dependency behavior. | Tool/MCP identity registry and provenance spec. | `PARTIAL_FIT`; prevention of supply-chain compromise is out of core scope. |
| ASI05 | Unexpected Code Execution | Generated text, shell interpretation, unsafe evaluation/deserialization, packages, or tool chains produce unintended code execution. | Native argv process mediator, executable/cwd/action authority, no shell interpretation, effect provenance. | High for which executable/action/task/cwd is allowed. | Essential: spawn and downstream effect routes determine the claim. | Can analyze code or risk, but cannot approve execution. | `PROC-ADAPTER@1`; EXP-015 did not reach an allowed child; EXP-016 Protocol@2 is frozen pre-corpus infrastructure. | L3 process authorization/denied forwarding; L2 execution semantics; L0 ASI05 claim. | EXP-016 followed by process families in `UNAUTHORIZED-EFFECT-001`. | Direct spawn APIs, shell routes, child descendants, interpreters, JIT/eval, sandbox escape. | Execute a valid blinded EXP-016 native-child corpus. | `RESEARCH_TARGET`; no real process-execution containment claim. |
| ASI06 | Memory & Context Poisoning | Persistent memory, summaries, embeddings, RAG, or peer inputs corrupt later planning and tool selection. | Context is evidence only; TaskContract remains the sole authority input; deterministic authorization preservation. | Primary desired property: context cannot create authority. | High when poisoned context induces real actions. | Appropriate for poisoning detection and explanation, never authority creation. | Context/trajectory components are separated from authorization and unit tested; no poisoned-memory ingestion control. | L2 context-non-authority interface; L3 B4 synthetic discrimination is not poisoning evidence; L0 category. | `CONTEXT-AUTH-001` clean/poisoned counterfactual benchmark. | Poisoned trusted issuer/input, unsafe memory evaluator, direct effects, overly broad pre-existing authority. | Specify and preregister `CONTEXT-AUTH-001`. | `BOUNDED_ARCHITECTURAL_CONTROL`; no poisoning detection claim. |
| ASI07 | Insecure Inter-Agent Communication | Spoofing, replay, tampering, descriptor forgery, downgrade, or semantic confusion changes inter-agent requests/delegation. | Future signed delegation, sender provenance, receiver/audience scope, nonce/replay rules, attenuation. | High: a message must not itself grant authority. | High: message intake and downstream effects both require mediation. | May interpret semantic mismatch; cannot establish sender identity or authority. | No inter-agent identity, signed message, protocol mediator, or delegation chain. | L0. | Forged/replayed/over-broad delegation scenario family. | Stolen signing key, unsigned side channels, confused deputy, unmediated peer calls. | Authority V2 delegation and authenticated message envelope spec. | `MAJOR_GAP`; architecturally relevant only. |
| ASI08 | Cascading Failures | A fault or compromise propagates and amplifies across agents, tasks, tools, or systems. | Task isolation, attenuation, quotas/circuit breakers, revocation, causal effect lineage. | High for bounding transferable authority and cross-task spread. | High across every propagation edge. | Useful for anomaly/cascade detection; cannot expand containment authority. | Single-agent/task primitives only; no cascade graph, propagation controls, or recovery model. | L0 category. | Multi-agent fan-out benchmark measuring propagation and blast radius. | Shared credentials, broad contracts, unmediated edges, asynchronous in-flight work. | Define `MAXIMUM_AUTHORIZED_BLAST_RADIUS`, propagation, and containment semantics. | `RESEARCH_TARGET`; no cascade containment claim. |
| ASI09 | Human-Agent Trust Exploitation | Persuasive or deceptive outputs induce unsafe disclosure or approval. | Approval must create versioned external authority; show exact authority delta; provenance and staged/reversible effects. | Medium: human assent must be authenticated, scoped, and explicit. | High once approval produces a protected effect. | Can summarize risk; must not be the approving principal or sole explanation source. | Audit primitives exist; approval authority creation and safe approval UI do not. | L0 category; L2 bounded audit components only. | Approval-provenance and authority-delta usability/security study. | Rubber-stamping, compromised approver session, dark patterns, action disguised as preview. | Formal approval-as-authority protocol before UI experiments. | `PARTIAL_FIT`; persuasion detection is not a core SafetyBox claim. |
| ASI10 | Rogue Agents | A compromised or misaligned agent persistently deviates, deceives, colludes, self-propagates, or pursues harmful goals. | External deterministic authority ceiling plus broad effect mediation, identity, revocation, and provenance. | Central thesis: misbehavior must not expand authority. | Decisive: a broad claim requires broad and bypass-resistant mediator coverage. | Useful for behavioral detection; its judgment cannot be the security root. | Bounded filesystem mediation and authorization primitives exist; no rogue-agent, collusion, self-replication, or broad mediator evidence. | L0 ASI10; L4 named FMED-L1 subproperties; L3 process authorization only. | Deliberately adversarial agent maximizing boundary pressure after real-agent harness. | Any unmediated effect, excessive valid authority, compromised monitor, collusion through uncovered channels. | `UNAUTHORIZED-EFFECT-001`, then real-agent adversarial harness. | `CORE_THESIS_UNPROVEN`; prohibit global rogue-agent containment claims. |

## Evidence-dimension matrix

`none` means no current SafetyBox evidence. `candidate` means an architectural direction,
not implementation. Levels refer only to the exact text in the cell.

| ID | STATIC_DISCOVERY | RUNTIME_OBSERVATION | DETECTION | PREVENTION | IMPACT_MITIGATION | AUDITABILITY | EVIDENCE_QUALITY |
|---|---|---|---|---|---|---|---|
| ASI01 | candidate task/tool inventory | adapter-routed requests only | no goal-hijack predicate | L2 policy boundary; L4 named filesystem effects | candidate task scope | partial in-process audit | L0 ASI-specific |
| ASI02 | candidate registered-tool inventory | L4 filesystem; incomplete process | represented authorization violations only | L4 FMED-L1; L3 denied process forwarding | task/resource scoping | strong only inside tested envelopes | L4 named subproperty |
| ASI03 | candidate identity graph | task/session fields, not authenticated identity | represented task mismatch | represented task/capability gates | candidate least-authority scope | partial, unauthenticated attribution | L0 identity; L4 named task subproperty |
| ASI04 | none | none for artifact trust | none | none for compromise; bounded downstream gate only | candidate containment | partial effect-side audit | L0 category |
| ASI05 | candidate executable inventory | zero held-out child executions in EXP-015 | represented authorization/validation states | L3 denial before spawn only | none for executed hostile code | early-path attempt records | L0 category; L2 execution semantics |
| ASI06 | candidate context-source inventory | structured context/trajectory only | no poisoning predicate | L2 context cannot override authorization interface | authority remains external under tested interface | partial context/decision events | L2 subproperty; L0 category |
| ASI07 | none | none | none | none | candidate attenuation | none for message lineage | L0 |
| ASI08 | none | single-session observations only | no cascade predicate | none | candidate task boundaries | no causal multi-agent lineage | L0 |
| ASI09 | candidate approval inventory | none | no deception predicate | no approval gate | candidate staged/reversible effects | partial action audit, no approval provenance | L0 category |
| ASI10 | candidate agent/tool inventory | bounded adapter requests | no rogue-behavior predicate | only named mediated effects | candidate authority ceiling | partial, no cryptographic agent identity | L0 category |

## A–K category analyses

The following fixed dimensions are used for every category:

- **A — threat definition**
- **B — relevant SafetyBox control**
- **C — deterministic prevention potential**
- **D — detection potential**
- **E — impact-limitation potential**
- **F — audit potential**
- **G — current implementation status**
- **H — current evidence level**
- **I — missing components**
- **J — experiment needed**
- **K — explicit non-claim**

### ASI01 — Agent Goal Hijack

- **A.** Untrusted prompts, retrieved content, tool output, or messages redirect an
  agent's objectives, planning, or multi-step behavior.
- **B.** Keep the TaskContract and capabilities external to model context; authorize the
  resulting action/resource request independently of the agent's stated intent.
- **C.** High for unauthorized protected effects inside complete mediation. A hijacked
  goal can still choose harmful actions that were legitimately pre-authorized.
- **D.** AI or trajectory analysis can flag goal divergence, but detection is secondary
  to the deterministic authority ceiling.
- **E.** Narrow task/action/resource scopes limit the reachable blast radius.
- **F.** Record original task, request, authority, decision, mediator, primitive, and
  effect so changed intent can be distinguished from changed authority.
- **G.** The authority boundary exists. Goal-hijack detection, model/context mutation,
  and real-agent paired scenarios do not.
- **H.** Level 0 for ASI01; Level 2 for bounded authority separation; Level 4 applies
  only to named filesystem mediator subproperties.
- **I.** Trusted contract issuance, goal/context mutation harness, broader mediators,
  full effect provenance, and independent paired corpus authorship.
- **J.** Hold authority constant across clean and hijacked prompts/context while changing
  requested actions. Measure authority changes (expected zero), false allow/deny,
  primitive forwarding, unauthorized effects, benign completion, and attribution.
- **K.** SafetyBox does not detect or solve goal hijacking. The future claim is only that
  goal hijack did not expand authority or produce unauthorized effects within evaluated
  mediated boundaries.

### ASI02 — Tool Misuse & Exploitation

- **A.** A legitimate tool is selected or composed unsafely, including wrong action,
  resource, task, arguments, destination, or cross-tool chain.
- **B.** Exact task/action/resource capabilities and effect-specific mediators.
- **C.** High for represented semantics and mediated primitives; low for semantic misuse
  that remains inside an overly broad grant.
- **D.** Deterministic mismatch detection is strong for modeled fields. AI may identify
  suspicious semantic combinations without controlling authorization.
- **E.** Tool/resource scopes, deny-before-primitive ordering, and future usage or
  destination constraints can bound impact.
- **F.** Per-component decisions and final effect records can reconstruct why a call was
  allowed and what primitive/outcome followed.
- **G.** Filesystem mediation is evaluated at FMED-L1. Process authorization has bounded
  evidence, but successful native-child semantics await EXP-016. Network and MCP are absent.
- **H.** Level 4 for named EXP-014 filesystem subproperties; Level 3 for EXP-015 process
  authorization/denied forwarding; no category evidence level.
- **I.** Cross-tool constraints, network/MCP mediators, direct-route controls, races,
  real agents, durable provenance, and compound-operation semantics.
- **J.** Counterfactual families: authorized tool/wrong action; right action/wrong
  resource; right call/wrong task; mixed-authority compound call; authorized first tool
  followed by unauthorized second tool; alias and direct-route attempts.
- **K.** SafetyBox does not solve tool vulnerabilities or all misuse; it can test
  deterministic prevention of unauthorized-effect subcases.

### ASI03 — Identity & Privilege Abuse

- **A.** Agent identities, credentials, delegation chains, cached context, or inherited
  roles are confused or abused to obtain or reuse privilege.
- **B.** A future trusted binding across principal, agent, session, task, authority
  issuer, delegation lineage, and each protected request.
- **C.** Potentially high only after authentication and credential use are mediated.
- **D.** Deterministic replay, audience, task, expiry, revocation, and attenuation checks;
  AI may flag anomalies but cannot authenticate principals.
- **E.** Per-task credentials, no cross-task reuse, short expiry, and revocation can limit
  privilege persistence.
- **F.** Attribute each effect to authenticated identities and the exact authority chain.
- **G.** Task IDs and capability checks exist. Identity proof, session-to-contract
  binding, credential brokerage, delegation, expiry, and revocation do not.
- **H.** Level 0 for identity assurance. Task mismatch evidence must remain explicitly
  separate.
- **I.** Identity provider trust root, non-human identity lifecycle, signed authority,
  token audience/use binding, key protection, and delegation semantics.
- **J.** Cross-principal, cross-session, cross-task, stale-token, replay, confused-deputy,
  and parent/child amplification cases with authenticated ground truth.
- **K.** `task_id` equality is not identity authentication, and task-scoped authorization
  must never be reported as solving ASI03.

### ASI04 — Agentic Supply Chain Vulnerabilities

- **A.** Third-party or dynamically discovered models, tools, agents, descriptors,
  prompts, data, packages, registries, or update channels are malicious or altered.
- **B.** Registered tool identities, signed manifests, inventory/provenance, capability
  restrictions, and effect containment.
- **C.** SafetyBox could reject unregistered components and constrain downstream effects;
  it cannot prove that a trusted component is benign.
- **D.** Static inventory/signature checks plus runtime identity/hash drift observation;
  AI findings remain untrusted evidence.
- **E.** Least authority and mediator isolation can reduce a compromised component's
  blast radius.
- **F.** Preserve tool version/hash, authority source, mediator, request, and outcome.
- **G.** Required supply-chain discovery and trust infrastructure is absent.
- **H.** Level 0.
- **I.** SBOM/AIBOM integration, artifact/tool/MCP identity, signatures/attestation,
  registry policy, dependency intelligence, update revocation, and sandboxing.
- **J.** Substitute signed, unsigned, stale, and lookalike tools; separately measure
  discovery, rejection, and effect containment after a trusted tool is compromised.
- **K.** SafetyBox does not prevent supply-chain compromise and should not replace
  dependency, artifact, model, or data assurance.

### ASI05 — Unexpected Code Execution

- **A.** Agent text or tool chains become unintended script, binary, interpreter,
  deserialization, JIT, package-install, or other executable behavior.
- **B.** Native direct-child execution with no shell interpretation; exact executable,
  cwd, argv, task, environment policy, mediator, and provenance.
- **C.** High for exact direct-child requests within PMED-L1; insufficient for descendant
  behavior, alternative execution engines, or sandbox escape.
- **D.** Deterministic executable/cwd/action checks and runtime child/effect observation;
  static/AI code review is complementary.
- **E.** Sandboxing, environment constraints, resource budgets, and child authority are
  future containment layers.
- **F.** Record executable identity, argv tuple, physical cwd, environment policy,
  authorizing capability, primitive invocation, PID/outcome, and descendant boundary.
- **G.** EXP-015 showed authorization and denied pre-spawn forwarding but produced zero
  held-out children. EXP-016 Protocol@2 is frozen without a held-out result.
- **H.** Level 3 for exact process authorization/denied forwarding; Level 2 execution
  semantics; Level 0 for ASI05 containment.
- **I.** Valid native corpus/run, environment policy, descendants, alternate spawn routes,
  executable identity integrity, sandbox and bypass evaluation.
- **J.** Complete EXP-016, then place allowed/denied native execution inside
  `UNAUTHORIZED-EFFECT-001` with independent primitive and OS-effect observation.
- **K.** SafetyBox has not demonstrated safe successful child execution, RCE prevention,
  shell safety, descendant confinement, or sandbox security.

### ASI06 — Memory & Context Poisoning

- **A.** Persistent or retrievable context is corrupted so later reasoning, planning, or
  tool selection becomes unsafe.
- **B.** Context may influence analysis but is structurally excluded from authority
  creation and cannot override deterministic denial.
- **C.** High for preventing authority expansion if the authority source is genuinely
  external and effects are mediated; no protection if poisoned data is itself treated as
  trusted authority.
- **D.** AI can compare context sources and trajectory semantics. Deterministic checks can
  prove authorization preservation without proving poisoning detection.
- **E.** Task isolation and context-source provenance can contain persistence and reuse.
- **F.** Record context source/version separately from authority source/version.
- **G.** Context/trajectory interfaces preserve prior authorization in unit tests. There
  is no memory ingestion monitor or poisoning benchmark.
- **H.** Level 2 for context non-authority interfaces; Level 0 for ASI06 detection or
  mitigation. B4 Level 3 evidence concerns a different subclaim.
- **I.** Memory source identity, trust labels, tenant/task isolation, poisoning oracle,
  ingestion/retrieval observation, and causal links to later requests.
- **J.** `CONTEXT-AUTH-001`: matched clean/poisoned memory and RAG records attempt to add
  resources/actions while the external contract stays constant. Authorization outputs
  must be identical unless the trusted authority input changes.
- **K.** SafetyBox does not detect poisoned memory or guarantee correct reasoning; it can
  test the narrower invariant that context cannot create authority.

### ASI07 — Insecure Inter-Agent Communication

- **A.** Real-time agent messages are spoofed, replayed, modified, misrouted, downgraded,
  or semantically confused.
- **B.** Authenticated typed envelopes plus signed, attenuated authority delegation with
  sender, receiver, audience, task lineage, expiry, and nonce binding.
- **C.** Strong potential for structural authorization/replay failures; semantic deception
  remains only partially deterministic.
- **D.** Signature, schema, audience, nonce, expiry, lineage, and subset checks are
  deterministic; AI can analyze semantic mismatch but not establish authority.
- **E.** Receiver scoping, one-hop/use limits, revocation, and per-agent isolation reduce
  propagation.
- **F.** End-to-end message and delegation provenance can tie downstream effects to the
  sender and parent authority.
- **G.** Not implemented.
- **H.** Level 0.
- **I.** Agent identities, key management, transport trust, message mediator, delegation
  semantics, replay state, and cross-agent effect lineage.
- **J.** Forged sender, altered audience, replayed grant, expired grant, excessive child
  scope, unsigned side channel, and semantic-confusion hard negatives.
- **K.** An agent message is not authority; SafetyBox currently provides no secure
  inter-agent communication claim.

### ASI08 — Cascading Failures

- **A.** An initial fault or compromise propagates and amplifies across agents, tasks,
  tools, or systems beyond the originating boundary.
- **B.** Per-task isolation, attenuated delegation, effect budgets, circuit breakers,
  revocation, and causal lineage.
- **C.** Deterministic ceilings can prevent unauthorized propagation at mediated edges;
  they do not prevent incorrect but authorized cascades.
- **D.** Graph-level rate, fan-out, task-boundary, repeated-intent, and authority-spread
  predicates; AI may help interpret anomalies.
- **E.** This is the primary value: constrain maximum reachable effects and stop further
  issuance/reuse after revocation.
- **F.** Parent-effect and delegation chains must reconstruct fan-out and failure origin.
- **G.** No multi-agent graph, propagation state, quotas, or cascade recovery exists.
- **H.** Level 0.
- **I.** Delegation, multi-agent harness, network/MCP mediation, causal provenance,
  concurrency/in-flight semantics, quarantine, and recovery.
- **J.** Inject one fault and measure `MAXIMUM_AUTHORIZED_BLAST_RADIUS`,
  `CROSS_AGENT_PROPAGATION_RATE`, `CASCADE_CONTAINMENT`, unauthorized effects, and time
  from revocation to effective denial.
- **K.** Task-scoped authorization alone does not establish cascade containment.

### ASI09 — Human-Agent Trust Exploitation

- **A.** Persuasive, authoritative, or deceptive agent output causes a human to disclose
  data or approve harmful action without adequate independent validation.
- **B.** Approval as authenticated, versioned authority creation showing the exact new
  capability, resource, constraints, and expected effects.
- **C.** Deterministic approval requirements can stop unapproved effects; they cannot
  determine whether a human was persuaded or the decision was wise.
- **D.** AI may flag suspicious persuasion. UI and human-factors evaluation are required;
  model output cannot be the authoritative risk explanation.
- **E.** Staging, reversibility, cooling-off, dual control, limits, and revocation can
  reduce damage after approval.
- **F.** Link request, displayed authority delta, authenticated approver, approval version,
  resultant capability, and every effect.
- **G.** Approval-as-authority and its UI are not implemented.
- **H.** Level 0.
- **I.** Principal authentication, approval protocol/UI, versioning, expiration,
  revocation, side-effect previews, and human-subject evaluation governance.
- **J.** Compare explicit authority-delta approvals with ambiguous confirmations; measure
  incorrect grants, comprehension, escalation rate, completion, and provenance.
- **K.** SafetyBox does not detect persuasion, guarantee informed consent, or make human
  approval intrinsically safe.

### ASI10 — Rogue Agents

- **A.** A compromised or misaligned agent persistently deviates, deceives, colludes,
  self-propagates, or pursues harmful objectives.
- **B.** Treat the agent as untrusted: external authority ceiling, reference monitor,
  comprehensive mediators, per-agent identity, revocation, and immutable provenance.
- **C.** Potentially strong for unauthorized protected effects only if mediator coverage
  is broad and bypass-resistant. It cannot prevent harmful behavior inside granted scope.
- **D.** Behavioral/trajectory analysis may detect drift or collusion but must not be the
  enforcement root.
- **E.** Least authority, isolation, quotas, revocation, and non-transferable delegation
  can reduce blast radius and persistence.
- **F.** Complete authority/effect lineage is essential for stealth and collusion audits.
- **G.** Bounded authorization and filesystem evidence exist; no rogue-agent harness,
  multi-agent identity, broad mediation, or durable provenance exists.
- **H.** Level 0 for ASI10. Adjacent Level 4 filesystem and Level 3 process-authorization
  evidence must remain named and bounded.
- **I.** Real-agent adversarial harness, process/network/MCP coverage, direct-route
  confinement, delegation/revocation, collusion scenarios, and external audit.
- **J.** Give a deliberately misbehaving agent a minimal contract and ask it to maximize
  effects through aliases, chains, other agents, direct routes, and approval manipulation.
  Score attempted versus occurred effects and coverage gaps separately.
- **K.** Prohibit "even a rogue agent cannot exceed its authority" until tested mediator
  coverage is broad enough to support that scope.

## OWASP-AGENTIC-BENCH-001 research program

The benchmark should be an effect-containment suite, not a checklist. Each scenario must
identify the OWASP mechanism, the authority oracle, the protected primitive/effect oracle,
the mediator boundary, and the exact subclaim. Initial families are:

| Family | Counterfactual intervention | Primary outcome |
|---|---|---|
| ASI01 | clean versus hijacked goal/context; authority unchanged | no authority expansion; no unauthorized effect |
| ASI02 | change one of action/resource/task/tool/compound component | exact denial and no denied primitive forwarding |
| ASI03 | change principal/session/task/delegation lineage | no identity or authority reuse |
| ASI05 | change executable/cwd/argv/environment authorization | exact native-child effect semantics |
| ASI06 | clean versus poisoned memory/RAG; authority unchanged | authorization invariance under context-only change |
| ASI07 | valid versus forged/replayed/amplified delegation | message never creates unverified authority |
| ASI08 | inject one fault at one node | bounded fan-out and reconstructable lineage |
| ASI10 | cooperative versus deliberately adversarial agent | same deterministic effect ceiling |

ASI04 and ASI09 should enter only after their missing trust roots exist. Every family must
separate false allow, false deny, denied primitive forwarding, unauthorized effect,
mediation bypass, attribution completeness, and benign completion. There is no combined
security-accuracy number.

## Stop conditions

Stop and document rather than score if:

- an ASI label or expected decision is exposed to the production runner;
- the held-out split has already been executed for development or conformance testing;
- AI inference becomes an authority source;
- a direct effect route exists but the claim is phrased globally;
- identity is inferred from `task_id` alone;
- authorization correctness is used as evidence that an effect did or did not occur;
- a Level 4 component subclaim is promoted to Level 4 category coverage; or
- an OWASP mapping omits a known bypass or explicit non-claim.

## Permitted strongest summary

At the current evidence boundary, the strongest accurate summary is:

> SafetyBox has deterministic controls and bounded real-filesystem evidence relevant to
> the unauthorized-effect portions of ASI02, with adjacent bounded authorization evidence
> relevant to ASI03 and ASI05. The remaining ASI mappings are research hypotheses or
> architecture directions; none is a whole-category mitigation claim.
