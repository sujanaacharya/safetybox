#!/usr/bin/env python3
"""DEV-only adversarial resource-semantics and explanation mutation fixtures."""

from __future__ import annotations

import copy
import json
import unicodedata
from collections.abc import Callable
from typing import Any

RESOURCE_FAULTS = (
    "PREFIX_MATCH",
    "PARENT_CHILD_REVERSAL",
    "UNICODE_NORMALIZATION",
    "ACTION_RESOURCE_SWAP",
    "CWD_EXEC_CONFUSION",
)

EXPLANATION_FAULTS = (
    "WRONG_COMPONENT_ORDER",
    "MISSING_COMPONENT",
    "WRONG_MATCHED_CAPABILITY",
    "WRONG_RESOURCE",
    "WRONG_RULE",
    "WRONG_REASON",
    "WRONG_AUTHORITY_SOURCE",
)

RAW_FAULTS = (
    "CAPABILITY_REORDER",
    "COMPONENT_REORDER",
    "MISSING_FIELD",
    "DIGEST_MISMATCH",
    "TASK_MISMATCH",
    "RESOURCE_CORRUPTION",
)


def bounded_model_decision(scenario: dict[str, Any]) -> dict[str, Any]:
    """Third finite relation model used only for DEV mutation-detection evidence."""
    requests = [
        scenario["request"],
        *(item["request"] for item in scenario["additional_components"]),
    ]

    def covers(scope: str, resource: str) -> bool:
        if scope == resource:
            return True
        if not scope.endswith("/**"):
            return False
        root = tuple(scope[:-3].split("/")[1:])
        value = tuple(resource.split("/")[1:])
        return bool(root) and len(value) > len(root) and value[: len(root)] == root

    component_ids = [
        "primary",
        *(item["name"] for item in scenario["additional_components"]),
    ]
    component_decisions = {
        component_id: (
            "ALLOW"
            if request["task_id"] == scenario["contract_task_id"]
            and any(
                capability["action"] == request["action"]
                and covers(capability["resource"], request["resource"])
                for capability in scenario["capabilities"]
            )
            else "DENY"
        )
        for component_id, request in zip(component_ids, requests, strict=True)
    }
    return {
        "decision": "ALLOW"
        if all(value == "ALLOW" for value in component_decisions.values())
        else "DENY",
        "components": component_decisions,
    }


def faulty_decision(
    scenario: dict[str, Any], fault: str, correct: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, Any]:
    """Evaluate a deliberately faulty semantic variant; never flip output unconditionally."""
    value = copy.deepcopy(scenario)
    requests = [value["request"], *(part["request"] for part in value["additional_components"])]
    if fault == "PREFIX_MATCH":
        for request in requests:
            for capability in value["capabilities"]:
                if capability["action"] == request["action"] and request["resource"].startswith(
                    capability["resource"]
                ):
                    capability["resource"] = request["resource"]
    elif fault == "PARENT_CHILD_REVERSAL":
        for request in requests:
            for capability in value["capabilities"]:
                if capability["action"] == request["action"] and capability["resource"].startswith(
                    request["resource"] + "/"
                ):
                    capability["resource"] = request["resource"]
    elif fault == "UNICODE_NORMALIZATION":
        for request in requests:
            for capability in value["capabilities"]:
                if capability["action"] == request["action"] and unicodedata.normalize(
                    "NFKC", capability["resource"]
                ) == unicodedata.normalize("NFKC", request["resource"]):
                    capability["resource"] = request["resource"]
    elif fault == "ACTION_RESOURCE_SWAP":
        for request in requests:
            for capability in value["capabilities"]:
                if (
                    capability["action"] == request["resource"]
                    and capability["resource"] == request["action"]
                ):
                    capability["action"], capability["resource"] = (
                        request["action"],
                        request["resource"],
                    )
    elif fault == "CWD_EXEC_CONFUSION":
        if len(requests) == 2:
            first, second = requests
            for capability in value["capabilities"]:
                if capability == {"action": first["action"], "resource": first["resource"]}:
                    capability.update(action=second["action"], resource=second["resource"])
                elif capability == {"action": second["action"], "resource": second["resource"]}:
                    capability.update(action=first["action"], resource=first["resource"])
    else:
        raise ValueError(f"unknown fault {fault}")
    return correct(value)


def mutate_explanation(components: list[dict[str, Any]], fault: str) -> list[dict[str, Any]]:
    value = copy.deepcopy(components)
    if fault == "WRONG_COMPONENT_ORDER":
        value.reverse()
    elif fault == "MISSING_COMPONENT":
        value.pop()
    else:
        field = {
            "WRONG_MATCHED_CAPABILITY": "matched_capability",
            "WRONG_RESOURCE": "resource",
            "WRONG_RULE": "rule",
            "WRONG_REASON": "reason",
            "WRONG_AUTHORITY_SOURCE": "authority_source",
        }.get(fault)
        if field is None:
            raise ValueError(f"unknown fault {fault}")
        value[0][field] = "MUTATED"
    return value


def mutate_raw_payload(payload: bytes | str, fault: str) -> str:
    """Inject one raw-schema/integrity fault without repairing any digest."""
    value = json.loads(payload)
    if fault == "CAPABILITY_REORDER":
        value["authorization_input"]["capabilities"].reverse()
    elif fault == "COMPONENT_REORDER":
        value["authorization_input"]["components"].reverse()
    elif fault == "MISSING_FIELD":
        value.pop("run_id")
    elif fault == "DIGEST_MISMATCH":
        value["input_digest"] = "0" * 64
    elif fault == "TASK_MISMATCH":
        value["authorization_input"]["components"][0]["request"]["task_id"] = "mutated-task"
    elif fault == "RESOURCE_CORRUPTION":
        value["authorization_input"]["components"][0]["request"]["resource"] += "-mutated"
    else:
        raise ValueError(f"unknown fault {fault}")
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
