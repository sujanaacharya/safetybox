# AUTH-COVERAGE-001 final independent pre-run validity gate

**Gate identity:** `AUTH-COVERAGE-001-FINAL-PRE-RUN-GATE@1`  
**Reviewed freeze:** `fb894b2b5631632456f84884c64fc14aff40a536`  
**Protocol:** `AUTH-COVERAGE-001-PROTOCOL@1`  
**Corpus:** `AUTH-COVERAGE-001-CORPUS@1`  
**Review date:** 2026-09-25  
**Decision:** `BLOCKED_BENCHMARK_LEAKAGE`

This was an adversarial scientific review. It did not run the canonical benchmark, create
`results/AUTH-COVERAGE-001`, or intentionally invoke production authorization on any
held-out scenario. The existing corpus-wide production-conformance test was specifically
deselected during this gate.

## Blocking findings

### B1: runtime scenario IDs disclose every label

`build_corpus.py` publishes both the scenario-ID construction and its small search space.
For base index `n` in 1 through 1,800 it computes the runtime ID from
`SHA256("AUTH-COVERAGE-001|scenario|{n}|allow")` or the corresponding `deny` string.
It also publishes the deterministic dimension ordering and the special
`CONTRACT_IDENTITY` rule. An attacker can therefore construct a label lookup without
opening `labels.json`, without fitting on `DEV`, and without invoking an authorization
implementation.

The independent reconstruction recognized 3,600/3,600 runtime IDs and predicted
3,600/3,600 labels, including 2,160/2,160 `HELD_OUT` labels. The simpler attack that uses
only the literal `allow`/`deny` preimages, without the contract-identity correction, is
already 3,500/3,600 overall and 2,097/2,160 on `HELD_OUT`. This is a material runtime-visible
shortcut and meets the protocol's stop condition. Opaque-looking hashes are not opaque
when their labeled preimages and bounded enumeration domain are public.

This defect cannot be repaired within the frozen corpus because changing scenario IDs,
the generator, or membership would violate the task's immutability constraints. It
requires a new corpus version.

### B2: the zero-exposure premise is contradicted by frozen evidence

`tests/test_auth_coverage_corpus.py::test_scope_serialization_and_component_results_conform_to_production`
loads all 3,600 scenarios, constructs production `Capability`, `TaskContract`, and
`CapabilityEvaluator` objects, invokes `CapabilityEvaluator.evaluate` for every component,
and compares each production decision with Oracle A. The frozen pre-run audit records the
suite containing that test as passing.

The `HELD_OUT` split contains 2,160 scenarios and 3,220 components: 1,100 filesystem
component calls and 2,120 process component calls. Consequently the repository evidence
supports at least 3,220 held-out production authorization evaluations in a documented
suite run, with 2,160 scenario outcomes exposed to Oracle-A assertions. The exact
historical repetition count is not recoverable. No result package exists, but
"prediction exposure = 0" and "held-out production executions = 0" are false as scientific
provenance claims.

### B3: the future run path is not yet an isolated canonical runner

`capture_raw.py` is cleanly import-isolated, and `score_sealed.py` verifies a sealed raw
checksum before loading labels. However, no canonical execution process converts runtime
scenarios into production decisions. Capture accepts a separately prepared incoming
prediction file, so the repository cannot prove what that producer imported. The raw
schema does not require tool, contract task, full capabilities, or complete authority
provenance and therefore cannot independently reconstruct the authorization input. It
also does not stream and seal partial evidence after the first prediction. The requested
error taxonomy, per-tool/per-difficulty/per-quadrant reports, pair-quality subsets, and
`PARTIAL_AFTER_PREDICTION_EXPOSURE` transition are not frozen in executable contracts.

These are independently blocking runner-isolation/readiness defects. They do not change
the primary disposition, which uses the more specific leakage code.

## Integrity record

The worktree was clean and `HEAD` equaled the supplied freeze SHA before this gate document
was added. Both checksum manifests verified every listed file. The reviewed digests were:

