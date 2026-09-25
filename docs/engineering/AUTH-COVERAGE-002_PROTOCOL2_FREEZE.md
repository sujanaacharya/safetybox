# AUTH-COVERAGE-002 Protocol@2 freeze

**Identity:** `AUTH-COVERAGE-002-PROTOCOL@2`

**Decision:** `FROZEN`

**Quantitative-table SHA-256:**
`a311763dbe8dfa656daf3cc25d1c6d4cc850755d1a4af4691c74b756ddbc0204`

**Frozen substrate:** `8e3ba29bbadcdc9c4de4c0d306e8eaaf013dab78`

**Prior blocked protocol:** `AUTH-COVERAGE-002-PROTOCOL@1` remains immutable

**Freeze evidence:** `AUTH-COVERAGE-002-PROTOCOL2-DEV-PROOF@1`

**Independent review:** `AUTH-COVERAGE-002-PROTOCOL2-INDEPENDENT-REVIEW@1`

The protocol is frozen before any new VALIDATION or HELD_OUT realization, baseline,
classifier measurement, leakage measurement, or production prediction. The rejected @1
candidate is disclosed development/negative evidence only. All normative files are bound
by `experiments/AUTH-COVERAGE-002/protocol2/PROTOCOL2_SHA256SUMS`.

The freeze fixes the quantitative table, leakage adversary, classifier hyperparameters,
branch rules, ordered explanation schemas, whole-input presentation rules, pair mechanics,
external-pack dual-oracle admission, structural normalization, adaptivity/versioning
policy, and the Gate A/Gate B separation. No waiver mechanism exists.

Freeze does not authorize creation of VALIDATION or HELD_OUT data. Future Gate A is
`AUTHORIZED_TO_MATERIALIZE_AUTH002_CORPUS2_HELDOUT`; future Gate B is
`AUTHORIZED_TO_EXECUTE_AUTH002_CORPUS2_HELDOUT_PRODUCTION`.

At freeze: new HELD_OUT scenarios = 0; reservations = 0; starts = 0; exposures = 0;
completions = 0; raw records = 0.
