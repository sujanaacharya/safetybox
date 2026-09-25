# EXP-015-RUN-001

Mechanical raw-run package for the canonical one-shot PMED-L1 evaluation.

- Starting HEAD: `5b9d2e4c9b21729aa73af4b95972a15c17e3a8bc`
- Canonical raw records: 120 in `runs.jsonl`
- Preregistered repeats: 6 in `repeats.jsonl`
- Raw checksum: `6e2d27f789595e6df83742c07866ca60c2b21c64d9738c21943d160ca036f2d8`
- Label isolation: proved through the raw completion barrier in `execution_state.json`
- Label join and independent recomputation: `label_join_manifest.json` and
  `independent_recompute.json`
- Validity: valid raw execution with retained scoring-harness limitations; see
  `summary.json` and the engineering run record.

The frozen corpus declared all 120 runtime routes as `ADAPTER`, including its three
manifest-designated PMED controls. Its regular helper fixtures materialized as shebang
scripts while the frozen adapter accepts only native ELF. These facts were not repaired.

Verify the frozen package from the repository root with:

```text
sha256sum --check results/EXP-015/SHA256SUMS
```
