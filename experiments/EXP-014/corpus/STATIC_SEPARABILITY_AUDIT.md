# Static Separability Audit

Corpus: `EXP-014-CORPUS@1`

Method: deterministic value-to-majority lookup across all 96 scenario/session units. No
model was trained and no adapter output was inspected.

## Single-feature results

| Runtime-visible feature | Lookup accuracy |
|---|---:|
| operation | 0.448 |
| path length | 0.500 |
| path depth | 0.406 |
| relative vs absolute | 0.375 |
| contains `..` segment | 0.375 |
| contains Unicode | 0.375 |
| root name | 0.552 |
| task category (not encoded; one constant value) | 0.375 |
| resource subtree | 0.552 |
| number of capabilities | 0.406 |
| source/destination presence | 0.448 |
| fixture object-type set | 0.552 |
| symlink marker | 0.479 |
| hard-link marker | 0.448 |
| failure-injection type | 0.438 |
| scenario structural length | 0.458 |
| fixture size | 0.448 |
| route | 0.396 |

## Obvious two-feature combinations

| Combination | Lookup accuracy |
|---|---:|
| operation + path depth | 0.479 |
| operation + root name | 0.594 |
| operation + capability count | 0.479 |
| fixture object-type set + failure-injection type | 0.615 |
| route + operation | 0.469 |

No tested single feature or obvious two-feature combination perfectly predicts the seven
terminal classifications. The maximum observed lookup accuracy is 0.615.

## Interpretation and limitations

Link markers and injection types are legitimate fixture-construction inputs, not author
metadata. They necessarily make some validation/failure subclasses easier to identify;
those cases are separated from primary authorization correctness, whose expected decision
is joined only after execution. Direct-route identity is also necessarily visible because
the control must select a direct API. Neither fact lets a simple lookup recover the global
terminal taxonomy.

Scenario IDs, request IDs, and task IDs are excluded from this audit because every value is
unique and opaque; a lookup table over unique identities is memorization, not a static
property test. Pair/family IDs, rationales, hard-negative flags, and expected outcomes are
not runtime features and were not tested as inputs. No high-capacity classifier,
combinatorial feature search, or adapter prediction was used. Finite lookup checks cannot
prove the absence of every possible leakage channel.
