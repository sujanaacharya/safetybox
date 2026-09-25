# SafetyBox Research Tracks

**Program identity:** `SAFETYBOX-RESEARCH-PROGRAM@1`

**Status:** governing roadmap; individual evidence remains in frozen artifacts and the
[claims ledger](CLAIMS_LEDGER.md)

## Program question

Can autonomous AI agents remain useful and capable while deterministic, task-scoped
authority prevents them from producing protected effects beyond explicitly delegated
authority?

The program deliberately separates authority decisions from mediator reachability and
observed effects. No aggregate “security accuracy” or program score is defined.

## Persistent tracks

| Track | Question | Primary outputs | Exit evidence / current state |
|---|---|---|---|
| A — Task-scoped deterministic authorization | Does policy distinguish valid authority by subject, task, action, resource, constraints, and validity? | formal model, counterfactual corpora, `AUTH-COVERAGE-002` | blinded Level 3 result required; AUTH-COVERAGE-001 is blocked |
| B — Effect mediation completeness | Which protected primitives are compulsorily mediated, and which bypass? | route inventories, filesystem/process/network/MCP mediators, coverage matrix | effect-class-specific Level 4 evidence; currently only bounded EXP-014 filesystem evidence |
| C — Authority provenance and attribution | Can every observed effect be reconstructed to valid authority and causal lineage? | immutable effect envelopes, replay/reconstruction, durable audit | current M3/EXP-014 evidence is bounded and non-durable |
| D — AI-to-authority compilation | Can probabilistic task interpretation be compiled into deterministic least-authority proposals safely? | proposal schema, deterministic compiler/verifier, abstention/approval study | architecture only; AI never becomes an issuer |
| E — Trajectory/context semantics | Can history improve analysis or safely reduce authority without granting it? | B4/context benchmarks, restriction experiments | Level 3 bounded observational evidence; no expansion path allowed |
| F — Delegation, attenuation, revocation | Can authority move across agents without amplification and stop predictably? | Authority V2 semantics, signed lineage, lifecycle tests | specification first; implementation future |
| G — OWASP agentic control validation | Which unauthorized-effect subproperties of current OWASP threats receive deterministic value? | evidence-dimensional mappings and `OWASP-AGENTIC-BENCH-001` | mapping is Level 0 unless a named control/evidence artifact raises a dimension |
| H — Real-agent evaluation | Does containment preserve completion under actual agent trajectories? | provider-neutral harness, task/attempt/effect/approval/recovery measures | no real-agent evidence |
| I — External benchmark/red-team evaluation | Do claims survive independent scenarios, route discovery, and replication? | external packs, audit reports, design-partner evidence | no Level 5 evidence |

## Cross-track research questions

- **Authorization correctness:** does a deterministic decision match independently
  specified valid authority, including compounds and ambiguity?
- **Mediation completeness:** can every in-scope protected effect occur only through the
  registered mediator, including aliases and failure paths?
- **Effect correctness:** did the requested, authorized effect—and no substituted
  effect—actually occur?
- **Task isolation:** can an authority object, cached result, or session state cross a task
  boundary?
- **Authority provenance:** who issued authority, through which delegation or approval,
  and can it be reconstructed from an effect?
- **Delegation and attenuation:** is every child authority a subset of its parent across
  task, action, resource, time, use, and destination dimensions?
- **Revocation and expiry:** when do new and in-flight operations cease to be valid?
- **AI/context non-authority:** can any model output, prompt, memory, or trajectory state
  create or expand authority?
- **Trajectory semantics:** can history flag or reduce risk without becoming an
  unreviewed authority source?
- **Real-agent utility:** what completion, false-deny, approval, recovery, and latency cost
  accompanies containment?

## Top-level metric contract