| Artifact | SHA-256 |
|---|---|
| `protocol.json` | `3dff0168312d015115d11cdfdec04035c6846c6d592001c08dd71f91dcc06de5` |
| root `CHECKSUMS.sha256` | `0135a13b4ddd306adfaffc27752f9d0207025632fa398f4765e37ac63d03b0b4` |
| corpus `CHECKSUMS.sha256` | `8509a2fb1b72fe05af828ba00cf0ef6ee1463a0a00595a0b3f1da91737b87a22` |
| formal specification | `e55ec63c3a8eee868225c80bccb5a4462c5dbf457e6c990f3f67d25d99c6db43` |
| Oracle A | `1439bacb198bd0206e8e571f47d14876147539f1fb029c8fc40ffae209b450e1` |
| Oracle B | `32a8358450f3e41646d498eb00ab0fe43fc9d862a9968e4cf055d11213802739` |
| pair registry | `07e199fefaba439b5044f9ef123835fd37a31776a453a6d6442732a0039bb31a` |
| difficulty metadata | `31d4b03f67506a218318e0500ce5bbec4452d79ea67e17a3f039c8b83e966161` |
| split contract | `2541d83b05bd8a060051a777b003353cdc4ca5e9dc683bc446df6f1d0ae75103` |
| scoring contract | `1861fbffa2ff8a959d7dc51d6f022b8b3f3b2eafab21aaebf71f082e1ac5c620` |

The corpus manifest, protocol identity, corpus identity, 3,600 scenario count, checksum
coverage, and one-to-one scenario/label/difficulty joins are internally consistent.
`results/AUTH-COVERAGE-001` was absent. Integrity of bytes is `PASS`; the claimed exposure
state is `FAIL` for the reason above.

The predecessor Git tree objects match their baseline values exactly:

| Predecessor | Git tree object | Result |
|---|---|---|
| EXP-014 | `69697ad049e69e7a0710fec5f25d3f6c0318651a` | unchanged |
| EXP-015 | `ed6ea158bfab3564e8b1a89e23831f21fca630a3` | unchanged |
| EXP-016 | `18db7f1b889838e4ddf4355712ce207ec82ae055` | unchanged |

## Oracle independence and semantic coupling

Oracle A and Oracle B share only `schema.validate_scenario` as an imported module. They
also share the schema vocabulary, rule/reason strings, exact-equality semantics, and the
same-team written specification. They do not share helpers, matcher functions, production
modules, production constants, capability objects, or production composition code.

Oracle A iterates request components and filters capabilities with `_covers`; its subtree
matcher is materially the same canonical-prefix formulation used in production. Oracle B
first builds a grant relation and uses segment-vector containment for subtrees. Production
filters action capabilities and delegates resource matching to `Capability.matches` /
`resource_matches`. All three use direct task and action equality because those predicates
are elementary.

| Dimension | A versus B | A versus production | B versus production | At least one independent oracle detects a production bug? |
|---|---|---|---|---|
| TASK | MODERATE | MODERATE | MODERATE | yes |
| ACTION | MODERATE | MODERATE | MODERATE | yes |
| RESOURCE | HIGH | LOW | HIGH | yes, Oracle B |
| CAPABILITY | MODERATE | MODERATE | HIGH | yes |
| COMPOUND | MODERATE | MODERATE | MODERATE | yes, if the runner actually uses production compound composition |
| TOOL | LOW | LOW | LOW | only shape/schema faults; authorization is intentionally generic |

A task, action, resource, capability, compound-conjunction, or irrelevant-capability bug
in production is semantically distinguishable by at least one oracle. The important bounds
are that both oracles are same-team, share one schema validator, and reproduce the same
normative design. They are not external validation. Oracle independence is not itself a
blocker, but the absent production runner prevents the compound claim from being exercised
cleanly in a future run.

## Formal-specification review

