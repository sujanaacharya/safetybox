# AUTH-COVERAGE-002 Protocol@3 preregistration

Identity: `AUTH-COVERAGE-002-PROTOCOL@3`. This is a successor preregistration, not a patch to Protocol@2. Protocol@2 remains `VALID_BUT_INSUFFICIENT_FOR_SUCCESSOR_GENERATOR_REALIZATION`: it froze Generator@2, whose valid DEV-only contract lacks canonical validation realization semantics.

Protocol@3 authorizes a future `AUTH-COVERAGE-002-GENERATOR@3` and `AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1`. Generator@3 may add only seed registration, canonical realization authorization, materialization-ledger and attempt binding, crash policy, manifest binding, and Gate-A/B integration. It may not change authorization/label semantics, families, pairs, difficulty, presentation definitions, normalizer, Oracle A/B, metric definitions, quantitative gates, classifiers, or statistical methods.

The quantitative table is byte-identical to Protocol@2 (`a311763dbe8dfa656daf3cc25d1c6d4cc850755d1a4af4691c74b756ddbc0204`). In particular it preserves the 0.555 leakage limits, 0.05 branch deviation, 3,200 templates, cluster maximum 4, whole-input targets, and all existing mutation, explanation, raw/scorer, pair, and leakage requirements.

Canonical DEV, VALIDATION, and HELD_OUT are distinct from disposable DEV. Generator@3 must preregister one canonical DEV seed, one validation seed/entropy procedure, and one delayed held-out entropy procedure. No seed search, preview selection, or regeneration under an attempt is permitted. Runtime IDs remain OS-CSPRNG opaque identifiers independent of semantic seeds.

The first durably written canonical semantic record is the materialization-exposure boundary. A partial materialization blocks the attempt; Protocol@3 does not authorize resume. Canonical Validation becomes spent at that boundary. HELD_OUT remains unauthorized until Gate A returns `AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE`; production remains unauthorized until Gate B returns `AUTHORIZED_TO_EXECUTE_HELDOUT_PRODUCTION_ONCE` after sealed corpus audit and final pre-run review.

The materialization ledger is separate from the prediction-exposure ledger. Every authorization binds protocol, generator SHA, attempt, split, seed/entropy commitment, count, timestamp, artifact digest, and source SHA; it is single-use. Normal tests, imports, utilities, and unregistered CLIs must reject canonical realization before output.

AUTH-COVERAGE continues to evaluate authorization correctness only. It does not establish effect prevention, complete mediation/attribution, network/MCP protection, authenticated identity security, delegation safety, or rogue-agent containment.

The required chain is Protocol@3 → Generator@3 → attempt → canonical DEV → canonical VALIDATION → Gate A → HELD_OUT once → corpus audit/freeze → final pre-run audit → Gate B → one-shot raw-first production → raw seal → scoring → analysis.
