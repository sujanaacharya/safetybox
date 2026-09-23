# Enforcement Controller

## Responsibility

The controller is the only logical component permitted to translate authorization results into external execution or containment. It receives a bound request, capability result, policy result, risk/trajectory signals, and approval state; applies deterministic precedence; commits the decision; and either invokes an adapter or prevents execution.

## Outcome application

- `ALLOW`: issue execution authorization bound to the exact normalized request.
- `DENY`: finalize without adapter invocation.
- `ALLOW_WITH_LIMITS`: apply and record a strictly narrower request, then authorize that exact form.
- `REQUIRE_APPROVAL`: place the request in a non-executing pending state; validate approver identity, scope, expiry, and request binding on response.
- `DEGRADE_CAPABILITIES`: atomically revoke/narrow capabilities and record the new snapshot before processing further requests.
- `PAUSE`: reject or queue new requests according to a defined bounded policy; no privileged action proceeds.
- `QUARANTINE`: isolate the session, revoke privileged capabilities, preserve evidence, and allow only explicitly safe administrative operations.
- `TERMINATE`: close the session and reject all later agent requests.

## Safety requirements

Decision persistence must precede side effects. Execution authorization must resist replay and TOCTOU substitution. Concurrent requests require serialization or transactional state snapshots. A crash after authorization but before/after execution must be distinguishable on recovery; “unknown execution status” cannot be treated as success or safely retried without adapter-specific idempotency.

Approvals do not override maximum privilege or terminal state. Advisory semantic signals may make an outcome stricter but cannot relax deterministic prohibitions.
