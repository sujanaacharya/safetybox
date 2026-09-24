# ADR-006: Real Filesystem Mediation Boundary

Status: Accepted

Date: 2026-09-24

## Context

SafetyBox currently authorizes canonical logical resources through an in-process
single-resource monitor. It has no real filesystem adapter, physical path validation,
two-resource rename authorization, or adapter-ingress audit semantics. EXP-014 needs a
freezeable design boundary without implying complete mediation, OS confinement, TOCTOU
resistance, implementation, or evidence.

Repository governance requires an architecture decision for changes to trust boundaries,
event ordering, policy behavior, contract/capability meaning, and reproducibility
guarantees. The EXP-014 design affects each of those areas.

## Decision

Adopt FMED-L1 as the first real-tool boundary: only operations routed through a future
isolated Linux filesystem adapter are mediated. Policy continues to authorize canonical
logical `/workspace` resources; ephemeral host paths are mapping details and never become
`TaskContract` resources.

The adapter design must:

- perform purely syntactic lexical canonicalization before authorization, with no target
  filesystem lookup or protected-state disclosure;
- use existing task/action/resource capability semantics, with no filesystem-specific
  allow path;
- perform no-follow physical target validation only after authorization allows;
- reject every encountered intermediate or terminal symlink in v1 and apply the bounded
  operation-specific hard-link rule in the EXP-014 protocol;
- authorize both rename endpoints through a reviewed generic compound composition of two
  ordinary `TaskContractPolicy` evaluations, recording both decisions and executing only
  after both allow;
- preserve M3 lifecycle semantics and add adapter evidence through one reviewed canonical
  M3-compatible envelope/schema extension rather than a parallel audit model; and
- commit every required pre-execution audit record before the requested primitive, while
  reporting post-start uncertainty truthfully as `FAIL_INDETERMINATE`.

These are accepted design constraints, not implemented behavior. The adapter, compound
authorizer, and additive event/schema model remain future work and require review and
freeze before held-out corpus authorship.

TOCTOU is `NOT_SOLVED`. Lexical normalization, no-follow inspection, symlink rejection,
and `st_nlink` checks do not by themselves bind the checked object to the operated object
or establish race-resistant mediation.

## Alternatives Considered

- Authorize temporary host paths directly in task capabilities.
- Resolve or inspect physical paths before authorization.
- Treat rename as authorized by its source resource alone.
- Add a filesystem-specific authorizer outside `TaskContractPolicy` semantics.
- Emit an adapter-private audit stream separate from M3.
- Claim direct `os.*`, `pathlib`, shell, or inherited-descriptor routes are mediated at
  FMED-L1.
- Treat canonicalize-then-open checks as a TOCTOU solution.

## Consequences

### Positive

- Keeps logical authority stable across temporary host roots.
- Makes the pre-authorization information boundary and authorize-before-effect order
  testable.
- Prevents source-only rename authority and preserves attributable endpoint decisions.
- Extends rather than forks the canonical audit lifecycle.
- Keeps direct-route bypass and race limitations explicit.

### Negative

- Reject-all links and multi-link regular files exclude legitimate filesystem uses.
- Compound authorization and adapter evidence require additive generic interfaces before
  implementation.
- FMED-L1 provides no protection against direct filesystem routes.
- Deterministic state observation and fault injection increase harness complexity.

### Risks

- Name-to-object races can invalidate post-allow checks before primitive invocation.
- Incomplete mapping between logical resources and primitive arguments can expand scope.
- A failed completion audit or partial write can leave effects that cannot be reported as
  denial or rollback.
- Finite adapter-routed evaluation cannot establish complete mediation or production
  readiness.

## Research Impact

This decision governs EXP-014 protocol version 1. It permits development-only fixtures
after protocol freeze, followed by adapter/event freeze, held-out real-tool corpus
authorship, corpus freeze, and one-shot evaluation. Even successful evidence is limited
to named filesystem-mediated sub-properties at FMED-L1/RTM-1 and cannot validate an entire
OWASP category.
