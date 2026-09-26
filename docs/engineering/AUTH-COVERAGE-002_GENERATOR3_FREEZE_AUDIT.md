# AUTH-COVERAGE-002 Generator@3 freeze audit

Disposition: `SCIENTIFICALLY_VALIDATED` (commit/push status is an independent
operational field).

Generator identity: `AUTH-COVERAGE-002-GENERATOR@3`. Protocol dependency:
`AUTH-COVERAGE-002-PROTOCOL@3` at freeze commit
`6959866f9ddb298e9cf5153544dc8a4551a83265`. Expected generator identity is
the frozen contract digest
`e792195d841a664137bc4c31bcfb83be0be421fe394c029d9c4feee96b953a94`;
the complete implementation/evidence set is bound by `GENERATOR3_SHA256SUMS`.

## Semantic compatibility

`BENCHMARK_SEMANTIC_DIFF = 0`. Generator@3's disposable lane delegates
directly to frozen Generator@2. The canonical lane calls the same
`generate_authoring` only after authority consumption and STARTED are durable;
it adds no label, family, pair, difficulty, presentation, leakage, classifier,
metric, structural-normalizer, oracle, or explanation behavior.

The disposable capacity/oracle/raw/scorer lane passed 43/43 tests. It includes
the 4,000-record structural-capacity proof, all frozen family/pair/presentation
requirements, raw reconstruction and scoring isolation, and explanation
scoring. A Generator@3-specific 800-record proof had 800/800 Oracle A/B/label
agreements. Frozen Oracle files and checksums were unchanged.

## Authority architecture and threat model

The real authority issuer is not Generator@3. Three Protocol@3-provisioned JSON
artifacts bind protocol identity/checksum, expected generator identity, source
SHA, real attempt, split, commitment, purpose, use count, record count,
provisioning timestamp, Gate-A requirement, governance source, and artifact
digest. Their approved digests and root are immutable in the real verifier.
Real materialization additionally requires exact Git-HEAD bytes. The ordinary
API has no real issuance method and accepts no caller split, seed, record list,
count, `canonical` flag, retry, reset, or force input.

The test-only provisioner requires `SYNTHETIC` protocol, generator, and attempt
identities and rejects `AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1`, including from a
fresh external process. Exact built-in verifier/store types and immutable
instance boundaries prevent duck-typed, subclass, method-shadow, alternate
root, and post-construction redirection attacks. Lower-level semantic
generation cannot create ledger, anchor, state, manifest, or seal evidence.

This is cooperative scientific-governance integrity. It detects ordinary
caller substitution, deletion, truncation, rollback, and inconsistent durable
evidence. It does not claim security against an administrator who rewrites Git
history, the verifier, authority root, semantic package, anchor, and state
together.

## Durable state and crash behavior

The fsynced hash-chained JSONL ledger and independently replaced/fsynced anchor
record authority digest, attempt, split, `AUTHORITY_CONSUMED`, `STARTED`,
`FIRST_RECORD_DURABLE`, `COMPLETED`, `SEALED`, and `PARTIAL_BLOCKED`. State is
separately fsynced. The semantic package fsync precedes
`FIRST_RECORD_DURABLE`, exactly implementing Protocol@3's first-durable-record
boundary.

Before that boundary, the only retry reuses the same authority and commitment;
if a crash occurred immediately after consumption, retry first records the
missing STARTED event and never consumes again. At or after the boundary,
fresh-process reconciliation records/returns terminal partial-blocked evidence
or a terminal completed-unsealed/sealed state. It never creates semantic data.

Fresh-process crash results:

| Injection point | Reconciled state | Status |
|---|---|---|
| before/after authority verification | NOT_STARTED | SUPPORTED |
| after consumption; after STARTED; before first write; torn first write | STARTED_UNOBSERVED | SUPPORTED |
| after first fsync; after boundary event; mid-generation; after last record; before COMPLETED | PARTIAL_OBSERVED_BLOCKED | SUPPORTED |
| after COMPLETED; before/after manifest; during verification; before SEALED | COMPLETED_UNSEALED | SUPPORTED |
| after SEALED | SEALED | SUPPORTED |

Ledger deletion returns `LEDGER_MISSING`; suffix removal and older-ledger
replacement return `ANCHOR_MISMATCH`; corrupt chains return `LEDGER_CORRUPT`;
state divergence returns `STATE_INCONSISTENT`. Missing or changed sealed
manifests return `MANIFEST_MISMATCH`. Missing evidence never means UNUSED.

