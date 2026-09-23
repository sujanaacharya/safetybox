# Task Contract

## Purpose and status

A `TaskContract` is the conceptual, versioned source of task-specific authority and constraints. It is subject to refinement and has no implemented schema in M0. Descriptive text informs policy but never grants capabilities by itself.

## Conceptual fields

| Field | Meaning |
|---|---|
| `task_id` | Stable identifier for this task instance. |
| `task_description` | Human-readable bounded purpose. |
| `allowed_goals` / `forbidden_goals` | Declared objectives and explicit exclusions. |
| `allowed_tools` / `forbidden_tools` | Candidate adapter/tool namespaces; resource authority is still required. |
| `allowed_resources` | Enumerated resource classes or identifiers. |
| `resource_scopes` | Path, domain, table, API, operation, row, or other boundaries. |
| `network_policy` | Default posture, destinations, methods, ports, transfer limits, and DNS/proxy rules. |
| `filesystem_policy` | Roots, read/write/execute distinctions, symlink behavior, and sensitive exclusions. |
| `shell_policy` | Executables, arguments, environment, working directory, time, and subprocess constraints. |
| `database_policy` | Connections, schemas/tables, read/write operations, row/field constraints, and query limits. |
| `maximum_privilege` | Non-expandable ceiling for this task. |
| `approval_requirements` | Actions and thresholds requiring external approval, plus approver scope. |
| `execution_limits` | Time, calls, bytes, concurrency, cost, and retry limits. |
| `data_sensitivity` | Classification and handling constraints. |
| `expected_behavior` | Testable action/sequence expectations; deviations are signals, not automatic proof of harm. |
| `termination_conditions` | Completion, limit, violation, timeout, or explicit stop conditions. |
| `metadata` | Schema version, issuer, issue time, hashes, labels, and provenance. |

Validation must reject ambiguous or conflicting mandatory fields. Defaults should deny undeclared privileged actions. Contract amendments require authorization, versioning, and audit; the agent cannot self-amend its contract.

## Example A: benign code-analysis agent

```yaml
task_description: Analyze a repository and report static findings
allowed_goals: [inspect source, parse AST, run approved static analysis]
allowed_tools: [filesystem.read, shell.execute]
resource_scopes:
  filesystem.read: /workspace/project/**
shell_policy:
  executables: [ruff, mypy]
forbidden_tools: [network.connect, database.query]
forbidden_resources: [~/.ssh/**, ~/.aws/**, /etc/shadow]
forbidden_goals: [transmit repository content, modify system files]
maximum_privilege: read-only repository plus enumerated analyzers
```

## Example B: file summarization agent

```yaml
task_description: Summarize documents in an assigned input directory
allowed_tools: [filesystem.read, filesystem.write]
resource_scopes:
  filesystem.read: /workspace/input/*.txt
  filesystem.write: /workspace/output/summary.md
network_policy: {default: deny}
filesystem_policy:
  deny_symlink_escape: true
  maximum_input_bytes: 50000000
data_sensitivity: confidential-local
termination_conditions: [summary_written, time_limit_reached]
```

Reading unrelated home files, overwriting inputs, or sending content to a network destination is outside this contract.

## Example C: database-reporting agent

```yaml
task_description: Generate a monthly aggregate sales report
allowed_tools: [database.query, filesystem.write]
database_policy:
  connection: reporting-replica
  operations: [select]
  tables: [analytics.monthly_sales]
  deny_columns: [customer_email, payment_token]
  row_scope: "month = declared_report_month"
resource_scopes:
  filesystem.write: /workspace/reports/monthly.csv
approval_requirements:
  - export_rows_over: 10000
execution_limits: {query_count: 20, wall_time_seconds: 600}
```

Writes to the database, alternate connections, sensitive columns, and unrelated months are excluded even though “database” is an allowed tool category.
