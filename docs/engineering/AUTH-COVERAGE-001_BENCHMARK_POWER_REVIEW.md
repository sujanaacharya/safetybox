# AUTH-COVERAGE-001 benchmark power review

Coverage classifications describe frozen corpus support, not observed SafetyBox
performance. Final counts are machine-derived in the pre-run validity audit.

| Candidate claim | Coverage | Boundary |
|---|---|---|
| filesystem/process task binding | SUBSTANTIAL | logical task IDs, not authenticated identity |
| exact and subtree logical resource binding | SUBSTANTIAL | no physical resolution |
| distractor and zero-relevant rejection | SUBSTANTIAL | frozen capability model only |
| legitimate suspicious-looking preservation | SUBSTANTIAL | authorization, not execution |
| compound process exec/cwd authorization | SUBSTANTIAL | two registered components |
| cross-task authority reuse rejection | SUBSTANTIAL | no delegation implementation |
| cross-tool semantic consistency | MODERATE | structural equivalence only |
| authority explanation completeness | SUBSTANTIAL | mechanical fields, not prose quality |
| delegation and attenuation | CONTROL_ONLY | model-level precursor |
| network, MCP, database authority | CONTROL_ONLY | future schema only |
| real mediator/effect safety | CONTROL_ONLY | explicitly outside benchmark |

Even a perfect future result supports only conformance within the frozen model and corpus.
It cannot establish external validity, identity guarantees, physical execution safety,
delegation enforcement, or resistance to unmodeled adversaries.
