# AUTH-COVERAGE-002 execution-substrate freeze audit

**Audit identity:** `AUTH-COVERAGE-002-EXECUTION-SUBSTRATE-FREEZE-AUDIT@1`  
**Substrate identity:** `AUTH-COVERAGE-002-EXECUTION-SUBSTRATE@1`  
**Starting HEAD:** `45bbe571fa23b6c2f373256cc7faf7f5a41b9d6b`  
**Freeze commit:** `SELF` (the commit containing this audit and `SUBSTRATE_SHA256SUMS`)  
**Decision:** `FREEZE`  
**Held-out scenarios authored:** **0**  
**Held-out prediction exposures:** **0**

## Scope

This freeze covers the production runner, exposure ledger, raw schema and reconstruction,
run state machine, label/file isolation, reconciliation, raw sealing, scoring boundary,
error taxonomy, metric contract, and synthetic DEV proofs. It creates no
AUTH-COVERAGE-002 corpus, held-out scenario, label, or result package.

## Freeze conditions

| Condition | Disposition |
|---|---|
| label-blind production execution | PASS — exact four-file runtime inventory, strict recursive schema, import and ordinary-file gates |
| durable reservation before call | PASS — fsynced `RESERVED`, then fsynced `STARTED`, then call boundary |
| call implies exposure | PASS — `STARTED` is durable before the single-use invocation permit can be consumed |
| crash after call | PASS — conservatively exposed; missing/invalid raw terminalizes partial |
| duplicate token/scenario/run | PASS — semantic ledger transitions and atomic held-out scope reservation reject them |
| restart after exposure | PASS — active exposed reconciliation terminalizes partial; held-out runner refuses restart |
| raw reconstruction and capability order | PASS — 100% synthetic reconstruction; received arrays retain order |
| implementation/corpus binding | PASS — SHA, exact source set/checksums, policy/spec/schema/runner versions, corpus/runtime checksums, and per-input digests |
| raw/ledger integrity | PASS — canonical digests, hash chain, durable anchor, immutable prefix snapshot, raw-to-completion cross-links |
| sealing/scoring boundary | PASS — only independently verified `SEALED_RAW` can score in the analysis process |
| error and metric contracts | PASS — executable frozen taxonomy/strata, `NOT_EXERCISED`, Wilson and exact zero-error bounds |
| ordinary pytest held-out guard | PASS — rejected before reservation; no held-out fixture was executed |
| predecessor integrity | PASS — EXP-014, EXP-015, EXP-016, and AUTH-COVERAGE-001 checksum manifests verify unchanged |

## Adversarial disposition

Resolved attacks include execution before reservation; ordinary-pytest contamination;
case/alias and arbitrary-file label leakage; ignored nested runtime fields; duplicate token,
scenario, or held-out run; generic held-out reservation bypass; first-event anchor crash;
raw-write failure followed by rerun; active-run continuation after a completed prediction;
terminal-reconciliation reopening; implementation change between scenarios; coordinated
raw/raw-manifest tampering; metadata substitution; shared-ledger extension after seal; and
seal recovery after a snapshot was written.

The remaining findings are **BOUNDED**. The generic ledger and Python gates are cooperative
research governance, not a privileged-attacker or hostile-native-code security boundary.
A future protocol must freeze one singleton persistent ledger path, prevent DEV artifacts
from being relabeled as HELD_OUT, audit semantic leakage inside otherwise valid request
arguments, and govern abandoned pre-call held-out reservations. Fault injection proves the
defined control-flow/fsync ordering, not physical power-loss behavior. Replacing the ledger,
anchor, code, and freeze manifest together is outside the claim. No adversarial finding is
`BLOCKING` at freeze.

## Validation record

- focused substrate tests: **111 passed** before freeze-manifest test addition;
- full pytest: **820 passed, 2 failed**; both failures are frozen EXP-015 lifecycle checks
  caused by the historically present `results/EXP-015` and process-import state;
- applicable pytest with those two frozen dispositions deselected: **820 passed**;
- substrate coverage in applicable suite: **83%** (`2596` statements, `447` missed);
- repository Ruff: PASS;
- mypy over `src` and all three AUTH-COVERAGE-002 entry scripts: PASS (`82` files);
- `git diff --check`: PASS.

`experiments/AUTH-COVERAGE-002/SUBSTRATE_SHA256SUMS` freezes the exact instrument, tests,
contracts, registry, and documentation. The freeze test verifies every listed byte and the
zero-corpus/zero-exposure declarations.

## Exactly one next task

Design, author, independently audit, and freeze `AUTH-COVERAGE-002-PROTOCOL@1` and its
newly blinded DEV/VALIDATION/HELD_OUT corpus using the frozen raw-first runner and exposure
ledger, with cryptographically opaque scenario identities, zero production access to
HELD_OUT, independent oracle agreement, strong counterfactual authority tests, leakage
attacks, structural-diversity analysis, and a final zero-exposure gate before any canonical
prediction.
