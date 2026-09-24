# EXP-015 Corpus@2 Schema v2 Freeze Audit

**Audit ID:** `EXP-015-CORPUS-2-SCHEMA-V2-FREEZE-AUDIT@1`
**Scope:** development/schema proofs only; adapter executions: **0**.

## Proof inventory and contamination

All `DEV-SCHEMA-*` test proofs are contaminated development/schema-proof artifacts and
must not be reused exactly in future Corpus@2. The inventory covers matched and
mismatched opaque task binding; missing exec, missing cwd, both missing, exact exec and
cwd resource mismatches, many irrelevant capabilities, and an authority-positive
counterpart. It also covers every executable/cwd fixture kind, helper behavior, fault
stage/mode, and both routes. It contains no held-out scenario, label, prediction, pair
registry, or EXP-015 result.

The matched proof has request and contract task `task-A`. Its exact counterfactual uses
request task `task-B` and contract task `task-A`; every other runtime field and its
normalized materialized state are equal. Both validate and materialize. The independent
development oracle accepts the matched member and rejects the mismatched member, proving
that the runtime schema exposes needed authority inputs without deciding authority.

## Structure-versus-authority audit

The explicit `STRUCTURALLY_VALID_BUT_UNAUTHORIZED` proof group materializes task
mismatch, exec-resource mismatch, cwd-resource mismatch, missing exec capability,
missing cwd capability, and both missing capabilities. A normal authority-positive
counterpart also materializes. The separate structurally-invalid group rejects a wrong
schema version, empty ID, boolean timeout, non-string argv item, invalid route, and
invalid capability syntax.

The v1 review found two additional structure/authority corrections in v2: contract
capabilities may be empty and request resources need not occur in any capability. There
is no schema equality requirement between request resources and capability resources, no
required matching action, and no task/capability coupling. Fixture request paths remain
structurally valid absolute logical paths. Route is structural only.

The session/actor review found no authenticated identity relation available to enforce;
these fields are retained as opaque required provenance and deliberately not bound to a
contract. This is an unresolved frozen identity limitation.

## Isolation and determinism

Proofs materialize task counterfactuals under separate roots with equivalent normalized
state. Changing scenario ID changes neither task IDs nor fixture state. Runtime DTOs
contain no labels, pair IDs, manifests, or outcome fields; no materializer import reaches
adapter, authorization, labels, scoring, pairs, canonicalization, or process validation.
The normalized state deliberately omits identity but materialized DTO/raw provenance
preserve both task IDs independently.

Corpus@2 workflow is now: author directly to runtime schema v2; materialize every case
twice without adapter execution; perform authority-oracle, strong-pair, static-
separability, contamination, and coverage audits; then freeze corpus before any one-shot
execution. No migration path or v1 fallback is permitted.
