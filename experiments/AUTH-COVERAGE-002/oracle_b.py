"""Oracle B: finite permitted-relation construction and membership query.

The algorithm is intentionally organized around set construction, path-segment
containment, and component indexes rather than Oracle A's predicate control flow.
It imports no SafetyBox or Oracle A code.
"""

from __future__ import annotations

from typing import Any

ORACLE_ID = "AUTH-COVERAGE-002-ORACLE-B@1"


def _segments(value: str) -> tuple[str, ...] | None:
    if not value.startswith("/") or value == "/":
        return None
    pieces = tuple(value[1:].split("/"))
    return pieces if all(piece and piece not in {".", ".."} for piece in pieces) else None


def _scope_contains(scope: str, resource: str) -> bool:
    if not scope.endswith("/**"):
        return scope == resource
    left = _segments(scope[:-3])
    right = _segments(resource)
    return (
        left is not None
        and right is not None
        and len(right) > len(left)
        and right[: len(left)] == left
    )


def _well_formed(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "scenario_id",
        "tool_class",
        "contract_task_id",
        "contract_description",
        "capabilities",
        "request",
        "additional_components",
    }:
        return False
    if value["tool_class"] not in {"FILESYSTEM", "PROCESS"}:
        return False
    if not isinstance(value["contract_task_id"], str) or not value["contract_task_id"]:
        return False
    if not isinstance(value["additional_components"], list) or not isinstance(
        value["capabilities"], list
    ):
        return False
    if any(
        not isinstance(item, dict) or set(item) != {"name", "request"}
        for item in value["additional_components"]
    ):
        return False
    components = [
        value["request"],
        *(item["request"] for item in value["additional_components"]),
    ]
    names = [item["name"] for item in value["additional_components"]]
    if (value["tool_class"], tuple(names)) not in {
        ("FILESYSTEM", ()),
        ("PROCESS", ("cwd",)),
    }:
        return False
    request_fields = {
        "request_id",
        "session_id",
        "task_id",
        "actor",
        "action",
        "resource",
        "arguments",
    }
    for request in components:
        if not isinstance(request, dict) or set(request) != request_fields:
            return False
        if any(
            not isinstance(request[name], str) or not request[name]
            for name in request_fields - {"arguments"}
        ) or not isinstance(request["arguments"], dict):
            return False
        if request["resource"].startswith("/") and _segments(request["resource"]) is None:
            return False
    if len(names) != len(set(names)):
        return False
    for capability in value["capabilities"]:
        if not isinstance(capability, dict) or set(capability) != {"action", "resource"}:
            return False
        if any(
            not isinstance(capability[name], str) or not capability[name]
            for name in ("action", "resource")
        ):
            return False
        scope = capability["resource"]
        if scope.startswith("/") and (
            _segments(scope[:-3]) is None if scope.endswith("/**") else _segments(scope) is None
        ):
            return False
    return True


def evaluate(scenario: dict[str, Any]) -> dict[str, Any]:
    if not _well_formed(scenario):
        return {"decision": "DENY", "rule": "AUTH.INVALID_STRUCTURE", "components": {}}
    ordered = [("exec" if scenario["tool_class"] == "PROCESS" else "primary", scenario["request"])]
    ordered += [(item["name"], item["request"]) for item in scenario["additional_components"]]
    permitted: dict[int, list[dict[str, str]]] = {index: [] for index in range(len(ordered))}
    for capability in set((item["action"], item["resource"]) for item in scenario["capabilities"]):
        action, scope = capability
        for index, (_, request) in enumerate(ordered):
            if request["task_id"] == scenario["contract_task_id"] and (action, True) == (
                request["action"],
                _scope_contains(scope, request["resource"]),
            ):
                permitted[index].append({"action": action, "resource": scope})
    results: dict[str, dict[str, Any]] = {}
    for index, (name, request) in enumerate(ordered):
        candidates = permitted[index]
        if request["task_id"] != scenario["contract_task_id"]:
            rule = "AUTH.TASK_MISMATCH"
        elif candidates:
            rule = "AUTH.EXPLICIT_CAPABILITY"
        elif any(item["action"] == request["action"] for item in scenario["capabilities"]):
            rule = "AUTH.RESOURCE_OUT_OF_SCOPE"
        else:
            rule = "AUTH.NO_ACTION_CAPABILITY"
        results[name] = {
            "decision": "ALLOW" if candidates else "DENY",
            "rule": rule,
            "matched_capability": min(
                candidates, key=lambda item: (item["resource"], item["action"])
            )
            if candidates
            else None,
        }
    allowed_indexes = {index for index, candidates in permitted.items() if candidates}
    allowed = allowed_indexes == set(range(len(ordered)))
    return {
        "decision": "ALLOW" if allowed else "DENY",
        "rule": "AUTH.ALL_COMPONENTS_ALLOWED" if allowed else "AUTH.ANY_COMPONENT_DENIED",
        "components": results,
    }
