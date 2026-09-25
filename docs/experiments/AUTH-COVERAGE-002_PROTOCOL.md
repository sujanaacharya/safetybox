# AUTH-COVERAGE-002 authorization benchmark protocol

**Protocol identity:** `AUTH-COVERAGE-002-PROTOCOL@1`  
**Execution protocol:** `AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1`  
**Substrate freeze:** `8e3ba29bbadcdc9c4de4c0d306e8eaaf013dab78`  
**Status:** preregistered before canonical corpus generation; not run

## Question, hypotheses, and scope

The research question is whether SafetyBox's deterministic `TaskContract` authorization
correctly distinguishes `AUTHORIZED` from `UNAUTHORIZED` for filesystem and process
requests under task, action, resource, capability, and compound-component pressure while
preserving legitimate behavior. H1 is that the frozen production policy conforms to the
independent normative relation on the one-shot HELD_OUT split. H0 is any false allow,
false deny, production error, missing explanation field, or unreconstructable raw record.
Secondary hypotheses cover task isolation, exact resource and action binding, absence of
partial-capability synthesis, compound conjunction, irrelevant-capability/order
invariance, and context non-authority.

This is authorization-only evidence for the question **is authority determined
correctly?** It does not establish mediation, attribution, real effects, authenticated
identity, delegation safety, network or MCP safety, rogue-agent containment, or
production readiness. Physical resource existence is outside the label relation.

## Normative relation and invalid controls

`AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1` is the sole written source of truth. A request is
allowed exactly when its task equals the contract task and every required component is
covered by one indivisible capability having the exact action and either the exact
resource or a valid strict-descendant `/**` scope. Different capabilities may authorize
different compound components; partial action/resource matches may not synthesize one
component's authority. Empty capability sets deny. Duplicate capability values collapse
under production set semantics and do not amplify authority. Irrelevant capabilities are
inert. Malformed structures are a separate small fail-closed control family and are not
part of primary accuracy denominators.

## Population, splits, and blinding

The target is 4,000 valid scenarios, at least half authorized, with approximately equal
filesystem/process and authorized/unauthorized totals. Dependence roots (pairs,
metamorphic siblings, and cross-tool groups) are allocated atomically by a CSPRNG to DEV,
VALIDATION, and HELD_OUT in a 20/20/60 ratio before inspecting labels. Near-template
siblings never cross splits. Exact and normalized semantic duplicates across splits are
forbidden.

HELD_OUT may never be used for production regression, policy tuning, oracle debugging,
generator debugging, baseline training, or difficulty calibration. Its runtime package
is physically separate from labels, pairs, families, difficulty, oracle output,
generation provenance, pressure dimensions, and split-derivation metadata. Runtime IDs
are independent 256-bit OS-CSPRNG tokens allocated after semantics and split assignment;
the allocator accepts no labels or semantic inputs. Authoring keys never enter runtime.

DEV production execution is permitted only through the frozen ledger-governed runner for
instrument or policy debugging and cannot support a primary claim. VALIDATION production
execution is permitted once for runner rehearsal and predeclared leakage/conformance
checks; after the final production implementation freeze, no tuning may use it. HELD_OUT
permits exactly one production authorization execution only after a separate independent
final scientific gate. This authorship session performs no HELD_OUT production call.

## Families, pairs, and structural difficulty

Primary families are `HARD_BENIGN`, `HARD_UNAUTHORIZED`, `EDGE_BENIGN`,
`EDGE_UNAUTHORIZED`, `TASK_BINDING`, `CROSS_TASK_REUSE`, `RESOURCE_BOUNDARY`,
`ACTION_BOUNDARY`, `CAPABILITY_PRESENCE`, `CAPABILITY_DISTRACTOR`, `ZERO_RELEVANT`,
`CAPABILITY_SYNTHESIS`, `COMPOUND_AUTHORIZATION`, `SUSPICIOUS_BENIGN`,
`BENIGN_LOOKING_UNAUTHORIZED`, `AI_CONTEXT_NON_AUTHORITY`, and
`CROSS_TOOL_EQUIVALENCE`. Hardness is structural, based only on frozen distractor count,
near-resource count, partial matches, compound complexity, task pressure, and mutation
distance. Suspicious words are data, not difficulty by themselves. Authority distance is
descriptive and never creates labels.

Every primary causal scenario records an analysis-only `pressure_dimension` from `TASK`,
`ACTION`, `RESOURCE`, `CAPABILITY`, `COMPOUND`, `CROSS_TASK`, or `SYNTHESIS`. Frozen
single-dimension mutations are `M_TASK`, `M_ACTION`, `M_RESOURCE`,
`M_REMOVE_RELEVANT_CAP`, `M_ADD_IRRELEVANT_CAP`, `M_REORDER_CAPS`, `M_SUSPICIOUS_DATA`,
and `M_TOOL_ANALOGUE`. An independent pair auditor, not the generator's declarations,
assigns `STRICT_STRONG`, `STRONG_AUXILIARY`, `MODERATE`, or `WEAK`; final `WEAK` must be
zero. At least 80% of at least 1,500 pairs must be `STRICT_STRONG`.

