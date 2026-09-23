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

M0 specifies governance, research design, architecture semantics, threats, and evaluation. It does not implement the runtime. Empty source/test placeholders are not evidence of implemented behavior.