| Metric | Meaning | Required stratification |
|---|---|---|
| `FALSE_ALLOW_RATE` | authority-negative requests allowed | tool/effect class, denial cause, task/action/resource/identity dimension |
| `FALSE_DENY_RATE` | authority-positive requests denied | tool/effect class, benign family, failure reason |
| `UNAUTHORIZED_EFFECT_RATE` | unauthorized opportunities producing prohibited effects | effect class, mediator route, bypass class |
| `MEDIATION_BYPASS_RATE` | exercised effect routes escaping required mediation | route and primitive |
| `BENIGN_AUTHORIZATION_PRESERVATION` | benign authority-positive opportunities still authorized | family and component |
| `BENIGN_COMPLETION_RATE` | benign trials meeting external success criteria | task, model/agent, intervention class |
| `TASK_BINDING_ACCURACY` | task-binding cases decided correctly | same-task/cross-task and identity state |
| `CROSS_TASK_REUSE_RATE` | cross-task reuse attempts accepted or producing effects | decision and effect separately |
| `AUTHORITY_AMPLIFICATION_VIOLATIONS` | child/derived authority objects not subsets of valid parents | violated subset dimension |
| `PAIR_ACCURACY` | counterfactual pairs with both outcomes correct | pair strength and changed dimension |
| `COMPOUND_AUTHORIZATION_ACCURACY` | compound requests with all component/final decisions correct | AA/AD/DA/DD and atomicity policy |
| `EFFECT_ATTRIBUTION_COMPLETENESS` | observed effects with complete valid provenance | required field and effect class |
| `MEDIATION_COVERAGE` | evidence-qualified mediated primitives over declared known primitives | surface, environment, evidence level |
| `APPROVAL_ESCALATION_RATE` | future: eligible trials generating approval requests | benign/adversarial, authority delta |
| `ABSTENTION_RATE` | future: compiler/analyzer declines to propose a definitive result | cause and ground-truth stratum |

No weighted aggregate is permitted. Every report includes counts, denominators,
uncertainty, exclusions, evidence level, and separate authorization, mediation, effect,
attribution, and utility sections.

## Experiment state and retirement discipline

| Artifact | Program interpretation |
|---|---|
| EXP-014 | retained Level 4 real-tool evidence for named adapter-routed filesystem subproperties; no complete mediation claim |
| EXP-015 | retained Level 3 authorization/non-forwarding evidence; unsuccessful positive child execution prevents the broader process claim |
| EXP-016 Protocol@2 | active pre-corpus process-execution infrastructure; no held-out result |
| AUTH-COVERAGE-001 | permanently blocked as held-out evidence by reconstructable labels, prior production exposure, incomplete canonical runner/raw records, absent partial-exposure state, and incomplete executable scoring |
| AUTH-COVERAGE-002 | proposed clean replacement using a newly generated blinded corpus |

AUTH-COVERAGE-001's frozen methodology and adversarial failure analysis remain valuable
research evidence. It must never be cited as a valid held-out performance result.

## Session sequence by dependency

“Session” is an ordered research unit, not a time estimate.

1. Freeze `AUTH-COVERAGE-002` protocol, canonical raw-first runner contract, and reusable
   exposure ledger before corpus generation.
2. Independently author, seal, and audit the new DEV/VALIDATION/HELD_OUT corpus.
3. Execute the one-shot run; score only after raw sealing; conduct adversarial validity
   analysis and bounded claim review.
4. Complete EXP-016 corpus authorship/freeze, then its one-shot native-child run and
   validity analysis without modifying Protocol@2 artifacts.
5. Freeze `UNAUTHORIZED-EFFECT-001` for filesystem plus process with independent effect
   oracles and route inventories.
6. Implement only the durable effect/provenance and harness support required by that
   frozen protocol; then author its corpus.
7. Execute and analyze `UNAUTHORIZED-EFFECT-001` with authorization, bypass, effect,
   attribution, and utility results kept separate.
8. Freeze Authority Model V2 semantics and formal subset/lifecycle verification before
   delegation implementation.
9. Specify and build network mediation, then MCP mediation/identity and nested-effect
   attribution; expand the coverage matrix after evidence, not before.
10. Freeze and execute `OWASP-AGENTIC-BENCH-001` over only control paths with adequate
    mediator evidence.
11. Add a provider-neutral real-agent evaluation, then independent external packs and
    red-team route discovery.

## Stop conditions

Stop, preserve evidence, and issue a disposition when a guarantee is not deterministically
enforceable; labels can be inferred; held-out predictions are exposed; authorization and
effects are combined without evidence; OWASP wording exceeds a named dimension; AI is
treated as an authority source; formal subset/lifecycle semantics are ambiguous; or
unknown mediation coverage is presented as a global security claim.

## Quality gate for a major claim

Each major claim requires: a precise specification; named implementation; development
tests; preregistered held-out benchmark; independent adversarial audit; real-system
evidence where the claim concerns real effects; explicit limitations; reproducible frozen
artifacts; a claims-ledger entry; and evidence level per claim dimension. Missing items
must remain visible rather than averaged away.
