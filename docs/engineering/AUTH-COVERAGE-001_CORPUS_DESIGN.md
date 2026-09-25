# AUTH-COVERAGE-001 corpus design

**Design identity:** `AUTH-COVERAGE-001-CORPUS-DESIGN@1`

**Normative corpus:** `AUTH-COVERAGE-001-CORPUS@1`

## Construction model

Scenarios are generated from reviewed structural templates, then deterministically
materialized, assigned opaque IDs, labeled by two independent oracles, and audited. A
scenario contributes only when it exercises a registered claim, pair, property,
metamorphic relation, mutation, or calibration control. Count alone is not a freeze gate.

Runtime-visible scenario records contain the request, contract, capabilities, tool, and
operation data required to make a decision. Labels, family tags, split, pair membership,
difficulty, expected subdecisions, and claim mappings remain scoring-side.

## Filesystem decisions

Filesystem actions cover `filesystem.read`, `filesystem.write`, `filesystem.list`, and
`filesystem.delete`. Resources cover exact files; siblings; parents and children;
prefix/suffix confusables; Unicode-near names; literal dot segments; canonical equivalents;
relative-looking strings; other roots; nested scopes; and `/**` scopes. This is logical
string authorization. It intentionally performs no normalization, symlink traversal, stat,
mount, permission, or physical-path validation.

## Process decisions

A process request always has independent executable and cwd components. The executable
component uses `process.exec`; cwd uses `process.cwd`. Coverage balances `AA`, `AD`, `DA`,
and `DD`, including exact, sibling, parent, child, same-basename/different-path, missing
action, wrong-action/right-resource, and right-action/wrong-resource cases. `argv` contains
both neutral and alarming literals but never affects authority.

## Composition and synthesis resistance

Distractor sets include one relevant capability among many, zero relevant capabilities
among many plausible capabilities, same action on near resources, different actions on the
same resource, and split partial matches. A component allows only if one capability
individually matches its task, action, and resource. Separate partial capabilities never
synthesize authority. Process components may be covered by different complete
capabilities, because process semantics explicitly require two independent decisions; a
partial match within either component still denies the whole operation.

## Pair and cross-tool registries

Pair records identify two opaque scenario IDs, the changed dimension, strength, frozen
field-difference proof, and expected relation. Registered dimensions are task, action,
exec resource, cwd resource, filesystem resource, capability presence, capability scope,
compound subdecision, tool, contract identity, and cross-task reuse.

Cross-tool groups compare structural principles rather than pretending filesystem and
process actions are identical. Each group names the shared principle and one or more cases
per tool. The metric passes a group only if every member decision is correct.

## Split policy

Splits are assigned by stable hash after pair/group construction. All members of a pair or
cross-tool group remain in the same split to prevent relational leakage. Template roots are
also grouped so a generated template cannot straddle DEV and HELD_OUT. The held-out corpus
is frozen but not executed by this task.

## External packs

An `EXTERNAL_PACK@1` submission contains pack identity, author independence metadata,
schema version, scenarios, optional proposed pair relations, and provenance. It cannot
contain expected production outputs. Ingestion remaps identifiers, recomputes all oracle
labels and difficulty, verifies pair differences, rejects semantic duplicates, and records
same-team/external authorship without changing metrics.

## Review capacity

Audit reports summarize every template and enumerate anomaly samples. Canonical generation
is deterministic and source-controlled. The freeze gate rejects low-value repeated
instantiations even if that reduces the total below target; falling below a required target
then blocks freeze rather than encouraging filler.
