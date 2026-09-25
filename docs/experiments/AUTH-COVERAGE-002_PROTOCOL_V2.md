# AUTH-COVERAGE-002 Protocol@2 preregistration

**Identity:** `AUTH-COVERAGE-002-PROTOCOL@2`

**Status:** `FROZEN_BEFORE_VALIDATION_OR_HELD_OUT_REALIZATION`

**Frozen substrate:** `8e3ba29bbadcdc9c4de4c0d306e8eaaf013dab78`

**Predecessor:** `AUTH-COVERAGE-002-PROTOCOL@1`, permanently
`BLOCKED_PROTOCOL_AND_EXPLANATION_VALIDITY`

## Version boundary and prior knowledge

Protocol@1 is not fixed or amended. Protocol@2 has a new identity because observations
preceded changes to quantitative leakage thresholds, materialization policy, explanation
ordering, whole-input presentation categories, pair-evidence persistence, and external-pack
admission. The rejected `AUTH-COVERAGE-002-CORPUS@1-CANDIDATE` counts, oracle results,
diversity results, leakage attacks, and reviews are disclosed prior development knowledge.
They informed conservative power and margin choices but are never result evidence.

No new VALIDATION realization, HELD_OUT realization, production baseline, leakage
measurement, classifier measurement, or production prediction existed when this protocol
and its quantitative table were frozen. Only formal reasoning, rejected @1 evidence, and
synthetic DEV fixtures were used.

## Scope and claims

The normative authorization relation remains
`AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1`. The experiment tests authority correctness for
filesystem and process requests. It does not test mediation or effects; future flagship
interpretation combines this evidence with EXP-016 and UNAUTHORIZED-EFFECT-001. Analysis
may map precursor relevance to ASI01, ASI02, ASI03, ASI05, ASI06, and ASI10, but may not
claim full mitigation.

## Machine-readable quantitative gates

Every numeric validity condition is in
`experiments/AUTH-COVERAGE-002/protocol2/quantitative_gates.json`. The table is
checksum-frozen in `PROTOCOL2_SHA256SUMS`; later audits must report that exact checksum.
The future corpus has exactly 4,000 scenarios: DEV 800, VALIDATION 800, HELD_OUT 2,400.
The required whole-input benign-looking unauthorized count is 500 and the construction
plan is 650. The analogous suspicious-authorized requirement and plan are 500 and 650.
The margin absorbs small implementation-neutral audit perturbations without changing a
threshold after observation.

The 12 label attacks share familywise alpha 0.01 by Bonferroni, per-attack alpha 1/1,200.
For the fixed VALIDATION denominator 800, an accuracy or balanced accuracy above 0.555
blocks. This boundary is the rounded-down binomial critical region corresponding to a
one-sided familywise-controlled chance test: standard error under a balanced 0.5 null is
sqrt(0.25/800), and the Bonferroni critical normal approximation is about 3.14 standard
errors (0.5555). The executable gate uses 0.555, the stricter representable boundary.
Each attack also uses 10,000 fixed-seed label permutations and the plus-one p-value
`(1 + count(permuted balanced accuracy >= observed))/(10,000 + 1)`; p < 1/1,200 blocks.
This permutation p-value is the sole multiplicity-controlled inferential statistic.
Accuracy, balanced-accuracy, and asymmetric-error limits are fixed non-inferential effect
size gates. VALIDATION is exactly 400 ALLOW and 400 DENY, so its null is fixed at 0.5.

An attack also blocks when one error rate is at most 0.25 and the other at most 0.60.
This detects one-class shortcuts without incorrectly treating an always-one-label control
as evidence of leakage. `metric_definitions.json` makes deterministic/reversible encoding
an exact conditional-entropy/bijection check, including fixed ID/digest prefix widths.
Generator leaf branches are frozen in `branch_registry.json`; every leaf below support 40
is aggregated at its fixed `{tool}:{family}` parent rather than omitted. Every evaluated
branch has absolute deviation at most 0.05 from the fixed 0.5 label rate, and the branch
inference attack has balanced accuracy at most 0.555. One-sided branches are forbidden.
Family, difficulty, and pair membership predictability is reported and becomes blocking
when its frozen group deviations exceed 0.05 or a primary label attack fails.

## Frozen label-inference adversary

