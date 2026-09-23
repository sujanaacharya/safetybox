# Reproducibility

## Reproduction target

A qualified independent researcher should be able to reconstruct the environment, execute the registered protocol, validate artifact integrity, and obtain results within declared tolerances. Bitwise equality may be feasible for deterministic policy evaluation but not for all model/provider interactions.

## Required artifacts

- exact Git SHA and SafetyBox version;
- experiment registration and metadata conforming to the versioned schema;
- task contract, policy set, benchmark/scenario, and adapter versions/hashes;
- Python, OS, dependency lock, hardware, locale/timezone, and relevant environment details;
- model/provider identifiers, snapshot when known, decoding settings, seed availability, and dates;
- execution commands, trial ordering, timeouts, retry rules, and stopping criteria;
- raw event/audit references, result manifest, analysis code/version, and checksums;
- exclusions, protocol deviations, provider incidents, and nondeterminism notes.

Secrets are referenced by variable name or credential class, never captured. Sensitive or non-redistributable data require a documented lawful retrieval/substitution path.

## Determinism tiers

1. **Core replay:** identical normalized inputs/state/version should reproduce the exact decision tuple.
2. **Harness replay:** local scenarios should reproduce within declared system-performance tolerances.
3. **Model-assisted replay:** stochastic or externally versioned models are repeated and reported distributionally; unavailable snapshots are a limitation.

## M4 simulation replay

The M4 scenario runner creates fresh in-memory policy, monitor, audit, tool, and world objects for every run. Equivalent runs should match semantic step outcomes (decision, rule ID, execution flag, logical effect), world snapshots, and ordered event types. M3 event UUIDs and UTC timestamps intentionally remain observational nondeterministic metadata and are excluded from equality checks.

## Artifact lifecycle

Draft outputs remain clearly marked and may be regenerated. Finalization validates required metadata, freezes the manifest, computes checksums, and marks result files immutable under governance. Corrections add a successor artifact and explanation without rewriting the original. Large files use durable external storage with content-addressed manifests.

## Independent validation

Before M12, perform a clean-environment run using only published instructions, verify every checksum, compare registered and executed protocols, and record discrepancies. A failed reproduction is reported as evidence, not concealed through undocumented manual repair.
