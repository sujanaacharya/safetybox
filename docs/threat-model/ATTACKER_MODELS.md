# Attacker Models

## AM-01 — Accidental or unreliable agent

The agent makes mistaken, hallucinated, overly broad, or looping requests without adversarial intent. SafetyBox should constrain effects without needing to infer intent.

## AM-02 — Prompt/content injector

An external party controls instructions embedded in user content, web pages, files, tool results, or retrieved context but does not directly control the enforcement plane.

## AM-03 — Intentionally evasive protected agent

The agent knows or learns aspects of policy and adapts requests, argument encodings, timing, sequences, or delegation to evade monitoring. It cannot directly alter correctly isolated SafetyBox state under the base model.

## AM-04 — Compromised external tool/service

A tool or service returns misleading/malicious output, behaves differently from its declared interface, or exposes effects not fully observable to SafetyBox.

## AM-05 — Malicious or over-privileged task issuer

The contract issuer intentionally grants harmful authority or describes a harmful task. SafetyBox can enforce the contract but is not assumed to determine whether every authorized goal is ethically acceptable. Deployment governance must restrict issuer authority.

## AM-06 — Cross-session or collaborating agents

Multiple agents exploit shared state, delegated capability, or partial observability to compose a violation.

## Privileged attackers

A malicious host administrator or attacker controlling the SafetyBox process, kernel, identity root, or policy-signing authority is outside the core enforcement guarantee. Such threats motivate defense in depth but must not be described as solved.
