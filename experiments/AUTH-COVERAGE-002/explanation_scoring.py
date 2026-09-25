"""Supplemental full-component explanation scoring over frozen raw records.

The frozen metric adapter retains its original compatibility metric.  This
module is the preregistered AUTH-COVERAGE-002 analysis path for the stronger
structured explanation contract, including compound component evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from safetybox.research.auth_coverage_raw import RawAuthorizationRecord

RULE_MAP = {
    "POL-M2-CAPABILITY-ALLOW": "AUTH.EXPLICIT_CAPABILITY",
    "POL-M2-CAPABILITY-MISSING": "AUTH.NO_ACTION_CAPABILITY",
    "POL-M2-RESOURCE-OUT-OF-SCOPE": "AUTH.RESOURCE_OUT_OF_SCOPE",
    "POL-M2-TASK-MISMATCH": "AUTH.TASK_MISMATCH",
    "POL-COMPOUND-ALL-ALLOW": "AUTH.ALL_COMPONENTS_ALLOWED",
    "POL-COMPOUND-DENY": "AUTH.ANY_COMPONENT_DENIED",
}


def _matched_value(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    return {"action": value.action, "resource": value.resource}  # type: ignore[attr-defined]


def score_raw_explanation(
    record: RawAuthorizationRecord,
    runtime: Mapping[str, Any],
    analysis: Mapping[str, Any],
) -> list[str]:
    """Return stable field-level errors; an empty list is a complete match."""
    errors: list[str] = []
    output = record.authorization_output
    expected = analysis["expected_explanation"]
    if output.final_decision != expected["decision"]:
        errors.append("final.decision")
    expected_final_rule = (
        expected["rule"]
        if runtime["tool_class"] == "PROCESS"
        else expected["components"]["primary"]["rule"]
    )
    if RULE_MAP.get(output.rule_id or "") != expected_final_rule:
        errors.append("final.rule")
    if output.reason_code != output.rule_id:
        errors.append("final.reason_code")
    if output.authority_source != "TaskContract":
        errors.append("final.authority_source")
    provenance = output.authority_provenance
    if (
        provenance.get("authority_source") != "TaskContract"
        or provenance.get("contract_identity") != runtime["contract_task_id"]
    ):
        errors.append("final.authority_provenance")

    requests = [
        runtime["request"],
        *(item["request"] for item in runtime["additional_components"]),
    ]
    expected_names = list(expected["components"])
    if len(output.component_decisions) != len(requests):
        errors.append("components.count")
        return errors
    for index, (observed, request) in enumerate(
        zip(output.component_decisions, requests, strict=True)
    ):
        expected_name = expected_names[index]
        production_name = observed.component
        mapped_name = (
            "exec"
            if runtime["tool_class"] == "PROCESS" and production_name == "primary"
            else production_name
        )
        prefix = f"component[{expected_name}]"
        if mapped_name != expected_name:
            errors.append(f"{prefix}.name")
            continue
        wanted = expected["components"][expected_name]
        comparisons = {
            "decision": observed.decision,
            "rule": RULE_MAP.get(observed.rule_id or ""),
            "reason_code": RULE_MAP.get(observed.reason_code or ""),
            "task": request["task_id"],
            "action": request["action"],
            "resource": request["resource"],
            "matched_capability": _matched_value(observed.matched_capability),
            "authority_source": observed.authority_source,
        }
        for field, actual in comparisons.items():
            if actual != wanted[field]:
                errors.append(f"{prefix}.{field}")
    return errors


def explanation_summary(error_lists: list[list[str]]) -> dict[str, object]:
    complete = sum(not errors for errors in error_lists)
    return {
        "contract_id": "AUTH-COVERAGE-002-EXPLANATION-CONTRACT@1",
        "complete": complete,
        "denominator": len(error_lists),
        "rate": complete / len(error_lists) if error_lists else None,
        "errors": sum(len(errors) for errors in error_lists),
    }
