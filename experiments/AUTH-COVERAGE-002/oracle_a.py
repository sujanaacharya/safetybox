"""Oracle A: direct predicate evaluation of the written AUTH-COVERAGE-002 spec.

This module deliberately imports no SafetyBox code and performs no I/O.
"""

from __future__ import annotations

from typing import Any

ORACLE_ID = "AUTH-COVERAGE-002-ORACLE-A@1"


def _canonical_path(value: str) -> bool:
    return (
        value.startswith("/")
        and value != "/"
        and all(part not in {"", ".", ".."} for part in value[1:].split("/"))
    )


def _covers(capability: dict[str, str], request: dict[str, Any]) -> bool:
    if capability["action"] != request["action"]:
        return False
    scope = capability["resource"]
    resource = request["resource"]
    if scope.endswith("/**"):
        root = scope[:-3]
        return (
            _canonical_path(root) and _canonical_path(resource) and resource.startswith(root + "/")
        )
    return scope == resource


def _valid_request(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "request_id",
        "session_id",
        "task_id",
        "actor",
        "action",
        "resource",
        "arguments",
    }:
        return False
    if any(
        not isinstance(value[name], str) or not value[name]
        for name in ("request_id", "session_id", "task_id", "actor", "action", "resource")
    ) or not isinstance(value["arguments"], dict):
        return False
    resource = value["resource"]
    return not resource.startswith("/") or _canonical_path(resource)


def _valid(scenario: object) -> bool:
    if not isinstance(scenario, dict) or set(scenario) != {
        "scenario_id",
        "tool_class",
        "contract_task_id",
        "contract_description",
        "capabilities",
        "request",
        "additional_components",
    }:
        return False
    if (
        scenario["tool_class"] not in {"FILESYSTEM", "PROCESS"}
        or not isinstance(scenario["contract_task_id"], str)
        or not scenario["contract_task_id"]
    ):
        return False
    if (
        not _valid_request(scenario["request"])
        or not isinstance(scenario["capabilities"], list)
        or not isinstance(scenario["additional_components"], list)
    ):
        return False
    for capability in scenario["capabilities"]:
        if (
            not isinstance(capability, dict)
            or set(capability) != {"action", "resource"}
            or any(
                not isinstance(capability.get(name), str) or not capability.get(name)
                for name in ("action", "resource")
            )
        ):
            return False
        scope = capability["resource"]
        if scope.endswith("/**") and not _canonical_path(scope[:-3]):
            return False
        if scope.startswith("/") and not scope.endswith("/**") and not _canonical_path(scope):
            return False
    names = []
    for component in scenario["additional_components"]:
        if (
            not isinstance(component, dict)
            or set(component) != {"name", "request"}
            or not isinstance(component["name"], str)
            or not component["name"]
            or not _valid_request(component["request"])
        ):
            return False
        names.append(component["name"])
    if len(names) != len(set(names)):
        return False
    return (scenario["tool_class"] == "FILESYSTEM" and not names) or (
        scenario["tool_class"] == "PROCESS" and names == ["cwd"]
    )


def _component(
    contract_task: str, capabilities: list[dict[str, str]], request: dict[str, Any]
) -> dict[str, Any]:
    if request["task_id"] != contract_task:
        return {"decision": "DENY", "rule": "AUTH.TASK_MISMATCH", "matched_capability": None}
    action_caps = [item for item in capabilities if item["action"] == request["action"]]
    matching = [item for item in action_caps if _covers(item, request)]
    if matching:
        selected = min(matching, key=lambda item: (item["resource"], item["action"]))
        return {
            "decision": "ALLOW",
            "rule": "AUTH.EXPLICIT_CAPABILITY",
            "matched_capability": selected,
        }
    rule = "AUTH.NO_ACTION_CAPABILITY" if not action_caps else "AUTH.RESOURCE_OUT_OF_SCOPE"
    return {"decision": "DENY", "rule": rule, "matched_capability": None}


def evaluate(scenario: dict[str, Any]) -> dict[str, Any]:
    if not _valid(scenario):
        return {"decision": "DENY", "rule": "AUTH.INVALID_STRUCTURE", "components": {}}
    components = [
        ("exec" if scenario["tool_class"] == "PROCESS" else "primary", scenario["request"])
    ]
    components.extend((item["name"], item["request"]) for item in scenario["additional_components"])
    results = {
        name: _component(scenario["contract_task_id"], scenario["capabilities"], request)
        for name, request in components
    }
    allowed = all(item["decision"] == "ALLOW" for item in results.values())
    return {
        "decision": "ALLOW" if allowed else "DENY",
        "rule": "AUTH.ALL_COMPONENTS_ALLOWED" if allowed else "AUTH.ANY_COMPONENT_DENIED",
        "components": results,
    }
