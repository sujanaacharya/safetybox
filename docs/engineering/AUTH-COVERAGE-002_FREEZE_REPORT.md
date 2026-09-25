# AUTH-COVERAGE-002 corpus freeze report

**Protocol:** `AUTH-COVERAGE-002-PROTOCOL@1`
**Candidate:** `AUTH-COVERAGE-002-CORPUS@1-CANDIDATE`
**Decision:** `BLOCKED_PROTOCOL_AND_EXPLANATION_VALIDITY`
**Starting substrate:** `8e3ba29bbadcdc9c4de4c0d306e8eaaf013dab78`

**This document is not a freeze certificate.** The candidate described below failed the
independent scientific gate; see `AUTH-COVERAGE-002_BLOCKED_AUDIT.md`. No root freeze
manifest, freeze commit, push, or run authorization exists.

The rejected candidate contains 4,000 scenarios: DEV 800, VALIDATION 800, HELD_OUT 2,400;
filesystem 2,000 and process 2,000; ALLOW 2,000 and DENY 2,000. It has 1,908 hard
authorized, 1,912 hard unauthorized, 92 edge authorized, and 88 edge unauthorized
scenarios.

Coverage families include suspicious authorized 600, benign-looking unauthorized 600,
task binding 700 scenarios/350 strict pairs, cross-task reuse 350, resource boundary 800,
action boundary 600, synthesis 600, distractor 4,000, and zero-relevant 750. Compound
quadrants are AA 1,000, AD 318, DA 334, DD 348. Context-non-authority metadata exists for
all 4,000 scenarios, including 100 decision-preserving registered context-pair roots.

The 2,000-pair registry contains 1,600 strict-strong and 400 strong-auxiliary pairs, with
zero moderate or weak pairs. All 250 cross-tool groups are strictly comparable. There are
3,900 normalized semantic templates, largest cluster 2, zero exact duplicates, zero
cross-split duplicates, and zero cross-split normalized near-templates.

Oracle agreement is 4,000/4,000. The independent bounded model passes 72,660 states.
No HELD_OUT reservation, start, exposure, completion, raw record, result package, or
production authorization call exists. The checksum root under `corpus/manifests` binds
protocol, spec, oracles, all three runtime packages, analysis, pair, difficulty, split,
cross-tool, external-pack, contract, and construction manifests.

The freeze does not authorize execution and makes only authorization-corpus claims. All
non-claims and same-team limitations in the protocol remain binding.

Every value in this report is development/negative evidence only; none is HELD_OUT
result evidence.
