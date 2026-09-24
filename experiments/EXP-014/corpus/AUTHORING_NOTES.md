# EXP-014 Corpus Authoring Notes

## Independence mechanism

The mechanism is protocol/design-only authorship after the adapter freeze. The authoring
base was clean and exactly
`b49a5cd0ff28a38eb8314291f51c106d2df9bd7c`. The permitted source surface was:

- the frozen EXP-014 protocol and experiment document;
- `REAL-FILESYSTEM-MEDIATION-REQUIREMENTS@1`;
- the frozen architecture, ADR-006, safety invariants, and real-filesystem threat model;
- the adapter development-validation contamination record and pre-corpus freeze audit;
- public `FilesystemRequest`, result taxonomy, exported filesystem API names,
  `TaskContract`, and `Capability` schema/component-scope declarations solely for
  serialization and policy-contract compatibility; and
- the EXP-013 corpus loader/tests solely for repository corpus packaging conventions.

No private adapter orchestration, canonicalizer helper, target-validation helper, primitive
branch, error mapping, or corpus prediction was inspected to construct cases. This is not
claimed to be blinded independent authorship: the author knew the public frozen design and
the named classes of contaminated development cases. The protection is temporal freeze,
source-surface restriction, explicit contamination exclusion, and one-shot evaluation.
The development test source was later parsed mechanically for operation/path/destination
duplicate auditing; this was contamination analysis, not observation of adapter outputs.

## Scenario and label model

One scenario/session is one primary example. Events, primitive calls, audit records, and
rename subdecisions are evidence within that example and never inflate the denominator.
Each scenario has one terminal classification. The exact frozen result category is stored
separately when applicable: `ALLOW`, `DENY`, `FAIL_CLOSED`, `TOOL_ERROR`, or
`FAIL_INDETERMINATE`. Post-allow safety rejection additionally expects
`TARGET_VALIDATION_REJECT`. Direct routes have no adapter result category.

`scenarios.yaml` contains only materialization, dependency, contract, and request data.
`labels.yaml` contains all expected outcomes and author reasoning. The typed runtime model
has no field for label, family, pair, rationale, hard-negative status, or expected outcome.

## Size discipline and hard negatives

The 96 cases were retained because each adds an operation, boundary, counterfactual,
failure mode, nondisclosure target, requirement/threat mapping, or hard negative. No case
was added solely to raise N.

A hard negative is a legitimate case likely to trigger an over-aggressive blocker: dotted
names, NFD request spelling mapping to an NFC fixture, repeated separators, in-root
dot-dot cancellation, boundary-adjacent subtree names, authorized two-endpoint rename,
ordinary files/directories matched against link fixtures, and valid missing create/mkdir
leaves. The corpus marks 23 such cases; it does not mark every allowed request.

## Counterfactual pair quality

There are 48 complete, unique pairs:

- 45 strong pairs change one intended semantic variable, such as capability relationship,
  task binding, component boundary, terminal/ancestor object type, link count, target
  existence/type, audit behavior, or primitive failure behavior.
- `CF-014-047` is moderate: the source remains denied while destination authority changes,
  so the terminal label is unchanged even though the second rename subdecision differs.
- `CF-014-046` is a weak control pair because it contrasts two direct APIs rather than an
  allowed/blocked adapter counterfactual.
- `CF-014-048` is weak: it combines two hostile rename endpoint patterns to cover a host
  absolute source without displacing the stronger rename pairs.

Operation alone, filename keywords, path depth, and fixture count do not separate the
terminal taxonomy. Allowed and denied pairs intentionally reuse similarly shaped names;
neither `private`, `public`, nor attack-like tokens serve as label conventions.

## Ambiguity decisions

- TOCTOU/symlink-swap races are excluded and reported `NOT_EVALUATED`, because the frozen
  protocol begins at `NOT_SOLVED` and defines no race harness.
- Inherited-descriptor bypass is `NOT_EVALUATED`; no relevant platform fixture is supplied.
- Permission-like failure uses the existing primitive dependency boundary rather than host
  permission bits, which are unreliable under process-owned temporary roots.
- Symlink creation followed by access is represented by deterministic fixture construction
  immediately before the single access request; no adapter symlink-creation operation is
  invented.
- Hard-link unavailability is an unsupported environment, not a successful rejection.
- No ambiguous cross-device, non-empty directory replacement, recursive operation,
  external filesystem, or platform-normalization case was guessed into the corpus.

## Adversarial manual review

The review checked for trivial label names, unique descriptive identifiers, repeated
templates, unrealistic paths, insufficient rename/nondisclosure/failure coverage, and
development resemblance. Numeric task descriptions were replaced with a constant neutral
description to remove an unnecessary identifier channel. A malformed draft hard-link
destination fixture and one absent hard-link target were corrected during schema-only
validation. A host-absolute rejection was added while retaining explicit root-escape
coverage. No adapter run informed these changes.

The final review found 16 rename cases, all nine operations in both successful and denied
forms, ten symlink rejection topologies, seven multi-link rejection operations, two direct
controls, and the full requested failure set. Prediction execution remained zero.
