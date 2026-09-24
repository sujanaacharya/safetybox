# Development Contamination Audit

## Sources and exclusion set

The frozen inventory is
[`EXP-014-ADAPTER-DEVELOPMENT-VALIDATION.md`](../../../docs/experiments/EXP-014-ADAPTER-DEVELOPMENT-VALIDATION.md),
augmented by
[`EXP-014_PRE_CORPUS_FREEZE_AUDIT.md`](../../../docs/engineering/EXP-014_PRE_CORPUS_FREEZE_AUDIT.md)
and the fixture declarations in the frozen development test. The exclusion set covers:

- `DEV-FS-LEXICAL-001` through `DEV-FS-LEXICAL-009` and their `public/a.txt` spellings;
- `DEV-FS-SYMLINK-*` names/topologies, including `link.bin`, `chain-a`, `chain-b`,
  `linked-parent`, and `secret.bin`;
- all `DEV-FS-OP-*`, `DEV-FS-RENAME-*`, root/session, create-parent, and mkdir-parent
  operation/authority arrangements;
- `DEV-FS-PRIMITIVE-FAILURE-*` permission/write combinations;
- adapter-ingress, canonicalization, execution-start, post-state, and terminal-success
  development audit injections;
- hostile mapper, state-digest mutation/equivalent-root, post-effect lifecycle, and
  normalized legacy-M3 audit cases; and
- the default `DEV-FS-REQUEST-001` identifier and development payload/path tuples.

Held-out paths use cedar/quartz/ember/lotus/alpha families, corpus-specific bytes and
sentinels, different symlink names/targets, different hard-link layouts, and distinct
rename/failure arrangements. Scenario and request identifiers use only opaque `FSH-014-*`
forms.

## Comparison method

The audit used four levels:

| Classification | Method | Result |
|---|---|---|
| `EXACT_DUPLICATE` | Compare operation, request path, destination, fixture paths/bytes, authority arrangement, and injection together. | 0 |
| `STRUCTURAL_NEAR_DUPLICATE` | Manual comparison of operation/path relation, symlink topology, rename relation, and injection stage. | 6 documented classes |
| `ACCEPTABLE_SHARED_PRIMITIVE` | Required public semantics whose primitive cannot be removed merely because development tested it. | Root stat, operation success/denial, link rejection, audit gates |
| `DISTINCT` | New names plus a materially different path/authority/topology/failure relation. | All remaining cases |

The automated test also extracts constant development `request(...)` operation/path/
destination tuples. The only shared tuple is `filesystem.stat` on `/workspace`. It is not
an exact scenario duplicate: the held-out pair uses a different root fixture and a matched
validator-dependency failure, while the development inventory used ordinary root behavior.
It is classified `STRUCTURAL_NEAR_DUPLICATE` and `ACCEPTABLE_SHARED_PRIMITIVE` because the
frozen protocol explicitly requires root-boundary semantics.

Other justified structural near-duplicate classes are the abstract primitives mandated by
the protocol: one normal-vs-symlink component, one normal-vs-multi-link terminal, missing
required target, non-empty directory deletion, pre-execution audit rejection, and terminal
audit rejection. Their held-out path tuples, bytes, authority relationships, link shapes,
and paired counterfactuals differ from development; they are not cosmetic renames of a
development fixture.

## Conclusion

**PASS with documented shared primitives.** No exact development fixture or renamed
template is present. Structural similarity remains where the frozen requirements demand
the same security primitive, and those cases use independently authored concrete layouts.
This is evidence of deliberate contamination control, not a mathematical proof of corpus
independence.
