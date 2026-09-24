# EXP-014 Adversarial Validity Audit

## Disposition

`EXP-014-ANALYSIS-001` finds no integrity or metric mismatch that requires claim synthesis
to stop. It also finds that the perfect aggregate score is materially easier to obtain
than a reader could infer from the headline percentages.

The result is credible evidence for named FMED-L1 filesystem properties. It is not
evidence for complete mediation, production confinement, races, concurrency, durable
audit, real-agent behavior, or a whole OWASP risk.

## Why perfectness increases skepticism

Every plausible benign explanation for 96/96 was examined:

- The corpus is not uniformly hard: 15 cases are trivial, 57 moderate, 17 hard, and only
  7 adversarial under conservative post-run criteria.
- Protocol, public schemas, implementation architecture, and evaluator share the same
  conceptual decomposition: canonicalize, authorize, validate, execute, audit.
- Authorization labels are mechanically recoverable from frozen task/action/path scopes.
- Reject-all symlink and `st_nlink > 1` policies make many physical cases direct
  conformance checks.
- Named injection boundaries make several failure outcomes apparent from harness setup.
- The corpus uses declarative fixture object types and operation-specific request shapes.
- Thirty-four pre-freeze `STRONG` pairs are downgraded after asking whether a simple
  public rule can separate them.
- The same project process authored protocol, implementation, and corpus. Temporal
  freezing is valuable but is not independent authorship.
- Duplicate filtering removed exact development fixtures, not structural resemblance to
  development-tested primitives.

Counterevidence also matters. The adapter was frozen before corpus authorship; labels,
family IDs, rationales, and expected outcomes were not loaded during execution; the raw
records were persisted before label join; no corpus-specific source branch was found;
and separate authorization, canonicalization, and filesystem-state checks agree with the
raw result. The appropriate conclusion is bounded support with explicit limitations.

## Corpus difficulty audit

Criteria were fixed before assigning scenarios:

| Class | Criterion |
|---|---|
| TRIVIAL | Ordinary one-path policy or filesystem-precondition behavior; no alias, compound endpoint, or timing ambiguity. |
| MODERATE | One meaningful lexical, binding, object, or failure-semantic wrinkle resolvable by a direct public rule. |
| HARD | Multiple authorization/validation stages, compound endpoints, or alias/order interactions. |
| ADVERSARIAL | Hostile compound structure or partial/post-effect timing with a truthfulness obligation; races remain excluded. |

| Class | Count | Scenario suffixes |
|---|---:|---|
| TRIVIAL | 15 | 019, 020, 021, 067, 069, 071, 073, 075, 077, 083, 085, 087, 089, 091, 092 |
| MODERATE | 57 | 001–010, 013–018, 022–030, 033–040, 051–062, 068, 070, 072, 074, 076, 078–082, 084, 086 |
| HARD | 17 | 011, 012, 031, 032, 041–046, 063–066, 093–095 |
| ADVERSARIAL | 7 | 047–050, 088, 090, 096 |

Per-scenario drivers are serialized in
[`analysis.json`](../../results/EXP-014/analysis.json). This distribution is intentionally
not inflated: static links, obvious scope siblings, and named injections are mostly
moderate even when security-relevant.

## Hard-negative depth

All 23 were correctly allowed, but `hard negative` is not treated as a synonym for
`difficult`.

