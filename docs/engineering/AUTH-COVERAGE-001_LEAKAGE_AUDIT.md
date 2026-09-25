# AUTH-COVERAGE-001 leakage and duplicate audit

**Audit ID:** `AUTH-COVERAGE-001-LEAKAGE-AUDIT@1`

**Purpose:** determine whether superficial runtime-visible features disclose the
deterministic label or inflate the effective sample size.

## Label isolation

Runtime scenarios contain opaque IDs, split, request, operation data, contract,
and capabilities. Labels, families, difficulty, authority distance, claim tags,
and pair identity live in separate construction artifacts. The audit rejects
runtime scenarios containing top-level label metadata and rejects IDs containing
outcome-bearing tokens such as allow, deny, authorized, unauthorized, benign,
hard, or mismatch.

Construction authors and this audit necessarily inspect labels; that is
same-team benchmark construction, not prediction exposure. The future runner has
a separate API with no label argument. It persists an immutable raw decision file
and checksum receipt before the separately invoked scorer can load labels.

## Frozen superficial probes

The audit reports:

- label balance by split and tool;
- the best single threshold on serialized request length;
- the best single threshold and point-biserial correlation for total requested
  resource-string length;
- the best single threshold on capability count;
- suspicious-literal/label cross-tabulation;
- all registered intentionally weak baseline predictors; and
- whether any label-only field appears in a runtime scenario.

Threshold searches are leakage diagnostics, not benchmark models and not
SafetyBox functionality. Their resubstitution accuracy is conservatively reported
as a warning signal, not a generalization estimate. In addition, a deterministic
single numeric decision stump selects among capability count, component count,
operation-data length, request length, requested-resource length, and suspicious-
literal count on `DEV`, then reports one evaluation on `VALIDATION`. It never
loads `HELD_OUT` labels. Counterfactual pairs must remain within one split, so a
pair cannot bridge this construction-time train/evaluation boundary. This tiny
classifier is only a generator-leakage probe and adds no dependency.

## Duplicate method

The auditor computes two SHA-256-keyed equivalence relations:

1. byte-semantic JSON equality including all IDs; and
2. semantic equality after removing scenario, subject/session, contract, and
   capability identifiers.

Exact duplicates are a freeze failure. Semantic duplicate groups are reported
for review: they may identify count inflation, or may be intentional metamorphic
replicates whose differing property was removed by the conservative projection.
They are never silently discarded or counted as independent evidence without
review.

## Leakage stop condition

Freeze stops if a superficial feature or simple heuristic predicts labels well
enough to undermine the intended near-boundary corpus, if identifiers encode
labels/families, if capability count is effectively diagnostic, or if duplicate
templates inflate a headline denominator. There is deliberately no universal
numeric threshold divorced from the baseline table and family composition; the
pre-run review must make and record the disposition.

## Frozen result

**Result: PASS.** All 3,600 runtime IDs are opaque under the frozen token test,
label-only fields are absent from every runtime scenario, and exact duplicate
count is zero. There are 100 semantic-projection groups (200 scenarios); every
one is an intentional registered `CONTRACT_IDENTITY` pair whose only removed
distinction is provenance identity and whose authorization relation is `SAME`.
They are retained as metamorphic contract-identity evidence, not treated as 200
independent authorization-boundary examples.

The best capability-count threshold reached 50.17%; requested-resource length
reached 53.97%, with label correlation -0.01595; serialized request length also
reached 53.97%. Suspicious literals were balanced: ordinary 896 ALLOW/904 DENY
and suspicious 904 ALLOW/896 DENY. The DEV-trained superficial stump selected
requested-resource length, achieving 53.61% on 720 DEV cases and 53.33% on 720
VALIDATION cases. It did not inspect HELD_OUT. No superficial probe
exposed a useful label channel.

Machine-readable findings are in
`experiments/AUTH-COVERAGE-001/audit/audit_report.json`. This audit did not open
or create held-out predictions.
