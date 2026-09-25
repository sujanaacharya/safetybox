# EXP-015 pre-run gate redisposition

**Gate ID:** `EXP-015-PRE-RUN-GATE-REDISPOSITION@1`
**Supersedes:** no prior record; this is additive to the earlier blocked record.
**Decision:** `READY_FOR_EXP_015_RUN_001`

The earlier `EXP-015-PRE-RUN-ENVIRONMENT-GATE@1` remains unchanged.  Its
shared-process `sys.modules` blocker is resolved by the independent fresh
process proof recorded in
[`EXP-015_PRE_RUN_TEST_PROCESS_ISOLATION_DISPOSITION.md`](EXP-015_PRE_RUN_TEST_PROCESS_ISOLATION_DISPOSITION.md).

All required pre-run checks pass: fresh-process Corpus@2
integrity/import-isolation, the remaining development suite, DEV-PROC,
authorization regression, 95% normal coverage, Ruff, mypy, frozen checksums,
and EXP-014 integrity.  Protocol, PROC-ADAPTER@1, schema/materializer v2, and
Corpus@2 remain at their frozen SHAs.  Held-out adapter executions are **0**,
`results/EXP-015/` is absent, and `EXP-015-RUN-001` remains unspent.

This decision authorizes no execution within this change.  The next task is the
separate, canonical one-shot run.