The authorization specification fixes exact case-sensitive task and action equality,
lexical resource identity, strict-descendant `/**` semantics, no Unicode/case/symlink
normalization, one complete capability per atomic component, conjunctive compounds,
duplicate capability IDs as invalid, malformed/unsupported structures as fail-closed,
empty capability sets as deny, and behavior/context/unknown metadata as non-authority.
Distinct complete capabilities may cover distinct process components; partial action and
resource matches may not synthesize one atomic grant. Cross-tool equivalence is a benchmark
comparison, not an authorization identity rule.

No ambiguity was found that changes a frozen held-out decision. There is nevertheless an
explanation-level mismatch worth bounding: some frozen boundary probes contain
non-canonical resources that the formal model classifies as invalid, while the serialized
schema and construction oracles accept their shape and deny them as unmatched. The final
decision remains `DENY`, and the frozen scorer does not compare reason codes, so this does
not change labels. Formal-spec disposition: `PASS_WITH_BOUNDED_EXPLANATION_MISMATCH`, not
`BLOCKED_FORMAL_SPEC`.

## Exhaustive and invariant verification

The reported 604 states cover 256 atomic states (2 tasks, 2 actions, 2 resources and all
16 capability subsets per contract task), 16 exact-boundary probes, 8 split-capability
no-synthesis probes, 256 process-compound states with all quadrants, 64 attenuation-set
pairs, and 4 invalid structures. The checker imports the normative formal model and no
`safetybox` production module. This is `MEANINGFUL_BOUNDED_VERIFICATION`, not an unbounded
proof and not production evidence.

A gate-only expanded enumeration used 3 tasks, 3 filesystem actions, 3 resources, all 512
atomic capability subsets, and all 64 process capability subsets. It passed 46,782 primary
states: 41,472 atomic, 54 exact-boundary, 27 split-synthesis, 5,184 compound, and 45 subtree
states. It also passed 41,472 order checks, 41,472 irrelevant-addition checks, 27,648
cross-task checks, and 41,472 suspicious/AI/unknown-context checks. Compound counts were
AA 432, AD 432, DA 432, DD 3,888. No production module was imported. Z3 is not installed;
adding it solely for appearance was rejected because deterministic enumeration is cheap
and sufficient for the stated finite abstraction.

The required properties all passed at specification level:
`NO_AUTHORITY_AMPLIFICATION`, `NO_CROSS_TASK_REUSE`,
`NO_IRRELEVANT_CAPABILITY_EFFECT`, `NO_CAPABILITY_ORDER_EFFECT`,
`NO_SUSPICIOUSNESS_AUTHORITY_EFFECT`, `NO_INNOCENCE_AUTHORITY_EFFECT`,
`EXACT_RESOURCE_BINDING`, `COMPOUND_SUBDECISION_INDEPENDENCE`,
`AI_CONTEXT_CANNOT_GRANT_AUTHORITY`, and
`UNKNOWN_CONTEXT_CANNOT_EXPAND_AUTHORITY`.

## Pair and stratum reaudit

All 1,800 registered pairs resolve, have exact declared leaf differences, remain within a
split, and contain no orphan. Applying the stricter definition in this gate gives:

| Independent class | Count | Interpretation |
|---|---:|---|
| `STRICT_STRONG` | 1,320 | exactly one authority-relevant semantic dimension |
| `STRONG_WITH_AUXILIARY_CHANGE` | 0 | none required this class |
| `MODERATE` | 480 | 300 capability-presence multi-leaf changes, 80 split-capability changes, and 100 contract-identity metamorphic pairs |
| `WEAK` | 0 | none |

The frozen registry's 1,420 `STRONG` count overstates strict authority counterfactuals by
100 because `CONTRACT_IDENTITY` changes two mirrored provenance IDs and zero
authority-relevant dimensions. This is not weak evidence and does not create a material
weak-pair fraction; the conservative strict denominator remains 1,320, above the protocol
minimum.

