# EXP-014 Results and Adversarial Post-Run Analysis

## 1. Identity

- Analysis: `EXP-014-ANALYSIS-001`
- Run: `EXP-014-RUN-001`
- Corpus: `EXP-014-CORPUS@1`
- Adapter: `FS-ADAPTER@1`
- Boundary: `FMED-L1`
- Analysis-start HEAD: `3410dad44cf3b476b52065a6b91b256a667173f7`

This is derived post-run analysis. It does not alter or rerun the protocol, adapter,
corpus, labels, predictions, success criteria, or raw results.

## 2. Frozen references

| Artifact | Git SHA |
|---|---|
| Protocol/design | `7baf20293caa83d3fff6a200174c4f8840918607` |
| Implementation | `b49a5cd0ff28a38eb8314291f51c106d2df9bd7c` |
| Corpus | `5ac7311bb8f086cca97f474069d068067ac73142` |
| Raw results | `17a0f6b6409ac85a2ee1a2d49f36a5748e3ab310` |
| Lifecycle disposition | `EXP-014-POST-RUN-GATE-DISPOSITION@1` |

The frozen raw SHA-256 values are:

| File | SHA-256 |
|---|---|
| `runs.jsonl` | `2584f54038c3f68d4c2b34382a699c542dbe070cc053e8f63b084e57d7012526` |
| `repeats.jsonl` | `88be9f6d88e9fbcc1ef34b846f8f75a95533988800513931c79a283b2ca3bd20` |
| `summary.json` | `31f93a81ed8423c1c242edbd72fae627411a3d6bfdd3b7830a0fa3e8aedb8209` |
| `independent_recompute.json` | `043808b4d68f25dca8cce47504458b031f5adb6d3ce9b9b4f19aa16af63eae62` |
| `SHA256SUMS` | `31fb12aa676574fca6621c92c96dd55a0372375a969ccc0897527952b3ad9f0d` |

`sha256sum -c` passed, and these five files are byte-identical to the raw-result freeze.
The protocol, adapter sources, and corpus data remain unchanged from their freezes. The
post-freeze corpus-test edit only retired the obsolete pre-run result-directory absence
assertion documented by the lifecycle disposition.

## 3. Research question

EXP-014 asked whether SafetyBox could mediate real filesystem operations so authorized
operations execute, unauthorized operations have no protected effect, authorization
precedes effect, and audit evidence reconstructs attempted and completed behavior.

The answer is **yes within the frozen corpus, tested channels, isolated Linux temporary
filesystem, and FMED-L1 adapter route**. It is not evidence of universal filesystem
confinement or complete mediation.

## 4. Mediation boundary

Empirically, FMED-L1 means calls routed through `FS-ADAPTER@1`. It includes the nine typed
operations, logical `/workspace` mapping, task/capability authorization, post-allow
physical validation, real local filesystem primitives, and in-process audit lifecycle.

It excludes direct `os.*`, direct `pathlib`, shell redirection, native code, inherited
descriptors, process compromise, concurrency, a TOCTOU adversary, kernel bypass,
container escape, and every non-filesystem transport. Scenarios `091/092` intentionally
demonstrate direct-route bypass and are controls, not adapter failures.

## 5. Corpus

The corpus contains 96 scenarios: 94 adapter routes and two direct-route controls. All
nine operations have successful and policy-denied cases. There are 48 pairs, 23 declared
hard negatives, 20 symlink-family cases, 14 hard-link-family cases, 16 renames, and two
registered repeats.

Post-run difficulty was classified using criteria fixed before classification:

- `TRIVIAL`: ordinary one-path policy or precondition behavior;
- `MODERATE`: one meaningful lexical, policy, object, or failure wrinkle;
- `HARD`: multiple stages/endpoints or alias/order interactions; and
- `ADVERSARIAL`: compound hostile structure or partial/post-effect truthfulness.

