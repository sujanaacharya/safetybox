# AUTH-COVERAGE-002 raw schema

`AUTH-COVERAGE-002-RAW-SCHEMA@1` freezes compact UTF-8 canonical JSON: object keys sorted,
arrays retained in received order, no insignificant whitespace, and NaN/infinity rejected.

Every record contains schema/record/canonicalization versions; experiment, run, and opaque
scenario IDs; production Git SHA, source artifact checksums, policy version,
TaskContract/spec versions, runner checksum/version; tool class; contract task/description;
complete ordered capabilities with received index, action, resource/scope, task binding and
capability digest; complete request/session/task/actor/action/resource/arguments for every
ordered component; structured component and final decisions; matched capability, rule,
reason code/text, authority source/provenance; truthful error/call-began state; UTC start and
finish timestamps; monotonic sequence; and input, output, and whole-record digests.

Expected labels and all family/difficulty/pair/oracle/error/scoring metadata are rejected
recursively. `DECISION_UNKNOWN` represents a begun invocation with no valid decision; it is
never coerced to deny.

The independent parser rejects missing, unknown, duplicate, noncanonical, or corrupt
fields. Reconstruction uses only the persisted record to rebuild the `TaskContract`,
received capability tuple, primary `ActionRequest`, and compound components; its canonical
digest must equal the stored input digest. Synthetic reconstruction is 100%.