All 180 task-binding pairs are strict: only `request.task_id` changes, the base member has
complete action/resource capability coverage, and no simultaneous action, resource, or
capability mismatch is introduced. All 200 cross-task-reuse pairs are genuine: authority
exists under Task A, the second request names Task B, the contract remains Task A, no
independent Task-B contract is present, and task identity is the sole denial cause.

The preregistered difficulty family names are not accepted uncritically. Using structural
difficulty and authority distance gives:

| Frozen stratum | Conservative reassessment |
|---|---|
| 1,350 `HARD_BENIGN` | 687 `STRONG_HARD_BENIGN`; 593 `MODERATE_HARD_BENIGN`; 70 `EDGE_OR_EASY` |
| 1,350 `HARD_UNAUTHORIZED` | 1,093 `CLOSE_BOUNDARY`; 257 `MULTI_MISMATCH`; 0 `EDGE_OR_EASY` |
| 300 zero-relevant negatives | 286 `STRONG_ZERO_RELEVANT`; 14 `MODERATE_ZERO_RELEVANT`; 0 `EASY_CONTROL` |

Every zero-relevant case has at least three partial matches (range 3--9), so distractors are
plausible rather than vocabulary-only controls. The family assignment itself is partly
index-driven; these conservative classes, not the original family names alone, should
govern any eventual interpretation.

## Compound, capability, and behavior separation

The frozen process distribution recomputes exactly as AA 901, AD 225, DA 319, DD 355.
AA is allowed only when both retained subdecisions allow; every other quadrant denies.
There are 925 atomic component instances across 811 scenarios where a capability has the
right action/wrong resource and another has the right resource/wrong action while no
single capability covers the component. They deny. Eighty registered
`MULTI_CAPABILITY_SPLIT` pairs directly target this attack.

Independent spec-level transformations over all 3,600 scenarios produced zero failures
for capability reorder, one irrelevant addition, four cumulative irrelevant additions,
opaque-ID rename, suspicious-argv replacement, unknown/AI context replacement, and an
away-from-contract task mutation on all 1,800 allowed cases. Capability count by itself is
near chance. Physical existence, symlink status, executable loadability, and other
filesystem/process validity are absent from label predicates.

Suspicious vocabulary is separated from authority: 904 suspicious-looking cases allow,
896 deny, 896 ordinary-looking cases allow, and 904 deny. Thus suspicious content neither
systematically denies nor grants. The corpus also contains 904 registered
`SUSPICIOUS_BENIGN` cases and 904 `INNOCENT_LOOKING_BUT_UNAUTHORIZED` cases. Trusted
context, B4, AI inference, and unknown context are not consumed by the authority predicate.

## Baseline attacks and leakage

Pair accuracy means both members are correct. `difficulty-only` learns a majority label per
difficulty on DEV; `tool-only` does the same per tool. Difficulty and family are not
runtime-visible and are included only as leakage diagnostics.

| Baseline | Accuracy | False-allow rate | False-deny rate | Pair accuracy |
|---|---:|---:|---:|---:|
| always allow | 50.00% | 100.00% | 0.00% | 2.78% |
| always deny | 50.00% | 0.00% | 100.00% | 2.78% |
| task equality only | 60.56% | 78.89% | 0.00% | 23.89% |
| action only | 53.64% | 92.72% | 0.00% | 9.39% |
| resource only | 65.50% | 69.00% | 0.00% | 33.78% |
| first capability only | 51.83% | 0.00% | 96.33% | 6.44% |
| capability count | 50.00% | 100.00% | 0.00% | 2.78% |
| resource similarity | 58.39% | 83.22% | 0.00% | 19.56% |
| tool only | 50.00% | 0.00% | 100.00% | 2.78% |
| difficulty only | 67.69% | 12.11% | 52.50% | 37.11% |
| suspicious keyword | 49.78% | 50.22% | 50.22% | 2.56% |
| public scenario-ID decoder | **100.00%** | **0.00%** | **0.00%** | **100.00%** |

Task-only, action-only, resource-only, resource-similarity, and capability-count attacks
are dangerous despite mediocre accuracy because their false-allow rates are 69--100%.

