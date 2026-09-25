# EXP-016 — Native Direct-Child Process Mediation and Execution Semantics

**Protocol:** `EXP-016-PROTOCOL@1`

**Status:** preregistered pre-corpus infrastructure; development-only proof evidence

**Starting state:** `71cb87b771978f3fc55edac7bf2a0f45809c9d55`

**Held-out scenarios:** 0

## Purpose

EXP-016 asks: given an already-authorized process request with independently verified
native-executable fixtures, does SafetyBox correctly mediate real direct-child process
execution semantics?

EXP-015 remains frozen. Its raw result at
`65d047de0fe3b484eaed64bd2adc8562a5835eea` and adversarial analysis at
`71cb87b771978f3fc55edac7bf2a0f45809c9d55` are inputs to this design, not artifacts to
repair or rerun. EXP-016 adopts the resulting principle: **materializability is not
enough**. Every intended-valid fixture must independently prove production-validation
reachability before the held-out corpus can freeze.

The machine-readable protocol is
[`experiments/EXP-016/protocol.yaml`](../../experiments/EXP-016/protocol.yaml). The
scoring, family, reachability, requirement, threat, and claim registries under
`experiments/EXP-016/contracts/` are normative.

## Research questions

- **RQ-016-01:** Can an authorized, independently verified native executable pass
  validation and produce a real direct child?
- **RQ-016-02:** Does the adapter preserve argv literally without shell
  reinterpretation?
- **RQ-016-03:** Does the child receive only the frozen minimal environment?
- **RQ-016-04:** Are stdout/stderr capture, counts, hashes, and truncation truthful?
- **RQ-016-05:** Are nonzero exit, timeout, signal, and supported injected-failure
  semantics classified truthfully?
- **RQ-016-06:** Does audit ordering occur correctly around real child spawn?
- **RQ-016-07:** Are adapter-mediated direct-child semantics deterministic under
  preregistered repeats?
- **RQ-016-08:** Can explicit `DIRECT_CONTROL` controls demonstrate the PMED-L1 routing
  boundary?

## Hypotheses

- **H-016-01:** Every registered authorized intended-success case with an independently
  valid native ELF reaches real child creation.
- **H-016-02:** Requested argv equals length-framed child-observed argv byte-exactly.
- **H-016-03:** Shell-looking strings remain literal and create no shell-selected effect.
- **H-016-04:** The child environment is exactly `LANG=C.UTF-8` and
  `LC_ALL=C.UTF-8`; registered parent `HOME`, `PATH`, and `EXP016_PARENT_SECRET`
  sentinels are absent.
- **H-016-05:** Retained bytes, complete byte counts, complete-stream SHA-256 values, and
  truncation flags equal independent expectations.
- **H-016-06:** Registered exit, signal, TERM timeout, KILL escalation, and supported
  injected failures receive their preregistered terminal classes.
- **H-016-07:** Every registered policy-denied request invokes no protected spawn
  primitive.
- **H-016-08:** A safe direct native control creates a child without `ProcessAdapter`,
  demonstrating the PMED-L1 routing limitation.

Each hypothesis has an explicit registered-case denominator. A zero denominator yields
`NOT_EXERCISED`, never `PASS`.

## Scope and exclusions

The primary scope is sequential, normal-user, Linux direct-child execution through
`PROC-ADAPTER@1`: native ELF validation, physical cwd validation, exact argv delivery,
`shell=False`, minimal environment, bounded output, exit/signal/timeout behavior,
supported failure injection, ordered audit evidence, deterministic repeats, and safe
direct-route controls.

Authorization is a controlled precondition. Most future cases must use a known compound
`ALLOW` under an independently verified `TaskContract`. A smaller bounded `DENY` set
reconfirms no-spawn behavior. The future corpus should be approximately 80% authorized
execution/validation/failure cases and 20% deny/direct controls; exact counts are
deferred to corpus freeze.

EXP-016 excludes arbitrary process confinement, descendants, network confinement, child
filesystem mediation beyond selected markers, TOCTOU safety, authenticated identity or
session binding, shell safety beyond literal `shell=False` delivery, concurrency,
privilege changes, dangerous resource exhaustion, real-agent deployment, and production
readiness.

## Metrics and required execution evidence

The first-class benign completion metric is:

`successful intended benign operations / AUTHORIZED_EXPECTED_TO_EXECUTE`

`AUTHORIZED_EXPECTED_VALIDATION_REJECT` and
`AUTHORIZED_EXPECTED_FAILURE_SEMANTIC` are distinct denominators and cannot depress or
inflate benign completion.

Every attempt contributes to this frozen stage funnel:

`AUTHORIZED → EXEC_VALIDATION_REACHED → EXEC_VALIDATION_PASSED → CWD_VALIDATION_REACHED
→ CWD_VALIDATION_PASSED → PREAUDIT_COMMITTED → SPAWN_ATTEMPTED → CHILD_CREATED →
CHILD_COMPLETED → TERMINAL_AUDIT_COMPLETED`

Overall execution-semantic success cannot be met by authorization results. It requires
a positive, substantial held-out child denominator frozen before execution and correct
completion of every registered intended-success case. No automatic RTM-2 promotion is
preregistered.

## Raw-first isolation and one-shot governance

Runtime scenarios must contain materialization and perturbation inputs only. Expected
authority, validation, terminal class, family, requirement mapping, threat mapping, and
scoring values remain in separate metadata unavailable to execution. Raw records freeze
before labels are joined.

This freeze does not authorize corpus authorship or an experiment run. The subsequent
order is corpus authorship under these contracts, independent fixture gating,
contamination/determinism/count/mapping audits, corpus freeze, one raw execution, raw
freeze, label join, scoring, and adversarial analysis. Criteria may not be relaxed after
the run.

## Evidence and claim discipline

All current execution results are contaminated development proofs of infrastructure
reachability. They are not held-out EXP-016 findings. The eight claim candidates remain
`PROPOSED`; this freeze promotes none. Evidence may support a later RTM decision only if
real adapter-routed native children execute successfully in the held-out run.