| Difficulty | Count | Scenario suffixes |
|---|---:|---|
| TRIVIAL | 15 | 019, 020, 021, 067, 069, 071, 073, 075, 077, 083, 085, 087, 089, 091, 092 |
| MODERATE | 57 | 001–010, 013–018, 022–030, 033–040, 051–062, 068, 070, 072, 074, 076, 078–082, 084, 086 |
| HARD | 17 | 011, 012, 031, 032, 041–046, 063–066, 093–095 |
| ADVERSARIAL | 7 | 047–050, 088, 090, 096 |

This distribution does not justify calling the corpus broadly adversarial. The majority
is moderate and many outcomes follow directly from public semantics.

## 6. Execution integrity

A new data-only recomputation parsed frozen `runs.jsonl` and label declarations without
importing the adapter, evaluator, or production helpers. It matched the raw summary for
terminal outcomes, authorization, denied mutation, nondisclosure, ordering,
reconstruction, truthfulness, pairs, and hard negatives.

The archived evaluator does not itself reproduce every manually enriched field in frozen
`summary.json`—notably `sentinel_audit` and lifecycle-caveat wording. This is a
reproducibility limitation of the frozen summary, not a mismatch in `runs.jsonl`; the
underlying claims were independently checked again here.

## 7. Terminal outcomes

All 96 terminal classifications match the frozen labels:

| Terminal | Correct/total |
|---|---:|
| `ALLOW_SUCCESS` | 36/36 |
| `POLICY_DENY` | 28/28 |
| `TARGET_VALIDATION_REJECT` | 17/17 |
| `TOOL_ERROR` | 6/6 |
| `FAIL_CLOSED` | 5/5 |
| `FAIL_INDETERMINATE` | 2/2 |
| `EXPECTED_FMED_L1_BYPASS` | 2/2 |

These categories are not one kind of prediction. Policy decisions provide decision
discrimination; injected errors and fixed safety rules largely provide semantic
conformance; direct routes demonstrate the boundary.

## 8. Authorization

Authorization correctness is 91/91. A separate analysis implementation derived canonical
paths, enforced exact task/action matching, applied component-aware subtree scope, and
required both rename endpoints. It used only frozen contract/capability declarations and
protocol semantics. It matched all 91 human labels and all 91 adapter decisions with no
ambiguity or contradiction.

This is `STRONG_WITHIN_SCOPE`, not evidence that a task contract captures real user
intent or that all agent routes are mediated.

## 9. Side-effect prevention

All 19 policy-denied mutations had:

- no wrapped protected primitive invocation;
- no independently observed whole-tree state change; and
- equal evaluator pre/post snapshot digests.

The evidence is independent of adapter-generated state digests. Policy denial precedes
adapter digest capture, so those cases have null adapter pre/post digests; the result is
carried by the evaluator's separate recursive `lstat`/`scandir`/content-hash snapshot and
primitive wrapper. This is `INDEPENDENT` within the trusted same-process harness.

## 10. Nondisclosure

The 9/9 result comprises read 3/3, list 2/2, and stat 4/4. No protected retrieval
primitive was called, no public result was returned, and an independent post-run search
found no corpus sentinel in the safe error or serialized audit/event channels.

The evidence is `PARTIALLY_INDEPENDENT`: stdout, stderr, external logs, exception
`__cause__`, debug representations, tracebacks, and out-of-band primitive diagnostics
were not captured. No leakage was observed, but those omitted channels are not claimed.

## 11. Canonicalization

A separate protocol-derived implementation performed Unicode NFC normalization and a
POSIX component-stack reduction without importing the production canonicalizer. It
matched source/destination observations in all 70 INV-018 cases, including source-first
fail-closed behavior for scenario `096`.

This supplies genuinely independent checking for the registered static-path cases. It
does not address concurrent path replacement or OS object identity binding.

## 12. Symlink/hard-link

All declared symlinks were actual `os.symlink` objects. The 20/20 family result covers
terminal, intermediate, relative, mapped-absolute, chain, dangling, rename, and
create-parent uses; 15 of those family scenarios contain symlink objects and five are
ordinary matched controls. Fixtures were static before one request; 20/20 is not TOCTOU
evidence.

