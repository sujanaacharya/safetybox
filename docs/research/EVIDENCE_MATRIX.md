# Evidence Matrix

Evidence levels follow the
[OWASP coverage plan](../strategy/OWASP_GENAI_AGENTIC_COVERAGE_PLAN.md): Level 0 is
architecture relevance, Level 1 implemented versioned semantics, Level 2 unit/adversarial
component tests, Level 3 preregistered held-out synthetic evaluation, Level 4 real-system
evaluation, and Level 5 external replication. A level applies only to the named
sub-property and evidence dimension.

| Claim/Question | Component | Experiment | Evidence level | Evidence | Scope | Limitation |
|---|---|---|---:|---|---|---|
| Does authorization precede a protected logical tool call? | M1 `ReferenceMonitor` | Unit tests/M4 regression | Level 2 | Allow is the sole forwarding branch; deny and authorizer failure do not invoke the in-process protected tool. | In-process API. | No real tool, interception, TOCTOU, or process boundary. |
| Can authority be scoped by task, action, and canonical logical path? | M2 contract/capability policy | Unit tests/M4 regression | Level 2 | Task mismatch, action absence, exact resource, and component-aware subtree behavior are tested. | Immutable logical model. | No filesystem resolution, symlink, hard-link, or OS identity. |
| Are logical authorization lifecycles attributable and ordered? | M3 event/audit model | Unit tests/M4 regression | Level 2 | Session/task/request/correlation, rule ID, parent link, and sequence behavior are tested; pre/post audit failure semantics are explicit. | Single-process in-memory audit. | Not durable, tamper-evident, concurrent, distributed, or complete for adapter pre-canonicalization failures. |
| Can registered synthetic threats be replayed deterministically? | M4 simulator | Unit tests | Level 2 | Harmless logical world and declared expected effects are reproducible. | Synthetic scenarios. | No real filesystem/network/database effects. |
| Does sequence monitoring add observations beyond action authorization? | M5 | EXP-009 | Level 3 | 40/40 positives detected; 20 TRJ-001 positives had no policy block. | `EXP-009-CORPUS@1`, frozen rules. | 33/40 negatives flagged; observational only. |
| Can trusted context improve synthetic specificity? | M5.1 | EXP-012 | Level 3 | 40/40 positives and 40/40 negatives classified correctly on the frozen primary corpus. | Clean, structured, synthetic declarations. | Single-observation mismatch separated labels; declaration correctness untested. |
| Does ordered history add discriminative information beyond B2? | B4 vs B2 | EXP-013 | Level 3 | Held-out synthetic evidence only: B4 discriminated 38/40 history-required pairs; 0/40 matched-negative false positives; B2 discriminated 0/40. | `EXP-013-CORPUS@1`, frozen structured semantics. | Handcrafted synthetic data, two misses, no real effects or independent label review. |
| Can SafetyBox mediate real filesystem effects correctly? | `FS-ADAPTER@1` | EXP-014 | Level 4 | Designed, implemented, unit tested, and held-out real-tool evaluated: 94/94 adapter-routed terminal outcomes in real temporary filesystems. | `EXP-014-CORPUS@1`; isolated sequential Linux FMED-L1 calls. | Real-agent evaluated: no. Production-ready: no. Direct routes, races, concurrency, and non-Linux filesystems remain outside scope. |
| Is filesystem mediation complete or bypass-resistant? | Deployment/interception boundary | EXP-014 controls | Level 1 | Two direct-route controls empirically demonstrate expected FMED-L1 bypass. | Boundary demonstration only. | No FMED-L2/3/4 interception evidence; complete mediation remains not established. |
| Are denied real reads nondisclosing and denied mutations effect-free? | `FS-ADAPTER@1` + independent observer | EXP-014 | Level 4 | 19/19 denied mutations had no wrapped primitive invocation or independently observed state change; 9/9 denied retrievals had no protected call/result in measured channels. | Frozen adapter-routed cases and evaluated caller/error/audit channels. | Nondisclosure omits process/debug channels; no concurrency, TOCTOU, or external observer process. |
| Does real-tool audit reconstruct every attempt and effect? | `FS-AUDIT-ENVELOPE@1` / M3 bridge | EXP-014 | Level 4 | 94/94 adapter attempts passed reconstruction-field and truthfulness checks; primitive/state observations provide partial semantic independence. | In-process isolated real filesystem run. | Reconstruction is schema-coupled; audit is not durable, tamper-evident, remote, concurrent, or forensic-grade. |
| Can SafetyBox mediate real subprocess execution? | Proposed subprocess adapter | EXP-015 | Level 0 | Preregistered PMED-L1 requirements, architecture, threat model, ADR, and fixed protocol only. | Proposed direct executable, ordered argv, logical cwd, minimal environment, and direct-child lifecycle. | No implementation, helper, unit test, held-out corpus, subprocess run, shell mediation, descendant control, real agent, or production evidence. |
| Is SafetyBox integrated with a real agent framework? | Agent harness | None | Level 0 | Roadmap relevance only. | None. | No agent/framework/model evidence. |
| Does SafetyBox establish causal data lineage? | Future lineage layer | None | Level 0 | Architecture need identified. | None. | Action order and role association do not prove byte/field flow. |
| Is SafetyBox production-ready? | Whole system | None | Level 0 | No supporting evaluation. | None. | No deployment, durability, bypass-resistant mediation, operational, or external-replication evidence. |
| Does SafetyBox validate an entire OWASP category? | Whole system | None | Level 0 | Unsupported; mappings identify relevance and possible named sub-properties only. | None. | No whole-category experimental coverage or claim. |

Level 4 now applies only to the named EXP-014 real-filesystem sub-properties above. No
Level 5 evidence exists, and no entire OWASP category or whole-system claim is Level 4.
