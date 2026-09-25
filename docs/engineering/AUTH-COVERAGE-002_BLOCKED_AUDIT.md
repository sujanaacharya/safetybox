# AUTH-COVERAGE-002 blocked authorship audit

**Audit identity:** `AUTH-COVERAGE-002_BLOCKED_AUDIT@1`
**Decision:** `BLOCKED_PROTOCOL_AND_EXPLANATION_VALIDITY`
**Protocol:** `AUTH-COVERAGE-002-PROTOCOL@1`
**Candidate corpus identity:** `AUTH-COVERAGE-002-CORPUS@1-CANDIDATE` (never frozen)
**HELD_OUT production exposure:** 0

All candidate counts, oracle outputs, structural-diversity measurements, leakage
observations, and reviewer findings in this record and its accompanying artifacts are
`DEVELOPMENT / NEGATIVE EVIDENCE ONLY`. They are not held-out result evidence.

## Blocking findings

1. The protocol says material shortcut prediction blocks freezing but did not preregister
   a numerical decision rule. A `task-only + 3 percentage points` tolerance was introduced
   after observing earlier VALIDATION attacks. The clean candidate's categorical Naive
   Bayes result (59.5%) and logistic result (59.125%) therefore cannot be declared passing
   under a genuinely preregistered threshold. The task-only composition baseline was
   57.25%.
2. Before the clean-candidate restart, earlier candidate generator changes were informed
   by all-split structural audit output. Those candidates were invalidated, but protocol
   @1 itself cannot be retroactively repaired. A new protocol/corpus identity is required
   to preregister the leakage rule and clean authorship boundary.
3. The one-shot clean candidate failed its full-component explanation compatibility
   rehearsal: synthetic process component name `exec` did not match the raw input's
   production primary name at raw-record construction. Under the frozen final-candidate
   failure policy, the candidate must block instead of being repaired and regenerated.
4. The independent pair auditor computed auxiliary changes in memory but did not persist
   them into a reviewed full registry. The checked-in unreviewed registry therefore still
   reports empty auxiliary changes, so the final strict-pair evidence package is
   incomplete even though the source-side nonce bug was corrected.
5. The whole-runtime-input audit counted 496 benign-looking unauthorized scenarios,
   below the preregistered target; family tags had overstated the qualifying count.
6. External-pack admission did not mechanically enforce all nested runtime, analysis,
   label, pressure, pair, tool-specific, dual-oracle, and specification-validity rules.

## Candidate facts that did pass

The rejected clean candidate has 4,000 scenarios (800 DEV, 800 VALIDATION, 2,400
HELD_OUT), 2,000 per tool and 2,000 per label. It has 3,900 normalized semantic templates,
largest cluster 2, zero exact/cross-split/near-template duplicates, 1,600 auditor-rated
strict-strong and 400 strong-auxiliary pairs, 250 strictly comparable cross-tool groups,
and 4,000/4,000 dual-oracle agreement. Families include 1,874 hard benign, 1,878 hard
unauthorized, 600 suspicious authorized, 600 benign-looking unauthorized, 300 cross-task
reuse, 600 synthesis, and 454 semantically audited zero-relevant scenarios. Compound
quadrants are AA 1,000, AD 335, DA 339, DD 326.

Oracle B was repaired to fail closed under optimized Python. Frozen substrate checksums
were restored. The final runtime/analysis leakage attacks now use actual runtime order and
actual bound input-digest prefixes, and the categorical attack no longer outperforms the
task-only baseline by more than the rejected post-hoc tolerance. These improvements are
useful inputs to a successor protocol but do not cure @1.

## Exposure and execution disposition

No HELD_OUT production authorization was invoked. No exposure ledger, reservation,
STARTED event, completion, raw HELD_OUT record, result package, freeze manifest, freeze
commit, push, or run authorization was created. `AUTH-COVERAGE-002-RUN-001` remains
unauthorized.

## Required successor boundary

A successor protocol must use a new identity, preregister its quantitative leakage and
pair-registry gates before any VALIDATION observation, freeze the corrected explanation
scorer and clean generator first, materialize a new corpus once, and obtain an independent
review without redesigning from the successor HELD_OUT realization.