Cross-tool groups declare one abstract property—`TASK_BINDING`,
`EXACT_RESOURCE_BINDING`, `IRRELEVANT_CAPABILITY_INVARIANCE`, `CAPABILITY_PRESENCE`,
`NO_PARTIAL_SYNTHESIS`, or `ACTION_BINDING`—and instantiate it independently for
filesystem and process. At least 200 groups must pass strict comparability audit.

## Oracles and formal checks

Oracle A directly evaluates written predicates. Oracle B separately constructs the set of
permitted action/resource tuples for the finite request domain and queries membership.
Neither imports SafetyBox, `TaskContractPolicy`, `ReferenceMonitor`, or production
resource/capability matchers. Their task, action, resource, capability, compound, and tool
paths are separately audited for at least moderate independent bug-detection capability.
Any canonical disagreement blocks freezing; no vote or adjudication may overwrite it.

A bounded model explores at least 50,000 states without production calls, checking task
isolation, action/resource binding, no authority amplification or synthesis, irrelevant
capability and order invariance, compound truth tables, and context non-authority.

## Metrics and statistics

The frozen `AUTH-COVERAGE-002-METRIC-CONTRACT@1` controls scoring. Primary reports are
accuracy, false-allow rate, false-deny rate, exact binomial confidence intervals, pair
accuracy, compound quadrant accuracy, structured explanation completeness, and every
predeclared family denominator. Dependence-aware reporting includes pair/group-cluster
bootstrap intervals and effective template counts; scenario-level intervals are not
represented as independent population inference. No post-hoc family may enter a primary
claim.

Baseline attacks on DEV/VALIDATION only include always allow/deny, task equality, action,
resource, first capability, capability count, resource similarity/depth/length, tool,
difficulty, keyword, string/JSON length, input-digest prefix, file position, manifest
order, and ID features. Logistic regression, a shallow decision tree, and a simple linear
model train only on DEV and evaluate only VALIDATION with superficial features and no
embeddings or model calls. Material runtime-only label prediction, or generator-branch
prediction that is both high and label-correlated, is blocking.

## Metamorphic and explanation contracts

Adding an irrelevant capability, reordering capabilities, changing an opaque ID,
changing suspicious argv/context, or changing unrelated metadata preserves the decision.
A task mismatch flips task-bound authority; removing the sole relevant capability flips
allow to deny. Expected explanations are structured fields: final and component decision,
rule, reason, task, action, resource, matched capability for allow, and authority
provenance where production supports it. Prose quality is not scored.

## One-shot policy, stop conditions, and exposure

`AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1` supplies the raw-first state machine. Before any
future HELD_OUT call the single persistent path
`experiments/AUTH-COVERAGE-002/governance/exposure_ledger.jsonl` must reconcile to zero
reservations, starts, exposures, completions, failures, and raw records for this corpus.
Pytest and noncanonical purposes must fail before reservation and the production-call
counter must remain zero. A STARTED event permanently consumes the one-shot opportunity;
any partial exposed run blocks restart.

Freeze is blocked by oracle disagreement, exact or cross-split semantic duplicates,
WEAK pairs, an unjustified normalized cluster above eight, label/runtime contamination,
material shortcut leakage, a failed fresh-process isolation test, unexplained ledger
state, predecessor mutation, or any HELD_OUT reservation/start/exposure/raw record.

## OWASP boundary, claims, and preregistered wording

Analysis-only annotations may say `RELEVANT_CONTROL_EVIDENCE` for ASI01, ASI02, ASI03,
ASI05, ASI06, and ASI10. They may never say a category is solved. In particular ASI03
does not resolve identity, and ASI05 covers process authority only; real execution belongs
to EXP-016.

Candidate result wording (values remain placeholders): “On a blinded, synthetic,
same-team-authored, structurally hard, counterfactual, task-scoped, deterministic held-out
authorization corpus of `{N}` scenarios, frozen SafetyBox production authorization had
`{false_allows}` false allows and `{false_denies}` false denies under the preregistered
logical specification.” “Blinded” means label-separated execution, not blinded authorship
or external validation.

Frozen non-claims: not external validation; not zero population risk; not real-effect
prevention; not mediation completeness; not authenticated identity; not network, MCP, or
delegation evidence; not production readiness; not rogue-agent containment; not an AI
safety proof. Same-team protocol, oracle, generator, and corpus authorship remains a major
limitation even after dual-oracle and reviewer-lane checks.

## External packs and review

The external-pack schema accepts separately supplied runtime inputs, analysis metadata,
and authority labels without changing this specification or the metric contract. Every
pack requires both frozen oracle evaluations and the same duplicate, pair, isolation, and
leakage gates. Before freeze, separate adversarial, systems-security, benchmark-method,
formal, and competitor reviews classify every issue `RESOLVED`, `BOUNDED`, or `BLOCKING`;
no `BLOCKING` issue may remain.
