# AUTH-COVERAGE-001 oracle independence

**Assessment:** improved but not fully independent

Oracle A is a direct executable transcription of the normative predicate: validate the
structure, enforce task equality, then search for a single action/resource capability per
component. Oracle B is separately structured around capability grants and independent set
relations. It does not import Oracle A or production authorization code. The corpus freeze
requires byte-for-byte equality of their decision and component-label outputs.

Both oracles necessarily share the written authorization specification, corpus authors,
repository, and same-team review. This is conceptual coupling. Agreement catches many
implementation mistakes but cannot prove that the shared specification is correct or that
both authors did not encode the same misunderstanding. Production code is used only in
development conformance tests; production results never define labels.

## Independence controls

- Different control flow and internal representations.
- No imports between oracles.
- No import of `safetybox.capabilities`, `safetybox.authorization`, adapters, or policy.
- Invalid structures fail closed in both implementations.
- Corpus labels are regenerated independently and compared before writing the freeze.
- Exhaustive small-state verification uses a third finite relational model.
- Metamorphic expectations are derived from declared transformations, not observed
  production decisions.
- Source-import and checksum gates make the dependency boundary mechanically inspectable.

## Remaining bias and reduction plan

All current scenario authorship, semantics, and oracle review are same-team. The benchmark
must not be called externally validated. A future version should use an external pack whose
authors receive only the written interface and semantics, an independent specification
review, and a blinded pre-run audit. External contributions must preserve the frozen
scoring contract; otherwise they constitute a new benchmark version.
