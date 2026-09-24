# EXP-013 Synthesis

## Question

EXP-013 asked whether ordered deterministic trajectory state adds discriminative
information beyond independent evaluation of each observation against trusted context.
The preregistered comparison was frozen B2 versus frozen B4 on matched
history-required counterfactual pairs.

## Why EXP-012 was not enough

EXP-012 produced a perfect M5.1 result, but every positive contained an
observation-local `CONTEXT_MISMATCH`. A history-free rule—flag a scenario if any one
observation mismatches—separated all 80 primary scenarios. EXP-012 therefore established
clean deterministic context comparison, not that multi-step history was necessary.

## What EXP-013 changed

EXP-013 froze a new 96-scenario corpus after B2 and B4 were frozen. Its 80 primary
scenarios form 40 strong positive/negative pairs. Pair members share exact static trusted
context and normalized local evidence, and every primary observation is
`CONTEXT_CONSISTENT`. The changed variable is an ordered/grouped relation: accumulated
roles, cross-source grouping, phase transition, finalization/re-entry, fallback episode,
or cross-phase order.

## Result

| Condition | Positive detection | Hard-negative FP | Pair accuracy |
|---|---:|---:|---:|
| B2 | 0/40 | 0/40 | 0/40 |
| M5.1-C | 0/40 | 0/40 | 0/40 |
| B4 | 38/40 | 0/40 | 38/40 |

B4 recall was 0.95, FPR 0, precision 1.0, F1 0.974, accuracy 0.975, and balanced
accuracy 0.975. All ten preregistered success criteria passed. Sixty of sixty normalized
repeat comparisons agreed.

Every B4 true-positive scenario includes at least one finding dependent on a retained
cross-observation relationship, and its matched negative removes that relation and the
finding. Five scenarios were first flagged at action 1 for an undeclared initial phase;
those earliest findings do not use prior observations, but each scenario later produces
a true transition or finalization-history finding. Earliest detection and evidence depth
must therefore remain distinct concepts.

The two misses, `HX-013-033-B` and `HX-013-034-B`, restart after termination at a
candidate the ground truth treats as unable to start an episode. B4 permits the restart,
resets state, and has no declared allowed-start relation to test. This is a frozen
state-machine/context-representation boundary, not a window or binding failure.

## Supported claim

> On `EXP-013-CORPUS@1`, the frozen B4 monitor correctly discriminated 38 of 40
> history-required counterfactual pairs that the frozen single-observation B2 baseline
> could not distinguish, with no false positives among 40 matched hard negatives.

This is stronger evidence for genuine historical contribution than EXP-012 because
local status mismatch cannot explain the primary result. It is still synthetic,
handcrafted, declaration-dependent evidence without independent label review.

## What remains unsupported

EXP-013 does not show that SafetyBox detects unsafe agents generally, prevents the
observed behavior, works with real tools, tolerates incorrect context, detects
internally consistent semantic staleness, proves payload transfer, or generalizes beyond
the frozen corpus. B4 reasons about observed role/order relationships, not byte-level or
field-level causal lineage. Its window of 16 was not ablated and is not shown optimal.

## Architectural implication

The research progression is now clearer:

```text
TaskContract + Capability -> deterministic action authorization
M3                         -> reconstructable provenance
M5                         -> sequence observation
TaskContext / M5.1         -> semantic context comparison
B2                         -> single-observation context baseline
B4                         -> bounded structured historical reasoning
```

The next implementation milestone should be real tool mediation, beginning with a
filesystem adapter and then subprocess, network, MCP interception, an SDK, and a real
agent harness. This tests SafetyBox's strongest current differentiator—runtime control
and history-aware behavior—before a broad static scanner is built. Data lineage is the
major later primitive needed for sensitive-information and hybrid static/runtime claims.