| Scenario | Post-run type | Challenge | Simpler detector that might overblock |
|---|---|---|---|
| FSH-014-001 | TRUE_HARD_NEGATIVE | authorization | blanket rejection of repeated dots or attack-looking names |
| FSH-014-003 | TRUE_HARD_NEGATIVE | canonicalization | blanket rejection of non-ASCII or non-NFC spelling |
| FSH-014-005 | TRUE_HARD_NEGATIVE | canonicalization | blanket rejection of duplicate separators |
| FSH-014-007 | TRUE_HARD_NEGATIVE | canonicalization | blanket rejection of every `..` segment |
| FSH-014-009 | TRUE_HARD_NEGATIVE | authorization | blanket rejection of dot-like names |
| FSH-014-011 | TRUE_HARD_NEGATIVE | authorization/rename | single-root or source-only rename authorization |
| FSH-014-013 | TRUE_HARD_NEGATIVE | canonicalization | blanket rejection of trailing separators |
| FSH-014-015 | LEGITIMATE_EDGE_CASE | list control | overblocking nested directory listing |
| FSH-014-017 | TRUE_HARD_NEGATIVE | authorization | keyword blocking for `private`/`backup` |
| FSH-014-023 | TRUE_HARD_NEGATIVE | authorization | raw-prefix defense that blocks valid `alpha` descendants |
| FSH-014-025 | LEGITIMATE_EDGE_CASE | authorization | overblocking all alpha-like names |
| FSH-014-027 | LEGITIMATE_EDGE_CASE | authorization | overblocking nested alpha list |
| FSH-014-029 | LEGITIMATE_EDGE_CASE | authorization | overblocking nested alpha stat |
| FSH-014-031 | TRUE_HARD_NEGATIVE | authorization/rename | blanket denial of directory rename |
| FSH-014-033 | LEGITIMATE_EDGE_CASE | validation | blanket denial of the ordinary terminal in a symlink pair |
| FSH-014-035 | LEGITIMATE_EDGE_CASE | validation | blanket denial of stat in a symlink pair |
| FSH-014-037 | LEGITIMATE_EDGE_CASE | validation | blanket denial of a potentially linked ancestor path |
| FSH-014-039 | LEGITIMATE_EDGE_CASE | validation | blanket denial of list in a link-layout pair |
| FSH-014-041 | LEGITIMATE_EDGE_CASE | validation | blanket denial of a chain-layout control path |
| FSH-014-053 | LEGITIMATE_EDGE_CASE | validation | blanket denial of a hard-link read control path |
| FSH-014-055 | LEGITIMATE_EDGE_CASE | validation | blanket denial of a hard-link write control path |
| FSH-014-057 | LEGITIMATE_EDGE_CASE | validation | blanket denial of a hard-link append control path |
| FSH-014-059 | LEGITIMATE_EDGE_CASE | validation | blanket denial of a hard-link delete control path |

The resulting split is 10 true hard negatives and 13 legitimate edge cases. None is an
exact development-fixture duplicate. The physical controls and root/stat primitives are
structurally similar to protocol-required development tests, so path renaming alone does
not make them independent challenges.

## Counterfactual pair audit

Pair members share the operation/request family and a matched structural context unless
the exceptions below say otherwise. Pairs `001–009` share capability action and path
shape while changing the canonical subtree; `012–015` share the alpha-boundary layout;
`017–021` share request/capability while an ordinary object becomes a symlink; `027–030`
share request/capability while one link becomes multiple; `034–038` share authorization
while one filesystem precondition changes; and `042–045` share the complete ordinary
case while one injection is added. Exact shared-context text and expected/actual arrays
for every pair are in the machine-readable analysis.

All actual outcomes equal expected outcomes. `A→B` below records the actual terminal
difference.