All declared hard links were actual `os.link` aliases. Environment preflight explicitly
observed `st_nlink >= 2`. Among 14 family cases, 10 contain actual multi-link fixtures:
seven were authorized then rejected and three were policy-denied before link validation;
the other four are single-link allow controls. Per-scenario numeric `st_nlink` was not
serialized. This is a race-sensitive link-count policy, not inode confinement.
The frozen summary's `supported_cases: 14` names the full family, not 14 actual hard-link
fixtures; raw runtime markers show 10. The scored 14/14 family outcome is unchanged.

## 13. Rename

All 16 rename outcomes were correct. The matrix meaningfully covers allow/allow,
allow/deny, deny/allow, deny/deny, cross-subtree moves, both subdecisions after a source
denial, validation only after two allows, an existing regular-file destination,
empty-directory rename, prefix collision, symlink source/destination parent, multi-link
source/destination, and host-absolute source rejection.

Missing dimensions include concurrent mutation, TOCTOU, cross-device `EXDEV`, permission
failure, same-source/destination, incompatible or nonempty-directory replacement, mount
points, open-handle behavior, and case-folding filesystems.

## 14. Failures

Five tool-error cases use real filesystem state: missing target, missing parent, wrong
type, existing create leaf, and nonempty delete target. The permission-like error is
dependency injected. Authorization and validator exceptions are injected; pre/post audit
loss uses an injected in-process sink; partial write is synthetic but produces a real
measured partial mutation. Root escape and host-namespace rejection are lexical.

These cases establish frozen branch semantics and truthful uncertainty. They do not
establish behavior under real disk-full, host permission, storage-service, or remote audit
outages.

## 15. Audit

Reconstruction field checks pass 94/94, and audit truthfulness checks pass 94/94.

Reconstruction is `SCHEMA_COUPLED_FIELD_COMPLETENESS`: the runner uses separate code but
validates the same public envelope and event assumptions as the producer. Semantic
truthfulness is stronger (`MIXED_INDEPENDENT_OBSERVATION`) because execution claims are
compared with wrapped primitive calls and independent filesystem snapshots.

The audit is in-process. It is not durable, remote, append-only cryptographic,
tamper-evident, crash-consistent, or forensic-grade.

## 16. Ordering

All 94 adapter attempts passed ordering checks. Event order is an internal canonical
trace, while the primitive wrapper independently recorded the committed event types and
sequence numbers visible at invocation. Evidence is therefore `MIXED`: stronger than an
audit-only inference, weaker than external tracing or concurrent/process-level evidence.

## 17. Counterfactual pairs

All 48 pairs have correct frozen outcomes, but post-run quality is:

| Strength | Count |
|---|---:|
| STRONG | 11 |
| MODERATE | 29 |
| WEAK | 2 |
| CONTROL | 6 |

Thirty-four of the 45 pre-freeze `STRONG` pairs were downgraded. Many are valid minimal
contrasts but can be separated by a first path component, exact action/task equality,
fixture link marker, or named failure injection. Pair `041` changes both authority and
injection. Pair `046` has no terminal contrast. Pair `047` changes the second rename
subdecision but not the terminal denial. Pair `048` is not minimal. The full per-pair
record is in [EXP-014-VALIDITY-AUDIT.md](EXP-014-VALIDITY-AUDIT.md) and
[`analysis.json`](../../results/EXP-014/analysis.json).

## 18. Hard negatives

All 23 declared hard negatives are correct, but the post-run audit classifies 10 as
`TRUE_HARD_NEGATIVE` and 13 as `LEGITIMATE_EDGE_CASE`. The strongest examples are NFD to
NFC normalization, safe in-root `..`, repeated separators, trailing separators, dotted
names, suspicious but authorized names, component-boundary neighbors, and two-endpoint
rename. Ordinary single-link objects paired against link fixtures are useful controls but
not deep hard negatives.

## 19. Operation breakdown

