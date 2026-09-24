# EXP-013 Counterfactual-Pair Audit

Analysis ID: `EXP-013-ANALYSIS-001`  
Corpus: `EXP-013-CORPUS@1`  
Frozen run: `EXP-013-RUN-001`

## Audit method

All 40 pairs were reconstructed from frozen `runs.jsonl` and checked against the frozen
pair documentation. Each pair shares the exact `TaskContext`, exact
`B4HistoricalConstraints`, task category, context versions, normalized local evidence
multiset, and local reason-ID multiset. Every primary observation has
`CONTEXT_CONSISTENT` status. The `A/B` suffix is not a label convention: positive
membership changes by family.

The compact table uses these historical-variable codes:

- `RA`: aggregation-scope placement changes the accumulated role combination.
- `CSG`: a scope boundary changes cross-source grouping.
- `PT`: observation order changes the initial phase or directed transition.
- `PF`: collection moves from before to after finalization, re-entering a closed phase.
- `FB`: candidate order or the termination/restart episode boundary changes.
- `CP`: phase grouping changes to interleaving or re-entry.

`Shared static/local` records exact shared static context plus the number of matched
`CONTEXT_CONSISTENT` observations. `B2` values are positive/negative-member outcomes;
`M5.1-C` uses the same order. `B4` records positive/negative-member flags.

| Pair | Family | Shared static/local | Changed | B2 | M5.1-C | B4 P/N | B4 rules | Correct |
|---|---|---|---|---|---|---|---|---|
| `CF-013-001` | MS-A | exact; CC x4 | RA | N/N | none/none | yes/no | 001 | yes |
| `CF-013-002` | MS-A | exact; CC x5 | RA | N/N | none/none | yes/no | 001 | yes |
| `CF-013-003` | MS-A | exact; CC x5 | RA | N/N | none/none | yes/no | 001 | yes |
| `CF-013-004` | MS-A | exact; CC x6 | RA | N/N | none/none | yes/no | 001 | yes |
| `CF-013-005` | MS-A | exact; CC x6 | RA | N/N | none/none | yes/no | 001 | yes |
| `CF-013-006` | MS-A | exact; CC x7 | RA | N/N | none/none | yes/no | 001 | yes |
| `CF-013-007` | MS-A | exact; CC x7 | RA | N/N | none/none | yes/no | 001 | yes |
| `CF-013-008` | MS-B | exact; CC x5 | CSG | N/N | none/none | yes/no | 001 | yes |
| `CF-013-009` | MS-B | exact; CC x6 | CSG | N/N | none/none | yes/no | 001 | yes |
| `CF-013-010` | MS-B | exact; CC x6 | CSG | N/N | none/none | yes/no | 001 | yes |
| `CF-013-011` | MS-B | exact; CC x7 | CSG | N/N | none/none | yes/no | 001 | yes |
| `CF-013-012` | MS-B | exact; CC x7 | CSG | N/N | none/none | yes/no | 001 | yes |
| `CF-013-013` | MS-B | exact; CC x8 | CSG | N/N | none/none | yes/no | 001 | yes |
| `CF-013-014` | MS-B | exact; CC x8 | CSG | N/N | none/none | yes/no | 001 | yes |
| `CF-013-015` | MS-C | exact; CC x2 | PT | N/N | none/none | yes/no | 002 | yes |
| `CF-013-016` | MS-C | exact; CC x4 | PT | N/N | none/none | yes/no | 002 | yes |
| `CF-013-017` | MS-C | exact; CC x6 | PT | N/N | none/none | yes/no | 002 | yes |
| `CF-013-018` | MS-C | exact; CC x4 | PT | N/N | none/none | yes/no | 002 | yes |
| `CF-013-019` | MS-C | exact; CC x6 | PT | N/N | none/none | yes/no | 002 | yes |
| `CF-013-020` | MS-C | exact; CC x7 | PT | N/N | none/none | yes/no | 002 | yes |
| `CF-013-021` | MS-C | exact; CC x6 | PT | N/N | none/none | yes/no | 002 | yes |
| `CF-013-022` | MS-D | exact; CC x4 | PF | N/N | none/none | yes/no | 002+003 | yes |
| `CF-013-023` | MS-D | exact; CC x5 | PF | N/N | none/none | yes/no | 002+003 | yes |
| `CF-013-024` | MS-D | exact; CC x6 | PF | N/N | none/none | yes/no | 002+003 | yes |
| `CF-013-025` | MS-D | exact; CC x5 | PF | N/N | none/none | yes/no | 002+003 | yes |
| `CF-013-026` | MS-D | exact; CC x6 | PF | N/N | none/none | yes/no | 002+003 | yes |
| `CF-013-027` | MS-D | exact; CC x7 | PF | N/N | none/none | yes/no | 002+003 | yes |
| `CF-013-028` | MS-D | exact; CC x6 | PF | N/N | none/none | yes/no | 002+003 | yes |
| `CF-013-029` | MS-E | exact; CC x4 | FB | N/N | none/none | yes/no | 004 | yes |
| `CF-013-030` | MS-E | exact; CC x5 | FB | N/N | none/none | yes/no | 004 | yes |
| `CF-013-031` | MS-E | exact; CC x6 | FB | N/N | none/none | yes/no | 004 | yes |
| `CF-013-032` | MS-E | exact; CC x5 | FB | N/N | none/none | yes/no | 004 | yes |
| `CF-013-033` | MS-E | exact; CC x6 | FB | N/N | none/none | no/no | none | **no** |
| `CF-013-034` | MS-E | exact; CC x7 | FB | N/N | none/none | no/no | none | **no** |
| `CF-013-035` | MS-F | exact; CC x3 | CP | N/N | none/none | yes/no | 002 | yes |
| `CF-013-036` | MS-F | exact; CC x5 | CP | N/N | none/none | yes/no | 002 | yes |
| `CF-013-037` | MS-F | exact; CC x5 | CP | N/N | none/none | yes/no | 002 | yes |
| `CF-013-038` | MS-F | exact; CC x6 | CP | N/N | none/none | yes/no | 002 | yes |
| `CF-013-039` | MS-F | exact; CC x6 | CP | N/N | none/none | yes/no | 002 | yes |
| `CF-013-040` | MS-F | exact; CC x7 | CP | N/N | none/none | yes/no | 002 | yes |