The frozen superficial classifier was independently reproduced: a single numeric stump
trained only on 720 DEV cases selected requested-resource length `< 73`, reached 53.61% on
DEV and 53.33% on 720 VALIDATION cases, and did not load HELD_OUT. There is no exact
cross-split scenario duplicate and registered pair/template-root groups remain within one
split. That result does not address the deterministic ID decoder.

Other DEV-to-VALIDATION probes were: raw hexadecimal ID order 51.11% validation,
resource depth/path separators 53.47%, task-ID length 49.58%, capability count 49.86%,
action 52.36%, tool 49.58%, and basename-pattern category 57.22%. Difficulty class reaches
68.33% validation. Family metadata is effectively a label field: the full family tuple
reaches 99.03% validation and the `BENIGN` versus `UNAUTHORIZED` token reaches 100%.
Family, difficulty, and pair registries are scorer-only artifacts, so this is an isolation
requirement rather than a second runtime leak. Runtime `split` is visible but close to
balanced; production must never receive or branch on it.

Balance is 1,800/1,800 overall. Filesystem is 899 allow/901 deny and process is 901/899.
DEV is 352/368, VALIDATION 363/357, and HELD_OUT 1,085/1,075. Capability-count buckets are
near balanced. Difficulty is not: EASY is 70/0, MODERATE 785/218, HARD 687/1,059, and
ADVERSARIAL 258/523 (allow/deny). Resource-depth buckets are also uneven because malformed
boundary mutations add/remove separators. Pair membership covers all 3,600 cases and is
balanced; task-binding membership is 180/180. Compound quadrants determine labels by
definition and therefore must be reported separately, not treated as a leakage feature.

## Cross-tool quality and structural diversity

No cross-tool group is strictly comparable because a filesystem request has one component
and a process request has two. Of 600 groups, 509 preserve task-bound status and decision
and are `PARTIALLY_COMPARABLE`; 91 match only the final label while differing in whether
task mismatch is causal and are `WEAK_ANALOGY`. Strong cross-tool-equivalence claims are
unsupported. The frozen consistency definition itself is exact and simple--both members
must be individually correct--but it measures paired correctness, not semantic equivalence.

There are zero exact scenario duplicates. Removing opaque subject/session/contract/
capability IDs yields 100 two-member clusters, all registered contract-identity
metamorphic pairs; the largest such cluster is 2. A gate normalization based on tool,
task-bound status, component action, capability relationship counts, capability count,
mutation dimension, boundary kind, and suspiciousness yields 906 semantic templates; its
largest cluster is 16. A coarser authority-only projection yields 302 signatures and a
largest cluster of 136. All 3,600 cases are generator-produced and all are members of one
of 1,800 pairs. Thus N=3,600 is not 3,600 independent semantic designs, but the generator
does not merely repeat a tiny handful of templates.

Mutation-path audit found that task, action, request resource, capability scope/presence,
and compound-component mutations stay within their declared semantic dimensions. The 100
contract-ID mutations are non-authority provenance changes and the 80 split-capability
mutations intentionally modify two capability leaves. Irrelevant addition, reorder,
suspicious argv, unknown context, and opaque-ID transformations are verified by the
metamorphic sweep and formal enumeration rather than by frozen opposite-label pairs.

## Joins, held-out provenance, and run architecture

There are exactly 3,600 unique scenario IDs, 3,600 unique label IDs, and 3,600 unique
difficulty/membership rows with identical key sets: no duplicates, orphans, or missing
metadata. Pair and cross-tool references resolve. Held-out membership is fixed in the
freeze commit and no held-out ID was found in production tests, policy files, manual notes,
or result artifacts outside the frozen registries. That literal-ID search is not enough to
establish non-use because the corpus-wide production test loops over the runtime file.