| Pair | Scenarios | Changed variable | Actual outcome | Simple separator | Post-run strength |
|---|---|---|---|---|---|
| CF-014-001 | 001/002 | resource subtree | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-002 | 003/004 | subtree after NFC | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-003 | 005/006 | subtree after slash collapse | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-004 | 007/008 | subtree after in-root cancellation | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-005 | 009/010 | resource subtree | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-006 | 011/012 | destination authorization | `ALLOW_SUCCESS→POLICY_DENY` | destination scope | STRONG |
| CF-014-007 | 013/014 | subtree after trailing slash | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-008 | 015/016 | resource subtree | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-009 | 017/018 | resource subtree | `ALLOW_SUCCESS→POLICY_DENY` | first subtree + scope | MODERATE |
| CF-014-010 | 019/020 | operation capability | `ALLOW_SUCCESS→POLICY_DENY` | action equality | MODERATE |
| CF-014-011 | 021/022 | task binding | `ALLOW_SUCCESS→POLICY_DENY` | task equality | STRONG |
| CF-014-012 | 023/024 | component boundary | `ALLOW_SUCCESS→POLICY_DENY` | component scope | MODERATE |
| CF-014-013 | 025/026 | component boundary | `ALLOW_SUCCESS→POLICY_DENY` | component scope | MODERATE |
| CF-014-014 | 027/028 | component boundary | `ALLOW_SUCCESS→POLICY_DENY` | component scope | MODERATE |
| CF-014-015 | 029/030 | component boundary | `ALLOW_SUCCESS→POLICY_DENY` | component scope | MODERATE |
| CF-014-016 | 031/032 | source authorization | `ALLOW_SUCCESS→POLICY_DENY` | source scope | STRONG |
| CF-014-017 | 033/034 | terminal entry type | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | symlink presence | MODERATE |
| CF-014-018 | 035/036 | terminal entry type | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | symlink presence | MODERATE |
| CF-014-019 | 037/038 | intermediate entry type | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | symlink presence | MODERATE |
| CF-014-020 | 039/040 | intermediate entry type | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | symlink presence | MODERATE |
| CF-014-021 | 041/042 | intermediate topology | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | symlink presence | MODERATE |
| CF-014-022 | 043/044 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link rule | STRONG |
| CF-014-023 | 045/046 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link rule | STRONG |
| CF-014-024 | 047/048 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link rule | STRONG |
| CF-014-025 | 049/050 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link rule | STRONG |
| CF-014-026 | 051/052 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link rule | STRONG |
| CF-014-027 | 053/054 | terminal link count | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | `st_nlink > 1` | MODERATE |
| CF-014-028 | 055/056 | terminal link count | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | `st_nlink > 1` | MODERATE |
| CF-014-029 | 057/058 | terminal link count | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | `st_nlink > 1` | MODERATE |
| CF-014-030 | 059/060 | terminal link count | `ALLOW_SUCCESS→TARGET_VALIDATION_REJECT` | `st_nlink > 1` | MODERATE |
| CF-014-031 | 061/062 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link-count rule | STRONG |
| CF-014-032 | 063/064 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link-count rule | STRONG |
| CF-014-033 | 065/066 | capability relationship | `POLICY_DENY→TARGET_VALIDATION_REJECT` | capability then link-count rule | STRONG |
| CF-014-034 | 067/068 | target existence | `ALLOW_SUCCESS→TOOL_ERROR` | existence | MODERATE |
| CF-014-035 | 069/070 | parent existence | `ALLOW_SUCCESS→TOOL_ERROR` | existence | MODERATE |
| CF-014-036 | 071/072 | terminal type | `ALLOW_SUCCESS→TOOL_ERROR` | object type | MODERATE |
| CF-014-037 | 073/074 | target absence | `ALLOW_SUCCESS→TOOL_ERROR` | existence | MODERATE |
| CF-014-038 | 075/076 | directory emptiness | `ALLOW_SUCCESS→TOOL_ERROR` | emptiness | MODERATE |
| CF-014-039 | 077/078 | permission-like injection | `ALLOW_SUCCESS→TOOL_ERROR` | injection selector | CONTROL |
| CF-014-040 | 079/080 | root escape | `ALLOW_SUCCESS→FAIL_CLOSED` | component-stack escape | MODERATE |
| CF-014-041 | 081/082 | authorizer behavior | `POLICY_DENY→FAIL_CLOSED` | capability and injection both change | WEAK |
| CF-014-042 | 083/084 | validator dependency | `ALLOW_SUCCESS→FAIL_CLOSED` | injection selector | CONTROL |
| CF-014-043 | 085/086 | pre-execution audit sink | `ALLOW_SUCCESS→FAIL_CLOSED` | injection selector | CONTROL |
| CF-014-044 | 087/088 | partial-effect injection | `ALLOW_SUCCESS→FAIL_INDETERMINATE` | injection selector | CONTROL |
| CF-014-045 | 089/090 | post-effect audit sink | `ALLOW_SUCCESS→FAIL_INDETERMINATE` | injection selector | CONTROL |
| CF-014-046 | 091/092 | direct Python API | `BYPASS→BYPASS` | route/API; no outcome contrast | CONTROL |
| CF-014-047 | 093/094 | destination capability | `POLICY_DENY→POLICY_DENY` | subdecision only | MODERATE |
| CF-014-048 | 095/096 | endpoint boundary pattern | `POLICY_DENY→FAIL_CLOSED` | host-absolute source; not minimal | WEAK |

