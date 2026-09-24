# EXP-015 Corpus@2 Schema Freeze Audit

`EXP-015-CORPUS-2-SCHEMA-FREEZE-AUDIT@1` records a schema/infrastructure-only freeze.
No held-out Corpus@2 scenarios, predictions, adapter invocations, or EXP-015 results are
created by this change. Corpus@1 remains
`RETIRED_PRE_EXPOSURE_INVALID_RUNTIME_MATERIALIZATION`.

Proof identifiers `SCHEMA-PROOF-*` exercise normal, missing, symlink, non-executable,
directory, and unsupported-wrapper executable objects; every cwd kind; every helper
recipe; every fault stage/mode; and both routes. Proofs materialize only. They verify
normalization, lstat-visible object state, and ID-independent deterministic construction.

Gates frozen for Corpus@2 authorship: each validation and execution/failure record must
be constructible from runtime data alone; materialize every authored record twice before
adapter execution; audit imports and hidden tables; use one scoring pair registry; derive
manifest counts; run independent authority/canonicalization and contamination audits;
then run static separability, pair-quality, and coverage audits before corpus freeze.

Authoring order is schema/materializer freeze, bulk authoring, materialization audit,
independent authority oracle, static separability, pair-quality, contamination, corpus
freeze, environment gate, and one-shot run. Corpus@2 may reuse research dimensions but
must use substantially new instances/pairs, classify similarity, and have zero exact
Corpus@1 or DEV-PROC reuse.
