# EXP-015 Corpus@2 Schema-v1 Validity Disposition

**Disposition ID:** `EXP-015-CORPUS-2-SCHEMA-V1-DISPOSITION@1`
**Classification:** `INSUFFICIENT_FOR_EXP_015_CORPUS_2_AUTHORING`

`EXP-015-RUNTIME-SCHEMA@1` enforced `request.task_id == task_contract.task_id`.
The frozen EXP-015 capability evaluator instead treats a task mismatch as an
authorization denial. Consequently v1 prevented a valid task-binding
authorization-negative from being represented, validated, and materialized.

This is a representational defect, not evidence that v1 is generally unsafe: v1 remains
preserved as its historical schema/materializer freeze. Schema validation validates
runtime shape and independently well-formed IDs; authorization decides whether the
request task is authorized by the supplied task contract.

This disposition was reached before any Corpus@2 scenario authoring, held-out adapter
execution, result creation, or prediction exposure. It creates no adapter contamination.
Corpus@1 remains retired under its existing disposition.
