# EXP-016 family and population model v2

**Definitions:** `EXP-016-FAMILY-REGISTRY@2`

**Population model:** `EXP-016-CORPUS-POPULATION-MODEL@2`

**Design target:** `EXP-016-CORPUS-DESIGN@1`

## Definitions are not membership

The 20 canonical families remain conceptually useful, but their registry now contains only
purpose, route, prerequisites, lifecycle shape, metric contributions, minimum future count,
requirements, threats, and repeat eligibility. It contains no scenario IDs or current
corpus count.

Future corpus membership is a separate label-side artifact with exactly one primary family
and separately typed secondary tags per opaque scenario ID. Adding membership cannot mutate
family definitions.

## Population states

| State | Meaning | Frozen count |
|---|---|---|
| `PLANNED` | Constraints/design target exist; instances do not | null |
| `MATERIALIZED` | Instances exist for offline pre-freeze audit | null |
| `FROZEN` | Exact positive membership and manifest are immutable | exact positive integer |

The current state is `PLANNED`: planned total 120, materialized count zero, frozen count
unset. This does not claim an empty frozen corpus.

Exact family counts must be preregistered in corpus design metadata before scenario content
is authored. At eventual corpus freeze, runtime inputs, isolated labels, family and repeat
membership, exact counts, requirement/threat joins, reachability/materialization evidence,
contamination classification, and checksums become immutable together.

Synthetic regression data proves that a positive disposable membership can join the same
definitions without altering them. Those `DEV-SYNTH-*` identifiers are contaminated and
cannot be reused as held-out inputs.
