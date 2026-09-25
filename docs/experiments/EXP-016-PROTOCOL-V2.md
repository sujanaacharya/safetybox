# EXP-016 Protocol@2

**Protocol:** `EXP-016-PROTOCOL@2`

**Evidence status:** preregistered governance; no held-out evidence

**Machine source:**
[`experiments/EXP-016/v2/protocol.yaml`](../../experiments/EXP-016/v2/protocol.yaml)

Protocol@2 governs future EXP-016 corpus authorship and scoring. It leaves Protocol@1 and
all EXP-015 artifacts immutable. The research question, native helper, physical
reachability principle, label isolation, deterministic-repeat projection, explicit scope
boundaries, candidate-claim status, and RTM-1 maturity remain unchanged.

## Corrected governance model

Protocol@2 makes four corrections:

1. Family definitions contain no scenarios. Future instance membership is a separate
   corpus artifact.
2. A planned total is distinct from materialized instances and a frozen corpus count.
   Before corpus freeze the latter is unset, not zero.
3. Lifecycle evidence is a route-aware typed partial order rather than a strict success
   prefix.
4. `ADAPTER` and `DIRECT_CONTROL` have independent applicable states and denominators.

The planned corpus total is 120. Exact family counts must be frozen in a separate design
target before scenario content is authored. No corpus instance is created by this protocol
freeze.

## Lifecycle evidence

Adapter evidence distinguishes authorization, executable validation, cwd validation,
preaudit, spawn, child creation, child observation, capture, child terminal outcome, and
terminal audit. Attempted failure, not reached, indeterminate, and not applicable are never
collapsed into false or success.

Terminal audit may legitimately commit after a confirmed spawn failure even though no child
exists. Conversely, a direct control can create and complete a child while all adapter-only
dimensions are `NOT_APPLICABLE`.

## Scoring and isolation

Raw execution records contain observations only. The experiment-side derivation produces a
typed lifecycle state after raw completion. Labels, family membership, requirements,
threats, repeats, and expected outcomes remain isolated until the raw barrier.

Every metric declares applicable routes. Zero applicable denominator remains
`NOT_EXERCISED`; `NOT_APPLICABLE` is excluded and can never count as a pass. Overall success
requires a positive frozen corpus, positive denominators, and at least one real applicable
adapter child for positive spawn-ordering claims.

## Evidence discipline

This governance freeze executes no held-out scenario, promotes no claim, and authorizes no
one-shot run. Development proofs use only synthetic lifecycle dictionaries and disposable
membership identifiers and are permanently contaminated for held-out reuse.
