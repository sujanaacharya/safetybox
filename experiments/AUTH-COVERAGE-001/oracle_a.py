"""Oracle A: direct executable transcription of the normative specification."""

from __future__ import annotations

from typing import Any

from schema import validate_scenario

ORACLE_ID = "AUTH-COVERAGE-001-ORACLE-A@1"


def _canonical_absolute(path: str) -> bool:
    if not path.startswith("/") or path == "/":
        return False
    return all(part not in {"", ".", ".."} for part in path[1:].split("/"))


def _covers(capability: dict[str, str], action: str, resource: str) -> bool:
    if capability["action"] != action:
        return False
    if capability["scope_type"] == "EXACT":
        return capability["resource"] == resource
    root = capability["resource"].removesuffix("/**")
    return (
        _canonical_absolute(root)
        and _canonical_absolute(resource)
        and resource.startswith(root + "/")
    )


def evaluate(scenario: dict[str, Any]) -> dict[str, Any]:
    """Return the complete deterministic authority record for one scenario."""
    validate_scenario(scenario)
    request = scenario["request"]
    contract = scenario["contract"]
    task_ok = request["task_id"] == contract["task_id"]
    component_decisions: dict[str, str] = {}
    matching: dict[str, str | None] = {}
    for component in request["components"]:
        candidates = sorted(
            (
                capability
                for capability in contract["capabilities"]
                if task_ok and _covers(capability, component["action"], component["resource"])
            ),
            key=lambda item: item["capability_id"],
        )
        name = component["component"]
        component_decisions[name] = "ALLOW" if candidates else "DENY"
        matching[name] = candidates[0]["capability_id"] if candidates else None
    decision = "ALLOW" if all(item == "ALLOW" for item in component_decisions.values()) else "DENY"
    if not task_ok:
        rule, reason = "AUTH-TASK-BINDING", "request task differs from contract task"
    elif decision == "ALLOW":
        rule, reason = "AUTH-ALL-COMPONENTS", "every component has one covering capability"
    else:
        rule, reason = "AUTH-COMPONENT-DENY", "at least one component lacks a covering capability"
    return {
        "scenario_id": scenario["scenario_id"],
        "decision": decision,
        "component_decisions": component_decisions,
        "rule": rule,
        "reason": reason,
        "authority_source": contract["contract_id"],
        "matching_capabilities": matching,
        "explanation": {
            "subject": request["subject_id"],
            "session": request["session_id"],
            "task": request["task_id"],
            "action": [item["action"] for item in request["components"]],
            "resource": [item["resource"] for item in request["components"]],
            "capability": matching,
            "rule": rule,
            "authority_source": contract["contract_id"],
            "component": component_decisions,
            "decision": decision,
            "reason": reason,
        },
    }
