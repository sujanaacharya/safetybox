# SafetyBox Mediation Coverage Model

**Status:** living research model; current entries are not a completeness claim

**Model identity:** `SAFETYBOX-MEDIATION-COVERAGE@1`

**Mapping date:** 2026-09-25

## Definition

Mediation coverage is the evidence-qualified fraction of a declared protected-effect
surface whose effect-capable primitives are forced through a named reference monitor and
mediator. It is not the fraction of tools with an adapter, the fraction of tests passing,
or policy accuracy.

For effect class `c`, environment `d`, and declared primitive inventory `P(c,d)`:

```text
MC(c,d,L) = |{p in P(c,d): p is mediated with evidence level >= L}| / |P(c,d)|
```

The value is reportable only when `P(c,d)` is versioned and its discovery method and
known-unknowns are recorded. Otherwise report `UNKNOWN`, not `0%` or `100%`. Distinct
aliases, syscalls, inherited handles, subprocess descendants, native extensions, remote
services, and alternate protocol clients may be separate routes to the same effect.

## Evidence needed per primitive

Each row in a future machine-readable registry must contain:

- effect class and primitive/route identity;
- deployment/environment scope and discovery method;
- mediator and reference-monitor versions;
- request-to-primitive binding rule;
- allow, deny, bypass, failure, and concurrency evidence;
- independent effect observation method;
- known aliases, descendants, and unmediated paths;
- evidence level 0–5 and immutable evidence references;
- owner, review date, and status: `MEDIATED`, `PARTIAL`, `UNMEDIATED`, or `UNKNOWN`.

`MEDIATED` requires more than an adapter implementation: the registered deployment must
make the route compulsory, or the claim must be explicitly adapter-route-bounded.

## Current living matrix

| Effect surface | Known candidate primitives/routes | Mediated/evidenced route | Known bypass or unmediated path | Current level | Claim boundary |
|---|---|---|---|---:|---|
| filesystem | SafetyBox adapter; Python `os`/`pathlib`; shell/native calls; inherited descriptors; aliases and races | `FS-ADAPTER@1` at FMED-L1 | direct OS/native/shell routes, TOCTOU, concurrency, inherited descriptors | 4 for named EXP-014 sub-properties; not surface-wide | bounded adapter-routed isolated Linux cases only |
| process | SafetyBox adapter; `subprocess`; `os.system`/spawn; shell; native APIs; child descendants | `PROC-ADAPTER@1` development route; denied forwarding evaluated in EXP-015 | direct process APIs, shell, native calls, descendants | 3 for authorization/non-forwarding; 2 for execution implementation | no held-out successful execution until EXP-016 |
| network | sockets; HTTP libraries; subprocess/network-capable tools; browser | none | all routes | 0 | architecture only |
| MCP | framework clients; direct protocol clients; server-side nested effects | none | all routes and nested server effects | 0 | architecture only |
| database | drivers; ORM; HTTP APIs; CLI/subprocess | none | all routes | 0 | architecture only |
| browser | browser automation protocol; navigation/form APIs; downloads; extensions | none | all routes | 0 | architecture only |
| messaging/cloud | SDKs; HTTP; CLIs; MCP/tool wrappers | none | all routes | 0 | architecture only |

Evidence levels apply to the exact dimension named. EXP-015's Level 3 authorization
evidence cannot be relabeled Level 3 process-effect mediation.

## Discovery and denominator governance

Primitive discovery combines static call/dependency enumeration, runtime syscall or
protocol observation, adversarial alternate-route search, and environment configuration.
No one method establishes completeness. New routes expand the denominator; they do not
retroactively become “covered” because they cause the same high-level action.

The registry must preserve:

1. the inventory version used by each experiment;
2. additions/removals with rationale rather than rewritten history;
3. `UNKNOWN` routes when instrumentation cannot distinguish them;
4. effect classes produced by allowed children or remote tools; and
5. different denominators for local research harnesses and deployment profiles.

## Coverage gates

A mediator can enter a held-out effect experiment only after its development evidence
shows deterministic request normalization, decision-to-argument binding, denied primitive
non-forwarding, independent occurrence observation, truthful partial-effect states, and
enumerated direct controls. A global or category-wide claim additionally requires a
defensible deployment inventory and bypass resistance; adapter conformance alone cannot
satisfy that gate.

## Research expansion order

1. Complete EXP-016's native direct-child semantics.
2. Combine filesystem and process routes in `UNAUTHORIZED-EFFECT-001` while preserving
   their separate coverage denominators.
3. Specify a network mediator and network-independent effect oracle.
4. Specify MCP call mediation plus server identity and nested-effect attribution.
5. Add real-agent harness route discovery before claiming agent-stack coverage.
6. Seek external red-team discovery of missing paths before any high-coverage statement.