| Operation | Total | Authorization-evaluable |
|---|---:|---:|
| append | 12 | 11 |
| create | 8 | 8 |
| delete | 8 | 8 |
| list | 6 | 6 |
| mkdir | 2 | 2 |
| read | 14 | 14 |
| rename | 16 | 15 |
| stat | 14 | 13 |
| write | 16 | 14 |

Mkdir, list, create, and delete are underrepresented. That does not invalidate their
observed cases, but operation-specific generalization is weaker, especially for mkdir.

## 20. Performance

Across 94 adapter calls, total call duration was minimum 112,276 ns, median 392,644 ns,
mean 455,513 ns, p95 916,443 ns, and p99 1,412,479 ns. The observed local median is below
one millisecond.

This is not an incremental overhead benchmark: there is no unmediated baseline,
benchmark isolation, cross-machine comparison, concurrency, production workload, or
large-fixture study.

## 21. Invariants

| Invariant | Result | Scoped interpretation |
|---|---:|---|
| INV-016 | 19/19 | `SUPPORTED_WITHIN_EXP_014_FMED_L1`; strong within scope |
| INV-017 | 9/9 | `SUPPORTED_WITHIN_EXP_014_FMED_L1`; moderate within measured channels |
| INV-018 | 70/70 | supported for registered static path state; TOCTOU excluded |
| INV-019 | 5/5 | supported for tested branches; limited denominator/realism |

Repository-wide invariant status remains `DESIRED`; the vocabulary has no scoped
established state and the evidence does not justify a universal upgrade.

## 22. Requirements

REQ-005 and REQ-007 remain architectural-only. Empirical requirements pass their raw
checks, but evidence strength varies:

- `STRONG_WITHIN_SCOPE`: REQ-002, 003, 009–011, 013, 015, 017, 019, 021–023, 027;
- `LIMITED`: REQ-018, 020, 028–030, 032; and
- `MODERATE_WITHIN_SCOPE`: the remaining empirical requirements.

REQ-018 is limited by nine cases and channel coverage; REQ-029 by only two repeats;
REQ-030 is descriptive measurement; REQ-032 covers one Linux environment.

## 23. Threats

- `SUPPORTED_MITIGATION_WITHIN_EXP_014`: registered static traversal, prefix, symlink,
  hard-link, rename, path-representation, task mismatch, measured nondisclosure, injected
  audit-loss, and synthetic partial-write truthfulness cases.
- `EXPECTED_BOUNDARY`: direct API bypass.
- `NOT_EVALUATED`: symlink-swap/TOCTOU, inherited-descriptor bypass, concurrent adversary,
  process compromise, and kernel escape.

## 24. Success/failure criteria

The raw historical report contains 10 `PASS` and one `FAIL`: `no_frozen_regression`
failed solely because an obsolete pre-run assertion required `results/EXP-014/` not to
exist after the run created it. Under `EXP-014-POST-RUN-GATE-DISPOSITION@1`, the scientific
interpretation is:

`SCIENTIFIC_SUCCESS_CRITERION_PASS_WITH_LIFECYCLE_ARTIFACT`

The raw summary is not edited. Manual raw-evidence review confirms all 11 scientific
failure criteria remain `NOT_TRIGGERED`, subject to the denominators and instrumentation
limits documented here.

## 25. Adversarial validity analysis

Plausible explanations for perfectness include:

- 57/96 cases are only moderate and 15/96 are trivial;
- protocol semantics closely match the implementation decomposition;
- policy labels follow deterministic task/action/component-scope declarations;
- fixture object types make reject-all symlink and link-count behavior straightforward;
- named dependency/audit injections direct execution into known failure branches;
- 34 pre-freeze strong pairs are weaker under post-run scrutiny;
- the same project authored protocol, implementation, and corpus;
- structural near-duplicates of required development primitives remain despite zero exact
  duplicates; and
- public schema and route choices expose test intent for conformance cases.

Against these concerns, the adapter was frozen before corpus authorship, labels were not
runtime inputs, exact development duplicates were excluded, no corpus-specific production
branch was found, independent authorization/canonicalization checks agree, and real OS
objects/effects were observed. The result is credible within scope, not broadly external.

