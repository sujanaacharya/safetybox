# AUTH-COVERAGE-002 Generator@4 Freeze Audit

Decision: `VALIDATED_PENDING_HOST_COMMIT`.

Generator identity: `AUTH-COVERAGE-002-GENERATOR@4`. Protocol identity:
`AUTH-COVERAGE-002-PROTOCOL@4`, frozen at Git SHA
`31f2ee9e504de74f6b93e5a860fd6d92ae5f7fa2`. Substrate identity:
`AUTH-COVERAGE-002-SUBSTRATE@2`, manifest SHA-256
`d9d827c9544cc4f27bb0d925adf1091a9dd4f6081d8f984b07c8df154739cc60`.
Generator identity checksum (the immutable Generator@4 contract digest):
`db9dd09fa8014f4b1c79fae7b8cd76330fedb7a6162808ab5e5be95bf625be24`.

## Versioning rationale and source changes

Generator@3 cannot be reused because it hard-binds Protocol@3, Corpus@3-Attempt-1,
its authority digests, and its state root. Generator@4 loads the proven Generator@3
governance implementation in an isolated module and rebinds only Protocol@4,
Substrate@2, Corpus@4-Attempt-1, authority, state/ledger, manifest, and contamination
identities. Frozen Generator@2 remains the sole semantic generator.

Every Generator@3-to-Generator@4 difference is classified in
`generator3_to_generator4_change_manifest.json`. The categories are exclusively:
`PROTOCOL4_BINDING`, `SUBSTRATE2_BINDING`, `ATTEMPT4_BINDING`,
`AUTHORITY_VERSIONING`, `STATE_ROOT_VERSIONING`, `CONTAMINATION_BINDING`,
`MANIFEST_VERSIONING`, `TEST_GOVERNANCE`, and `DOCUMENTATION`.

## Semantic, threshold, and compatibility parity

`BENCHMARK_SEMANTIC_DIFF = 0`. Executable comparisons at three fixed proof points,
including two 800-record lanes, produced byte-equivalent semantic objects and identical
digests between Generator@3 and Generator@4. The detailed digests are recorded in
`generator4_parity_evidence.json`.

`SCIENTIFIC_THRESHOLD_DIFF = 0` and `CLASSIFIER_CONFIG_DIFF = 0`. Protocol@2 and
Protocol@3 quantitative-gate bytes are identical with SHA-256
`a311763dbe8dfa656daf3cc25d1c6d4cc850755d1a4af4691c74b756ddbc0204`.
The leakage suite, classifier implementation, metric definitions, normalizer/gate
governance, presentation rules, and both oracles retain their frozen checksums in
`generator4_threshold_evidence.json`.

The disposable proof established 800/800 Oracle A/B agreement and 800/800 agreement
with generated labels. Frozen Generator@2/raw/scorer suites passed as part of a
135-test compatibility run. Pair membership, all six families, presentation classes,
structural normalization, leakage attacks, classifier settings, and raw/scorer
reconstruction remain delegated to unchanged frozen sources.

## Authority, state, ledger, and manifest

Generator@4 verifies authority and has no real minting API. No consumable authority is
present. The real authority registry is a fixed future path,
`protocol4/materialization_authority/authority-registry.json`, and must be committed,
self-digesting, Protocol@4/Generator@4/Substrate@2/Attempt-1 bound, exact-split, and
`PROVISIONED_NOT_CONSUMED`. Its absence fails closed today. This permits the separately
governed next task to provision authority without modifying frozen Generator@4.

Synthetic fixtures prove acceptance of correct Protocol@4/Substrate@2 bindings and
rejection of Protocol@3, wrong protocol checksum, wrong Generator@4 checksum, wrong
substrate identity/checksum, old attempt, wrong split/path, wrong commitment, and wrong
semantic source. Direct callers cannot inject a verifier for the real attempt, redirect
the real state root, use duck types or subclasses, shadow verifier methods, pass manual
authority objects, or use `canonical=False`. Old Protocol@3 DEV, VALIDATION, and HELD_OUT
authority artifacts reject. Old manifests and old state roots reject.

