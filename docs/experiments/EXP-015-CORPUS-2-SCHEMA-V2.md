# EXP-015-CORPUS@2 Runtime Schema v2

**Schema / materializer:** `EXP-015-RUNTIME-SCHEMA@2` /
`EXP-015-MATERIALIZER@2`
**Status:** `SCHEMA_FROZEN`, development/schema-proof only; no held-out corpus exists.

Schema v2 has two independent opaque task IDs: `request.task_id` and
`task_contract.task_id`. Both are non-empty bounded IDs with a defined representation;
the schema does not compare them. A future authority oracle consumes both values and
derives task mismatch as a denial. Runtime records carry an explicit v2 `schema_id`, and
materialized output records both the schema and materializer IDs.

The schema validates structure, not authority. It permits zero relevant capabilities,
many irrelevant capabilities, mixed actions, absent exec/cwd capabilities, and exact
process.exec/process.cwd resource mismatches. It still rejects malformed IDs,
missing/type-invalid fields, invalid paths, invalid route and fixture enums, malformed
capabilities, invalid timeout representation, and unknown fixture kinds.

Both `ADAPTER` and `DIRECT_CONTROL` are runtime routes only. Neither signals an
authorization result. Fixture forms preserve normal, missing, symlink, directory,
non-executable, and wrapper executables; all cwd forms; all helper recipes; and all
fault stages/modes. These are runtime conditions, never labels.

Corpus@2 authors must use v2 directly. There is no Corpus@1 migration, automatic
scenario migration, or compatibility fallback to v1 equality semantics. Task IDs must be
opaque and their naming/format distributions balanced across later authority-positive
and authority-negative cases; names such as `task-allow` or `task-deny` are prohibited.
