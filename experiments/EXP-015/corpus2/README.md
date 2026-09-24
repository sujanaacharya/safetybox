# EXP-015-CORPUS@2

Frozen held-out, authorization-heavy PMED-L1 corpus. Runtime scenarios are
schema-only data under `EXP-015-RUNTIME-SCHEMA@2`; labels and pairs are separate
scoring artifacts. `build_corpus.py` is deterministic and imports no adapter.

Run the offline gate with `PYTHONPATH=src python3.11 integrity_check.py`.
It materializes each scenario twice but never executes a child or ProcessAdapter.
