# SafetyBox Effect Provenance Model

## Status and objective

**Specification identity:** `SAFETYBOX-EFFECT-PROVENANCE-MODEL@1`

**Specification date:** 2026-09-25

This is a future research specification. Current M3 audit is single-process, in-memory,
and non-durable; EXP-014 provides bounded real-filesystem evidence at FMED-L1. Neither is
a complete implementation of this model.

The objective is to make each observed protected effect reconstructable from authenticated
authority through deterministic decision and mediator invocation to actual outcome, while
representing missing or indeterminate evidence truthfully.

## Provenance is not logging

An audit statement that an operation succeeded is not, by itself, proof that the effect
occurred. Effect provenance requires links among independently meaningful records:

```text
authority issuance/delegation
    -> normalized request
    -> authorization decision
    -> execution reservation/start
    -> protected primitive invocation
    -> observed actual outcome/effect
```

Each arrow is a typed causal or derivation edge, not mere timestamp adjacency. Ordering is
defined by trusted commit sequence within its domain; timestamps are observational.

## Conceptual immutable effect record

| Field | Required meaning |
|---|---|
| `effect_id` | Opaque globally unique effect-attempt identity. Identity alone is not proof of occurrence. |
| `schema_version` | Versioned interpretation of the record. |
| `session_id` | Authenticated enforcement session. |
| `principal_id` | Accountable authenticated principal. |
| `agent_id` | Protected agent/workload identity under the deployment threat model. |
| `task_id` / `task_version` | Authenticated task instance and authority-bearing version. |
| `request_id` / `correlation_id` | Exact normalized request and lifecycle correlation. |
| `requested_action` / `requested_resource` | What authorization evaluated. |
| `actual_action` / `actual_resource` | Canonical primitive/effect identity actually attempted or observed. |
| `capability_id` / `authority_version` | Exact committed authority used for the decision, or an explicit `NO_VALID_AUTHORITY` disposition for an observed violation. |
| `authority_source` | Authenticated root issuer/source type, or explicit verified absence. |
| `authorizing_rule` | Deterministic policy/rule and decision version, or an explicit `NO_AUTHORIZATION_DECISION` bypass disposition. |
| `authorization_snapshot` | Integrity reference to evaluated inputs/state/decision, or explicit absence established by orphan/bypass observation. |
| `mediator_id` / `mediator_version` | Reference monitor/adapter instance and software identity. |
| `primitive` | Exact protected primitive or registered route invoked. |
| `governed_arguments_reference` | Redacted canonical arguments or integrity reference sufficient to verify binding. |
| `outcome` | Typed lifecycle/result state; never inferred solely from `ALLOW`. |
| `effect_summary` | Minimal structured observed state transition, disclosure, process, send, or other result. |
| `sequence` / `timestamp` | Trusted commit order plus observational time source/precision. |
| `parent_effect_id` | Direct causal parent when defined, including child-process or compound-operation lineage. |
| `delegation_chain` | Ordered integrity references from root authority to used authority. |
| `approval_reference` | External approval that created the authority, if any. |
| `observation_source` | Primitive wrapper, independent before/after observer, remote acknowledgement, or other named evidence source. |
| `integrity` | Record/store integrity metadata under a declared threat model. |
| `redaction_class` | Access and disclosure policy for sensitive fields. |

An implementation may normalize these fields across multiple append-only records rather
than one object, provided reconstruction is deterministic and missing links are explicit.

## Lifecycle and truthful outcomes

The provenance model distinguishes authorization, invocation, and effect:

| State | Meaning |
|---|---|
| `REQUEST_RECORDED` | A normalized request was committed; no authorization or execution implied. |
| `AUTHORIZED` | Covering authority and rule were committed; no primitive invocation implied. |
| `DENIED` | Non-execution decision committed for the bound request. |
| `START_RESERVED` | Required audit/usage reservation committed; primitive not yet proven invoked. |
| `PRIMITIVE_INVOKED` | The mediator crossed the registered invocation boundary. |
| `EFFECT_OBSERVED` | Registered observation confirms the effect/result. |
| `NO_EFFECT_OBSERVED` | Observation confirms no registered effect under named detection limits. |
| `FAILED_BEFORE_INVOKE` | Failure occurred before primitive invocation. |
| `FAILED_AFTER_INVOKE` | Invocation occurred and a failure was observed; rollback is not implied. |
| `INDETERMINATE` | Available evidence cannot determine invocation or effect truthfully. |

Post-invocation audit failure must not be reported as denial, non-execution, or rollback.
A timeout, lost acknowledgement, or process crash may require `INDETERMINATE`. Recovery
may append a successor observation but must not rewrite the original record.

## Reconstruction predicate

For effect `e`, `Attributable(e)` requires more than field presence:

```text
Attributable(e) :=
       RequiredFieldsPresent(e)
   and IdentityBindingsVerify(e)
   and AuthorityDispositionVerifies(e)
   and AuthorizationDispositionVerifies(e)
   and RequestToPrimitiveBindingVerifies(e)
   and OutcomeEvidenceVerifies(e)
   and OrderingAndCausalLinksVerify(e)
   and IntegrityVerifies(e)
```

`AuthorityDispositionVerifies` either establishes that the named authority was valid at
the authorization and primitive-start boundaries or verifies that no valid authority was
present for a recorded violation. `AuthorizationDispositionVerifies` similarly validates
the exact decision snapshot or the observed absence of the required authorization path.
Attribution therefore does not imply authorization or mediation.
`RequestToPrimitiveBindingVerifies` compares the authorized canonical
action/resource/arguments with those actually supplied, or records the missing binding
for a bypass. `OutcomeEvidenceVerifies` is effect-class specific; it may require an
independent state digest, child observation, remote receipt, or database transaction
identifier.

