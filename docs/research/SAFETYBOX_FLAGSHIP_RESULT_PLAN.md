# SafetyBox Flagship Result Plan

**Status:** candidate result target; not a claim or preregistration

**Target identity:** `SAFETYBOX-FLAGSHIP-TARGET@1`

## Candidate result

The highest-value near-term target is:

> Across a preregistered, blinded, counterfactual filesystem-plus-native-process corpus,
> zero unauthorized protected effects are observed on explicitly enumerated mediated
> routes, while benign completion, false denial, mediation bypass, and effect-provenance
> completeness meet separately preregistered thresholds and independent authority and
> effect oracles agree.

This is a target, not “zero risk,” proof of universal prevention, or a current SafetyBox
property. Final wording must report `0/N`, a justified interval, route inventory version,
known bypasses, evidence level, and all utility/error results.

## Pressure test

| Question | Assessment |
|---|---|
| Is the outcome directly tied to the north star? | Yes: it measures actual protected effects, not decisions alone. |
| Can it be measured now? | Not yet. EXP-014 supplies bounded filesystem evidence, but EXP-016 must first demonstrate native child execution and no combined effect harness is frozen. |
| Is filesystem + process a defensible scope? | Yes if claims remain route-bounded and the two coverage denominators stay separate. It is not broad agent-system coverage. |
| Would zero unauthorized effects be informative? | Only with nontrivial unauthorized opportunities, strong counterfactual pairs, successful benign effects, bypass attempts, and independent effect observation. |
| Could policy accuracy hide bypass? | Not if the protocol reports authorization, primitive forwarding, bypass, occurrence, attribution, and completion independently. |
| Could the result be vacuous? | Yes if positive effects do not execute, as EXP-015 demonstrated. A nonvacuous benign-completion/reachability gate is mandatory. |
| Is independent verification plausible? | Authority and effect oracles can be separately implemented; external corpus/audit remains later Level 5 work. |

## Entry gates

1. `AUTH-COVERAGE-002` validates the authorization path using a sealed, non-exposed
   corpus and complete raw records.
2. EXP-016 establishes held-out native direct-child reachability and truthful lifecycle
   evidence, including successful benign completions.
3. Filesystem and process route inventories name all in-scope primitives and direct
   controls; known bypasses remain explicit.
4. The combined protocol freezes causal effect definitions, independent state/process
   oracles, request-to-primitive binding, failure states, and provenance reconstruction.
5. The runner is crash-safe and exposure-accounted before the corpus exists.

The first two can proceed as independent prerequisite branches; neither alone supports the
flagship claim.

## Precommitted result dimensions

- `FALSE_ALLOW_RATE` and `FALSE_DENY_RATE`;
- `DENIED_PRIMITIVE_FORWARD_RATE`;
- `UNAUTHORIZED_EFFECT_RATE`;
- `MEDIATION_BYPASS_RATE` and route-level coverage;
- `EFFECT_ATTRIBUTION_COMPLETENESS`;
- benign authorization preservation and benign completion;
- task-binding, cross-task reuse, compound, and pair accuracy;
- exclusions, partial/indeterminate outcomes, and uncertainty intervals.

No aggregate score or post hoc “safe” threshold is allowed.

## Exactly one immediate program task

Freeze and implement the `AUTH-COVERAGE-002` canonical raw-first runner plus exposure
ledger against a development-only synthetic fixture, before authoring any new benchmark
corpus.

This is smaller than executing the benchmark, blocks the recurrence of every critical
AUTH-COVERAGE-001 process failure, and allows independent corpus authorship to begin on a
stable runtime serialization. EXP-016 can continue afterward without being conflated with
authorization correctness.
