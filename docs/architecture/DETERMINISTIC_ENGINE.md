# Deterministic Engine

## Definition

For the same normalized request, task contract version, capability snapshot, policy set/version, trajectory state, engine version, and explicit environmental inputs, the deterministic core should return the same decision, rule identifiers, and state transition. Wall-clock time, external data, and randomness must enter as recorded inputs rather than hidden dependencies.

Determinism is a design goal to be verified, not a current implementation property.

## Intended evaluation pipeline

1. Validate identity, schema, and sequence context.
2. Canonicalize action, resource, and arguments without changing their meaning.
3. Resolve effective capabilities and expiry.
4. Evaluate hard contract and policy prohibitions.
5. Evaluate allow rules and quantitative constraints.
6. Evaluate registered trajectory/state rules.
7. Resolve conflicts using documented precedence.
8. produce an outcome, explanation, matched rule IDs, input/version hashes, and proposed state effects.
9. Commit the authorization decision before any adapter execution.

## Boundaries

Deterministic evaluation does not imply that agent, network, tool, operating system, or LLM behavior is deterministic. It also does not guarantee a policy captures unsafe semantics. Optional semantic detectors may generate signals, but deterministic denials and maximum-privilege constraints remain authoritative.

## Sources of hidden nondeterminism to control

- unordered collections or rule traversal;
- locale, path, case, or Unicode normalization;
- wall-clock checks without captured timestamps;
- concurrent event races;
- network lookups during evaluation;
- floating-point thresholds;
- unspecified policy conflict resolution;
- mutable external configuration.

Experiments should test repeatability and record discrepancies rather than assume them away.
