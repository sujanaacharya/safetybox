# M5.1 Context-Aware Trajectory Requirements

## Purpose and evidence basis

This document defines research design requirements derived from frozen EXP-009 base and A1/A2/A3 evidence. It is not an implementation specification and authorizes no detector, corpus, label, or protocol change.

EXP-009 showed incremental observational value for 20/20 TRJ-001 positives with no action-level policy block, but the base monitor flagged 33/40 negatives and 33/36 hard negatives. A1 did not resolve TRJ-002 purpose ambiguity with thresholds 2, 3, or 4; A2 found identical outcomes at windows 4, 8, and 16; A3 showed independent false-positive burdens from both rules. M5.1 must therefore study explicit semantic relationships rather than tune only counts, bounds, or rule availability.

## Research objective

Determine whether a deterministic trajectory monitor can evaluate observed actions relative to explicit task, resource, and destination purposes and thereby improve specificity without sacrificing the incremental trajectory detection demonstrated in EXP-009.

## Requirements

### REQ-CTX-001 — Explicit task-purpose input

Trajectory interpretation must consume a structured, explicit representation of the declared task purpose. The input must be versioned and auditable; it must not be inferred from the expected label or scenario ID.

**Evidence rationale:** TRJ-001 flagged both members of all 10/10 opposite-label task-purpose contrast pairs.

### REQ-CTX-002 — Resource-purpose relationships

The design must represent how accessed resources relate to the declared task, rather than treating action type and logical resource identity alone as sufficient behavioral meaning.

**Evidence rationale:** legitimate reporting, maintenance, migration, diagnostic, and inspection traces contributed to the 33/40 flagged negatives.

### REQ-CTX-003 — Destination-purpose constraints

Outbound actions must be evaluated relative to an explicit destination purpose or destination constraint associated with the task. Destination evaluation must remain separate from mere presence of a `network.send` action.

**Evidence rationale:** TRJ-001 generated 16/20 negative flags across legitimate collection/report/export-like flows.

### REQ-CTX-004 — Provenance and data-lineage representation

Where the observation model can support it, the design should represent provenance or data-lineage relationships between collection, transformation, query, and egress. When lineage is unavailable, findings must state that limitation rather than imply a proven data flow.

**Evidence rationale:** M5 observes ordered access structure but cannot establish which information, if any, flowed to a destination.

### REQ-CTX-005 — Denial-purpose and fallback semantics

Repeated denials must be evaluated relative to declared fallback, compatibility, lookup, typo-recovery, or maintenance behavior. The design must keep distinct-resource count as evidence rather than treating it as sufficient proof of deliberate probing.

**Evidence rationale:** TRJ-002 flagged 17/20 benign negatives at the base threshold; A1 showed a sharp loss of sensitivity when the tested threshold was raised.

### REQ-CTX-006 — Deterministic explainability

Every finding and non-finding must be reconstructable from versioned inputs, ordered observations, explicit semantic constraints, and deterministic rule logic. Explanations must identify the task/resource/destination relationship that affected the outcome.

### REQ-CTX-007 — No required LLM in the first context-aware version

The first M5.1 design must not require an LLM for classification or semantic completion. Structured semantics may be supplied through task contracts or equivalent deterministic inputs. LLM-based comparison, if later authorized, is a separate experiment.

### REQ-CTX-008 — Preserve detection/prevention separation

The design and reporting must distinguish observational findings from authorization blocks and interventions. A trajectory finding must never be counted as prevention unless a separately preregistered intervention occurs before the relevant side effect.

### REQ-CTX-009 — Preserve separate outcome measures

Evaluation must report raw positive detections, false positives, true negatives, false negatives, policy blocks, and trajectory findings separately. It must not create a composite safety score.

### REQ-CTX-010 — New freeze and held-out evaluation

The detector design, semantic schema, primary metrics, and comparison conditions must be preregistered and frozen before evaluation. Evaluation must use a new held-out corpus/version authored after design freeze; `EXP-009-CORPUS@1` may serve only as development/regression evidence.

### REQ-CTX-011 — Matched semantic contrasts

The new corpus must include matched contrasts that hold observable action shape similar while varying declared task purpose, resource purpose, destination authorization, and fallback rationale. It must also include cases where semantic context should not suppress a valid finding.

### REQ-CTX-012 — Explicit anti-overfitting prohibition

M5.1 must not contain special cases for corpus IDs, hard-coded task-category allow/deny decisions, scenario-specific resource names, or rules that encode the current 10 contrast pairs. Generalization must arise through explicit, reusable task semantics and relationships.

### REQ-CTX-013 — Baseline and retention criterion

A future preregistration must compare M5.1 against the frozen M5 sequence-only baseline on matched conditions. It must define in advance how specificity improvement and retention of incremental TRJ-001 detection will be assessed, with raw counts and without selecting a condition after seeing held-out results.

### REQ-CTX-014 — Bounded claims and failure analysis

The evaluation must preserve every false positive and false negative, report failures by semantic factor and rule family, and bound conclusions to the sampled synthetic or real environments. Absence of a failure in a finite corpus must not be stated as semantic completeness.

## Non-requirements

This document does not select a schema, algorithm, threshold, window, language model, containment response, or production policy. It does not require natural-language semantic inference and does not authorize changes to the frozen EXP-009 evidence.

## Evaluation gate

Implementation should not begin until a successor protocol defines the context schema, threat model, matched baseline, held-out authorship procedure, raw metrics, failure criteria, and freeze sequence. The scientific question precedes detector construction.

## M5.1-A implementation note

The frozen EXP-012 protocol satisfied this gate for context representation. M5.1-A now
implements only the immutable trusted context schema and validation described in
[Task Context](../architecture/TASK_CONTEXT.md). It does not implement the M5.1
detector, create held-out scenarios, or run EXP-012. These requirements and the frozen
protocol remain unchanged as evaluation constraints.