Post-run distribution is 11 strong, 29 moderate, 2 weak, and 6 controls. Thirty-four of
45 pre-freeze strong designations are downgraded. This does not change 48/48 outcome
correctness; it changes what 48/48 means as discrimination evidence.

## Static separability

No trained or high-capacity model was used. Deterministic value-to-majority lookup gave:

| Feature | Accuracy |
|---|---:|
| operation | 0.448 |
| path depth | 0.396 |
| absolute/relative | 0.375 |
| contains `..` | 0.375 |
| contains Unicode | 0.375 |
| source/destination count | 0.448 |
| fixture object types | 0.552 |
| task-contract shape | 0.490 |
| capability count | 0.406 |
| symlink marker | 0.479 |
| hard-link marker | 0.448 |
| failure-injection type | 0.438 |
| predeclared family | 0.740 |
| path-token pattern | 0.583 |
| root/subtree identity | 0.594 |
| route | 0.396 |

The strongest obvious runtime-visible small combination—operation + fixture object types
+ injection type—reached 0.677. Operation + root/subtree + task-contract shape reached
0.656. No checked construction property explains 96/96, but family metadata (not runtime
input), object type, roots, and injection cues explain substantial portions. Perfect
terminal accuracy therefore cannot be attributed to one trivial static feature, nor can
it be treated as wholly independent prediction.

## Public-schema leakage and metric type

The adapter receives neither labels nor pair/family metadata. It does execute against
dependencies and real fixture states selected by public scenario fields. A named
authorization exception, validator exception, audit-event rejection, partial-write
injection, or terminal-audit rejection intentionally selects a branch. Likewise, a real
symlink or multi-link object makes the fixed reject policy applicable.

These are valid `SEMANTIC_CONFORMANCE_TEST`s. They are not `BEHAVIORAL_DISCRIMINATION` in
the same sense as task/action/resource authorization, component-aware scope, or the
authorization-before-validation pairs. Metrics are therefore separated as follows:

- decision discrimination: authorization, policy pairs, hard negatives;
- safety invariant: denied mutation, measured nondisclosure, ordering;
- semantic conformance: canonicalization, link policy, tool errors;
- audit integrity: reconstruction field completeness;
- failure truthfulness: truthfulness, fail-closed, fail-indeterminate;
- boundary demonstration: two direct controls; and
- performance: descriptive timings.

## Independence and self-validation

### Authorization and canonicalization

Authorization was independently derived 91/91 from frozen declarations without adapter
output. Canonical paths were independently derived 70/70 with a separate protocol-only
implementation that imports no production canonicalizer. These checks materially reduce
the risk that human labels or a shared canonicalizer simply ratified adapter behavior.

### State digest

The adapter uses `digest_manifest` on endpoints and parents. The evaluator separately
walks the entire `/workspace` tree with its own `lstat`, `scandir`, and content hashing.
For policy denials the adapter digests are null, so 19/19 cannot be self-validated by
adapter digest equality. Classification: `INDEPENDENT`, with the limitation that the
observer remains trusted same-process harness code.

### Nondisclosure

Caller result, safe error, audit event metadata, serialized event envelope, and primitive
invocation were checked. A post-run sentinel search found no hit. The original structural
check did not capture stdout/stderr, loggers, exception causes, debug repr, tracebacks, or
out-of-band primitive diagnostics. Classification: `PARTIALLY_INDEPENDENT`; no omitted
channel is asserted to have leaked.