The intended sequence--runtime load, production decisions, raw persistence, close,
checksum, fresh scoring process, label load, registered metrics, independent recompute,
freeze--is sound as a requirement but is not implemented end to end. `capture_raw.py`
imports only standard-library modules and its fresh-import test finds no production,
oracle, scorer, or label import. `score_sealed.py` is separate. There is no execution
entrypoint, fresh-process orchestrator, independent recomputation entrypoint, or partial
evidence state machine. `raw_first.py` imports both capture and scoring and must not be an
execution-process import.

Production `CapabilityEvaluator` does not read scenario ID, family, difficulty, pair,
split, label, or expected outcome. The prospective missing runner cannot yet be audited
for those dependencies. The current raw validator requires decision, component decisions,
and deterministic explanation fields, but not tool, contract task, the capability set, or
enough request/contract data to reconstruct the decision. Raw-record sufficiency is
therefore `FAIL`.

Explanation completeness is objectively defined by field presence and explicit null on
denial; no subjective prose grade is used. The requested causal error taxonomy
(`FALSE_ALLOW`, `FALSE_DENY`, `TASK_BINDING_ERROR`, `ACTION_BINDING_ERROR`,
`RESOURCE_BINDING_ERROR`, `CAPABILITY_SYNTHESIS_ERROR`, `COMPOUND_AUTH_ERROR`,
`CROSS_TASK_REUSE_ERROR`, `EXPLANATION_ERROR`) is absent. The statistical contract is
otherwise correct: it uses numerator/denominator, Wilson intervals, and the exact one-sided
95% zero-error upper bound; it never permits the phrase "true error rate = 0%."

Metric-readiness dispositions are:

| Required report | Readiness |
|---|---|
| filesystem/process plus combined | FAIL: scorer has combined only |
| EASY/MODERATE/HARD/ADVERSARIAL | FAIL: absent from scorer |
| primary hard-benign false-deny | FAIL: benign aggregate mixes hard and edge |
| primary hard-unauthorized false-allow | FAIL: absent |
| all/strict/auxiliary/moderate pairs by dimension | FAIL: all-pair aggregate only |
| cross-task rejection | PASS |
| AA/AD/DA/DD, emphasizing false allows | FAIL: compound aggregate only |
| cross-tool exact definition | PASS definition; evidence quality bounded as above |

The external-pack JSON schema can express future cases without changing authorization
semantics, but the missing reporting strata and runner would require changing operational
scoring/metric machinery. External-pack readiness is therefore `FAIL` at this gate.

The one-shot policy forbids rerun and production tuning after exposure, but it does not
implement the mandatory `PARTIAL_AFTER_PREDICTION_EXPOSURE` state, durable per-decision
partial capture, or an explicit ban on scorer changes. The requested partial-run and
no-tuning policies are not run-ready.

## Competing-lab review

| Rank | Strongest criticism | Disposition |
|---:|---|---|
| 1 | Public deterministic scenario IDs recover every label | **BLOCKING** |
| 2 | Frozen test evidence contradicts zero held-out production execution | **BLOCKING** |
| 3 | No canonical import-isolated production execution process exists | **BLOCKING** |
| 4 | Raw records cannot reconstruct full authorization input/provenance | **BLOCKING** |
| 5 | Required stratified metrics and causal error taxonomy are not frozen executable reports | **BLOCKING** |
| 6 | Corpus, spec, and both oracles are same-team | BOUNDED, major limitation |
| 7 | No cross-tool group is strictly comparable | BOUNDED; prohibit strong cross-tool claim |
| 8 | Difficulty and family metadata strongly encode labels | RESOLVED only if scorer-only isolation is proven |
| 9 | Paired deterministic generation reduces effective independence | BOUNDED by template/signature counts |
| 10 | Oracle A's resource matcher is close to production and both oracles share semantics | BOUNDED by Oracle B and explicit coupling matrix |

### Systems-security review

Major concerns are the already exercised held-out production path, absent trustworthy
executor-to-seal chain, insufficient raw provenance, and lack of crash-safe partial
evidence. Minor concerns are runtime-visible split/ID fields, explanation validation that
checks presence rather than value consistency, and invalid-path cases whose denial reason
differs between formal and construction models. Claims must remain about logical
TaskContract authorization only; there is no containment, physical validation, identity,
delegation, network, MCP, or production-readiness evidence.

