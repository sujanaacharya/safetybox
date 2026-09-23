# Threat Model

## Objective

The model identifies unsafe external effects SafetyBox may attempt to prevent or contain, the signals available before those effects, and conditions under which claims do not hold. It covers accidental, prompt-injected, compromised, and intentionally evasive agent behavior without assuming the model can report its intent reliably.

## System under analysis

The protected system includes an agent requesting privileged actions through the SafetyBox interception boundary. Contracts, capabilities, policies, controller state, approval decisions, tool adapters, event/audit paths, and the execution environment form the control surface. The [Assets](ASSETS.md), [Trust Boundaries](TRUST_BOUNDARIES.md), and [Attacker Models](ATTACKER_MODELS.md) are canonical.

## Security objectives

- Complete pre-execution mediation of privileged actions.
- Task- and resource-scoped least authority.
- Non-bypassable deterministic prohibitions.
- Timely containment when defined behavioral evidence accumulates.
- Attributable and explainable decisions with evidence integrity.
- Bounded availability and safe failure behavior.

## Threat analysis method

Each scenario receives a stable `TS-NNN` identifier and records preconditions, objective, observable signals, expected response, current feasibility, false-positive concerns, candidate experiment, and status. The catalog is in [Attack Scenarios](ATTACK_SCENARIOS.md). Scenario status `SPECIFIED` means documented, not detected or mitigated.

## Assumptions and limitations

The enforcement host, identity roots, and adapter isolation are assumed trustworthy unless an experiment explicitly relaxes them. SafetyBox observes only mediated events and adapter-reported outcomes. Covert channels, physical effects, and semantic harm through permitted operations may be invisible. A valid authorization cannot guarantee that a tool is internally safe. These limitations constrain every prevention claim.

Risk is assessed per deployment; the initial catalog is not exhaustive. [Out of Scope](OUT_OF_SCOPE.md) identifies exclusions without implying they are unimportant.
