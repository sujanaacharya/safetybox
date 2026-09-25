# SafetyBox Research Dependency Graph

**Graph identity:** `SAFETYBOX-RESEARCH-DAG@1`

**Status:** program-order specification; arrows mean “must mature before the downstream
claim,” not necessarily that all work must be serial.

## DAG

```text
AUTH-COVERAGE-002 runner + exposure ledger
        |
        v
AUTH-COVERAGE-002 corpus -> one-shot authorization result ----+
                                                            |
EXP-016 Protocol@2 -> corpus -> native-child result ----------+-->
                                                            |   UNAUTHORIZED-EFFECT-001
filesystem evidence / EXP-014 -------------------------------+             |
                                                                          v
AUTHORITY-MODEL-V2 specification -> delegation/attenuation --------> provenance-rich
            |                         / expiry / revocation          effect program
            |                                                            |
            +----------------------> inter-agent scenarios <--------------+

network mediator ------------------------------+
MCP mediator + server identity ----------------+--> OWASP-AGENTIC-BENCH-001
UNAUTHORIZED-EFFECT-001 -----------------------+
AUTHORITY-MODEL-V2 / delegation ---------------+

OWASP-AGENTIC-BENCH-001 ----+
UNAUTHORIZED-EFFECT-001 ----+--> real-agent evaluation --> external packs/red team
network + MCP evidence ------+
```

## Dependency register

| Node | Hard prerequisites | Can run in parallel with | Unlocks |
|---|---|---|---|
| `AUTH-COVERAGE-002` runner/ledger | frozen runner and ledger specs | EXP-016 corpus work; Authority V2 specification | safe corpus serialization and exposure-accounted execution |
| `AUTH-COVERAGE-002` corpus/result | runner/ledger development proof and independent freeze audit | EXP-016 | defensible task-scoped authorization evidence |
| EXP-016 result | Protocol@2, native fixture, independently frozen corpus | AUTH-COVERAGE-002 | nonvacuous process-mediator evidence |
| `UNAUTHORIZED-EFFECT-001` | AUTH-COVERAGE-002 result, EXP-016 result, EXP-014 bounds, effect/provenance spec | Authority V2 specification | first direct north-star effect claim |
| `AUTHORITY-MODEL-V2` | formal semantics and independent subset/lifecycle model | authorization/process branches | implementation-ready delegation and lifecycle research |
| delegation/attenuation/revocation | Authority V2 freeze | network/MCP mediator design | ASI03/07/08 scenario credibility |
| network mediator | route inventory, canonical resource and effect oracle | MCP/authority work | network effects and broader OWASP benchmark |
| MCP mediator | server/tool identity, nested-effect/provenance semantics | network work | MCP/inter-agent/tool-supply scenarios |
| `OWASP-AGENTIC-BENCH-001` | named mediator evidence plus applicable authority/delegation controls | real-agent harness design | taxonomy-mapped containment evidence |
| real-agent evaluation | stable effect harness, route coverage, agent adapter, applicable OWASP scenarios | external pack planning | utility and recovery evidence |
| external packs/red team | frozen public interfaces/protocols and reproducible artifacts | none for final claim review | Level 5 evidence and missing-route discovery |

## Fastest scientifically valid path

Two prerequisite branches should advance independently:

1. make `AUTH-COVERAGE-002` execution scientifically safe, then create and run the new
   corpus; and
2. finish EXP-016's already-frozen native-child program.

They converge at `UNAUTHORIZED-EFFECT-001`, which is the first experiment capable of
testing the north star with both a validated decision path and nonvacuous real effects.
Building network/MCP breadth or a large OWASP suite before this convergence would produce
more mappings without resolving the central causal measurement.

## Milestone order

The preferred five milestones are retained with one refinement: M1 and M2 are parallel
prerequisite branches, not evidence that one validates the other.

| Order | Milestone | Exit condition |
|---|---|---|
| M1 | `AUTH-COVERAGE-002` | one-shot blinded authorization result with zero prior held-out execution and full reconstructable raw evidence |
| M2 | EXP-016 | native direct-child held-out execution reaches required lifecycle branches and benign completions |
| M3 | `UNAUTHORIZED-EFFECT-001` | separate authorization, forwarding, bypass, real-effect, attribution, and utility results for filesystem + process |
| M4 | `AUTHORITY-MODEL-V2` | frozen formal semantics plus verification plan for delegation, attenuation, expiry, revocation, provenance, and approval |
| M5 | `OWASP-AGENTIC-BENCH-001` | preregistered scenarios only for mapped subclaims with adequate control and mediator maturity |

M4 specification work may begin earlier, but implementation/evaluation must not displace
the M1–M3 path to direct effect evidence.
