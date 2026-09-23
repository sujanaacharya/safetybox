# Experiment Metadata Schema

This is a conceptual design, not an implemented schema. The first machine-readable version requires review and explicit schema versioning.

## Required metadata

| Field | Type/constraint | Meaning |
|---|---|---|
| `experiment_id` | `EXP-NNN` | Registered experiment identity. |
| `title` | non-empty string | Human-readable title. |
| `research_question` | list of `RQ-NN` | Questions addressed. |
| `hypotheses` | list of `H-NN` | Hypotheses tested; may be empty for descriptive studies. |
| `date` | ISO 8601 timestamp/date | Execution start and, in the final schema, end. |
| `git_sha` | full commit hash | Exact source revision. |
| `safetybox_version` | version string | Package/artifact version. |
| `python_version` | exact version | Interpreter used. |
| `os` | structured name/version/architecture | Execution platform. |
| `agent_framework` | name or `none` | Framework under test. |
| `agent_framework_version` | exact version or `not_applicable` | Framework version. |
| `model_provider` | name or `none` | Provider used. |
| `model` | stable model identifier or `none` | Model selection. |
| `model_version_if_known` | identifier or `unknown` | Provider-reported version/snapshot. |
| `temperature` | number or `not_applicable` | Sampling setting. |
| `seed_if_available` | value or `unavailable` | Seed and provider support. |
| `task_contract` | immutable path/hash/version | Exact contract. |
| `policy_set` | immutable path/hash/version | Exact policies. |
| `threat_scenario` | list of `TS-NNN` or empty | Scenario mapping. |
| `trial_number` | positive integer | Unique trial within condition. |
| `results` | structured metrics/artifact references | Observations, not conclusions. |
| `notes` | string | Deviations, incidents, or context. |

## Additional fields expected in version 1

`schema_version`, `registration_hash`, benchmark ID/version, baseline/condition, adapter versions, dependency/environment lock hash, hardware/runtime limits, start/end timestamps, randomization block, raw event-log reference/hash, stdout/stderr references, result status, exclusion flag/reason, analysis version, and artifact checksums.

## Validation rules

- IDs must resolve to repository records and use canonical formats.
- Configuration references must be immutable or content-addressed.
- `unknown`, `unavailable`, and `not_applicable` are distinct; required values cannot be empty.
- Secrets and raw sensitive payloads must not appear in metadata.
- A final result set cannot mix incompatible schema versions without a documented migration.
- Finalization records a manifest checksum and makes contained result files immutable by governance.

The schema should support JSON or YAML serialization later, but format selection is deferred.
