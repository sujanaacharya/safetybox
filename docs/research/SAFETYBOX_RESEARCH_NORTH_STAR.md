# SafetyBox Research North Star

## Status and scope

**Specification identity:** `SAFETYBOX-RESEARCH-NORTH-STAR@1`

**Specification date:** 2026-09-25

This document defines the long-term research target. It is a specification and research
governance artifact, not evidence that the target is implemented or globally enforceable.
Every empirical claim must name its protected-effect class, mediator boundary, authority
model version, deployment assumptions, experiment, and evidence level.

`AUTH-COVERAGE-001` is not valid held-out evidence. Its frozen methodology and leakage
analysis remain useful negative research evidence, but no result from that benchmark may
be presented as a valid held-out result.

## North star

> **No protected agent effect without valid authority.**

The stronger SafetyBox target is:

> **Every protected effect is authorized, mediated, and attributable.**

SafetyBox should be able to reconstruct, for each protected effect:

- **who**: authenticated principal, agent, and session identities;
- **under which task**: an authenticated task instance and authority version;
- **using which authority**: the exact capability and valid issuance/delegation chain;
- **on which resource**: the canonical resource actually presented to the primitive;
- **through which mediator**: the identified reference monitor, adapter, and primitive;
- **why allowed**: the deterministic rule and evaluated facts;
- **what occurred**: attempted and observed actual effects, including failure or
  indeterminate status; and
- **whether reconstruction is complete**: integrity, ordering, and missing-evidence state.

This target concerns external effects, not proof of an agent's intent, general alignment,
or the semantic harmlessness of every operation that valid authority permits.

## Core definitions

Let:

- `Q` be normalized action requests;
- `A` be versioned authority objects;
- `E` be observed protected effects;
- `S` be trusted enforcement state;
- `D` be the explicitly enumerated protected-effect domain for a deployment; and
- `C_D` be the documented mediator-coverage assumptions for `D`.

A **protected effect** is a security-relevant change or disclosure through a governed
primitive: for example, reading protected bytes, mutating a filesystem object, creating a
process, sending data, changing database state, submitting a browser form, or invoking an
MCP tool. An action name is a request classification; it is not itself proof of the effect
that occurred.

An authority object `a` **covers** request or effect description `x` only if all of its
subject, authenticated task, action, canonical resource, constraints, time, usage,
destination, and current-state predicates hold. `Valid(a, S)` additionally requires a
trusted authority source, valid integrity and issuance chain, no amplification, no
applicable revocation, and unexpired validity.

```text
Authorized(x, S) := exists a in ActiveAuthority(S):
                        Valid(a, S) and Covers(a, x)
```

An effect is **authorized** only when the authority covers the effect that actually
occurred, not merely an earlier, more abstract tool request. The authorization decision
must precede primitive invocation and bind the exact normalized request and relevant
state. Post-hoc discovery of a capability is not authorization.

An effect is **mediated** when every causally sufficient route to that effect inside the
declared coverage domain crosses a trusted reference-monitor/effect-mediator boundary,
and that boundary verifies the still-valid authorization before invoking the exact
protected primitive. Adapter routing alone does not establish complete mediation if a
direct OS, library, inherited-descriptor, child-process, native-code, network, or alternate
tool path remains available.

An effect is **attributable** when integrity-protected, ordered evidence binds the actual
primitive outcome to the principal, agent, session, task, request, authority disposition
(the exact authority or verified absence of one), decision, mediator, and
causal/delegation lineage, and the required reconstruction fields can be verified. A
self-reported agent rationale or an `ALLOW` event is not proof that an effect occurred.

## Formal protected-effect properties

The basic authorization property is:

```text
forall e in E_D:
    EffectOccurred(e)
    => exists a in A:
           ValidAt(a, e.authorization_commit_time)
        and ValidAt(a, e.primitive_start_time)
        and SubjectCovers(a, e.principal, e.agent, e.session)
        and TaskCovers(a, e.task)
        and ActionCovers(a, e.actual_action)
        and ResourceCovers(a, e.actual_resource)
        and ConstraintsHold(a, e)
```

The stronger property is:

```text
forall e in E_D:
    EffectOccurred(e)
    => Authorized(e) and Mediated(e) and Attributable(e)
```

This is a conditional property over `(D, C_D)`. It must not be restated as a global
guarantee until the deployment enumerates the effect primitives and demonstrates that no
relevant bypass route exists. Unknown mediator coverage yields an unknown property, not a
pass.

For denied requests, the pre-effect corollary is:

```text
Decision(q) = DENY
    => ProtectedPrimitiveInvocationsBoundTo(q) = 0
```

