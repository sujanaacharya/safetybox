# AUTH-COVERAGE-001 freeze report

**Freeze decision:** `FREEZE_READY_NOT_RUN`

**Evidence status:** deterministic benchmark construction and development verification;
no held-out predictions and no production performance result

| # | Required report item | Frozen result |
|---:|---|---|
| 1 | Protocol identity | `AUTH-COVERAGE-001-PROTOCOL@1` |
| 2 | Corpus identity | `AUTH-COVERAGE-001-CORPUS@1` |
| 3 | Freeze decision | `FREEZE_READY_NOT_RUN` |
| 4 | Freeze SHA | Git commit recorded in final handoff |
| 5 | Total scenario count | 3,600 |
| 6 | Filesystem count | 1,800 |
| 7 | Process count | 1,800 |
| 8 | Authorized count | 1,800 |
| 9 | Unauthorized count | 1,800 |
| 10 | Hard benign count | 1,350 |
| 11 | Hard unauthorized count | 1,350 |
| 12 | Edge benign count | 450 |
| 13 | Edge unauthorized count | 450 |
| 14 | Strong pair count | 1,420 |
| 15 | Moderate pair count | 380 |
| 16 | Weak pair count | 0 |
| 17 | Task-binding pair count | 180 (360 scenarios) |
| 18 | Cross-task reuse count | 200 actual rejection attempts |
| 19 | Resource-boundary count | 1,320 scenarios; all frozen boundary subtypes nonzero |
| 20 | Capability-distractor count | 3,600 |
| 21 | Zero-relevant count | 300 hard negatives |
| 22 | Compound AA/AD/DA/DD | 901 / 225 / 319 / 355 |
| 23 | Suspicious-benign count | 904 |
| 24 | Innocent-looking unauthorized count | 904 |
| 25 | Cross-tool consistency count | 600 equivalence groups / 1,200 tagged scenarios |
| 26 | Property-generated case count | 3,600 |
| 27 | Metamorphic checks | 100 corpus contract-identity checks plus bounded invariant checks |
| 28 | Mutation checks | 1,700 decision-relevant corpus mutations |
| 29 | Deterministic invariants | 17 bounded invariant categories, all PASS |
| 30 | Exhaustive state-space size | 604 explicit states |
| 31 | Exhaustive verification result | PASS |
| 32 | Formal-method result | No external solver; deterministic exhaustive enumeration selected |
| 33 | Oracle A implementation | `oracle_a.py`, direct specification evaluator |
| 34 | Oracle B implementation | `oracle_b.py`, independent grant-relation evaluator |
| 35 | Oracle agreement | 3,600 / 3,600 exact records |
| 36 | Oracle-independence assessment | Improved, not fully independent; written semantics and team are shared |
| 37 | Same-team bias | Authorship, semantics, and both oracles are same-team; no external-validation claim |
| 38 | Difficulty distribution | 70 easy / 1,003 moderate / 1,746 hard / 781 adversarial |
| 39 | Duplicate audit | 0 exact; 100 semantic groups are registered contract-ID metamorphic pairs |
| 40 | Leakage audit | PASS; best superficial validation stump 53.33%, HELD_OUT unused |
| 41 | Always-allow baseline | 50.00% accuracy; FAR 100.00%; FDR 0.00% |
| 42 | Always-deny baseline | 50.00% accuracy; FAR 0.00%; FDR 100.00% |
| 43 | Task-only baseline | 60.56% accuracy; FAR 78.89%; FDR 0.00% |
| 44 | Action-only baseline | 53.64% accuracy; FAR 92.72%; FDR 0.00% |
| 45 | Resource-only baseline | 65.50% accuracy; FAR 69.00%; FDR 0.00% |
| 46 | First-capability baseline | 51.83% accuracy; FAR 0.00%; FDR 96.33% |
| 47 | Suspicious-keyword baseline | 49.78% accuracy; FAR/FDR 50.22% / 50.22% |
| 48 | Simple-classifier leakage test | DEV stump 53.61%; VALIDATION 53.33%; HELD_OUT not loaded |
| 49 | False-allow metric definition | unauthorized predicted ALLOW / unauthorized |
| 50 | False-deny metric definition | authorized predicted DENY / authorized |
| 51 | Pair metric definition | pairs with both members correct / registered pairs |
| 52 | Task-binding metric definition | correct tagged task-binding decisions / tagged task-binding decisions |
| 53 | Cross-task metric definition | denied reuse attempts / registered reuse attempts |
| 54 | Compound metric definition | correct top-level and component decisions / process compound cases |
| 55 | Cross-tool metric definition | groups with both structurally corresponding members correct / groups |
| 56 | Explanation-completeness metric | mechanically complete applicable fields / component explanations |
| 57 | Formal authorization spec | `AUTH-COVERAGE-001-AUTHORIZATION-SPEC@1` |
| 58 | Authority-distance design | denied component count: 0 exact, 1 one mismatch, 2 compound double mismatch; analysis only |
| 59 | No-amplification property | PASS in split-capability corpus and exhaustive model |
| 60 | No-cross-task-reuse property | PASS in exhaustive model; 200 frozen benchmark attempts prepared |
| 61 | No-capability-order-effect property | PASS in exhaustive and metamorphic development tests |
| 62 | No-suspiciousness-authority-effect property | PASS in exhaustive checks; balanced corpus family prepared |
| 63 | AI-context-cannot-grant-authority property | PASS in exhaustive checks; 1,808 corpus cases tagged |
| 64 | Delegation precursor | Model-only parent/child/chain subset checks; not production evidence |
| 65 | Attenuation precursor | Task/action/resource checked; time/usage/destination conceptual only |
| 66 | External-pack interface | `EXTERNAL_PACK@1`; pack labels never authoritative |
| 67 | Held-out prediction exposure | NONE |
| 68 | Raw-first architecture | Standard-library capture isolated from separate checksum-gated scorer |
| 69 | One-shot run policy | Existing output hard-fails; rerun after exposure prohibited |
| 70 | Benchmark power review | Substantial for core task/resource/distractor/compound families; moderate cross-tool; control-only future mediators/delegation |
| 71 | Claim-pressure result | Perfect future result supports frozen-model conformance only |
| 72 | Explicit non-claims | External validity, physical execution, network/MCP/DB, identity, delegation implementation, performance, race freedom, model resistance |
| 73 | Tests | 34 focused PASS; applicable full suite 707 PASS / 2 established EXP-015 pre-run gates deselected |
| 74 | Coverage | 94% overall; 5,968 statements, 332 missed |
| 75 | Ruff | PASS |
| 76 | mypy | PASS, strict configuration over 69 source files |
| 77 | EXP-014 integrity | UNCHANGED |
| 78 | EXP-015 integrity | UNCHANGED |
| 79 | EXP-016 integrity | UNCHANGED |
| 80 | Checksums | Corpus and freeze checksum manifests; canonical audit SHA recorded |
| 81 | Files created | New protocol/spec/audit docs, experiment implementation/corpus/contracts, and four test modules |
| 82 | Files modified | No pre-existing repository file; all task artifacts are new |
| 83 | Parallel lanes used | A/H formal; B/C/D/F corpus/oracles; G/I/J audit/scoring; root protocol/reconciliation/freeze |
| 84 | Reconciliation | Corrected contract-ID non-authority, production `/**` encoding, distance/denominators, boundary subtypes, split isolation, confidence intervals, and raw-label isolation |
| 85 | Commit SHA | Recorded in final handoff |
| 86 | Final git status | Recorded after commit/push in final handoff |
| 87 | Exactly one next task | Independent final pre-run gate; only that gate may authorize one-shot held-out execution |

## Exactly one next task

Perform an independent final AUTH-COVERAGE-001 pre-run gate, including oracle independence,
leakage, heuristic-baseline, counterfactual-quality, difficulty, checksum, label-isolation,
and one-shot-run readiness audits; only then authorize the canonical held-out benchmark
execution.
