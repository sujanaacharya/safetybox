# EXP-015-RUN-001 Raw Result

**Run ID:** `EXP-015-RUN-001`  
**Scope:** mechanical one-shot raw execution and scoring record only  
**Validity:** `VALID_RAW_EXECUTION_WITH_RETAINED_SCORING_HARNESS_LIMITATIONS`

This document does not perform adversarial claim synthesis, promote RTM status, or
change CL-011.

## Frozen identity

| Item | Value |
|---|---|
| Starting HEAD / pre-run disposition | `5b9d2e4c9b21729aa73af4b95972a15c17e3a8bc` |
| Protocol | `1b1d22eaded580e9b6f6311bf0e3a8145002e98d` |
| PROC-ADAPTER@1 implementation | `12c585a9830436d8a88d356cfecbdff132b55487` |
| Runtime schema/materializer v2 | `37368667c438ccbf6a84819ef355590450617d73` |
| Corpus@2 | `35dfbb095727f459277db8c7df58864f3be5e907` |
| Python / platform | `3.11.16`; Linux `6.8.0-138-generic` x86_64 |
| SafetyBox | `0.0.0` |

The initial worktree was clean, `results/EXP-015/` was absent, Corpus@2 checksums
passed, the fresh-process isolation gate passed, and every frozen-path diff was empty.
Immutable run metadata was persisted before prediction exposure.

## Execution chronology and isolation

One runner launch stopped in preflight because it incorrectly assumed numeric scenario
order. It executed zero canonical scenarios, made zero held-out `ProcessAdapter` calls,
and produced no prediction. This is preserved in `pre_exposure_attempts.jsonl`. Before
prediction exposure, that assertion alone was removed so the checksum-covered JSON list
itself supplied the frozen order; the new runner digest was recorded in immutable
metadata.

The exposed execution then processed all 120 scenarios once in the frozen list order and
executed exactly the six registered repeats. Each JSONL record was flushed and fsynced.
The execution process never opened `labels.json` or `pairs.json` and never imported
`safetybox.experiments.exp015_corpus2_scoring`. Module snapshots before scenario 1 and
after the 120th raw persistence are in `execution_state.json`.

The raw writer closed with 120 records. The canonical raw checksum was
`6e2d27f789595e6df83742c07866ca60c2b21c64d9738c21943d160ca036f2d8`.
Only then did a separate process load labels and pairs. The complete join, source
checksums, count, and timestamp are in `label_join_manifest.json`.

## Mechanical results

| Measure | Result |
|---|---:|
| Authority-positive | 60 |
| Authority-negative | 60 |
| True allow / false deny | 60 / 0 |
| True deny / false allow | 60 / 0 |
| False-allow / false-deny rate | 0/60 / 0/60 |
| Hard benign authorization | 40/40 |
| Hard unauthorized authorization | 50/50 |
| Strong pairs | 36/36 |
| Task binding | 12/12 pairs; 0 false allow; 0 false deny |
| Exec / cwd subdecisions | 120/120 / 120/120 |
| Expected and actual AA/AD/DA/DD | 60/20/20/20 |
| Zero-relevant capability | 18/18 |
| Denied-spawn prevention | 60/60 |
| Validation-case authorization / registered rejection | 16/16 / 16/16 |
| Execution/failure authorization / terminal semantics | 12/12 / 0/12 |
| Canonical lexical comparisons | 120/120 |
| Terminal accuracy | 0/120 |
| Registered repeats as frozen scorer compared them | 0/6 |
| Independent recomputation | MATCH for every section it recomputed |

Authorization truth was never rewritten by validation or terminal outcomes. Every
authority-positive regular helper was authorized and then rejected during executable
validation because the materializer emitted a shebang script and the frozen adapter
requires ELF. Therefore no child was spawned in any canonical scenario. Ordering, argv,
environment, output, timeout, signal, nonzero-exit, and post-spawn properties requiring
a child were not empirically demonstrated, even where the frozen scorer mechanically
rendered a zero numerator.

## Retained anomalies

1. Corpus@2 declares all 120 runtime routes as `ADAPTER`; the three manifest PMED
   controls (`C2-055` through `C2-057`) are not `DIRECT_CONTROL`. Zero direct controls
   executed, and the expected bypass criterion failed.
2. `REGULAR_EXECUTABLE` helpers materialize as shebang scripts, but PROC-ADAPTER@1
   accepts only native ELF. All 60 compound-ALLOW scenarios therefore stopped at
   executable validation.
3. The frozen scorer searched for `EDGE_BENIGN` and `EDGE_UNAUTHORIZED` difficulty
   names, while labels encode one `EDGE_CASE` class (30 total). Its two separate edge
   rows consequently have zero denominators and must not be mistaken for the registered
   20 benign / 10 unauthorized edge denominators. Overall authorization has zero errors.
4. The scorer recognized 24 `DISTRACTOR` tags rather than the preregistered 34-scenario
   family and did not construct the separately requested exact/no-exact split.
5. Labels contain no requirement or threat mapping fields, so the frozen scorer reports
   REQ-033--062 as `NOT_EVALUATED` and produces no machine threat rows.
6. Repeat comparison retained temporary-root resources in audit-event fields, producing
   0/6 even though these are ephemeral fixture paths. The scorer was not repaired or
   rerun after exposure.

These are disclosed scoring/corpus limitations, not grounds to rewrite raw evidence or
rerun the one-shot.

## Audit and boundaries

Raw field completeness was 120/120. Semantic reconstruction remains
`SCHEMA_COUPLED`. Audit truthfulness was 120/120 for the observations that occurred.
INV-020 is experiment-scoped empirically supported; INV-021 and INV-022 were not
evaluated because no child reached the primitive; INV-023 is only partially supported.

The evidence remains PMED-L1 only. Direct non-adapter invocation can bypass mediation.
Child filesystem syscalls are not FS-adapter mediated. Descendant, network, TOCTOU, and
authenticated session-to-contract confinement remain unestablished.

## Post-run validation

- Full pytest: 617 passed, with two lifecycle-only failures. One is the already known
  shared-process import-state assertion; the other is the fresh-process gate's frozen
  assertion that `results/EXP-015/` is absent. Neither test nor result was changed.
- Coverage with only those two lifecycle nodes deselected: 617 passed, 2 deselected,
  97% overall.
- Ruff: PASS.
- mypy `src`: PASS, 67 source files.
- `git diff --check`: PASS.
- Corpus@2, EXP-014 raw, and EXP-014 analysis checksum manifests: PASS.
- Protocol, adapter, schema/materializer, and Corpus@2 frozen-path diffs: empty.

## No-tuning confirmation

After the first held-out request reached `ProcessAdapter`, no adapter, authorization,
capability, TaskContract, ReferenceMonitor, schema, materializer, corpus, label, pair,
fixture, fault, canonicalization, runner, or scoring logic was changed. No scenario was
retried, substituted, skipped, or replaced. The scoring limitations above were retained
without repair.
