# AUTH-COVERAGE-001 bounded exhaustive verification

**Verifier identity:** `AUTH-COVERAGE-001-EXHAUSTIVE-VERIFIER@1`

**Specification identity:** `AUTH-COVERAGE-001-AUTHORIZATION-SPEC@1`

**Result:** `PASS`

**Evidence class:** architectural/development evidence, not held-out production evidence

## Method

`experiments/AUTH-COVERAGE-001/formal/exhaustive_verify.py` exhaustively enumerates a
small finite authorization model using only the standard library. It imports the
experiment-local executable specification and no production `safetybox` module. No TLA+,
Alloy, Z3, or other solver is claimed; deterministic enumeration is sufficient for this
bound and avoids decorative formal tooling.

The frozen machine-readable proof record is
`experiments/AUTH-COVERAGE-001/formal/exhaustive_results.json`. Tests require exact
equality between a fresh verifier result and that record.

The checker independently calculates expected decisions from finite set membership and
logical conjunction, then asserts the executable specification result and registered
metamorphic invariants.

## Frozen bound and result

| State family | Bound | Enumerated states |
|---|---|---:|
| Atomic filesystem | 2 tasks × 2 actions × 2 resources × 2 contract tasks × 16 capability subsets | 256 |
| Exact resource boundary | 2 tasks × 2 actions × 2 directional sibling pairs × allow/deny observations | 16 |
| Partial-capability synthesis | 2 tasks × 2 actions × 2 resource directions | 8 |
| Compound process | 2 tasks × 2 contract tasks × 2 executable resources × 2 cwd resources × 16 capability subsets | 256 |
| Attenuation pairs | 8 parent sets × 8 child sets | 64 |
| Invalid structures | empty components, non-canonical request, invalid capability, duplicate capability ID | 4 |
| **Total explicit states** |  | **604** |

Compound outcomes reached every quadrant:

| Quadrant | Count |
|---|---:|
| exec ALLOW / cwd ALLOW | 32 |
| exec ALLOW / cwd DENY | 32 |
| exec DENY / cwd ALLOW | 32 |
| exec DENY / cwd DENY | 160 |

The DD imbalance is a property of exhaustively including task mismatch and sparse
capability subsets, not a proposed corpus distribution. Corpus compound families should
be balanced where reasonable.

## Invariant check counts

| Invariant | Checks |
|---|---:|
| Normative finite-state semantics | 256 |
| Determinism | 256 |
| Explanation completeness | 256 |
| Capability-order independence | 256 |
| Irrelevant-capability independence | 256 |
| Suspiciousness independence | 256 |
| Innocence independence | 256 |
| AI-context non-authority | 256 |
| Unknown-context non-authority | 256 |
| Opaque request/contract ID independence | 512 |
| Cross-task reuse rejection | 128 |
| Exact resource binding | 8 |
| Compound subdecision independence | 256 |
| No authority amplification | 72 |
| Attenuation precursor | 64 |
| Delegation-chain precursor | 2 |
| Fail closed | 4 |

## Reproduction

```bash
.venv/bin/python experiments/AUTH-COVERAGE-001/formal/exhaustive_verify.py
```

The command emits a sorted JSON proof record and exits nonzero on any assertion failure.
Repository tests independently lock the reported identities, bounds, state counts,
quadrants, import isolation, and representative semantics.

## Interpretation and limits

Within the finite abstraction, every possible capability subset is covered rather than
sampled. This is stronger than a sampled unit test for task equality, action equality,
resource equality, compound conjunction, and the stated attenuation universe.

It is not a proof over arbitrary strings, arbitrary capability counts, physical resource
identity, runtime effects, authenticated subjects, temporal state, use counters,
destinations, network, MCP, DB, or production implementation correctness. The subtree
attenuation probe universe contains two exact children and one nested descendant; it is
a bounded model, not a general theorem prover. Same-team authorship and shared written
semantics remain sources of conceptual coupling.

The exhaustive result therefore supports only this statement: the independent executable
specification satisfies the registered invariants for all 604 states in the frozen
finite model. It must not be presented as held-out benchmark performance.
