# Failure Modes

| Failure | Potential consequence | Intended safe behavior | Evidence needed |
|---|---|---|---|
| Interception bypass | Unmediated privileged action | Deployment refuses privileged agent access outside adapters | Integration and adversarial bypass tests |
| Malformed/ambiguous request | Policy mismatch or argument confusion | Reject before execution; record validation reason | Parser/canonicalization tests |
| Policy engine error/timeout | Missing authorization | Privileged action fails closed; administrative availability behavior is explicitly configured | Fault-injection tests |
| Capability registry unavailable | Stale or unknown authority | Do not infer/grant capability; pause or deny | Recovery and partition tests |
| Event ordering failure | Incorrect trajectory/state | Stop affected session authorization, preserve evidence, require reconciliation | Concurrency and corruption tests |
| Audit sink unavailable | Unexplained execution | Apply a declared fail-safe mode; high-impact actions require durable decision record | Storage fault tests |
| Controller crash around execution | Duplicate or unknown side effect | Record indeterminate status; retry only with adapter idempotency guarantees | Crash-point tests |
| Adapter mismatch/TOCTOU | Authorized request differs from executed action | Bind authorization to canonical arguments/resource; deny on mismatch | End-to-end adapter tests |
| Approval replay or overbreadth | Unauthorized expansion | Bind approval to request, scope, approver, expiry, and nonce | Replay/scope tests |
| Policy/configuration tampering | Disabled protection | Authenticate configuration, separate write authority, alert and stop affected sessions | Tamper tests |
| Resource aliasing | Scope escape by symlink, DNS, path, or identifier | Resolve identity under adapter-specific rules before authorization/execution | Alias/rebinding tests |
| Telemetry overload | Dropped evidence or delayed control | Backpressure or containment; never silently drop enforcement-critical events | Load tests |
| False-positive trajectory signal | Benign task disruption | Explain, scope, and measure intervention; provide controlled approval/recovery | Benign benchmark trials |
| Compromised host/administrator | Total control-plane compromise | Outside core guarantee; use defense in depth and disclose boundary | Deployment threat analysis |

Safe behavior is operation-specific and must be configured explicitly. “Fail closed” must not itself create unexamined physical or availability hazards; deployment risk analysis may choose a safer paused state for a particular environment. No listed mitigation is implemented yet.
