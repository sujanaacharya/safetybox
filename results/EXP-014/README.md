# EXP-014-RUN-001

Factual raw-run identity only.

- Run: `EXP-014-RUN-001`
- Protocol freeze: `7baf20293caa83d3fff6a200174c4f8840918607`
- Implementation freeze: `b49a5cd0ff28a38eb8314291f51c106d2df9bd7c`
- Corpus freeze: `5ac7311bb8f086cca97f474069d068067ac73142`
- Environment: `Linux-6.8.0-138-generic-x86_64-with-glibc2.35`; Python `3.11.16`; `x86_64`
- Canonical records: 96 in `runs.jsonl`; repeat records: 2 in `repeats.jsonl`.
- Attempts: one canonical start and one completion event in `attempts.jsonl`; no infrastructure failure.
- Artifacts: `environment.json`, `protocol.json`, `attempts.jsonl`, `runs.jsonl`, `repeats.jsonl`, `summary.json`, `independent_recompute.json`, `evaluate.py`, `recompute.py`, and `SHA256SUMS`.
- Verify: run `(cd results/EXP-014 && sha256sum --check SHA256SUMS)` from the repository root.
- Host temporary-root paths are omitted; every execution used a fresh isolated root and all observed operation paths were confined beneath it.
- Post-run infrastructure caveat: the frozen pre-corpus test `test_corpus_contains_no_predictions_results_or_adapter_run_artifacts` now fails because this canonical results directory exists; 291 other tests pass. The frozen test was not modified.
