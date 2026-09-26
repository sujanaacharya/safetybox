# AUTH-COVERAGE-002 Substrate@2 remediation record

The frozen defect is reproduced at `protocol2/candidate_audit.py:386`:
`dict(splits)` emits only observed `Counter` keys. For 800 DEV and 800 VALIDATION
records it emits `{"DEV": 800, "VALIDATION": 800}`. The authoritative validator at
`protocol2/governance.py:643-656` expects exactly
`{"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}` during PRE_HELDOUT.

This is an omitted zero-valued key, not a naming, normalization, state, or count-schema
mismatch. Protocol@2's phase definition expressly defines zero realized HELD_OUT, its
machine validator checks exact keys, and its DEV-proof tests represent unrealized splits
with explicit zeros. A missing key therefore is not equivalent to a present key valued
zero. Extra keys, negative values, booleans, fractional values, strings, and nulls remain
invalid.

`AUTH-COVERAGE-002-SUBSTRATE@2` delegates all metric derivation and gate evaluation to
the frozen implementation. Its sole construction change emits the three required split
keys by indexed `Counter` access. For inputs where all split keys were already present,
the old and successor mappings and decisions are identical. Threshold and benchmark
semantic diffs are both zero.

The successor preserves unexpected split names in the constructed mapping so the frozen
exact-key validator rejects them by the same route. The permanent test matrix compares one
nondefect constructor fixture and eight preserved-evidence decision/error lanes with 100%
parity. The only authorizing entrypoint is `audit_candidate` through `derive_metrics`.

The analysis-only replay of preserved Attempt-1 evidence changes only `realized_split`
and returns a hypothetical machine-gate PASS. The permitted interpretation is only:
"The successor audit would not reproduce the substrate defect on the preserved evidence."
Attempt-1 remains permanently blocked and this replay creates no authorization.
The replay is deliberately a separate digest- and attempt-restricted analysis tool; the
sealed evidence does not contain the transient raw-record map needed to rerun every metric
derivation, so it re-evaluates the preserved machine-audit metrics rather than fabricating
missing raw inputs.
