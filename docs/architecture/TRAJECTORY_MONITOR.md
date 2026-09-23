# Trajectory Monitor

## Purpose

The trajectory monitor evaluates ordered event history to detect patterns not visible in a single authorized action: staged collection and exfiltration, repeated boundary probing, escalating privilege attempts, or unusual request sequences. It consumes committed canonical events and emits explainable signals; it does not grant authority or execute actions.

## Candidate rule forms

- bounded counts/rates over event windows;
- temporal sequences and forbidden transitions;
- cumulative bytes, rows, destinations, or resource breadth;
- divergence from contract-declared expected phases;
- correlations across child tool calls and delegated agents;
- repeated near-boundary requests following denials.

Rules must declare window semantics, state storage, reset behavior, late-event handling, task applicability, and false-positive rationale. Deterministic rules use sequence numbers rather than arrival timing where possible.

## Evaluation concerns

Trajectory detection can add early warning but may also punish legitimate retries, exploration, or long-running tasks. EXP-009 will compare action-only and trajectory-aware policies on matched sequences. Ablations should separate count, order, resource-breadth, and state-transition signals. Detection claims require pre-execution evidence; retrospective labeling alone is insufficient for prevention claims.

Cross-session and multi-agent correlation remain open problems because identity, delegation, and causal ordering may be incomplete.
