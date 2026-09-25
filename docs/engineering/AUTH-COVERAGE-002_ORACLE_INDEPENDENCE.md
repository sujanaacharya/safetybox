# AUTH-COVERAGE-002 oracle-independence audit

**Audit identity:** `AUTH-COVERAGE-002-ORACLE-INDEPENDENCE@1`
**Disposition:** PASS with bounded common-specification risk
**Production calls:** 0

Both oracles implement `AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1`, import no SafetyBox
module, and have no dependency edge between them. Oracle A uses request-first predicate
evaluation and filters action candidates before evaluating resource coverage. Oracle B
constructs an indexed finite permitted relation from deduplicated capability tuples and
then tests whether every component index is a member. Agreement is 4,000/4,000 canonical
scenarios and 48/48 malformed controls.

| Dimension | Oracle A | Oracle B | Independent bug-detection assessment |
|---|---|---|---|
| Task | early request predicate | membership construction gated per component | MODERATE |
| Action | filtered action-candidate list | `(action, contains)` tuple equality | MODERATE |
| Resource | canonical-string prefix predicate | path-segment tuple containment | STRONG |
| Capability | request-centric matching | capability-centric permitted-set construction | MODERATE |
| Compound | `all()` over named decisions | equality of permitted indexes to required indexes | MODERATE |
| Tool | ordered named request construction | indexed tool-shape relation | MODERATE |
| Invalid structure | explicit conditional validation | assertion-based closed validation block | MODERATE |

Resource matching does not repeat AUTH-COVERAGE-001's shared-matcher weakness: one oracle
uses guarded string boundaries, while the other decomposes paths into segments and checks
strict tuple-prefix containment. The exhaustive model separately covered resource binding
in 24,160 states.

The remaining common-mode risk is intrinsic: both implementations and the written
specification are same-team artifacts and use the same finite semantic vocabulary.
Agreement therefore establishes internal consistency and useful independent
bug-detection, not an externally validated ground truth. This is `BOUNDED`, not resolved.
