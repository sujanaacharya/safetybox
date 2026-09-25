"""Data-only schemas for AUTH-COVERAGE-002; contains no authorization logic."""

from __future__ import annotations

PROTOCOL_ID = "AUTH-COVERAGE-002-PROTOCOL@1"
SPEC_ID = "AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1"
CORPUS_ID = "AUTH-COVERAGE-002-CORPUS@1"
RUNTIME_SCHEMA_ID = "AUTH-COVERAGE-002-RUNTIME@1"
ANALYSIS_SCHEMA_ID = "AUTH-COVERAGE-002-ANALYSIS@1"
TOOLS = frozenset({"FILESYSTEM", "PROCESS"})


class SchemaError(ValueError):
    """The supplied object is outside the frozen benchmark schema."""


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{name} must be nonempty text")
    return value


def _request(value: object, name: str) -> None:
    if not isinstance(value, dict) or set(value) != {
        "request_id",
        "session_id",
        "task_id",
        "actor",
        "action",
        "resource",
        "arguments",
    }:
        raise SchemaError(f"{name} has invalid fields")
    for field in ("request_id", "session_id", "task_id", "actor", "action", "resource"):
        _text(value[field], f"{name}.{field}")
    if not isinstance(value["arguments"], dict):
        raise SchemaError(f"{name}.arguments must be an object")


def validate_runtime(value: object) -> None:
    """Validate the exact label-free schema consumed by the frozen runner."""
    if not isinstance(value, dict) or set(value) != {
        "scenario_id",
        "tool_class",
        "contract_task_id",
        "contract_description",
        "capabilities",
        "request",
        "additional_components",
    }:
        raise SchemaError("runtime scenario has invalid fields")
    scenario_id = _text(value["scenario_id"], "scenario_id")
    if len(scenario_id) != 64 or any(ch not in "0123456789abcdef" for ch in scenario_id):
        raise SchemaError("scenario_id must be a 256-bit lowercase hex token")
    if value["tool_class"] not in TOOLS:
        raise SchemaError("unsupported tool_class")
    _text(value["contract_task_id"], "contract_task_id")
    if not isinstance(value["contract_description"], str):
        raise SchemaError("contract_description must be text")
    capabilities = value["capabilities"]
    if not isinstance(capabilities, list):
        raise SchemaError("capabilities must be an ordered array")
    seen: set[tuple[str, str]] = set()
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict) or set(capability) != {"action", "resource"}:
            raise SchemaError(f"capability {index} has invalid fields")
        pair = (
            _text(capability["action"], "capability.action"),
            _text(capability["resource"], "capability.resource"),
        )
        if pair in seen:
            raise SchemaError("canonical valid corpus excludes duplicate capability values")
        seen.add(pair)
    _request(value["request"], "request")
    components = value["additional_components"]
    if not isinstance(components, list):
        raise SchemaError("additional_components must be an array")
    names: set[str] = set()
    for index, component in enumerate(components):
        if not isinstance(component, dict) or set(component) != {"name", "request"}:
            raise SchemaError(f"component {index} has invalid fields")
        name = _text(component["name"], "component.name")
        if name in names:
            raise SchemaError("component names must be unique")
        names.add(name)
        _request(component["request"], f"component[{index}].request")
    if value["tool_class"] == "FILESYSTEM" and components:
        raise SchemaError("filesystem has one primary component")
    if value["tool_class"] == "PROCESS" and [item["name"] for item in components] != ["cwd"]:
        raise SchemaError("process requires ordered exec(primary), cwd(additional)")


def validate_analysis_record(value: object) -> None:
    if not isinstance(value, dict):
        raise SchemaError("analysis record must be an object")
    required = {
        "scenario_id",
        "split",
        "expected_decision",
        "component_decisions",
        "families",
        "difficulty",
        "authority_distance",
        "pressure_dimension",
        "generation_template",
        "oracle_a",
        "oracle_b",
        "owasp_precursors",
        "expected_explanation",
    }
    if set(value) != required:
        raise SchemaError("analysis record has invalid fields")
    _text(value["scenario_id"], "analysis.scenario_id")
    if value["split"] not in {"DEV", "VALIDATION", "HELD_OUT"}:
        raise SchemaError("invalid split")
    if value["expected_decision"] not in {"ALLOW", "DENY"}:
        raise SchemaError("invalid expected decision")
    if value["difficulty"] not in {"EASY", "MODERATE", "HARD", "ADVERSARIAL"}:
        raise SchemaError("invalid difficulty")
    if value["pressure_dimension"] not in {
        "TASK_BINDING",
        "ACTION_BINDING",
        "RESOURCE_BINDING",
        "CAPABILITY_MATCH",
        "CAPABILITY_SYNTHESIS",
        "COMPOUND_AUTH",
        "CROSS_TASK_REUSE",
    }:
        raise SchemaError("invalid pressure dimension")