If any required predicate is unknown, attribution is incomplete. Reconstruction must
return structured missing/invalid reasons rather than silently counting the effect as
attributable.

## Authority and effect joins

For a mediated action, the join key is an integrity-protected authorization snapshot or
single-use execution ticket bound to:

```text
(request_id, session_id, task_id, principal/agent subject,
 action, canonical resource, governed arguments hash,
 authority_id/version, authority epoch, mediator_id,
 decision/rule version, expiry, nonce)
```

The mediator revalidates freshness immediately before primitive start. Tickets cannot be
replayed across requests, resources, sessions, tasks, mediators, authority epochs, or
expired state. A primitive whose actual bound values differ from the ticket is an effect
correctness failure even if both values would separately have been authorized.

For a bypass or orphan effect there may be no ticket to join. Independent effect
observation must then emit a typed orphan/bypass record and identify which expected
request, decision, authority, or mediator link is absent. This can establish attribution
to a route and verified lack of authority without inventing nonexistent records.

## Parent effects, compound actions, and delegation

`parent_effect_id` represents a declared causal edge, not a generic “related” tag. A
process launch may parent direct-child effects only when the observation architecture can
bind them. Descendant filesystem/network effects are not automatically mediated or
attributed merely because the launch was authorized.

Compound operations need one parent attempt and ordered component records. Each component
reports its own authority contribution, primitive boundary, and outcome. Partial execution
must remain visible. A final success record cannot erase a failed or unauthorized
component.

Delegation provenance records every parent authority, issuer/recipient identity, subset
verification rule, and creation commit. Effect attribution points to the leaf used and the
complete verified chain. Revoked/expired ancestors make a new effect unauthorized under
the proposed Authority V2 semantics.

## Observation requirements by effect class

| Effect class example | Minimum candidate evidence | Important limitation |
|---|---|---|
| Filesystem read | wrapped retrieval invocation plus controlled return-channel evidence | cannot establish absence of disclosure through uninstrumented process/debug channels |
| Filesystem mutation | primitive invocation plus operation-appropriate before/after identity and state | races, alternate paths, and external concurrent writers require stronger design |
| Process execute | spawn-boundary evidence, executable/argv/cwd/environment binding, child identity and terminal status | child descendants and their effects need separate mediation |
| Network send | socket/request binding, destination resolution state, byte/message disposition, remote/local acknowledgement policy | DNS/proxy/retry and ambiguous delivery semantics must be explicit |
| Database mutation | connection/query or structured operation binding plus transaction/commit identity | application triggers and downstream effects may extend the causal domain |
| MCP/tool call | registered server/tool identity, canonical arguments, response and server-side effect evidence when available | a client-side response alone may not prove remote effect truth |

This table gives research requirements, not current coverage claims.

## Integrity, durability, and confidentiality

The target store is append-only or equivalently tamper-evident under a named attacker
model. It must define atomic append, crash recovery, sequence allocation, multi-process
ordering, retention, correction records, key rotation, and verification. Hash chaining or
signatures do not make a dishonest or bypassed sensor truthful; observation trust and
mediation completeness remain separate.

Provenance can contain sensitive paths, arguments, identities, outputs, and authority
structure. Payload minimization, field-level redaction, encryption, access control,
retention/deletion policy, and integrity-preserving redacted views are required. Agent
access to audit data should not expose secrets or enable boundary probing.

## Metrics

```text
EFFECT_ATTRIBUTION_COMPLETENESS =
    observed occurred effects satisfying Attributable(e)
    / all observed occurred effects in the registered domain
```

Report completeness by effect class, mediator, outcome, and required-field/predicate
failure. Do not exclude `INDETERMINATE` or missing-link records without reporting them.

Related non-aggregate measures include request-to-primitive binding accuracy, authority
chain verification rate, outcome-observation completeness, orphan-effect count,
unmatched-allow count, and provenance integrity failure count. None substitutes for
authorization accuracy or mediation coverage.

## Verification program

1. Schema validation, canonical serialization, and version compatibility tests.
2. Deterministic replay/reconstruction from raw records.
3. Missing, duplicate, reordered, conflicting, forged, stale, and corrupted edge tests.
4. Authorization-to-primitive argument-binding tests for every mediator.
5. Pre/post-invocation fault injection and crash recovery.
6. Compound and partial-effect truthfulness tests.
7. Delegation, approval, expiry, revocation, and authority-epoch joins.
8. Orphan protected-effect injection and alternate-route bypass tests.
9. Independent effect observation where the effect class permits it.
10. Confidentiality/redaction tests that preserve verification without exposing payloads.

## Non-claims

Effect provenance does not itself prevent an effect, establish complete mediation, prove
agent intent, guarantee that an authorized effect is benign, or retroactively authorize an
effect. Complete records over one adapter route do not establish coverage of direct or
descendant routes. `INV-030` remains desired until the declared effect domain has both
coverage evidence and verifiable reconstruction.

## Related documents

- [Research North Star](SAFETYBOX_RESEARCH_NORTH_STAR.md)
- [Authority Model V2](SAFETYBOX_AUTHORITY_V2_RESEARCH_SPEC.md)
- [Audit and Provenance](../architecture/AUDIT_AND_PROVENANCE.md)
- [Event Model](../architecture/EVENT_MODEL.md)
- [Real Filesystem Mediation](../architecture/REAL_FILESYSTEM_MEDIATION.md)
- [Real Subprocess Mediation](../architecture/REAL_SUBPROCESS_MEDIATION.md)
