# Scope and Non-Goals

## In scope

- Pre-execution mediation of agent requests to files, shells, networks, APIs, databases, and other adapters.
- Explicit task contracts and scoped, revocable capabilities.
- Deterministic policy evaluation over canonical observable inputs.
- Ordered runtime events, trajectory policies, experimental risk state, audit, and provenance.
- Graduated decisions and containment actions.
- Controlled comparisons across models, providers, frameworks, and optional LLM monitors.
- Reproducible threat-scenario and benign-task experiments.

## Non-goals for the initial research program

- Proving an agent's internal intent or guaranteeing alignment.
- Guaranteeing safety outside documented trust and observation boundaries.
- Replacing operating-system isolation, authentication, secret management, or secure deployment practices.
- Detecting every harmful use of an otherwise authorized channel.
- Training or fine-tuning foundation models.
- Building a general-purpose agent framework or model-provider SDK.
- Treating a scalar “safety score” as a validated scientific construct.
- Using an LLM as a mandatory authorization dependency.
- Production deployment before invariants, failure modes, and performance are empirically tested.

## Current phase boundary

The repository now contains bounded in-process authorization/audit/trajectory components,
Level 3 synthetic subproperty evidence, and Level 4 real-filesystem evidence for named
EXP-014 adapter routes. EXP-015 did not demonstrate successful child execution; EXP-016
Protocol@2 has no held-out result; AUTH-COVERAGE-001 is blocked as valid held-out evidence.
The broader unauthorized-effect, Authority V2, network, MCP, real-agent, and external
evaluation programs remain specifications or future work. Architecture documents are not
evidence that these controls exist.