Ledger events bind protocol identity/checksum, generator identity/checksum, substrate
identity/checksum, attempt, authority digest, split, and the authority-bound seed
commitment. Future manifests bind all required identities plus record count, semantic
package digest, source SHA, ledger head/count, commitment, and terminal state. Synthetic
single-use, restart, reconciliation, and crash-boundary tests pass. Gate A retains the
exact committed evidence-byte digest check; real HELD_OUT count is exactly 2400.

The CLI exposes only authority verification and disposable DEV. It has no canonical
write command, force/reset/retry/new-seed/ignore-ledger option, or canonical downgrade.
Fresh import creates no authority, entropy, ledger, state, or materialization.

## Substrate@2 and contamination

Generator@4 plus Substrate@2 constructs PRE_HELDOUT counts exactly as
`{"DEV": expected_count, "VALIDATION": expected_count, "HELD_OUT": 0}`. Explicit
`HELD_OUT: 0` passes the frozen gate; a missing key or an unexpected key rejects.

The checksum-bound Generator@4 contamination registry covers Protocol@4's observed old
canonical DEV/VALIDATION registry, all Protocol@1 candidate runtime packages, the
substrate DEV contamination registry, all five Generator@2/Generator@3 disposable
proof seeds, and all three registered capacity lanes. Enforcement occurs before the
first semantic record write. Exact semantic-record reuse and exact canonical-runtime-
input reuse reject. The independent reviewer discovered incomplete capacity-lane,
Protocol@1, and substrate-registry coverage during review; all were corrected and have
executable regressions.

## Capacity and feasibility

A single fixed, non-searched disposable lane proves 4,000 records are feasible after
contamination exclusion: DEV 800, VALIDATION 800, HELD_OUT 2,400; 2,000 ALLOW and 2,000
DENY; 4,000 unique semantic instances, canonical inputs, and structural templates; zero
cross-split exact canonical-input overlap; 2,000 complete pairs; exact frozen family
targets; 1,333 benign-looking unauthorized and 667 suspicious-authorized cases. It
passes the complete historical contamination inventory. Evidence is in
`generator4_capacity_evidence.json`. This is capacity proof only and materialized no
canonical split.

## Independent review and red team

The separate reviewer attacked Protocol@3 downgrade, Generator@3 authority reuse,
old-attempt/state/manifest injection, Substrate@1 substitution, `canonical=False`, seed
substitution, authority forgery, state redirect, contamination reuse, semantic drift,
threshold drift, future provisioning, HELDOUT count, and Gate-A evidence substitution.
Final classification: all requested attacks `RESOLVED`; joint privileged rewrite of Git,
verifier, and evidence is `BOUNDED`; `BLOCKING = 0`. The report is
`generator4_independent_review.json`.

## Validation

- Generator@4 focused: 33 passed after final adversarial fixes.
- Final Generator@4/Protocol@4/Substrate@2 focused gate: 62 passed.
- Frozen semantic/oracle/raw/scorer compatibility selection: 135 passed.
- Applicable full repository pytest: 1,118 passed, 0 failed, 0 skipped, exactly 2
  documented EXP-015 lifecycle nodes deselected; no new exclusion.
- Coverage selection: 152 passed. Generator@4 wrapper 77%, Generator@4 authority 75%,
  inherited state/ledger/manifest governance 93%, inherited authority architecture 95%,
  Substrate@2 integration 87%; combined critical files 85%. High-risk named bindings
  have direct tests, although the preferred 90% per-new-file target is not met.
- Ruff: pass.
- Configured mypy (`src`): pass; targeted strict mypy on both Generator@4 sources: pass.
- `git diff --check`: pass.
- All predecessor checksum manifests: pass.

## Frozen/unused state and limitations

`AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1` remains DEV 0, VALIDATION 0, HELD_OUT 0.
Authority artifacts are 0. Production exposure remains reserved 0, started 0, exposed 0,
completed 0, raw 0. No `protocol4/materialization_state` or
`protocol4/materialization_authority` directory exists.

Real authority loading and real HELDOUT materialization are deliberately not exercised;
they are bounded by absent fixed-path committed authority and Gate-A artifacts. The
cooperative governance boundary does not defend against a privileged actor jointly
rewriting Git history, verifier code, and every bound artifact.

The sandbox does not authorize a host Git commit. Generator@4 is scientifically
validated but becomes frozen only when the host commits and pushes this exact checksum-
verified change set without materializing canonical data.
