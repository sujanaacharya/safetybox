# EXP-013 Corpus Freeze Checklist

Corpus: `EXP-013-CORPUS@1`
Decision: **READY FOR FREEZE — YES**

- [x] EXP-013 protocol v1 was frozen before corpus authoring
  (`632a4f82ab7c6487d82a166bca2e3354c7b9b763`).
- [x] B4 addendum v1 was frozen before B4
  (`37f614bad9f9cce652582cb720ffa7b2e65a7515`).
- [x] B4 implementation/schema/configuration was frozen before corpus authoring
  (`0b02b199e1f8e0f00aa87035bcbd4fced1aeda42`,
  `B4-BOUNDED-CONTEXT-TRAJECTORY@1`, `B4-CONFIG@1`,
  `B4-HISTORY-CONTEXT@1`).
- [x] B2 was frozen before corpus authoring
  (`3f8794e8b134b534365e0e26f48dd1886a50f662`,
  `B2-SINGLE-OBSERVATION@1`).
- [x] The achieved independence mechanism is documented truthfully as
  protocol/schema-only authoring with no B4 detector-source inspection; no independent
  authorship or review is claimed.
- [x] Labels, pair mapping, rationales, control axes, and versions are finalized in the
  ready-for-freeze candidate.
- [x] Exact, normalized renamed-template, repeated-rationale, and prior-corpus duplicate
  audits pass.
- [x] EXP-009, EXP-012, M5.1 development material, EXP-013 capability probes, B4
  development probes, and B4 unit-test traces are excluded by namespace and exact-trace
  checks; no development scenario ID or exact prior-corpus action/resource trace occurs.
- [x] Static single-feature separability audit passes: every preregistered feature has
  best deterministic value-lookup accuracy `0.500`; none perfectly separates labels.
- [x] All five preregistered obvious combination checks pass; none perfectly separates
  labels.
- [x] Frozen B2 parity passes for 40/40 primary pairs; failures: 0.
- [x] Matched-status audit passes for 40/40 primary pairs; every ordered status sequence
  is identical within its pair and every primary observation is `CONTEXT_CONSISTENT`.
- [x] Observation-local evidence and reason-ID multisets match within all 40 pairs.
- [x] History-necessity annotations cover all 80 primary scenarios and all six allowed
  dimensions/families.
- [x] Diversity review passes across 12 task categories, lengths 2 through 8, ordered,
  interleaved, repeated, phase, multi-source, post-finalization, fallback, role-group,
  and provenance structures.
- [x] No label-bearing identifier or description term occurs in runtime corpus inputs.
- [x] No `AGENT_SELF_REPORT` source occurs; all four represented trusted authorities
  occur under both primary labels.
- [x] B4 monitor/rules were not executed on the corpus; no B4 prediction, finding, or
  output was viewed.
- [x] M5.1-C was not executed on the corpus.
- [x] No EXP-013 final evaluation was run.
- [x] `results/EXP-013/` does not exist and no result artifact or TP/FP metric was
  created.
- [x] Corpus integrity tests pass: 8/8.
- [x] Repository runtime tests permitted by the no-detector-execution boundary pass:
  140/140. B4, M5.1-C, and the prior capability-audit test modules were deliberately
  excluded rather than violating the pre-freeze execution prohibition.
- [x] The same 140-test selection passes under `pytest --cov=safetybox`; total coverage
  is 83%, and the new corpus module is 100% covered.
- [x] `ruff check .`, `mypy src`, and `git diff --check` pass.
- [x] Frozen B4, B2, M5/M5.1, context, trajectory, EXP-013 protocol/addendum, and
  EXP-012 paths have no diff.
- [x] The work remains uncommitted, as required.

The initial worktree was clean at authoring base
`0b02b199e1f8e0f00aa87035bcbd4fced1aeda42`. The corpus becomes frozen only when these
ready-for-freeze files are committed without modification.