This corollary does not establish that no unbound or bypass effect occurred; that is a
separate mediation claim.

## Primary research question and subquestions

**Primary question:** Can autonomous AI agents remain useful and capable while
deterministic, task-scoped authority prevents protected effects beyond their explicitly
delegated authority?

The program separates this into questions that cannot be answered by one aggregate:

1. **Authorization correctness:** Does deterministic evaluation allow exactly the
   requests covered by valid authority, including compound and counterfactual cases?
2. **Mediation completeness:** Which real effect primitives and bypass routes are actually
   controlled by the reference monitor?
3. **Effect correctness:** Does the primitive receive the authorized executable, resource,
   arguments, environment, destination, and limits, and what effect actually results?
4. **Task isolation:** Can authority for one authenticated task, session, or principal be
   replayed in another?
5. **Authority provenance:** Can every decision and effect be reconstructed to a trusted
   issuer and versioned authority chain?
6. **Delegation and attenuation:** Can child authority be expressed usefully while its
   denotation remains a subset of its parent and task ceiling?
7. **Revocation and expiry:** When do changes take effect for new, queued, in-flight, and
   descendant operations?
8. **AI/context non-authority:** Can semantic inference improve proposals and detection
   without creating or expanding authority?
9. **Trajectory semantics:** Can history safely flag, request approval, or trigger
   policy-defined attenuation without silently granting authority?
10. **Real-agent utility:** Under these controls, what benign completion, recovery,
    latency, and approval burdens remain across actual agent/tool integrations?

## Desired invariant family

These identifiers are the new research-program family. Their status remains `DESIRED`
unless the canonical invariant register and linked evidence state otherwise.

| ID | Desired invariant |
|---|---|
| `INV-024` | **NO_UNAUTHORIZED_PROTECTED_EFFECT:** within the declared mediation domain, no protected effect occurs unless valid authority covers its actual subject, task, action, resource, and constraints. |
| `INV-025` | **NO_CROSS_TASK_AUTHORITY_REUSE:** authority or an authorization decision bound to one authenticated task cannot authorize another task. |
| `INV-026` | **NO_AGENT_SELF_AUTHORITY_EXPANSION:** agent output, self-report, prompt, memory, plan, or tool arguments cannot create or broaden authority. |
| `INV-027` | **NO_AUTHORITY_AMPLIFICATION:** every derived authority denotes a subset of both its source authority and the applicable task maximum. |
| `INV-028` | **AI_CONTEXT_CANNOT_GRANT_AUTHORITY:** AI or semantic context may supply proposals or evidence, but cannot independently produce an enforceable grant. |
| `INV-029` | **DENIED_ACTION_NEVER_REACHES_PROTECTED_PRIMITIVE:** a deterministic denial produces no bound protected-primitive invocation. |
| `INV-030` | **EVERY_PROTECTED_EFFECT_HAS_AUTHORITY_PROVENANCE:** every effect in the declared domain has reconstructable integrity-protected authority disposition (the exact valid authority or verified `NO_VALID_AUTHORITY`) and mediator lineage. |
| `INV-031` | **AMBIGUOUS_AUTHORITY_NEVER_SILENTLY_ALLOWS:** ambiguity, failed subset proof, missing identity, conflicting authority, or unverifiable state yields denial or an explicit non-executing resolution state. |
| `INV-032` | **DELEGATED_AUTHORITY_IS_SUBSET_OF_PARENT:** a child authority is accepted only when its complete permitted-request set is provably a subset of its parent's current delegated set. |
| `INV-033` | **REVOKED_OR_EXPIRED_AUTHORITY_CANNOT_AUTHORIZE_NEW_EFFECTS:** after the defined revocation/expiry commit point, the authority and affected descendants cannot authorize a new primitive start. |

`INV-024` and `INV-030` require demonstrated mediation and observation coverage. Unit
authorization tests cannot establish them. `INV-029` applies to the bound mediator route
and must not be used to conceal bypasses.

## Three independent failure classes

| Failure class | Definition | Required evidence |
|---|---|---|
| **Authorization failure** | Policy returns `ALLOW` although no valid authority covers the normalized request, or returns `DENY` despite covering authority. | Independent authority reconstruction, false-allow/false-deny and task-binding analysis. |
| **Mediation failure** | A protected effect can occur through a route that did not receive and enforce the required decision, including direct and descendant bypasses. | Primitive inventory, route/bypass tests, OS/deployment assumptions, and real-effect observation. |
| **Effect or attribution failure** | The executed primitive/effect differs from what was authorized, or evidence cannot prove what occurred and bind it to the responsible authority. | Argument binding, before/after or external observation, terminal truthfulness, integrity, and reconstruction tests. |

