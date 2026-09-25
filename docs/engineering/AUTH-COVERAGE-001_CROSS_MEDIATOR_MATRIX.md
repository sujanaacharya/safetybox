# AUTH-COVERAGE-001 cross-mediator matrix

Evidence maturity is tracked separately from implementation maturity. `FROZEN_BENCHMARK`
means authorization-only corpus evidence is prepared, not that a mediator executed.

| Authorization property | Filesystem | Process | Network | MCP | Database |
|---|---|---|---|---|---|
| task binding | frozen benchmark | frozen benchmark | schema future | schema future | schema future |
| exact resource binding | frozen benchmark | frozen benchmark | schema future | schema future | schema future |
| capability distractors | frozen benchmark | frozen benchmark | schema future | schema future | schema future |
| zero relevant authority | frozen benchmark | frozen benchmark | schema future | schema future | schema future |
| compound subdecisions | single component control | exec + cwd frozen | future | future | future |
| cross-task reuse | frozen benchmark | frozen benchmark | future | future | future |
| suspiciousness separation | operation data | argv data | future | future | future |
| physical mediation | out of scope | out of scope | out of scope | out of scope | out of scope |
| production implementation maturity | existing logical kernel | existing adapter authorization | not implemented | not implemented | not implemented |
| held-out execution evidence | not run | not run | none | none | none |
