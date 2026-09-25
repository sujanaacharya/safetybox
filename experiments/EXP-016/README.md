# EXP-016 pre-corpus infrastructure

EXP-016 is a new experiment for native direct-child process mediation and execution
semantics. This directory contains its frozen protocol, native C helper and provenance,
machine-readable reachability/scoring contracts, and a development-proof inventory.

There is deliberately no held-out corpus, held-out label file, prediction file, raw
result, or score here. The development proofs are contaminated infrastructure checks and
cannot be reused exactly as future held-out cases.

Build the helper with:

```bash
PYTHONPATH=src .venv/bin/python scripts/build_exp016_helper.py
```

The next phase may author a held-out corpus only under the contracts in `contracts/` and
the governance in `protocol.yaml`.
