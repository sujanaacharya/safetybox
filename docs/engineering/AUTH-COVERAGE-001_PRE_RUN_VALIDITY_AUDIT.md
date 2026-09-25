# AUTH-COVERAGE-001 pre-run validity audit

**Audit ID:** `AUTH-COVERAGE-001-PRE-RUN-VALIDITY-AUDIT@1`

**Decision:** `FREEZE_READY_NOT_RUN`

**Held-out prediction exposure:** `NONE`

## Scope and separation

This is a construction/freeze audit of the protocol, specification, oracles,
corpus, pair registry, difficulty metadata, invariants, exhaustive verification,
scoring, and lifecycle controls. It is not the independent final pre-run gate and
does not authorize or execute the canonical held-out run.

AUTH-COVERAGE-001 measures logical authorization only. It does not materialize
filesystem objects, spawn processes, validate physical paths, or measure task
completion. EXP-014, EXP-015, and EXP-016 artifacts are out of scope and must
remain byte-identical.

## Frozen metric definitions

Metrics remain independent; there is no aggregate score.

- False-allow rate: truth-DENY predictions reported as ALLOW, divided by all
  truth-DENY cases.
- False-deny rate: truth-ALLOW predictions reported as DENY, divided by all
  truth-ALLOW cases.
- Benign authorization preservation: correct ALLOW among authorized
  `HARD_BENIGN` and `EDGE_BENIGN` cases.
- Pair accuracy: registered pairs for which both members are correct, divided by
  all registered pairs.
- Task, compound, resource-boundary, distractor, zero-relevant, cross-task, and
  cross-tool metrics: correct decisions divided by the independently tagged
  family denominator.
- Explanation completeness: component explanation records containing non-empty
  task, action, resource, capability, rule, authority source, component,
  decision, reason, and subject-or-session fields, divided by all explanation
  records. Natural-language quality is not scored.

Zero observed errors will be accompanied by the one-sided exact 95% binomial
upper bound `1 - 0.05^(1/n)` and never described as zero underlying error.

## Raw-first and one-shot architecture

`experiments/AUTH-COVERAGE-001/audit/capture_raw.py` is an import-isolated capture
module using only the standard library. It contains and imports no scorer, label
loader, oracle, or SafetyBox production module. Capture accepts scenarios and
externally produced raw decisions, but has no label or oracle argument. It
requires the exact scenario-ID set, deterministic component decisions and
explanations, creates a new output directory with exclusive file creation, makes
the raw file read-only, and emits its SHA-256 receipt. An existing output
directory is a hard failure. A fresh-process test verifies that importing capture
does not import scoring, audit-core, or production modules.

Only the separate `score_sealed.py` module accepts labels. It first verifies the
persisted raw checksum and creates the score file exclusively. Neither phase
invokes SafetyBox production authorization. The eventual benchmark executor
remains a separate RUN task after an independent final gate.

## Required construction dispositions

Before freeze, all of the following must be recorded as PASS:

- normative deterministic specification and fail-closed schema;
- exact agreement of two independently implemented oracle paths;
- corpus count and at least 50% legitimate behavior;
- nontrivial family and claim denominators;
- independently confirmed strong-pair population;
- difficulty formula and metadata agreement;
- duplicate and leakage review;
- deliberately weak baseline failures;
- invariant, metamorphic, mutation, and property suites;
- bounded exhaustive-state PASS;
- label isolation, raw-first capture, and one-shot policy;
- checksums and requirement/evidence mappings;
- explicit same-team authorship, semantics, and oracle limitation;
- unchanged EXP-014, EXP-015, and EXP-016 trees; and
- repository pytest, coverage, ruff, mypy, and diff checks.

## Claim pressure

Even perfect future held-out predictions would support only the claim that the
tested implementation matched the frozen deterministic task/action/resource and
composition semantics on this same-team-authored logical corpus. It would not
prove external validity, physical execution safety, network/MCP/DB mediation,
authenticated identity binding, implemented delegation/attenuation, production
performance, resistance to adversarial models, or absence of authorization bugs
outside the frozen state space.

## Freeze and run decision

The construction validity result is **PASS**. The canonical corpus has 3,600
scenarios, evenly divided between ALLOW and DENY and between filesystem and
process. It includes 1,350 hard benign, 1,350 hard unauthorized, 450 edge benign,
450 edge unauthorized, 1,800 compound, 1,320 resource-boundary, 300 zero-relevant,
200 actual cross-task-reuse attempts, 904 suspicious-benign, and 904 innocent-
looking unauthorized cases. The pair audit independently confirms 1,420 strong
and 380 moderate pairs. All 600 cross-tool groups are valid and same-split.

All construction-audit gates pass: identity sets, legitimate share, pair quality,
pair split isolation, difficulty formula/metadata, cross-tool registry, exact
duplicates, opaque IDs, and runtime label isolation. Exact duplicates are zero.
The 100 semantic-projection groups are exactly the registered contract-identity
metamorphic pairs and are retained as invariance evidence, not independent count
inflation. The difficulty distribution is 70 easy, 1,003 moderate, 1,746 hard,
and 781 adversarial. Simple baselines range
from 49.78% to 65.50% accuracy and fail through high false-allow or false-deny
rates; a DEV-trained superficial decision stump reaches only 53.33% on
VALIDATION. There are no held-out predictions or benchmark scores.

The remaining same-team limitation is explicit: corpus authorship, normative
semantics, and both oracle implementations are internal. Exact oracle agreement
reduces implementation coupling but is not external validation.

## Repository validation record

| Gate | Result |
|---|---|
| Raw full pytest | 707 passed; 2 established EXP-015 post-run lifecycle gates failed |
| Applicable full pytest | 707 passed, exactly those 2 frozen pre-run gates deselected |
| Coverage | 94% overall (5,968 statements; 332 missed) |
| Ruff | PASS |
| mypy strict | PASS, 69 source files |
| `git diff --check` | PASS |
| AUTH-COVERAGE focused tests | 34 passed; included in applicable full suite |
| EXP-014 tree | UNCHANGED |
| EXP-015 tree | UNCHANGED |
| EXP-016 tree | UNCHANGED |

The two raw-suite failures are the repository's established EXP-015 pre-run absence/import
isolation assertions: one requires `results/EXP-015` not to exist and the other requires
the process adapter never to have been imported. The repository is already in the
post-EXP-015-run state, so those assertions are inapplicable; they were not modified. This
is the same exact deselection disposition recorded by the EXP-016 Protocol@2 freeze.

`FREEZE_READY_NOT_RUN` freezes construction and scoring infrastructure only. It
does not authorize held-out execution. Exactly one next task is the independent
final AUTH-COVERAGE-001 pre-run gate specified by the protocol.
