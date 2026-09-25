# AUTH-COVERAGE-002 raw-first runner

`AUTH-COVERAGE-002-RUNNER@1` is implemented by
`src/safetybox/research/auth_coverage_runner.py`; the fresh-process entry point is
`scripts/run_auth_coverage_002.py`.

The wrapper constructs the ordinary `TaskContract` and invokes the public production
authorizer. It has no expected-label, oracle, metric, family, pair, or difficulty input.
The scenario ID is used for order/correlation only and is excluded from the production-
input digest. Tests rename it while holding the authorization input fixed and obtain the
same decision and input/output digests.

Runtime and corpus manifests bind exact split, corpus reference, frozen order, and every
canonical input digest. The runner refuses modified packages, implementation SHA/source
checksums, mixed raw provenance, unexpected order, duplicate tokens/scenarios, custom
held-out authorizer seams, an ordinary pytest process, a second held-out run ID, and any
prediction after complete or partial sealing.

The raw writer uses canonical one-record-per-line JSON. It writes, flushes, and fsyncs each
record before the completion event. Capability arrays are never sorted; object keys are
canonicalized, while received array order remains observable. Sequential execution is the
only supported policy.

Synthetic fault hooks cover before/after reservation, immediately before/after production,
serialization, raw write, before/after fsync, completion, sealing, and scoring. The hooks
model control-flow interruption; actual durability derives from the explicit filesystem
ordering and is separately checked by subprocess scoring, hash/tamper tests, and prefix-
anchor recovery. A fault before fsync cannot be claimed durable merely because buffered
bytes are visible in the injecting process.

