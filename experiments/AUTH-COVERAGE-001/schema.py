"""Data-only schema validation for AUTH-COVERAGE-001.

This module deliberately contains no authorization logic.  Corpus construction,
the two oracles, and future runners can validate the same serialized shape
without sharing a decision implementation.
"""

from __future__ import annotations

from typing import Any

SCHEMA_ID = "AUTH-COVERAGE-001-SCENARIO@1"
CORPUS_ID = "AUTH-COVERAGE-001-CORPUS@1"
PROTOCOL_ID = "AUTH-COVERAGE-001-PROTOCOL@1"
TOOLS = frozenset({"FILESYSTEM", "PROCESS"})
SCOPES = frozenset({"EXACT", "SUBTREE"})


class SchemaError(ValueError):
    """A serialized benchmark object is structurally invalid."""


def _nonempty(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{location} must be a non-empty string")
    return value


def validate_scenario(value: dict[str, Any]) -> None:
    """Validate fields and uniqueness without deriving authorization truth."""
    if value.get("schema_id") != SCHEMA_ID:
        raise SchemaError("unknown schema_id")
    _nonempty(value.get("scenario_id"), "scenario_id")
    if value.get("split") not in {"DEV", "VALIDATION", "HELD_OUT"}:
        raise SchemaError("invalid split")
    request = value.get("request")
    contract = value.get("contract")
    if not isinstance(request, dict) or not isinstance(contract, dict):
        raise SchemaError("request and contract must be objects")
    for field in ("subject_id", "session_id", "task_id", "contract_id", "tool"):
        _nonempty(request.get(field), f"request.{field}")
    if request["tool"] not in TOOLS:
        raise SchemaError("unsupported request.tool")
    components = request.get("components")
    if not isinstance(components, list) or not components:
        raise SchemaError("request.components must be a non-empty list")
    names: set[str] = set()
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise SchemaError(f"request.components[{index}] must be an object")
        name = _nonempty(component.get("component"), f"component[{index}].component")
        _nonempty(component.get("action"), f"component[{index}].action")
        _nonempty(component.get("resource"), f"component[{index}].resource")
        if name in names:
            raise SchemaError("component names must be unique")
        names.add(name)
    data = request.get("operation_data")
    if not isinstance(data, dict):
        raise SchemaError("request.operation_data must be an object")
    argv = data.get("argv")
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        raise SchemaError("operation_data.argv must be a string list")
    _nonempty(contract.get("contract_id"), "contract.contract_id")
    _nonempty(contract.get("task_id"), "contract.task_id")
    capabilities = contract.get("capabilities")
    if not isinstance(capabilities, list):
        raise SchemaError("contract.capabilities must be a list")
    capability_ids: set[str] = set()
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            raise SchemaError(f"capabilities[{index}] must be an object")
        cap_id = _nonempty(capability.get("capability_id"), f"capabilities[{index}].id")
        _nonempty(capability.get("action"), f"capabilities[{index}].action")
        _nonempty(capability.get("resource"), f"capabilities[{index}].resource")
        if capability.get("scope_type") not in SCOPES:
            raise SchemaError("unsupported capability scope_type")
        if capability.get("scope_type") == "SUBTREE" and not capability["resource"].endswith("/**"):
            raise SchemaError("subtree capability resources must use production /** serialization")
        if capability.get("scope_type") == "EXACT" and capability["resource"].endswith("/**"):
            raise SchemaError("exact capability resources cannot use production subtree syntax")
        if cap_id in capability_ids:
            raise SchemaError("capability_id values must be unique")
        capability_ids.add(cap_id)
    if request["tool"] == "FILESYSTEM" and len(components) != 1:
        raise SchemaError("filesystem requests have exactly one component")
    if request["tool"] == "PROCESS" and {item["component"] for item in components} != {
        "exec",
        "cwd",
    }:
        raise SchemaError("process requests require exec and cwd components")
