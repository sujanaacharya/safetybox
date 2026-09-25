# SafetyBox Research Paper Program

**Status:** candidate publication program; no acceptance or publishability claim

## Paper 1 — Task-Scoped Deterministic Authorization for Autonomous Agents

**Research question.** Can exact subject/task/action/resource authority maintain benign
authorization while rejecting adversarial and counterfactual scope violations?

**Potential novelty.** A capability-oriented agent authorization model paired with
leakage-resistant counterfactual evaluation, compound decisions, and explicit
AI/context non-authority.

**Required evidence.** Formal semantics and bounded verification; `AUTH-COVERAGE-002` with
sealed held-out data, external-or-independent oracle/audit, pair/compound/stratified error
analysis; benign preservation; implementation and reproducibility artifacts.

**Missing work.** Canonical runner and exposure ledger, new corpus, one-shot run,
independent adversarial validity analysis, identity binding limits.

**Expected artifact.** Authority specification, evaluator, blinded corpus, raw prediction
record, scorer, exposure history, and claim ledger.

## Paper 2 — From Authorization to Effects: Runtime Mediation for Agentic Systems

**Research question.** Under enumerated filesystem and native-process boundaries, can
valid authority be causally bound to real protected effects while denials never reach the
protected primitive?

**Potential novelty.** Joint but non-collapsed measurement of authorization, mediator
reachability, actual effects, bypass, lifecycle uncertainty, and reconstructable
provenance.

**Required evidence.** EXP-014 bounded evidence, successful EXP-016 native-child results,
`UNAUTHORIZED-EFFECT-001`, independent effect oracles, route inventories, bypass/failure
analysis, benign completion, and confidence bounds.

**Missing work.** EXP-016 corpus/run; durable provenance support; combined protocol and
runner; external or real-agent replication.

**Expected artifact.** Versioned mediators, effect taxonomy, coverage registry,
filesystem/process corpus, raw lifecycle/effect evidence, and replay tools.

## Paper 3 — Benchmarking Unauthorized Agent Actions with Counterfactual Authority Tests

**Research question.** Which benchmark-design and governance controls yield valid
estimates of authority-boundary discrimination without label or prediction leakage?

**Potential novelty.** Opaque label-independent identifiers, execution exposure ledgers,
crash-safe one-shot state, raw-first scoring, mechanically isolated splits, and graded
counterfactual-pair quality grounded in an actual failed benchmark disposition.

**Required evidence.** Transparent AUTH-COVERAGE-001 failure case; new benchmark design;
red-team attempts against identifiers/serialization/imports; successful
AUTH-COVERAGE-002 execution; independent reproducibility.

**Missing work.** Implemented generic ledger/runner, adversarial process audit, external
scenario or oracle contribution, empirical comparison of shortcut attacks.

**Expected artifact.** Reusable benchmark-exposure and one-shot runner framework, corpus
data card, leakage tests, scorer, and retrospective.

## Paper 4 — Capability Attenuation and Delegation for Multi-Agent Systems

**Research question.** Can multi-agent authority be delegated, attenuated, expired, and
revoked without cross-task reuse or amplification while preserving useful workflows?

**Potential novelty.** A formal multi-dimensional subset relation, signed delegation
lineage, explicit in-flight revocation semantics, authority-bearing messages, and
effect-level provenance.

**Required evidence.** Frozen Authority V2 semantics; machine-checked finite or symbolic
properties; adversarial multi-agent scenarios; concurrency and cache tests; real-agent
utility; ASI03/07/08/10 subclaim mapping.

**Missing work.** Nearly all runtime implementation and empirical evaluation. Current
task IDs are not authenticated identity, and no delegation mechanism exists.

**Expected artifact.** Formal model, verifier, delegated-authority schema, inter-agent
scenario suite, lifecycle/concurrency harness, and traces.

## Common evidence bar

Every submission direction must keep negative results and limitations visible; publish
frozen protocols, versioned implementation, corpus construction/data card, raw records,
scoring code, exposure and deviation ledgers, statistical analysis, and exact claim
scope. Same-team evidence must be identified as such. Level 3 synthetic evidence cannot
stand in for a real-effect claim, and real-tool evidence cannot stand in for real-agent or
external validation.