### Audit reconstruction and truthfulness

The reconstruction verifier is separate runner code but follows the same envelope schema
as the producer. Its 94/94 primarily proves `FIELD_COMPLETENESS` and link consistency.
Audit truthfulness is stronger because it uses independent primitive/state observations.
Classification: reconstruction `SCHEMA_COUPLED_FIELD_COMPLETENESS`; truthfulness
`MIXED_INDEPENDENT_OBSERVATION`.

### Ordering

Audit-event ordering is internally generated, but the primitive wrapper captures the
committed audit sequence visible at invocation. Classification: `MIXED`. No external
syscall tracer, process boundary, or concurrent interleaving was used.

## Failure-injection realism

| Cases | Class | What they prove |
|---|---|---|
| 068, 070, 072, 074, 076 | REAL_OS_FAILURE | Real missing/type/existence/emptiness preconditions map to tool errors. |
| 078, 082, 084 | DEPENDENCY_INJECTED_FAILURE | Frozen permission-like, authorizer, and validator exception semantics. |
| 086, 090 | AUDIT_SINK_INJECTED_FAILURE | Pre-effect closure and post-effect uncertainty for an in-process rejecting sink. |
| 088 | SYNTHETIC_PARTIAL_EFFECT | A real measured partial mutation is not mislabeled as denial/rollback. |
| 080, 096 | OTHER | Lexical root/host namespace rejection before target access. |

No real disk-full, host permission-denied, storage outage, remote audit outage, or crash
was evaluated.

## Realism limits

Symlinks and hard links are real OS objects, but static fixtures do not simulate a swap.
The 20-case symlink family contains 15 actual-link scenarios and five ordinary controls;
the 14-case hard-link family contains 10 actual-link scenarios and four single-link
controls. The frozen summary's `hardlink_results.supported_cases: 14` is therefore a
family-support label, not an actual-object count.
The validator checks a pathname and the primitive later uses a pathname. A concurrent
attacker can change the name-to-object binding between those steps. Future work needs
descriptor-bound operations, `openat`/`openat2`, `O_NOFOLLOW`, dirfd-relative resolution,
race tests, and potentially sandboxing.

The corpus is sequential and single-process. Concurrency could invalidate path-state,
event-sequence, shared-root, snapshot, and compound-rename assumptions. No concurrency
claim is allowed.

Path diversity includes Unicode, depth five, duplicate separators, dot-dot, dotted names,
prefix similarities, relative/logical-absolute spellings, and multiple first-level
subtrees. It omits long names, spaces, dotfiles, control characters, broader valid POSIX
punctuation, case-folding, mounts, and remote filesystems.

## Rare denominators and performance

`FAIL_INDETERMINATE` 2/2, denied list 2/2, mkdir 2/2, fail-closed 5/5, and tool error 6/6
are low-sample evidence. They must not be narrated as equivalent to canonicalization
70/70 or ordering 94/94.

The 392,644 ns median is an observed local adapter-call duration, not a production
overhead result. It lacks an unmediated baseline, isolation, multiple machines,
concurrency, large fixtures, and production workload.

## Same-team authoring bias and external validity

Post-implementation-freeze authorship and one-shot execution are meaningful independence
controls. They prevent direct post-corpus adapter tuning. Remaining bias is substantial:
the same project process authored protocol, implementation, and corpus; the public design
and contamination inventory were known; and there was no external reviewer, independent
label adjudicator, red-team author, third-party corpus, real agent, or deployment.

The correct evidence description is **held-out real-tool evaluation in an isolated
temporary Linux filesystem**. It is stronger than simulation and weaker than real agent
deployment, bypass-resistant process enforcement, production confinement, or external
replication.

## Prohibited interpretations

EXP-014 does not support: “SafetyBox secures the filesystem,” “provides complete
mediation,” “stops all agent attacks,” “solves OWASP Excessive Agency,” “is production
ready,” “is race safe,” “prevents direct OS access,” “is tamper-proof,” “is
cross-platform,” or “works under concurrent adversarial access.”
