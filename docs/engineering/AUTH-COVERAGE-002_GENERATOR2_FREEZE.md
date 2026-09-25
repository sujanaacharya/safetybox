# AUTH-COVERAGE-002 Generator@2 freeze

**Identity:** `AUTH-COVERAGE-002-GENERATOR@2`

**Decision:** `FROZEN_DEV_ONLY`

**Protocol dependency:** `AUTH-COVERAGE-002-PROTOCOL@2` at commit
`5fc3e2673235286cc393878523581fcf7e8d6d2d`

**Proof:** `AUTH-COVERAGE-002-GENERATOR2-DEV-PROOF@1`

Generator@2 was developed only with deterministic synthetic DEV fixtures. Five robustness
seeds and three full-target capacity lanes are registered as contaminated DEV evidence and
cannot enter future VALIDATION or HELD_OUT data. No VALIDATION or HELD_OUT seed is
registered.

Given the same protocol, source, DEV seed, count, and template-root offset, semantic
authoring records reproduce exactly. Authoring output contains no runtime IDs. The DEV
fixture function assigns deterministic test IDs and rejects non-DEV input. The future
materializer accepts no injected allocator and assigns scenario, request, session, and
actor IDs directly with `secrets.token_hex(32)`.

The construction balances both labels within every tool/family parent, randomizes manifest
order, and supplies all 84 registered leaves. Pair intent is authoring-side only; the
separate protocol auditor assigns the final grade. Structural normalization is owned by
the frozen protocol and cannot be changed with this generator identity.

All source, tests, proof, and contamination records are bound by
`experiments/AUTH-COVERAGE-002/protocol2/GENERATOR2_SHA256SUMS`.

At freeze: new VALIDATION scenarios = 0; new HELD_OUT scenarios = 0; HELD_OUT reservations,
starts, exposures, completions, production calls, and raw records = 0.