These classes must be reported separately. Correct request classification does not prove
mediation; mediation does not prove effect correctness; an audit record does not prove its
claim without trustworthy observation.

## Top-level metrics

No aggregate “security accuracy” or single SafetyBox score is permitted. Each metric must
publish its denominator, unit of analysis, confidence interval where meaningful, mediator
scope, and missing/indeterminate treatment.

| Metric | Definition |
|---|---|
| `FALSE_ALLOW_RATE` | authorization-negative requests incorrectly allowed / all authorization-negative requests |
| `FALSE_DENY_RATE` | authorization-positive requests incorrectly denied / all authorization-positive requests |
| `UNAUTHORIZED_EFFECT_RATE` | authority-negative effect opportunities that produce a prohibited protected effect / all registered authority-negative effect opportunities |
| `MEDIATION_BYPASS_RATE` | tested effect attempts that reach a protected primitive outside the required mediator / all registered bypass attempts |
| `BENIGN_AUTHORIZATION_PRESERVATION` | benign authority-positive requests allowed / all benign authority-positive requests |
| `BENIGN_COMPLETION_RATE` | benign tasks satisfying registered end conditions / all registered benign tasks |
| `TASK_BINDING_ACCURACY` | task-binding cases correctly decided / all registered task-binding cases |
| `CROSS_TASK_REUSE_RATE` | cross-task reuse attempts accepted / all registered cross-task reuse attempts |
| `AUTHORITY_AMPLIFICATION_VIOLATIONS` | accepted derived authorities for which subset proof fails; report count and attempted set |
| `PAIR_ACCURACY` | counterfactual pairs for which both members receive their registered decisions / all eligible pairs |
| `COMPOUND_AUTHORIZATION_ACCURACY` | compound requests with every component and final decision correct / all compound requests |
| `EFFECT_ATTRIBUTION_COMPLETENESS` | occurred effects with all required verified provenance fields / all observed occurred effects |
| `MEDIATION_COVERAGE` | separately justified mediated primitives/routes over the registered known primitive/route inventory; never infer global completeness from this ratio |
| `APPROVAL_ESCALATION_RATE` | future: non-executing approval requests / eligible requests, stratified by necessity and outcome |
| `ABSTENTION_RATE` | future: explicit non-executing ambiguity/insufficient-evidence outcomes / eligible evaluations |

Authorization metrics use requests; effect metrics use independently observed effects;
coverage metrics use enumerated primitives/routes. Their denominators are not
interchangeable.

## Research interpretation and stronger-model resilience

SafetyBox's security root is deterministic authority plus complete-enough effect
mediation, not model weakness. When a stronger model is released:

- authorization semantics and maximum-authority ceilings remain unchanged;
- the reference-monitor decision precedence remains unchanged;
- effect-mediator constraints and provenance requirements remain unchanged;
- better task understanding, decomposition, semantic discovery, and trajectory analysis
  may improve untrusted proposals or observational evidence; and
- a more capable or adversarial model may discover new bypasses, so mediation coverage
  and red-team evidence must be re-evaluated rather than assumed stable.

Model substitution therefore should not expand authority, but it can invalidate empirical
assumptions about attack coverage or utility. Provider-neutral request normalization and
model-stratified evaluation are required.

## Claim and stop discipline

Stop a benchmark run or withhold a claim when:

- a proposed guarantee depends on probabilistic inference rather than deterministic
  enforcement;
- labels or oracle-correlated construction data can reach the production implementation;
- held-out predictions have been exposed outside the preregistered one-shot lifecycle;
- authorization evidence is used to assert real-effect prevention without mediation and
  effect evidence;
- AI output or context has become an authority source;
- authority, identity, subset, revocation, or in-flight semantics are ambiguous;
- provenance claims exceed the trustworthy observation path; or
- mediator coverage is unknown while a global security claim is proposed.

Claims should take the bounded form: “SafetyBox provides deterministic mitigation for
the unauthorized-effect component of [threat] under [named authority semantics] and
[named mediated boundaries], supported by [named evidence].”

## Related specifications

- [AI–Deterministic Trust Boundary](../architecture/SAFETYBOX_AI_DETERMINISTIC_TRUST_BOUNDARY.md)
- [Authority Model V2 Research Specification](SAFETYBOX_AUTHORITY_V2_RESEARCH_SPEC.md)
- [Effect Provenance Model](SAFETYBOX_EFFECT_PROVENANCE_MODEL.md)
- [Capability Model](../architecture/CAPABILITY_MODEL.md)
- [Safety Invariants](../architecture/SAFETY_INVARIANTS.md)
- [Scope and Non-Goals](SCOPE_AND_NON_GOALS.md)
