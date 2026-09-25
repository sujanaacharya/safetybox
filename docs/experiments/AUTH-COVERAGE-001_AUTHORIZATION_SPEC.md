# AUTH-COVERAGE-001 authorization specification

**Specification identity:** `AUTH-COVERAGE-001-AUTHORIZATION-SPEC@1`

**Status:** frozen normative benchmark specification; held-out run not authorized

**Scope:** deterministic logical authorization for filesystem and process requests

This specification defines benchmark truth independently of SafetyBox production code.
It intentionally does not decide physical path validity, symlink behavior, executable
validity, process creation, effects, or task completion.

## Vocabulary

- **Subject** is the requesting actor recorded for audit. Version 1 does not claim
  authenticated subject binding.
- **Session** is the recorded session identifier. Version 1 does not grant authority from
  session identity.
- **Task** is the opaque task identifier bound by a selected task contract.
- **Action** is the exact operation name, such as `filesystem.read`, `process.exec`, or
  `process.cwd`.
- **Resource** is a normalized logical identifier. Absolute paths use a lexical canonical
  representation with no empty, `.` or `..` segment.
- **Capability** is one indivisible `(action, resource-scope)` authority object. It does
  not carry a task ID; its containing contract supplies task binding, matching the
  production kernel.
- **Contract** is `(contract_id, task_id, capabilities)`. `contract_id` is provenance,
  not an authorization predicate.
- **Component** is one atomic action/resource authorization subdecision.
- **Decision** is exactly `ALLOW` or `DENY`.

Request IDs, contract IDs, capability IDs, argv, context, suspiciousness, apparent
innocence, and unrelated metadata are not authority predicates. Renaming any opaque ID
without changing authority content must preserve the decision.

## Valid input domain

All values are presented after the appropriate adapter's deterministic normalization.
The authorization oracle performs no I/O and no physical validation.

A version-1 filesystem request has exactly one component:

```text
(name=filesystem, action=filesystem.*, resource=canonical-logical-resource)
```

A version-1 process request has exactly two ordered components:

```text
(name=exec, action=process.exec, resource=canonical-executable)
(name=cwd,        action=process.cwd,  resource=canonical-logical-cwd)
```

The generic capability kernel permits exact scopes or canonical path scopes ending in
`/**` for any action. The frozen process corpus uses exact executable and cwd resources;
that is a corpus-design constraint, not a different authorization matcher. The scope
`/root/**` includes canonical descendants such as `/root/a` and
`/root/a/b`; it excludes `/root`, `/rootish/a`, and any non-canonical path. Matching is
case-sensitive and code-point exact. No Unicode normalization, case folding, symlink
resolution, hard-link resolution, mount interpretation, or host lookup occurs here.

Malformed requests, malformed contracts, duplicate capability IDs, unsupported tool
shapes, non-canonical path resources, and invalid scopes fail closed.

## Normative authorization function

For request `R`, contract `C`, component `x`, and capability `c`:

```text
TaskBound(R, C) := R.task_id = C.task_id

ExactMatch(c, x) :=
    c.action = x.action
    AND c.resource = x.resource

SubtreeMatch(c, x) :=
    c.action = x.action
    AND c.resource is canonical "/root/**"
    AND x.resource is a canonical strict descendant of "/root"

Covers(c, x) := ExactMatch(c, x) OR SubtreeMatch(c, x)

AuthorizeComponent(R, C, x) :=
    ALLOW iff inputs are valid
          AND TaskBound(R, C)
          AND EXISTS c IN C.capabilities: Covers(c, x)
    DENY otherwise

Authorize(R, C) :=
    ALLOW iff inputs are valid
          AND FOR ALL x IN R.components:
                  AuthorizeComponent(R, C, x) = ALLOW
    DENY otherwise
```

One capability must cover the complete action/resource pair for an atomic component.
An action match from one capability and a resource match from another cannot synthesize
authority. The process request is explicitly compound, so distinct valid capabilities
may cover its executable and cwd components; both subdecisions remain visible and both
must allow.

