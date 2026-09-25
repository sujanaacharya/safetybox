# AUTH-COVERAGE exposure ledger

`AUTH-COVERAGE-EXPOSURE-LEDGER@1` is a generic research-governance ledger usable by later
authorization, mediation, OWASP, and real-agent evaluations. Its minimum binding is
experiment, corpus, split, run, scenario, production component, implementation SHA, token,
event type, timestamp, and details.

Events are `RESERVED`, `STARTED`, `COMPLETED`, `FAILED_AFTER_CALL`,
`FAILED_BEFORE_CALL`, `ABORTED_BEFORE_CALL`, and `RECONCILED`. A 256-bit random token is
single-use. Same-run scenario duplication is rejected, and `reserve_canonical_scope`
atomically binds a held-out corpus scope to one run ID.

Each canonical event uses compact UTF-8 JSON with sorted object keys and no non-finite
numbers. For event N:

```text
digest_N = SHA256(ASCII(digest_N-1) || canonical_event_N)
```

The ledger uses `O_APPEND`, an advisory exclusive lock, flush, file fsync, and directory
fsync on creation. A durable genesis anchor is established before the first event can be
appended; a separately durable anchor then stores head and count. Historical mutation,
valid suffix deletion, sequence gaps, and semantic duplicates fail integrity. If the event
fsync wins a crash race over the anchor replacement, recovery moves the anchor forward
only when the old anchor exactly identifies a verified hash-chain prefix; it never accepts
truncation or replacement.

Mechanical queries expose prediction count, scenario exposure, run exposure, duplicate
count, incomplete count, integrity, and exact-scope zero-exposure gating. `STARTED` counts
exposure. `RESERVED` alone does not.

Complete and partial raw seals copy an integrity-verified ledger prefix into the run result
directory. Later unrelated events may extend the shared ledger without invalidating the
sealed run. Seal recovery accepts an existing snapshot only when it is a valid byte prefix
of current history. A canonical held-out manifest must bind the one protocol-governed
persistent ledger path. The substrate cannot discover an operator-created parallel ledger;
the later protocol/corpus freeze audit must reject manifests that do not use that singleton
path. This is a bounded governance assumption, not a production-security claim.

This is detectability and cooperative one-shot enforcement, not defense against a fully
privileged repository attacker who can replace every anchor and frozen artifact.
