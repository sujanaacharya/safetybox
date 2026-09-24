# EXP-015-CORPUS@2 Runtime Schema Freeze

**Audit ID:** `EXP-015-CORPUS-2-SCHEMA-FREEZE-AUDIT@1`  
**Corpus status:** `SCHEMA_FROZEN` (not authored)  
**Schema / materializer:** `EXP-015-RUNTIME-SCHEMA@1` / `EXP-015-MATERIALIZER@1`

Corpus@1 was retired pre-exposure because its 120 runtime records required hidden
runner state. Corpus@2 corrects that defect before authorship: one runtime record alone
constructs fixture state, a task contract, request, route, fault configuration, and
observation locations. Scenario IDs are opaque provenance only.

Runtime fields are `scenario_id`, `request`, `task_contract`, `route`, `executable`,
`cwd`, optional additional objects, parent environment, fault injection, and
observations. Requests carry session/task/request/actor identity, executable, argv,
cwd, and timeout. Capabilities are explicit `(action, resource)` pairs. Parent variables
are parent-process inputs only; the frozen adapter still owns the minimal child env.

Executable kinds are `REGULAR_EXECUTABLE`, `NON_EXECUTABLE_REGULAR`, `DIRECTORY`,
`SYMLINK`, `MISSING`, and `UNSUPPORTED_SCRIPT_OR_WRAPPER`. Symlinks require a target;
regular objects require content or a helper recipe; missing means no object. Cwd kinds
are `DIRECTORY`, `MISSING`, `SYMLINK`, and `NON_DIRECTORY`. Helper recipes are the
eleven neutral behaviors enumerated in `schema.yaml`. Fault data supplies a stage,
mode, and parameters at the five declared seams. Routes are `ADAPTER` and the small,
explicit PMED-L1-only `DIRECT_CONTROL` control route.

Observations identify channels and measurement locations (marker paths, stream
sentinels, and environment keys), never their required value. The runtime schema rejects
outcome-bearing field names. It has no labels, pair IDs, requirement IDs, threat tags,
quality tags, or expected results.

Scoring records live separately in `exp015_corpus2_scoring.py`. They contain authority,
validation, terminal, spawn, argv, environment, output, failure, difficulty, coverage,
and pair scoring facts. Its sole `PairRecord` registry has a unique pair ID, two scenario
IDs, one frozen changed dimension, and strength. `derive_manifest` mechanically derives
all listed count fields; runtime materialization never receives labels, pairs, or a
manifest.

Before authorship, targets are 120 cases, approximately 60/60 authority balance, at
least 32 hard-benign and 32 hard-unauthorized cases, at least 30 strong pairs, 16
validation cases, 12 execution/failure cases, 8 argv-boundary cases, 6 repeat selections,
and a small PMED-L1 control set. At least half of authority-positive cases must be
`EDGE_CASE` or `HARD_BENIGN`. Strong pairs change exactly one of the frozen authority
dimensions. Exact Corpus@1 reuse and DEV-PROC fixture/pair reuse are prohibited.
