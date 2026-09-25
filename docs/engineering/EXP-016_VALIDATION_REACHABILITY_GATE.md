# EXP-016 validation-reachability gate

**Artifact:** `EXP-016-VALIDATION-REACHABILITY-GATE@1`

**Principle:** materializability is not enough

## Independent oracle

The oracle in
[`exp016_reachability.py`](../../src/safetybox/experiments/exp016_reachability.py) does
not import the production process validator or `ProcessAdapter`. It uses independent
filesystem observation and direct ELF-header parsing.

Every future expected-valid executable must be classified
`VALID_NATIVE_EXECUTABLE` only after all of these checks pass:

1. Every path component and the terminal path exist.
2. No component is a symlink; the terminal object is a regular file.
3. The frozen expected-valid link policy is exactly one hard link.
4. Execute mode bits and effective execute access are present.
5. The first four bytes are `7f 45 4c 46`.
6. ELF class, byte order, type, and `e_machine` parse independently.
7. The object is `ET_EXEC` or PIE `ET_DYN` and `e_machine` matches the host.
8. Direct execution outside `ProcessAdapter` loads and behaves as declared.
9. Every required helper mode passes the direct smoke protocol.

Expected-invalid executables must independently match exactly one declared state:
`MISSING`, `SYMLINK`, `DIRECTORY`, `NON_EXECUTABLE`, or `WRAPPER_OR_SCRIPT`. An
expected-valid script is a hard freeze failure.

## Cwd gate

Every future cwd fixture must independently match `VALID_DIRECTORY`, `MISSING`,
`SYMLINK`, or `NON_DIRECTORY`. A case intended to exercise cwd validation must also have
a known compound authorization `ALLOW` and a `VALID_NATIVE_EXECUTABLE`, ensuring that
executable validation cannot mask cwd validation. The development adapter proof confirms
this structural reachability, but it is not used to classify the fixture.

## Seam gate

The scorer contract freezes each representable injection point and its prerequisites.

| Seam | Required prior reachability | Registered result |
|---|---|---|
| `PRE_EXECUTION_AUDIT` | compound ALLOW; both validations pass | fail closed; no primitive call |
| `SPAWN_FAILURE_CONFIRMED_NO_CHILD` | preexecution audit committed | spawn error; child false |
| `CAPTURE_FAILURE_AFTER_CHILD` | real child created and reaped | indeterminate; child true |
| `POST_COMPLETION_AUDIT_SUCCESS` | real zero-exit child completed | indeterminate; child true |
| `POST_COMPLETION_AUDIT_FAILURE` | real failure-semantic child completed | indeterminate; child true |

`PROC-ADAPTER@1` emits no audit event between synchronous child creation and completion.
Therefore a distinct `POST_SPAWN_AUDIT` seam is not representable and is prohibited in
the held-out corpus. This is explicit rather than simulated by a scorer-only label.

## Route gate

`ADAPTER` and `DIRECT_CONTROL` are machine-readable route values. `ADAPTER` dispatches
through the generic `ProcessAdapter` path. `DIRECT_CONTROL` dispatches through the
independent direct runner, which checks the executable and cwd oracle and invokes the
explicit native binary with `shell=False`. Development proof monkeypatching makes any
accidental `ProcessAdapter.execute` call fail during a direct control.

## Corpus freeze consequence

Future corpus authors must attach an oracle record to every fixture instance before
freeze. Any state mismatch, incompatible architecture/loader, failed smoke behavior,
unreachable declared seam, or scorer-only route assumption stops corpus freeze. The
oracle may establish reachability, never the expected adapter prediction.
