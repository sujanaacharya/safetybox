# AUTH-COVERAGE-001 corpus implementation

This directory contains the deterministic, authorization-only corpus implementation for
`AUTH-COVERAGE-001-CORPUS@1`. It does not execute filesystem or process effects and it does not
run the held-out benchmark.

- `schema.py` validates data shape only and contains no decision logic.
- `oracle_a.py` is a direct specification-style evaluator.
- `oracle_b.py` is an independently structured evaluator. It shares only structural validation
  with Oracle A and imports no production authorization code.
- `build_corpus.py` deterministically emits the runtime-visible scenarios separately from labels,
  counterfactual pairs, structural difficulty records, and cross-tool equivalence groups.
- `corpus/CHECKSUMS.sha256` covers every generated artifact except itself.

Capability `scope_type` is an auditable schema annotation, not an additional semantic feature.
`SUBTREE` is valid only when the stored resource uses production `/root/**` syntax; `EXACT` is
valid only without that suffix. Both oracles consume the serialized production form.

The frozen difficulty classifier uses the preregistered structural score: `EASY_CONTROL <= 11`,
`MODERATE <= 15`, `HARD <= 21`, and `ADVERSARIAL > 21`. The small easy stratum is retained as a
calibration control; moderate, hard, and adversarial cases dominate.

Regeneration is explicit and deterministic:

```bash
python3 experiments/AUTH-COVERAGE-001/build_corpus.py
```

Regeneration is a construction/freeze operation, not part of a benchmark run. A future runner must
load `scenarios.json` only, persist raw decisions, and join labels only in a separate scoring phase.
