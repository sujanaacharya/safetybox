# Ablation Plan

Ablations test which components or signals account for an observed effect. They are not substitutes for complete baselines.

| Ablation | Removed/changed factor | Primary questions |
|---|---|---|
| A1 | Task contract reduced to tool-level allowlist | Does resource/task scoping affect prevention and utility? |
| A2 | Capability constraints removed while tool permission remains | Which gains derive from action-resource constraints? |
| A3 | Trajectory monitor disabled | Does stateful monitoring add detection beyond action checks? |
| A4 | Rate/count signals disabled | Are results driven by frequency rather than sequence? |
| A5 | Sequence rules disabled | Are ordered patterns necessary? |
| A6 | Risk-state capability degradation disabled | Does graduated response improve utility/containment? |
| A7 | Approval unavailable | What safety/utility depends on human escalation? |
| A8 | Selected provenance/causal links withheld from monitoring | How does observability affect detection? |
| A9 | Optional LLM signal removed from B4 | What incremental semantic value and cost does it add? |
| A10 | Adapter/framework varied with normalized policy fixed | Are effects caused by integration differences? |
| A11 | Trajectory observation-window size varied | How do explicit bounded-state choices affect misses and incidental matches? |

Each ablation changes one declared factor where feasible, uses the same registered trial set, and reports both beneficial and adverse movement across safety, utility, and overhead. Interactions require factorial designs or explicit caveats; post-hoc ablations are labeled exploratory.
