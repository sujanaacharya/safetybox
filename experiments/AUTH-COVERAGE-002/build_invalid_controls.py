#!/usr/bin/env python3
"""Materialize executable invalid-structure controls outside primary denominators."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from oracle_a import evaluate as oracle_a
from oracle_b import evaluate as oracle_b
from schema import SchemaError, validate_runtime

OUTPUT = Path(__file__).resolve().parent / "corpus/analysis/invalid_structure_controls.json"


def base(index: int) -> dict[str, Any]:
    return {
        "scenario_id": f"invalid-control-{index}",
        "tool_class": "FILESYSTEM",
        "contract_task_id": "task-control",
        "contract_description": "invalid control",
        "capabilities": [{"action": "filesystem.read", "resource": "/control/item"}],
        "request": {
            "request_id": f"request-{index}",
            "session_id": "session",
            "task_id": "task-control",
            "actor": "control",
            "action": "filesystem.read",
            "resource": "/control/item",
            "arguments": {},
        },
        "additional_components": [],
    }


def mutate(value: dict[str, Any], stratum: str) -> None:
    if stratum == "EMPTY_ACTION":
        value["request"]["action"] = ""
    elif stratum == "EMPTY_RESOURCE":
        value["request"]["resource"] = ""
    elif stratum == "INVALID_SUBTREE_SCOPE":
        value["capabilities"][0]["resource"] = "/control/../escape/**"
    elif stratum == "NONCANONICAL_PATH":
        value["request"]["resource"] = "/control//item"
    elif stratum == "UNSUPPORTED_TOOL_SHAPE":
        value["tool_class"] = "NETWORK"
    elif stratum == "DUPLICATE_COMPONENT_NAMES":
        component = {"name": "cwd", "request": copy.deepcopy(value["request"])}
        value["tool_class"] = "PROCESS"
        value["additional_components"] = [component, copy.deepcopy(component)]
    elif stratum == "MALFORMED_CAPABILITY_OBJECT":
        value["capabilities"][0].pop("resource")
    elif stratum == "MISMATCHED_PROCESS_SHAPE":
        value["tool_class"] = "PROCESS"
    else:
        raise AssertionError(stratum)


def main() -> None:
    strata = (
        "EMPTY_ACTION",
        "EMPTY_RESOURCE",
        "INVALID_SUBTREE_SCOPE",
        "NONCANONICAL_PATH",
        "UNSUPPORTED_TOOL_SHAPE",
        "DUPLICATE_COMPONENT_NAMES",
        "MALFORMED_CAPABILITY_OBJECT",
        "MISMATCHED_PROCESS_SHAPE",
    )
    cases = []
    for stratum in strata:
        for occurrence in range(6):
            value = base(len(cases))
            mutate(value, stratum)
            rejected = False
            try:
                validate_runtime(value)
            except (SchemaError, KeyError, TypeError, ValueError):
                rejected = True
            a, b = oracle_a(value), oracle_b(value)
            if (
                not rejected
                or a != b
                or a != {"decision": "DENY", "rule": "AUTH.INVALID_STRUCTURE", "components": {}}
            ):
                raise AssertionError((stratum, occurrence, rejected, a, b))
            cases.append(
                {
                    "control_id": f"invalid-{len(cases):02d}",
                    "stratum": stratum,
                    "runtime_candidate": value,
                    "schema_rejected": rejected,
                    "oracle_a": a,
                    "oracle_b": b,
                    "expected_decision": "DENY",
                }
            )
    payload = {
        "control_registry_id": "AUTH-COVERAGE-002-INVALID-STRUCTURE-CONTROLS@1",
        "primary_accuracy_denominator": False,
        "production_execution_authorized": False,
        "case_count": len(cases),
        "cases": cases,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
