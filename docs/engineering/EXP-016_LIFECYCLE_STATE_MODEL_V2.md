# EXP-016 lifecycle state model v2

**Model:** `EXP-016-REACHABILITY-MODEL@2`

**Machine contract:**
[`lifecycle_model.json`](../../experiments/EXP-016/v2/contracts/lifecycle_model.json)

**Oracle:**
[`exp016_lifecycle_v2.py`](../../src/safetybox/experiments/exp016_lifecycle_v2.py)

## Why the prefix funnel was retired

The v1 funnel encoded success dependencies as a universal sequence. It therefore treated a
terminal audit after failed spawn as an impossible jump. Production semantics are instead a
partial order: attempting spawn requires successful adapter prerequisites; creating a child
requires successful spawn; completing a child requires creation; but recording an adapter
terminal outcome does not require a child.

## Typed dimensions

| Dimension | Important distinctions |
|---|---|
| Authorization | `ALLOW`, `DENY`, `FAILED`, `NOT_APPLICABLE` |
| Validation | `PASS`, `REJECT`, `NOT_REACHED`, `INDETERMINATE`, `NOT_APPLICABLE` |
| Preaudit | `COMMITTED`, `ATTEMPTED_FAILED`, `NOT_REACHED`, `NOT_APPLICABLE` |
| Spawn | `SUCCEEDED`, confirmed-no-child attempted failure, attempted indeterminate, not reached |
| Child creation | `CREATED`, `NOT_CREATED`, `INDETERMINATE` |
| Child observation | `COMPLETED`, `NOT_AVAILABLE`, `INDETERMINATE` |
| Capture | `COMPLETE`, `FAILED`, `NOT_REACHED`, `INDETERMINATE` |
| Child outcome | exit zero, nonzero, signal, timeout, unavailable, indeterminate |
| Terminal audit | `COMMITTED`, `ATTEMPTED_FAILED`, `NOT_EMITTED`, `INDETERMINATE`, `NOT_APPLICABLE` |
| Effect | `NONE`, `CONFIRMED`, `INDETERMINATE` |

## Registered adapter paths

The model covers policy denial, authorization failure, executable and cwd rejection,
preaudit failure, confirmed-no-child spawn failure, indeterminate spawn, exit zero,
nonzero exit, signal, timeout, post-child capture failure, and terminal-audit failure.

For the spawn regression, the truthful state is:

```text
authorization       ALLOW
exec validation     PASS
cwd validation      PASS
preaudit             COMMITTED
spawn                ATTEMPTED_FAILED_CONFIRMED_NO_CHILD
child creation       NOT_CREATED
child observation    NOT_AVAILABLE
terminal audit       COMMITTED
effect               NONE
```

This state is valid because `EXECUTION_FAILED` is an adapter terminal outcome. It makes no
child-completion claim.

## Derivation boundary

The oracle imports no production process module. It derives lifecycle state only from a
completed raw observation. This separation prevents expected labels from influencing
execution and avoids changing correct production behavior to fit an experiment abstraction.

Indeterminate child creation or effects remain indeterminate. The oracle rejects child
creation without successful spawn, completion without creation, spawn without adapter
prerequisites, fabricated adapter fields on direct controls, and route/dispatcher mismatch.