If multiple capabilities independently cover one component, the normative implementation
selects the lexicographically smallest capability ID only as deterministic explanation
evidence. Selection does not change authority.

## Decision reasons and explanations

Stable component rules are:

| Rule | Meaning |
|---|---|
| `AUTH.INVALID_STRUCTURE` | Request or authority structure is malformed. |
| `AUTH.TASK_MISMATCH` | Request task differs from contract task. |
| `AUTH.NO_MATCHING_CAPABILITY` | No single capability covers action and resource. |
| `AUTH.EXPLICIT_CAPABILITY` | One task-bound contract capability covers the component. |

Top-level rules are `AUTH.ALL_COMPONENTS_ALLOWED` and
`AUTH.ANY_COMPONENT_DENIED`. Each component explanation mechanically contains:

```text
subject, session, task, action, resource, capability, rule,
authority_source, component, decision, reason
```

`capability` is null for denial because no authority object granted the component.
Completeness is field-presence validation, not subjective prose scoring.

## Authority and behavior separation

Argv and request data may contain `password`, `token`, `secret`, `rm -rf`, `curl`,
`ssh`, `exploit`, `admin`, `/etc/passwd`, `credential`, `upload`, or `delete` without
changing hard authority. Trusted context, B4 results, model output, risk indicators, and
unknown metadata cannot convert `DENY` to `ALLOW`. Likewise, benign-looking content
cannot convert an unauthorized request to `ALLOW`. A separate analysis plane may emit a
flag but cannot rewrite this function's result.

## Formal properties

1. **Determinism:** equal authority inputs produce equal decisions and explanations.
2. **Task isolation:** a request under another task denies absent a separately selected,
   matching task contract.
3. **Monotonic irrelevance:** adding or removing a non-covering capability preserves the
   decision.
4. **Order independence:** capability permutation preserves authority semantics.
5. **Exact binding:** exact resource authority covers no sibling, parent, child, prefix,
   or suffix resource.
6. **No synthesis:** partial matches from unrelated capabilities do not combine.
7. **Compound conjunction:** every required process component is independently allowed.
8. **Fail closed:** invalid or unsupported structures do not grant authority.
9. **No behavior authority:** argv, apparent suspiciousness, apparent innocence, AI
   context, and unknown context do not grant or revoke hard authority.
10. **Opaque-identity invariance:** renaming scenario/request/contract identifiers without
    changing authority content preserves the decision.

## Delegation and attenuation precursor

Delegation is architectural/development evidence only; it is not implemented production
authority and is not held-out benchmark evidence. The future-compatible static model is:

```text
Authority = (authority_id, task_id, capabilities, parent_authority?)
DelegationChain = [root_authority, child_authority, ...]
```

A child is a valid attenuation only when it names its immediate parent, retains the same
task, and every child capability is contained by one parent capability. Exact scope is
contained only by the same exact resource or a covering filesystem subtree. A subtree is
contained only by the same or a broader parent subtree. Capabilities cannot combine to
cover one broader child capability.

Future attenuation dimensions are `task`, `action`, `resource`, `time`, `usage_count`,
and `destination`. Version 1 implements only task/action/resource subset checks and makes
no claim for the other dimensions.

## Future mediator extension

NETWORK, MCP, and DB adapters must add explicit component shapes and canonical resource
types while retaining the same philosophy: task-bound explicit authority, complete
single-component coverage, conjunctive compounds, fail-closed invalidity, stable
explanations, and no authority from behavior analysis. Adding a mediator must not change
the filesystem or process semantics above.

## Executable normative artifact and independence

The executable specification is
`experiments/AUTH-COVERAGE-001/formal/authorization_model.py`. It is outside the
production package and imports no `safetybox` module. Its conceptual semantics are
necessarily coupled to this written specification and to the production behavior the
benchmark intends to measure; implementation independence does not imply conceptual
independence. Same-team specification and oracle authorship is a frozen limitation.

This specification is not itself evidence about production accuracy. It is the source of
benchmark labels to be cross-checked against a separately implemented benchmark oracle
before corpus freeze.