`leakage_attack_suite.json` freezes DEV training, VALIDATION evaluation, feature families,
preprocessing, decision threshold 0.5, four model specifications, random seeds, and
permutation procedure. Runtime attacks include ID prefix, manifest order, JSON byte
length, recursive field count, received key order, path length/depth, capability count and
order, digest prefix, keyword cues, logistic regression, depth-three tree, ridge linear
model, and exact-category majority lookup with frozen DENY ties/unseen handling.
`candidate_audit.py` reconstructs the frozen production authorization input before
computing its digest; ID/digest reversibility checks cover 4, 8, 12, 16, 20, 24, and 32
prefix bits. The same executable suite predicts family, difficulty, pair membership, and
generator branch and measures each target's label-rate pathway. Hyperparameters cannot be
tuned after a VALIDATION observation.

## Generation and adaptivity order

The only permitted sequence is:

1. Freeze Protocol@2, its normative spec references, oracles, split algorithm, counts,
   families, difficulty rules, pair rules, leakage gates, and structural normalization.
2. Develop Generator@2 using DEV-only fixtures and register their contamination digests.
3. Freeze Generator@2 source, seed handling, lexicons, allocation, and templates.
4. In a later task, materialize DEV once and run DEV checks.
5. Materialize `AUTH-COVERAGE-002-CORPUS@2-VALIDATION@1` once and execute only frozen gates.
6. If any VALIDATION gate fails, block that candidate. Changing generator logic requires
   a new generator identity and next corpus identity (beginning with `CORPUS@3`) with its
   own `VALIDATION@1`. Observing a failed VALIDATION consumes the corpus identity even
   when no HELD_OUT was created.
7. If every gate passes, issue
   `AUTHORIZED_TO_MATERIALIZE_AUTH002_CORPUS2_HELDOUT` (Gate A).
8. In a separate later task, materialize HELD_OUT exactly once using the already frozen
   generator and CSPRNG ID allocator. No inspect-regenerate loop exists.
9. Audit the single realization. Any quota, leakage, diversity, pair, explanation, or
   integrity failure blocks Corpus@2. It cannot be regenerated under that corpus identity.
10. A further independent decision,
    `AUTHORIZED_TO_EXECUTE_AUTH002_CORPUS2_HELDOUT_PRODUCTION` (Gate B), is required before
    a production call. Gate A never implies Gate B.

Production policy, protocol, leakage thresholds, difficulty, pairs, structural
normalization, and generator logic cannot change after the declared implementation
freeze. After VALIDATION observation, the same cycle permits no generator change. After
HELD_OUT materialization, nothing changes. A protocol change creates a protocol identity;
a post-VALIDATION generator change creates a generator identity and corpus attempt;
HELD_OUT regeneration creates a corpus identity; a policy change after prediction creates
a run/experiment identity and leaves the old result historical.

## Explanation contract and root cause

The @1 failure was not an arbitrary expected-list defect. The frozen runner captures the
primary request with component ID `primary` and the process secondary request with ID
`cwd`, in evaluation order. @1 analysis expected `exec, cwd` and its scorer sometimes
translated `primary` to `exec` while still zipping positionally. That mixed ordered and
renamed semantics and failed raw construction.

Protocol@2 uses ordered semantics exclusively. Filesystem order is `[primary]`; process
order is `[primary, cwd]`. Raw component index, raw component ID, and frozen tool sequence
must agree. Each component contains `component_id`, `component_index`, `action`,
`resource`, `decision`, `matched_capability`, `rule`, `reason`, and `authority_source`.
There is no set-semantic fallback or manual ordering patch. DEV compatibility covers
filesystem ALLOW/DENY, process AA/AD/DA/DD, task/resource/action mismatch, zero relevant,
and synthesis. Mutations of order, presence, capability, resource, rule, reason, and
authority source must all fail.

## Whole-input presentation categories

`presentation_rules.json` freezes NFKC normalization, Unicode casefolding, tokenization,
cue vocabularies, and opaque syntax. The deterministic auditor recursively inspects every
runtime-visible string: action, resource, argv/arguments, capability descriptions and
action/resources, contract descriptions, task/request/session/actor fields, component
names, and other runtime strings. `BENIGN_LOOKING_UNAUTHORIZED` requires DENY, zero
suspicious cue matches, and a benign presentation cue across the complete input under the
frozen rule. `SUSPICIOUS_AUTHORIZED` requires ALLOW and at least one suspicious cue in the
complete input. Generator/family tags never establish category membership.

