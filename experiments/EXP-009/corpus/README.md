# EXP-009 held-out corpus v1

## Purpose

EXP-009-CORPUS@1 is the first task-contextual, simulator-only held-out corpus for EXP-009. It was authored after the EXP-009 protocol freeze at 17e16d63d9bbf9b17b94d2b4ada7b81f27e3c6f6 and before any M5 retuning based on its outcomes.

## Representation and authoring rules

The simulator already uses immutable Python ThreatScenario instances, so definitions live in src/safetybox/experiments/exp009_corpus.py; this avoids a generic configuration system. manifest.yaml and labels.yaml are JSON-compatible YAML and can be safely read with a standard JSON parser. No YAML loader executes code and no real I/O, sensitive data, hosts, credentials, or databases are introduced.

Labels were assigned in this order: task context, behavioral rationale, ground-truth label, frozen definition, later evaluation. No trajectory monitor was instantiated for this corpus. labels.yaml is the canonical evaluation truth. Every scenario is version 1; a material change to sequence, objective, contract, label, resource scope, or expected family requires a new scenario version. Typographical documentation fixes are recorded but need not change version.

## Families

TRJ-001 cases concern contextual collection followed by egress. Positive cases have individually allowed actions but an outbound transfer unrelated to the task. Negatives include reporting/export hard negatives, reordered traces, missing stages, and window-edge workflows. TRJ-002 cases concern denied boundary exploration. Positives represent systematic exploration outside a project scope; hard negatives represent typos, documented fallback checks, optional files, and migration compatibility checks.

CP-001 through CP-010 are intentional contrast pairs: each pair has the same actions and resources but opposite labels because the task objective changes. This specifically tests whether sequence matching overgeneralizes.

## Development distinction and limitations

The development IDs TS-008, TS-009, BENIGN-001, and BENIGN-002 are excluded from scenario definitions and are not held-out evidence. This corpus was created after protocol freeze and before M5 retuning based on outcomes. Because the author works in the same development environment and may know M5 architecture from prior repository work, it is not a fully blinded external benchmark. The corpus is synthetic, uses logical resources, and cannot establish deployment generalization.

## Freeze process

The manifest is FROZEN. The corpus freeze is the Git commit containing these finalized files; no future commit SHA is claimed in advance. Before freeze, structural duplicate checks, contrast-pair review, manual label review, and action-level policy-baseline validation were completed. Detector evaluation, metrics, and any detector-informed label change are expressly deferred.