Rule numbers abbreviate `B4TRJ-001` through `B4TRJ-004`. `N` is B2 `NEGATIVE`, and
`none` is M5.1-C `NO_FINDING`.

## Result

- B2: 0/40 pairs correct.
- M5.1-C: 0/40 pairs correct.
- B4: 38/40 pairs correct.
- B4 positive member flagged: 38/40.
- B4 negative member flagged: 0/40.

Every successful B4 pair changes a declared historical relationship while holding the
static declarations and local evidence fixed. The matched negative removes that
relationship and removes the finding, providing a direct within-pair history-necessity
check. This is stronger than interpreting B4 accuracy alone.

## Failed pairs

`CF-013-033` and `CF-013-034` are not false-positive tradeoffs: neither member is
flagged. Both permit restart after a declared termination. B4 resets the episode and
accepts the first candidate of the restarted episode without an allowed-start check.
The schema has no explicit episode-start relation, so the authored distinction—restart
at a candidate that cannot begin an episode—is not represented by the frozen rule
contract. See [EXP-013-FALSE-NEGATIVE-AUDIT.md](EXP-013-FALSE-NEGATIVE-AUDIT.md).

## Interpretation boundary

This audit supports discrimination of 38 specific synthetic counterfactual pairs. It
does not establish population-level accuracy, real-agent behavior, payload flow,
intervention efficacy, or independence from corpus-author knowledge of the public
protocol and schema.