### Benchmark-methodology review

The primary rejection is exact ID leakage. Additional limitations are paired rather than
independent sampling, one deterministic generator, direct label words in sealed family
metadata, imbalanced structural difficulty, zero strict cross-tool comparisons, and
same-team corpus/oracle/spec authorship. Pair quality is otherwise strong after reducing
the strict denominator to 1,320. Difficulty names need the conservative reassessment above.

### Formal-methods review

The core predicate is precise for frozen decisions, and finite enumeration is meaningful.
It is not a proof over unbounded identifiers, arbitrary component shapes, physical paths,
identity, time, usage, destination, delegation, or external mediators. Compound semantics
are clear, but no canonical production runner currently demonstrates use of the matching
production composition path. The schema/formal mismatch on non-canonical probes affects
reasons, not frozen decisions.

## Perfect-result pressure test and frozen non-claims

Because the corpus is leaked and production has already been exercised against held-out
inputs, even a future 3,600/3,600 result cannot be described as prospective held-out
validation. The strongest defensible template would be:

> In a same-team synthetic corpus with publicly decodable scenario identifiers and prior
> development-time production conformance exposure, the frozen implementation's recorded
> outputs agreed descriptively with [CORRECT]/3,600 frozen authorization labels. On the
> [UNAUTHORIZED_N] unauthorized cases, [FALSE_ALLOW_ERRORS] false allows were observed
> (one-sided 95% exact upper bound [BOUND] only if the observed count is zero); on the
> [AUTHORIZED_N] authorized cases, [FALSE_DENY_ERRORS] false denies were observed
> ([BOUND] under the same condition). This is retrospective bounded conformance evidence,
> not an uncontaminated held-out estimate or a claim of zero population error.

The following non-claims remain frozen: not external validation; not zero population error;
not real effect mediation; not network evidence; not MCP evidence; not authenticated
identity binding; not delegation implementation; not attenuation implementation; not
production readiness; not bypass containment outside mediated tools; and not proof that AI
models are safe. Same-team authorship remains a major limitation regardless of classifier
tests.

## Validation record

The only AUTH-COVERAGE test that calls production over the frozen corpus was not run.

| Check | Result |
|---|---|
| focused AUTH-COVERAGE | 33 passed, 1 prohibited production/held-out test deselected |
| applicable full pytest | 706 passed, 3 deselected |
| established EXP-015 lifecycle dispositions | the exact two documented nodes deselected |
| additional gate exclusion | corpus-wide production conformance test deselected |
| coverage | 94%; 5,968 statements, 332 missed |
| ruff | PASS |
| mypy strict | PASS; 69 source files |
| `git diff --check` | PASS |

The three full-suite deselections are:

1. `tests/test_exp015_corpus2.py::test_exp015_corpus2_integrity`;
2. `tests/gates/test_exp015_corpus2_fresh_process_isolation.py::test_exp015_corpus2_integrity_and_import_isolation_in_fresh_process`; and
3. `tests/test_auth_coverage_corpus.py::test_scope_serialization_and_component_results_conform_to_production`.

The first two are the established post-EXP-015-run lifecycle dispositions. The third is
required by this gate's prohibition on further held-out production authorization.

## Final disposition and next task

`BLOCKED_BENCHMARK_LEAKAGE`

The canonical `AUTH-COVERAGE-001-RUN-001` must not execute. There is no run task while this
frozen version remains blocked.

**Exactly one next task:** Design and independently review a new
`AUTH-COVERAGE-002-PROTOCOL@1` and newly blinded corpus version that removes reversible
runtime-ID label encoding, excludes held-out cases from every production test, and freezes
a complete fresh-process raw-first runner, reconstructable raw schema, partial-exposure
state machine, causal error taxonomy, and all required stratified metrics before any new
held-out production authorization occurs.
