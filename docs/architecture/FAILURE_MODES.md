# Failure Modes

| Failure | Potential consequence | Intended safe behavior | Evidence needed |
|---|---|---|---|
| Interception bypass | Unmediated privileged action | Deployment refuses privileged agent access outside adapters | Integration and adversarial bypass tests |
| Malformed/ambiguous request | Policy mismatch or argument confusion | Reject before execution; record validation reason | Parser/canonicalization tests |
| Policy engine error/timeout | Missing authorization | Privileged action fails closed; administrative availability behavior is explicitly configured | Fault-injection tests |
| Capability registry unavailable | Stale or unknown authority | Do not infer/grant capability; pause or deny | Recovery and partition tests |
| Event ordering failure | Incorrect trajectory/state | M5 rejects duplicate/decreasing delivered sequence numbers without reordering; controller behavior remains future work | Ordering and corruption tests |
| Audit sink unavailable before tool execution | Unexplained execution | M3 raises `AuditFailure` and fails closed before protected-tool invocation | M3 fault-injection unit test |
| Terminal audit sink failure after tool invocation | Missing terminal evidence after a real side effect | M3 raises `AuditFailure`; it cannot undo or conclusively report the already-invoked action | M3 crash-point-style unit test |
| Controller crash around execution | Duplicate or unknown side effect | Record indeterminate status; retry only with adapter idempotency guarantees | Crash-point tests |
| Adapter mismatch/TOCTOU | Authorized request differs from executed action | Bind authorization to canonical arguments/resource; deny on mismatch | End-to-end adapter tests |
| Approval replay or overbreadth | Unauthorized expansion | Bind approval to request, scope, approver, expiry, and nonce | Replay/scope tests |
| Policy/configuration tampering | Disabled protection | Authenticate configuration, separate write authority, alert and stop affected sessions | Tamper tests |
| Resource aliasing | Scope escape by symlink, DNS, path, or identifier | Resolve identity under adapter-specific rules before authorization/execution | Alias/rebinding tests |
| Telemetry overload | Dropped evidence or delayed control | Backpressure or containment; never silently drop enforcement-critical events | Load tests |
| False-positive trajectory signal | Benign task disruption | Explain, scope, and measure intervention; provide controlled approval/recovery | Benign benchmark trials |
| Trajectory window truncation | A longer pattern is not observed or does not match | Retain the explicit configured bound and report the limitation; evaluate window size in later ablations | Boundary-window tests and registered ablation |
| Missing or incomplete task context | A contextual interpretation cannot be made | Emit deterministic `INSUFFICIENT_CONTEXT`; do not convert it to benign or suspicious | Missing-dimension and abstention tests |
| Incorrect trusted context | Behavior can appear consistent with a wrong declaration | Preserve declaration provenance and bound claims to consistency, not safety | Context review, provenance, and adversarial configuration tests |
| Coarse semantic roles | Distinct data or resources can be conflated | Preserve exact role evidence and report the abstraction limit | Role-granularity development studies |
| Absent runtime lineage | Ordered access and outbound action can be mistaken for proven transfer | Use conservative ordering language; never claim bytes or payloads flowed | Finding-wording and logical-lineage tests |
| Context configuration burden | Incomplete declarations cause excessive abstention | Version, validate, and measure abstentions without guessing intent | Configuration and coverage studies |
| Compromised host/administrator | Total control-plane compromise | Outside core guarantee; use defense in depth and disclose boundary | Deployment threat analysis |

Safe behavior is operation-specific and must be configured explicitly. “Fail closed” must not itself create unexamined physical or availability hazards; deployment risk analysis may choose a safer paused state for a particular environment. No listed mitigation is implemented yet.
