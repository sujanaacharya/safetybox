# Independence Record

## Mechanism achieved

The achieved mechanism is **D: protocol/schema-only authoring with an explicit
no-detector-source-access rule**.

This corpus was authored by the primary Codex research agent in one session. No second
researcher, independent scenario author, split-family author, or blinded human label
reviewer was available. The corpus is therefore **not independently authored** and has
not received independent label review.

## Material available to the author

The author used:

- frozen EXP-013 protocol v1 and B4 addendum v1;
- public TaskContext, ContextEvaluation, B2, and B4 history-context schema
  documentation;
- public constructor signatures for B4 history-schema values and the schema validation
  and TaskContext-reference helpers;
- frozen B2 implementation and interfaces for the explicitly permitted parity audit;
- EXP-009 and EXP-012 corpus identifiers and action traces solely for contamination and
  duplicate exclusions; and
- the EXP-013 capability-audit reference and development-artifact names solely as an
  exclusion boundary.

The B4 implementation files were technically accessible in the repository. Their file
names were visible during repository inventory, but the author did not open or inspect
the contents of `src/safetybox/b4/monitor.py` or `src/safetybox/b4/rules.py`. Access to
`src/safetybox/b4/models.py` was limited to runtime inspection of public schema
signatures; its source text was not opened. The frozen addendum's public semantic
definitions were available as required for protocol-conforming authoring.

## Prediction and review blinding

- B4 monitor instantiated during authoring/audits: **no**.
- B4 rules imported for prediction: **no**.
- B4 predictions, findings, or outputs viewed: **no**.
- M5.1-C executed on this corpus: **no**.
- EXP-013 final evaluation executed: **no**.
- Label review: same author plus deterministic schema, parity, duplicate, and leakage
  tests; no independent or blinded reviewer.

The same author necessarily knew the frozen family definitions and public context
schema. This is partial procedural independence from detector implementation, not
independence from the preregistered research design. That limitation must accompany any
future analysis of the corpus.
