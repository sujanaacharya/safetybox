# Experiments

Executable registered studies belong in `EXP-NNN-short-slug/` directories. Each must
link research questions, hypotheses or preregistered questions, scenarios, frozen
configuration, and analysis. See the
[Experiment Plan](../docs/experiments/EXPERIMENT_PLAN.md).

## Identifier registry

IDs are allocated monotonically and never recycled. `EXP-001` through `EXP-011` were
allocated by the original research-question plan; only EXP-009 has an executable frozen
study in that range. Later registered studies are listed below.

| ID | Record | Status |
|---|---|---|
| EXP-001–EXP-008 | Reserved candidate experiments in the research plan | Not executed |
| EXP-009 | Trajectory monitor evaluation and registered ablations | Completed and frozen |
| EXP-010–EXP-011 | Reserved candidate experiments in the research plan | Not executed |
| EXP-012 | Context-aware trajectory evaluation | Completed and frozen |
| EXP-013 | Counterfactual multi-step context evaluation | Completed and frozen |
| EXP-014 | Real filesystem mediation and complete-path evaluation | `PREREGISTERED`; design only |

The next ID decision must search the repository and extend this registry; it must not
infer availability from missing directories alone.