## Pair evidence and independence

Every pair record stores pair ID, both scenario IDs, target dimension, expected relation,
generator intention, changed and unchanged fields, automated diff, auditor grade,
reviewer process, and evidence digest. The generator does not set the final grade.
`AUTH-COVERAGE-002-PAIR-AUDITOR@2` recomputes it from observed records.

`STRICT_STRONG` means exactly one authority-relevant semantic dimension changed, all
other authority dimensions stayed equal, no irrelevant label cue changed, runtime
metadata changes are decision-irrelevant, and the label relation is exact.
`STRONG_AUXILIARY` meets the authority conditions and differs in a persisted auxiliary
field whose value is absent from the authorization projection. `MODERATE` changes the
target dimension plus at least one other enumerated authority dimension while satisfying
the expected relation. `WEAK` violates those rules or cannot isolate the target.
No override exists; disagreement must be resolved before freeze by correcting evidence or
blocking, never by editing a grade.

## External packs and oracles

External packs undergo nested runtime and analysis schema validation, bijective label
joins, pressure validation, pair-reference validation, tool requirements, Oracle A and B
evaluation, exact oracle agreement, specification validity, and agreement with both label
and analysis. Schema conformance alone never admits a record.

Oracle A remains direct predicate evaluation and Oracle B finite tuple/segment membership.
Their source checksums freeze with the protocol. DEV mutation tests inject prefix,
parent/child, Unicode, action/resource-swap, and cwd/exec faults into each reviewer lane;
the unmutated other oracle and bounded-model expectation must detect every fault.

## Structural diversity and cross-split policy

The frozen projection retains tool, ordered component roles, action namespace, task-match
state, resource depth, argument container/scalar shape and cue class, capability action
relation class (exact request action, other tool action, or other namespace), subtree status,
and each capability-to-request action/resource relation. Argument values retain container
shape, scalar type, list cardinality, and frozen cue class while removing dictionary-key,
string-length, and token identity.
SHA-256 of canonical JSON is the structural-template hash. There must be at least 3,200
hashes, largest cluster at most four, no exact semantic instance across splits, and at
most 25% of distinct VALIDATION structural hashes may also occur in DEV. This bounded
overlap lets DEV-trained attacks learn structural classes without allowing exact instance
reuse. The normalization cannot change after seeing a candidate distribution.

## Materialization gate and stop conditions

The authoring generator emits no `scenario_id`, `request_id`, `session_id`, or `actor`.
The separate materializer assigns all four directly with `secrets.token_hex(32)`. DEV
fixtures use a separate frozen deterministic test-ID function that rejects non-DEV input;
future VALIDATION and HELD_OUT materialization rejects injected allocators and uses only
the operating-system CSPRNG without receiving labels, semantics, or branches.

The formal pre-HELDOUT signoff requires frozen protocol and thresholds, frozen generator,
passing raw/explanation pipeline, DEV pair and presentation auditors, frozen leakage and
structure suites, passing oracle independence mutations, intact runner substrate, and
zero HELD_OUT reservations, starts, exposures, completions, and raw records. Only then may
Gate A be issued. `governance.py` has explicit `DEV_PROOF`, `PRE_HELDOUT`,
`POST_MATERIALIZATION`, and `PRE_EXECUTION` phases, so targets are not mistaken for
realized HELD_OUT records. Any failed condition returns `BLOCK` without a waiver.

The asymmetric 0.25/0.60 rule requires a predictor to reduce one error by at least half
from the 0.5 null without allowing its other error above 0.60. The branch deviation 0.05
matches the maximum tolerated effect-size advantage, and support 40 bounds a branch-rate
standard error at 0.079 while forcing smaller leaves into fixed parents. The 3,200/4
diversity gates require at least 80% unique normalized structures and cap any one structure
at 0.1% of the corpus. These are fixed design sensitivities informed by disclosed @1 DEV
evidence; they are not estimates from a new candidate.

## Vague-language audit

The validity terms “should,” “approximately,” “near chance,” “material,” “strong,”
“substantial,” “meaningful,” and “adequate” have no operative role. `STRONG` appears only
as a mechanically defined pair-grade name. Qualitative limitations do not control a gate.
All freeze/run decisions refer to exact machine-readable thresholds or exact identities.
