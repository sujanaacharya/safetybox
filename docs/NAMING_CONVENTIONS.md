# Naming Conventions

## Stable identifiers

| Entity | Format | Example |
|---|---|---|
| Research question | `RQ-NN` | `RQ-01` |
| Hypothesis | `H-NN` | `H-01` |
| Experiment | `EXP-NNN` | `EXP-001` |
| Benchmark | `BM-NNN` | `BM-001` |
| Threat scenario | `TS-NNN` | `TS-001` |
| Architecture decision | `ADR-NNN` | `ADR-001` |
| Requirement | `REQ-NNN` | `REQ-001` |
| Safety invariant | `INV-NNN` | `INV-001` |
| Policy | `POL-NNN` | `POL-001` |
| Candidate claim | `CL-NNN` | `CL-001` |

Numbers are zero-padded, allocated monotonically within each namespace, never recycled, and retained after retirement. IDs identify records, not filesystem order.

## Files and directories

- Governance and canonical prose filenames use uppercase snake case: `TASK_CONTRACT.md`.
- ADR filenames use `ADR-NNN-short-kebab-title.md`.
- Experiment directories use `EXP-NNN-short-kebab-slug`; benchmarks use `BM-NNN-short-kebab-slug`.
- Python modules and symbols follow standard Python conventions: `snake_case` modules/functions and `PascalCase` classes.
- Configuration and schema names include an explicit version when compatibility matters.

## Runtime names

Canonical event types, enforcement outcomes, and trust states use uppercase snake case. Field names use lowercase snake case. Tool and capability action names use dotted lower-case namespaces such as `filesystem.read` and `network.connect`.