## Manifest and gates

The independently verified manifest binds protocol identity/checksum,
generator identity/checksum, attempt, split, authority digest, commitment,
record count, package digest, ordering policy, runtime-ID policy, source SHA,
COMPLETED ledger head/count, and target terminal state. Mutation of each of its
17 fields failed independently; deletion after SEALED failed closed.

HELD_OUT requires the exact
`AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE` decision and exact protocol,
generator, attempt, sealed DEV digest, sealed VALIDATION digest, and independent
evidence digest. Real Gate-A approval and evidence must be Git-HEAD-provisioned
artifacts at fixed paths. Seven field-forgery lanes and omission reject before
generation. Gate A cannot authorize production; Gate B cannot authorize
materialization.

## Evidence classification

| Requirement | Status | Evidence |
|---|---|---|
| benchmark semantics and Protocol@3 compatibility | SUPPORTED | exact delegation, checksum gates, semantic-diff test |
| external authority root; no real public mint | SUPPORTED | immutable real verifier configuration, Git provision check, synthetic-only factory |
| real-attempt, attempt/split/seed substitution and shopping | SUPPORTED | fresh-process guard, approved digest binding, API signature tests |
| canonical DEV/disposable DEV separation | SUPPORTED | distinct `disposable_dev` and authority-only canonical entry points |
| replay and duplicate VALIDATION/HELD_OUT after restart | SUPPORTED | fresh external interpreter tests |
| durable consumption, state, boundary, and partial terminality | SUPPORTED | full fresh-process crash matrix and ledger assertions |
| Gate A enforcement/forgery and Gate B separation | SUPPORTED | omission, seven mutations, direction-separation tests |
| ledger/anchor deletion, truncation, rollback | SUPPORTED | independent corruption and older-copy probes |
| reconciliation classes | SUPPORTED | NOT_STARTED, STARTED_UNOBSERVED, PARTIAL_OBSERVED_BLOCKED, COMPLETED_UNSEALED, SEALED, LEDGER_MISSING/CORRUPT, ANCHOR/MANIFEST mismatch, STATE_INCONSISTENT |
| manifest construction and independent verification | SUPPORTED | every bound field mutated plus deletion test |
| CLI hardening | SUPPORTED | no canonical write command; disposable DEV and verification only; no bypass options |
| pytest real-attempt guard and import safety | SUPPORTED | fresh-process factory rejection and before/after filesystem inventory |
| disposable capacity, Oracle, raw/scorer, structural/presentation capacity | SUPPORTED | 43 compatibility tests plus Generator@3 800/800 oracle proof |
| privileged all-filesystem/Git-history attacker resistance | NOT_SUPPORTED | explicitly outside scientific-governance threat model |

## Validation record

The independent read-only reviewer did not merely rerun author test names. It
first reproduced and classified three blocking defects—alternate real trust
root, duck-typed verifier/store, and real-to-synthetic mutable-domain bypass—
and a STARTED-ordering defect. After repair it independently retested
self-issuance, downgrade, substitution/shopping, replay, both split duplicates,
Gate omission/forgery/confusion, ledger deletion/truncation/rollback, manifest
deletion/mutation, attempt rename, partial restart, CLI/direct-Python/lower-level
bypasses, and import effects. Every in-scope finding is RESOLVED; joint
privileged rewrite of code, Git HEAD, and all evidence is BOUNDED. No BLOCKING
finding remains.

- Focused Generator@3 governance: 100 passed.
- Scientific compatibility lane: 43 passed.
- Pre-final raw repository diagnostic: 1,048 passed, 2 failed. Both failures are the exact
  frozen post-EXP-015 lifecycle conditions: the historical result directory
  exists and shared-interpreter adapter-import absence is no longer true.
- Final applicable full suite using the frozen disposition: 1,056 passed,
  2 deselected, 0 failed, 0 skipped.
- Focused branch coverage: authority verifier 94%, generator/governance 91%,
  combined 92%; all named high-risk branches have direct evidence.
- Ruff: PASS. mypy: PASS. `git diff --check`: PASS.
- Protocol@3, Protocol@2, Generator@2, and frozen execution-substrate checksum
  manifests: PASS. Earlier frozen experiment integrity is covered by the
  applicable full suite.

Final counts are canonical DEV 0, canonical VALIDATION 0, canonical HELD_OUT
0. Production reserved 0, started 0, exposed 0, completed 0, raw 0. No Gate-A
artifact exists and no production authorization was executed.
