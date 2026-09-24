# EXP-014 Post-Run Regression-Gate Disposition

**Disposition ID:** `EXP-014-POST-RUN-GATE-DISPOSITION@1`  
**Date:** 2026-09-24  
**Classification:** `PRE_RUN_GATE`  
**Canonical run:** `EXP-014-RUN-001`

## Assertion identity and original intent

The assertion was line 445 of
[`tests/test_exp014_corpus.py`](../../tests/test_exp014_corpus.py) at the corpus freeze,
inside
`test_corpus_contains_no_predictions_results_or_adapter_run_artifacts`:

```python
assert not (ROOT / "results" / "EXP-014").exists()
```

It was introduced on 2026-09-24 by corpus-freeze commit
`5ac7311bb8f086cca97f474069d068067ac73142`
(`data(exp-014): freeze held-out real-filesystem corpus`). The test module describes its
scope as validating declarative inputs and scoring metadata before the one-shot evaluation.
The assertion established that no EXP-014 result artifact had been generated while the
held-out corpus was being frozen and before the canonical run. It was a pre-run research
lifecycle guard, not a permanent system safety invariant.

The other assertions in that test protect the enduring rule that the corpus itself must
not contain predictions, results, metrics, traces, or prediction-derived fields. Those
checks remain unchanged.

## Frozen provenance and historical absence

| Stage | Freeze commit | Commit time | Git-tree evidence |
|---|---|---|---|
| Protocol/design | `7baf20293caa83d3fff6a200174c4f8840918607` | 2026-09-24T15:47:05+05:45 | Preregistered before implementation; no result is interpreted here. |
| Implementation | `b49a5cd0ff28a38eb8314291f51c106d2df9bd7c` | 2026-09-24T16:48:22+05:45 | `git ls-tree -r --name-only <sha> -- results/EXP-014` returned no paths; `git cat-file -e <sha>:results/EXP-014` failed because the path did not exist. |
| Corpus | `5ac7311bb8f086cca97f474069d068067ac73142` | 2026-09-24T17:17:49+05:45 | The same two Git object/tree checks returned no paths and confirmed that `results/EXP-014` did not exist. This commit introduced and passed the guard. |

The implementation-freeze audit independently records that `results/EXP-014` was absent;
see
[`EXP-014_PRE_CORPUS_FREEZE_AUDIT.md`](../engineering/EXP-014_PRE_CORPUS_FREEZE_AUDIT.md).
The Git-tree checks above are the stronger immutable proof for both requested freezes.

## Canonical lifecycle transition

The immutable attempt record in
[`results/EXP-014/attempts.jsonl`](../../results/EXP-014/attempts.jsonl) records:

- `CANONICAL_START` at `2026-09-24T17:36:58.281639+05:45`;
- `initial_cleanliness_gate_observed_before_results_creation: true` and an empty initial
  `git status --short`;
- `CANONICAL_COMPLETE` at `2026-09-24T17:37:03.879961+05:45`, with 96 canonical
  predictions persisted and run validity recorded as `VALID` at completion.

Creation of `results/EXP-014/` is therefore the expected transition from `PRE_RUN` to
`POST_RUN_RAW_UNFROZEN`. Its existence cannot remain an unconditional regression failure
in that later state. Filesystem existence alone is not treated as the research state:
the frozen commit identities, the start/completion records, the pre-run cleanliness
evidence, and the raw checksums jointly establish the transition.

## Resolution and scope

The current-working-tree absence assertion is retired from the universal regression
suite. The test is narrowly renamed to
`test_corpus_contains_no_predictions_or_result_artifacts` and continues to reject result
artifacts and prediction-derived fields inside the frozen corpus. The historical absence
fact remains preserved by the immutable freeze trees and this disposition. Normal runtime
tests do not acquire a dependency on Git history.

This lifecycle-scope correction changes no detector behavior, filesystem adapter,
authorization logic, M1/M2/M3 behavior, canonicalization, validation, protocol, corpus
scenario, corpus label, prediction, or raw scientific record. The canonical evaluation is
not being rerun.

## Recorded and post-run dispositions

The raw report remains historically faithful: it records 10 success criteria as `PASS`
and `no_frozen_regression` as `FAIL`, producing
`VALID_WITH_DOCUMENTED_INFRASTRUCTURE_CAVEAT`. That recorded value is not edited. Its sole
cause was the post-run result directory satisfying the obsolete pre-run condition; it was
not a prediction-time infrastructure failure and is not one of the 11 frozen scientific
failure criteria.

If post-run validation passes after this scope correction and all raw hashes remain
unchanged, the recommended later-analysis wording is: **the canonical run is `VALID`; the
raw report's `no_frozen_regression = FAIL` is a documented lifecycle-test artifact, not a
research-result failure.** Formal claim interpretation remains deferred to adversarial
post-run analysis. All 11 frozen scientific failure criteria remain recorded as
`NOT_TRIGGERED`.
