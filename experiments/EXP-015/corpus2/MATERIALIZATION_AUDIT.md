# Materialization audit

`integrity_check.py` ran 120 fresh-root materializations in pass 1 and 120 in
pass 2. Normalized executable/cwd object state, route, fault recipe, parent-env
keys, and observation channels were equal for every scenario. It independently
inspects `lstat` type, mode, symlink target, and missing state.

Task mismatch pairs retain both original task IDs and materialize the same
fixture state. Runtime construction occurs before labels are loaded; the check
asserts the adapter module is absent. All helper recipes, faults, observations,
environment sentinels, and additional PATH-trap objects are runtime fields.
