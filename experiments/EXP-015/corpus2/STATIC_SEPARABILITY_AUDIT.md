# Static separability audit

## Superficial label leakage

Scenario IDs, session IDs, actors, and opaque task-ID forms are shared across
classes. Capability count is deliberately non-diagnostic: positives include
distractors and negatives include zero, one, and many plausible capabilities.
No runtime field names an outcome, difficulty, pair, or requirement.

## Authorization semantic derivability

Task equality and exact action/resource grants correctly derive authority. This
is required semantic derivability, not leakage.

## Difficulty and terminal separability

Difficulty is scoring-only. Fixture kind, helper recipe, and fault stage can
identify conformance families; they are explicitly not claimed as authorization
difficulty evidence.