## 26. Evidence strength

`STRONG_WITHIN_SCOPE`: authorization, denied mutation prevention, canonicalization, and
ordering. `MODERATE_WITHIN_SCOPE`: measured nondisclosure, symlink/hard-link behavior,
rename, tool errors, audit field completeness, and audit truthfulness. `LIMITED`:
fail-closed/indeterminate rare classes, determinism, and performance. `NOT_ESTABLISHED`:
complete mediation, TOCTOU safety, concurrency, durable audit, production readiness,
cross-platform behavior, and real-agent operation.

The experiment qualifies as **held-out real-tool evaluation in an isolated temporary
Linux filesystem**. Repository evidence Level 4 is justified only for the named
filesystem-mediated sub-properties. RTM-1 is justified; RTM-2 is not.

## 27. Claim implications

The central candidate is supported when “within the tested boundary” and
“nondisclosure” are read exactly as the registered FMED-L1 scope and measured channels.
The strongest recommended wording is:

> On `EXP-014-CORPUS@1`, frozen `FS-ADAPTER@1` correctly produced the registered terminal
> outcome in all 94 adapter-routed held-out scenarios in an isolated temporary Linux
> filesystem at FMED-L1. It prevented a wrapped primitive call and independently observed
> state change in 19/19 policy-denied mutations; returned no protected value and invoked
> no protected retrieval primitive in 9/9 policy-denied read/list/stat cases, with no
> sentinel found in evaluated result, safe-error, or serialized audit/event channels; and
> satisfied tested ordering, reconstruction-field, and truthfulness checks in 94/94
> adapter attempts.

The shorter proposed 94-scenario claim should be narrowed this way because reconstruction
is partly schema-coupled, nondisclosure has channel limits, and 48/48 pairs have mixed
quality.

### Acquirer-readiness technical interpretation

EXP-014 changes the engineering asset, not its valuation: SafetyBox now has real
side-effect mediation, a frozen held-out real-tool evaluation, explicit failure
semantics, reconstructable audit records, separated policy/execution responsibilities, a
typed public interface, no additional runtime dependency, and an empirically documented
direct-bypass boundary.

A technical acquirer would still immediately ask for MCP, network, and shell mediation;
identity and authentication; concurrency and race hardening; durable or tamper-evident
audit; process-level interception; agent-framework integrations; real customer
deployment; external validation; data lineage; and an AI semantic layer. EXP-014 supplies
none of those missing assets and supports no valuation claim.

## 28. Limitations

No complete mediation, race safety, concurrency, external authoring, external
replication, durable audit, real-agent integration, customer deployment, cross-platform
support, production performance, causal data lineage, or semantic intent inference is
established. The check-then-use pathname design leaves TOCTOU windows. Future FMED-L2/3
work would need descriptor-bound operations such as `openat`/`openat2`, `O_NOFOLLOW`,
dirfd-relative resolution, race testing, interception guarantees, and possibly process
sandboxing.

## 29. OWASP implications

EXP-014 improves `RUNTIME_PREVENTION`, `AUDITABILITY`, and `REAL_TOOL_EVIDENCE` for narrow
adapter-routed filesystem sub-properties relevant to LLM03 Excessive Agency, ASI02 Tool
Misuse & Exploitation, improper tool access, and sensitive-information impact mitigation.
Those named dimensions may cite Level 4 evidence. No whole OWASP risk is covered or
solved.

## 30. Next research gap

The strongest next implementation milestone is **shell/subprocess mediation**. It is the
frozen architecture's next scientific dependency, reuses typed binding, authorization,
failure, ordering, and audit machinery, and addresses a major alternate effect route.
The ranking is: (1) shell/subprocess, (2) HTTP/network, (3) MCP proxy, (4) process-level
filesystem hardening, (5) Python SDK, (6) data lineage, and (7) AI project scanner.

This document decides only; it does not implement the next milestone.
