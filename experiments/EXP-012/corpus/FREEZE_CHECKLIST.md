# EXP-012-CORPUS@1 freeze checklist

- [x] EXP-012 protocol was frozen before corpus authoring.
- [x] M5 was frozen before corpus authoring.
- [x] M5.1-A, M5.1-B, and M5.1-C were frozen before corpus authoring.
- [x] Frozen detector and context source directories were clean at authoring start.
- [x] Neither trajectory monitor was instantiated or run on the new corpus during authoring.
- [x] No detector prediction or result was inspected while assigning labels.
- [x] Labels and detector-independent rationales are finalized.
- [x] Missing-context controls are separate from primary denominators.
- [x] Context provenance uses only TASK_CONTRACT, SYSTEM_POLICY, RESOURCE_REGISTRY, and TOOL_ADAPTER.
- [x] Duplicate and renamed-duplicate review is complete.
- [x] Diversity and concentration review is complete.
- [x] All 28 contrast pairs passed the four-point quality review.
- [x] EXP-009 and M5.1 development scenarios are excluded.
- [x] Prohibited label-bearing terms are absent from detector-facing identifiers and descriptions.
- [x] Structural and action-policy validation passed without trajectory-monitor execution on corpus inputs.
- [x] Corpus is ready to freeze in the commit containing these files.
- [x] EXP-012 evaluation has not been run.
- [x] No EXP-012 result directory or result file was created.

The commit containing this checklist supplies the corpus-freeze SHA. The manifest intentionally leaves that future SHA as `TO_BE_RECORDED_BY_FREEZE_COMMIT` because this task does not commit.

