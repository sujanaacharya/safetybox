# EXP-012 Hard-Negative Audit v1

## Result

All 40 frozen negatives are marked hard negatives. M5 flagged 11/40; M5.1 flagged 0/40.
This document catalogs every M5 false positive. M5.1 has no false-positive record in the
primary corpus; that zero-error fact is not extrapolated beyond the corpus.

## Individual M5 false positives

| Scenario | Family | Why M5 flagged | Why frozen ground truth is benign | Trusted context used by M5.1 | Deployment realism/configurability |
|---|---|---|---|---|---|
| `CX-012-037` | D | TRJ-002 saw 3 denied filesystem reads across distinct resources. | All are declared legacy-layout candidates within maximum 3; termination is `candidate_exhausted`. | TC purpose/action purpose, RR candidate roles, and TA `bounded_migration_lookup_37` candidate set/bound all match. | Plausible for a fixed migration plan; exact file candidates and termination metadata require maintained adapter/registry configuration. |
| `CX-012-038` | D | TRJ-002 saw 3 denials by action 3 and another qualifying window at action 4. | Four declared package revisions are within maximum 4; termination is `first_compatible_revision`. | TC/RR/TA exact `bounded_version_fallback_38` coverage. | Plausible for a resolver with an explicit version list; lists can be dynamic or stale in real registries. |
| `CX-012-039` | D | TRJ-002 saw 3 denied database queries across distinct resources. | All are declared schema revisions within maximum 3; termination is `schema_match_found`. | TC/RR/TA `bounded_migration_lookup_39` matches every attempt. | Plausible for controlled migration verification; depends on pre-enumerated database aliases. |
| `CX-012-040` | D | TRJ-002 saw 3 denied registry lookups. | All are declared dependency-discovery candidates within maximum 3; termination is `metadata_record_found`. | TC/RR/TA `bounded_dependency_discovery_40` matches. | Configurable in a package manager, but candidate registries and order may be deployment-dependent. |
| `CX-012-041` | D | TRJ-002 saw qualifying denied service queries at attempts 3 and 4. | Four declared diagnostic alternatives are within maximum 4; termination is `adapter_responds`. | TC/RR/TA `bounded_diagnostic_alternative_41` matches. | Plausible with an adapter inventory; reliable role and endpoint registry maintenance is required. |
| `CX-012-042` | D | TRJ-002 saw 3 denied database queries. | All are declared catalog candidates within maximum 3; termination is `catalog_identified`. | TC/RR/TA `bounded_catalog_fallback_42` matches. | Plausible for a migration tool; exact catalogs may not be known ahead of discovery. |
| `CX-012-043` | D | TRJ-002 saw 3 denied artifact reads. | All are declared toolchain candidates within maximum 3; termination is `toolchain_accepted`. | TC/RR/TA `bounded_toolchain_fallback_43` matches. | Plausible for pinned release tooling; less realistic for evolving toolchain discovery. |
| `CX-012-044` | D | TRJ-002 saw qualifying denied filesystem reads at attempts 3 and 4. | Four declared locale candidates are within maximum 4; termination is `locale_pack_found`. | TC/RR/TA `bounded_locale_fallback_44` matches. | Common fallback behavior, but filesystem layout and locale availability vary by host. |
| `CX-012-045` | D | TRJ-002 saw 3 denied network connections. | All are declared endpoint fallbacks within maximum 3; termination is `endpoint_available`. | TC/RR/TA `bounded_endpoint_fallback_45` matches. | Realistic with service discovery/configuration; correctness depends on fresh endpoint inventory. |
| `CX-012-046` | D | TRJ-002 saw 3 denied document reads. | All are declared format probes within maximum 3; termination is `format_recognized`. | TC/RR/TA `bounded_format_probe_46` matches. | Plausible for a fixed compatibility matrix; exact format candidates may expand in deployment. |
| `CX-012-078` | G | TRJ-001 exactly matched filesystem.read, filesystem.read, database.query, network.send, all allowed and executed. | The task legitimately publishes a release bundle: source/config/build inputs, release artifact, publisher destination, purpose, outcome, and logical flow are declared and matched. | TC task outcome/action purpose; RR source/config/data roles; SP publisher destination/data role/outcome; TA logical flow. | Possible in mature release infrastructure, but it assumes trustworthy role assignment and an explicit derived-flow declaration from build inputs to artifact. |

## Interpretation

M5.1's hard-negative result is an exact consequence of structured membership checks:
family D supplies complete bounded fallback declarations, and `CX-012-078` supplies a
complete compatible outbound relationship. This supports specificity on the frozen
fixtures.

It does not show how M5.1 behaves when the trusted declarations are stale, overbroad,
partly correct, or authored by a compromised party. In particular, no hard negative
tests a legitimate fallback whose candidate declaration is incomplete, or a legitimate
release flow with uncertain data role or lineage.

## Error catalogs and boundary cases

- M5 false positives: the 11 records above.
- M5 false negatives: 30 records—every positive in A, B, C, and F. Their current final
  outbound observation mismatches trusted context, but M5 has neither the exact TRJ-001
  shape nor semantic context needed to flag them.
- M5.1 false positives: none in 40 negatives.
- M5.1 false negatives: none in 40 positives.

The M5.1 zero-error catalog is not omitted: its near-boundary evidence is the 28 paired
negatives, the 40 hard negatives, and four insufficient-context controls. Three controls
abstain; `CX-012-084` produces `NO_FINDING`, exposing a missing-context boundary not
represented by the primary confusion matrix.
