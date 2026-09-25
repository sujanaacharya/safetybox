"""Oracle B: independently structured benchmark authority interpreter.

It intentionally does not import Oracle A, its helpers, or production policy
code.  Only the data-only schema validator is shared.
"""

from __future__ import annotations

from typing import Any

from schema import validate_scenario

ORACLE_ID = "AUTH-COVERAGE-001-ORACLE-B@1"


def _subtree_contains(parent: str, candidate: str) -> bool:
    parent_bits = parent.split("/")
    child_bits = candidate.split("/")
    valid_parent = parent.startswith("/") and len(parent_bits) > 1 and all(parent_bits[1:])
    valid_child = candidate.startswith("/") and len(child_bits) > 1 and all(child_bits[1:])
    if not valid_parent or not valid_child:
        return False
    if any(bit in {".", ".."} for bit in parent_bits[1:] + child_bits[1:]):
        return False
    return len(child_bits) > len(parent_bits) and child_bits[: len(parent_bits)] == parent_bits


def evaluate(scenario: dict[str, Any]) -> dict[str, Any]:
    """Interpret capability rows as independent grants, then conjunct components."""
    validate_scenario(scenario)
    req: dict[str, Any] = scenario["request"]
    authority: dict[str, Any] = scenario["contract"]
    bound = req["task_id"] == authority["task_id"]
    grants: dict[tuple[str, str], list[str]] = {}
    if bound:
        for row in authority["capabilities"]:
            for operation in req["components"]:
                same_verb = row["action"] == operation["action"]
                same_object = row["resource"] == operation["resource"]
                descendant = row["scope_type"] == "SUBTREE" and _subtree_contains(
                    row["resource"].removesuffix("/**"), operation["resource"]
                )
                if same_verb and (same_object if row["scope_type"] == "EXACT" else descendant):
                    key = (operation["component"], operation["resource"])
                    grants.setdefault(key, []).append(row["capability_id"])
    verdicts: dict[str, str] = {}
    selected: dict[str, str | None] = {}
    for operation in req["components"]:
        ids = sorted(grants.get((operation["component"], operation["resource"]), []))
        verdicts[operation["component"]] = "ALLOW" if ids else "DENY"
        selected[operation["component"]] = ids[0] if ids else None
    overall = "ALLOW" if set(verdicts.values()) == {"ALLOW"} else "DENY"
    if req["task_id"] != authority["task_id"]:
        code, explanation = "AUTH-TASK-BINDING", "request task differs from contract task"
    elif overall == "ALLOW":
        code, explanation = (
            "AUTH-ALL-COMPONENTS",
            "every component has one covering capability",
        )
    else:
        code, explanation = (
            "AUTH-COMPONENT-DENY",
            "at least one component lacks a covering capability",
        )
    return {
        "scenario_id": scenario["scenario_id"],
        "decision": overall,
        "component_decisions": verdicts,
        "rule": code,
        "reason": explanation,
        "authority_source": authority["contract_id"],
        "matching_capabilities": selected,
        "explanation": {
            "subject": req["subject_id"],
            "session": req["session_id"],
            "task": req["task_id"],
            "action": [operation["action"] for operation in req["components"]],
            "resource": [operation["resource"] for operation in req["components"]],
            "capability": selected,
            "rule": code,
            "authority_source": authority["contract_id"],
            "component": verdicts,
            "decision": overall,
            "reason": explanation,
        },
    }
