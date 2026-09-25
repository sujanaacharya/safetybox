# EXP-015 Adversarial Validity Audit

**Analysis ID:** `EXP-015-ANALYSIS-001`

**Canonical synthesis:**
[EXP-015 Adversarial Post-Run Analysis](../experiments/EXP-015-ANALYSIS.md)

**Raw-result freeze:** `65d047de0fe3b484eaed64bd2adc8562a5835eea`

This engineering record captures the frozen-source findings behind the canonical claim
synthesis. It is not a new score and does not mutate EXP-015 artifacts.

## Freeze verification

- Pre-analysis `HEAD` was the raw freeze and the worktree was clean.
- The protocol, implementation, schema/materializer, and Corpus@2 commit objects exist
  at the identities recorded in `run_metadata.json`.
- `results/EXP-015/SHA256SUMS` passed, including frozen `runs.jsonl` digest
  `6e2d27f789595e6df83742c07866ca60c2b21c64d9738c21943d160ca036f2d8`.
- Both `results/EXP-014/SHA256SUMS` and
  `results/EXP-014/ANALYSIS_SHA256SUMS` passed.
- Post-documentation verification must repeat these checks and show no diff under
  `results/EXP-015/`.

## Frozen-source causal chain

1. The protocol's `executable_canonicalization.post_allow_validation` accepts a
   controlled native executable and rejects a shebang or wrapper.
2. `ProcessTargetValidator.validate_executable` reads the first four bytes and rejects
   anything other than ELF magic, including `#!`.
3. Corpus@2 represents intended-valid helpers as `REGULAR_EXECUTABLE`.
4. `exp015_corpus2_schema_v2._helper_program` produces a Python shebang program.
5. `materialize` writes that text at mode `0755`.
6. Every authorization-positive intended-valid helper therefore reaches authorization,
   fails executable format validation, and never reaches cwd validation or spawn.

Classification: `CORPUS_FIXTURE_DESIGN_FAILURE`. The validation rule behaved as frozen.

## Case-level reassessment registry

### Registered hard benign

| Adversarial class | IDs |
|---|---|
| `STRONG_HARD_BENIGN` | `C2-001`–`013`, `C2-020`, `C2-021`, `C2-030`–`034`, `C2-039` |
| `MODERATE_HARD_BENIGN` | `C2-014`, `C2-016`, `C2-018`, `C2-019`, `C2-022`–`026`, `C2-028`, `C2-029`, `C2-035`, `C2-037`, `C2-040` |
| `EDGE_ONLY` | `C2-015`, `C2-017`, `C2-027`, `C2-036`, `C2-038` |

Counts: 21 strong, 14 moderate, 5 edge-only. This registry is analytical and does not
replace frozen labels.

### Registered hard unauthorized

| Family | IDs | Close-boundary count |
|---|---|---:|
| Task binding | `C2-061`–`072` | 12 |
| Exec/cwd capability mismatch | `C2-073`–`088` | 16 |
| Exec/cwd requested-resource near mismatch | `C2-089`–`096` | 8 |
| Compound single-component mismatch | `C2-098`, `099`, `102`, `103` | 4 |
| Compound dual mismatch | `C2-100`, `104` | 0 |
| Missing/zero-relevant family | `C2-105`–`112` | 0 |

Conservative close-boundary total: 40/50.

### Pair quality

The 12 task-binding pairs keep all inspected non-target runtime and authority fields
matched. The remaining 24 change one authority dimension but do not preserve `argv`.
The corpus builder accesses `scenarios[pos - 1]` even though the first 12 positive cases
were interleaved with their task-mismatch twins. Resource pairs also change the fixture
that follows the requested resource, and some helper/validation properties differ.

Post-run quality: 12 `VALID_STRONG`, 24 `MODERATE`, 0 `WEAK`. Registered decision
correctness remains 36/36.

## Harness findings

| Finding | Frozen evidence | Disposition |
|---|---|---|
| Direct controls absent | Manifest IDs `C2-055`–`057`; all runtime routes `ADAPTER` | Corpus route authoring error; 0/3 direct controls |
| Distractor denominator mismatch | 24 `DISTRACTOR` tags; conceptual audit also discusses 18 separately tagged zero-relevant cases | Claim 24/24 plus separate 18/18; do not reconstruct `/34` |
| Edge labels not recognized | 30 labels use combined `EDGE_CASE`; scorer seeks two other names | Preserve zero-denominator raw rows; do not infer registered split |
| Requirement mappings absent | No label `requirement_coverage` | REQ-033–062 `NOT_EVALUATED` |
| Threat mappings absent | No label `threat_coverage` | No threat-level empirical result |
| Repeat normalization incomplete | Temp-root paths remain in compared audit/authorization resources | Official 0/6, confounded; no replacement metric |
| Terminal defaults inconsistent | Denied labels default to `EXIT_0`; validation label/runtime tokens differ | Official 0/120 retained and interpreted as a major harness/outcome failure |
| Cwd checks masked | Expected-valid executable is a script | Physical cwd validation never reached |

## Immutability boundary

The analysis may classify or bound evidence, but it must not:

- edit result, corpus, protocol, runner, scorer, or implementation artifacts;
- recompute an official score;
- add post-hoc family, requirement, or threat labels;
- convert exploratory repeat stability into a PASS;
- substitute development tests for missing held-out execution; or
- describe EXP-016 as an EXP-015 rerun.

The commit containing this record is the analysis freeze. Its SHA is reported in the
final handoff rather than embedded recursively in the commit it identifies.
