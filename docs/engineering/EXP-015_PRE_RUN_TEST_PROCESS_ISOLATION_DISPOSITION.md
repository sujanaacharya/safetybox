# EXP-015 pre-run test-process isolation disposition

**Disposition ID:** `EXP-015-TEST-PROCESS-ISOLATION-DISPOSITION@1`
**Decision:** `TEST_PROCESS_ISOLATION_ARTIFACT_RESOLVED`

## Scope and frozen references

This disposition repairs pre-run test governance only.  It does not execute an
EXP-015 scenario, load a prediction for scoring, invoke `ProcessAdapter` on a
held-out input, or create `results/EXP-015/`.

| Reference | SHA |
|---|---|
| Protocol | `1b1d22eaded580e9b6f6311bf0e3a8145002e98d` |
| PROC-ADAPTER@1 implementation | `12c585a9830436d8a88d356cfecbdff132b55487` |
| Runtime schema/materializer v2 | `37368667c438ccbf6a84819ef355590450617d73` |
| EXP-015-CORPUS@2 | `35dfbb095727f459277db8c7df58864f3be5e907` |

The worktree began clean at `35dfbb095727f459277db8c7df58864f3be5e907`.
`results/EXP-015/` was absent before and after validation.  Held-out adapter
executions remain **0** and `EXP-015-RUN-001` remains unspent.

## Root cause and reproduction

`tests/test_exp015_corpus2.py::test_exp015_corpus2_integrity` invokes the
checksum-covered `experiments/EXP-015/corpus2/integrity_check.py`.  That frozen
script asserts that `safetybox.process.adapter` is absent from `sys.modules`.

- In a fresh pytest invocation, the exact node passed: **1 passed**.
- In one pytest process after
  `tests/dev/test_exp015_process_adapter.py::test_versions_are_explicit_and_stable`,
  it failed only at that assertion: **1 passed, 1 failed**.  The development
  module legitimately imports the public process package at collection, which
  imports `safetybox.process.adapter`.

The same frozen integrity/materialization code therefore passes in a clean
interpreter and fails only because unrelated earlier test activity remains in
the shared interpreter module cache.  This is a
`TEST_PROCESS_ISOLATION_ARTIFACT`, not a corpus-integrity failure,
label-isolation failure, adapter exposure, or schema failure.

## Actual guarantee

The frozen v2 materialization contract requires the Corpus@2 materializer and
offline integrity path themselves not to import the process package or adapter
(including private validation/canonicalization), production authorization,
labels, scoring, the pair registry, manifest/outcome machinery, or prediction
and result machinery.  It must only materialize fixtures and run offline
checks; it must never execute a child or `ProcessAdapter`.

That guarantee concerns imports caused by the Corpus@2 path.  It is different
from asserting that no unrelated test in a shared pytest interpreter has ever
imported the adapter.  Ambient `sys.modules` in that shared lifecycle is not a
reliable isolation oracle.

## Replacement proof and suite disposition

`scripts/check_exp015_corpus2_import_isolation.py` is non-frozen gate
infrastructure.  It launches a fresh child interpreter, runs the frozen
offline integrity/materialization script, and inspects `sys.modules` in that
same child before and after execution.  It rejects these frozen-contract
module prefixes:

- `safetybox.process` (including `safetybox.process.adapter`, validation, and
  canonicalization)
- `safetybox.authorization`
- `safetybox.experiments.exp015_corpus2_scoring` (the repository's Corpus@2
  labels and pair-registry owner)

There is no separate Corpus@2 pair-registry, prediction, or result module in
the repository; the final prefix is the exact scoring/pair implementation
named by the frozen contract.  The gate does not broaden the contract to
unrelated schema-safe modules.  Its development-only `--negative-proof` mode
imports the process adapter in a disposable child and verifies that the gate
rejects it.  The normal and negative gate tests both passed.

`tests/test_exp015_corpus2.py` was not modified.  It is not listed in
`corpus2/CHECKSUMS.sha256`, but it was introduced in the Corpus@2 freeze commit;
governance therefore treats it as frozen-adjacent and leaves it byte-identical.
The checksum-covered frozen integrity script is also unchanged.

The canonical pre-run sequence is now:

1. Run `.venv/bin/python scripts/check_exp015_corpus2_import_isolation.py`.
2. Run the full development suite with only
   `--deselect=tests/test_exp015_corpus2.py::test_exp015_corpus2_integrity`.

The exact deselection is required only because the frozen node is
lifecycle-sensitive, and is justified by the redundant stronger fresh-process
proof.  It is not a file-, directory-, or marker-wide exclusion and does not
remove any corpus integrity check.

## Validation record

| Check | Result |
|---|---|
| Fresh-process integrity/import-isolation gate | PASS |
| Disposable prohibited-import negative proof | PASS |
| Full remaining pytest (exact node deselected) | 618 passed, 1 deselected |
| DEV-PROC adapter suite | 82 passed |
| Capability / TaskContract / TaskContractPolicy / CompoundActionAuthorizer / ReferenceMonitor regression selection | 108 passed |
| Normal repository coverage | 95% (5,329 statements; 261 missed) |
| Ruff | PASS |
| mypy `src` | PASS (67 source files) |
| `git diff --check` | PASS |
| Corpus@1 and Corpus@2 checksum manifests | PASS |
| EXP-014 raw and analysis checksum manifests | PASS |

The 95% normal coverage is aligned with the historical 95--96% range.  The
prior 82% value is classified `RESTRICTED_PRE_FREEZE_COVERAGE_ARTIFACT`.

The DEV-PROC source contains no Corpus@2 scenario, label, or result reference;
its 82 permitted development tests use separate development fixtures.  It did
not create `results/EXP-015/` or execute a held-out helper instance.

Diff checks against all four frozen references found no changes to the protocol,
process implementation, v2 schema/materializer, or Corpus@2.  Both Corpus@2
and EXP-014 integrity manifests passed.
