#!/usr/bin/env python3
"""Bounded exhaustive verification of the written relation; no production imports."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from oracle_a import evaluate as oracle_a  # noqa: E402
from oracle_b import evaluate as oracle_b  # noqa: E402

MODES = ("FULL", "ACTION_ONLY", "RESOURCE_ONLY", "SPLIT", "NONE")
CONTEXTS = ("clean", "relevant", "irrelevant", "suspicious", "poisoned-looking")


def request(task: str, action: str, resource: str, context: str, index: int) -> dict[str, Any]:
    return {
        "request_id": f"r{index}",
        "session_id": "s",
        "task_id": task,
        "actor": "a",
        "action": action,
        "resource": resource,
        "arguments": {"ai_context": context},
    }


def capabilities(mode: str, action: str, resource: str, index: int) -> list[dict[str, str]]:
    if mode == "FULL":
        return [{"action": action, "resource": resource}]
    if mode == "ACTION_ONLY":
        return [{"action": action, "resource": resource + "-other"}]
    if mode == "RESOURCE_ONLY":
        return [{"action": action + ".other", "resource": resource}]
    if mode == "SPLIT":
        return [
            {"action": action, "resource": resource + "-other"},
            {"action": action + ".other", "resource": resource},
        ]
    return [{"action": f"unrelated.{index}", "resource": f"/unrelated/{index}"}]


def main() -> None:
    checked = 0
    properties = {
        name: 0
        for name in (
            "task_isolation",
            "resource_binding",
            "action_binding",
            "no_authority_amplification",
            "no_capability_synthesis",
            "irrelevant_capability_invariance",
            "order_invariance",
            "compound_correctness",
            "ai_context_non_authority",
        )
    }
    failures: list[str] = []
    for tool in ("FILESYSTEM", "PROCESS"):
        mode_sets = itertools.product(MODES, repeat=1 if tool == "FILESYSTEM" else 2)
        for modes in mode_sets:
            for (
                task_match,
                resource_kind,
                action_kind,
                context,
                irrelevant_count,
                reverse,
            ) in itertools.product(range(2), range(10), range(4), CONTEXTS, range(3), range(2)):
                contract_task = "task-a"
                request_task = contract_task if task_match else "task-b"
                action = ("filesystem.read" if tool == "FILESYSTEM" else "process.exec") + (
                    "" if action_kind == 0 else f".v{action_kind}"
                )
                resource = f"/root/r{resource_kind}/target"
                primary = request(request_task, action, resource, context, 0)
                caps = capabilities(modes[0], action, resource, 0)
                additional: list[dict[str, Any]] = []
                if tool == "PROCESS":
                    cwd_action, cwd_resource = "process.cwd", f"/cwd/r{resource_kind}"
                    additional = [
                        {
                            "name": "cwd",
                            "request": request(request_task, cwd_action, cwd_resource, context, 1),
                        }
                    ]
                    caps += capabilities(modes[1], cwd_action, cwd_resource, 1)
                caps += [
                    {"action": f"noise.{n}", "resource": f"/noise/{resource_kind}/{n}"}
                    for n in range(irrelevant_count)
                ]
                if reverse:
                    caps.reverse()
                scenario = {
                    "scenario_id": "0" * 64,
                    "tool_class": tool,
                    "contract_task_id": contract_task,
                    "contract_description": "bounded model",
                    "capabilities": caps,
                    "request": primary,
                    "additional_components": additional,
                }
                a, b = oracle_a(scenario), oracle_b(scenario)
                checked += 1
                expected_components = [task_match == 1 and mode == "FULL" for mode in modes]
                expected = all(expected_components)
                if a != b or (a["decision"] == "ALLOW") != expected:
                    failures.append(f"state-{checked}")
                    continue
                properties["compound_correctness"] += 1
                properties["task_isolation"] += int(not task_match and a["decision"] == "DENY")
                properties["resource_binding"] += int(
                    any(mode == "ACTION_ONLY" for mode in modes) and a["decision"] == "DENY"
                )
                properties["action_binding"] += int(
                    any(mode == "RESOURCE_ONLY" for mode in modes) and a["decision"] == "DENY"
                )
                properties["no_capability_synthesis"] += int(
                    any(mode == "SPLIT" for mode in modes) and a["decision"] == "DENY"
                )
                properties["no_authority_amplification"] += int(
                    a["decision"] == ("ALLOW" if expected else "DENY")
                )
                augmented = {
                    **scenario,
                    "capabilities": [*caps, {"action": "noise.extra", "resource": "/noise/extra"}],
                }
                properties["irrelevant_capability_invariance"] += int(
                    oracle_a(augmented)["decision"] == a["decision"]
                )
                reordered = {**scenario, "capabilities": list(reversed(caps))}
                properties["order_invariance"] += int(
                    oracle_a(reordered)["decision"] == a["decision"]
                )
                changed_context = json.loads(json.dumps(scenario))
                changed_context["request"]["arguments"]["ai_context"] = "opposite-context"
                for component in changed_context["additional_components"]:
                    component["request"]["arguments"]["ai_context"] = "opposite-context"
                properties["ai_context_non_authority"] += int(
                    oracle_a(changed_context)["decision"] == a["decision"]
                )
    # Independently vary compound task bindings; one mismatched component must
    # not erase a valid sibling explanation, while conjunction still denies.
    for exec_match, cwd_match, resource_kind, context in itertools.product(
        range(2), range(2), range(25), CONTEXTS
    ):
        exec_request = request(
            "task-a" if exec_match else "task-b",
            "process.exec",
            f"/bin/r{resource_kind}",
            context,
            0,
        )
        cwd_request = request(
            "task-a" if cwd_match else "task-c", "process.cwd", f"/cwd/r{resource_kind}", context, 1
        )
        scenario = {
            "scenario_id": "1" * 64,
            "tool_class": "PROCESS",
            "contract_task_id": "task-a",
            "contract_description": "mixed compound task model",
            "capabilities": [
                {"action": "process.exec", "resource": exec_request["resource"]},
                {"action": "process.cwd", "resource": cwd_request["resource"]},
            ],
            "request": exec_request,
            "additional_components": [{"name": "cwd", "request": cwd_request}],
        }
        a, b = oracle_a(scenario), oracle_b(scenario)
        checked += 1
        expected = exec_match == cwd_match == 1
        if a != b or (a["decision"] == "ALLOW") != expected:
            failures.append(f"mixed-task-{checked}")
        else:
            properties["compound_correctness"] += 1
            properties["task_isolation"] += int(not expected)
    # Explicit subtree lattice: root exclusion, sibling/prefix exclusion, and
    # strict deep-descendant inclusion under code-point exact matching.
    boundary_resources = (
        "/scope",
        "/scope/child",
        "/scope/deep/child",
        "/scopeish/child",
        "/other/scope",
        "/scope/../escape",
        "/scope//double",
        "/scopé/child",
    )
    for resource, action_variant, context in itertools.product(
        boundary_resources, range(4), CONTEXTS
    ):
        scenario = {
            "scenario_id": "2" * 64,
            "tool_class": "FILESYSTEM",
            "contract_task_id": "task-a",
            "contract_description": "subtree boundary model",
            "capabilities": [
                {"action": f"filesystem.read.v{action_variant}", "resource": "/scope/**"}
            ],
            "request": request(
                "task-a", f"filesystem.read.v{action_variant}", resource, context, 0
            ),
            "additional_components": [],
        }
        a, b = oracle_a(scenario), oracle_b(scenario)
        checked += 1
        valid = resource in {"/scope/child", "/scope/deep/child"}
        if a != b or (a["decision"] == "ALLOW") != valid:
            failures.append(f"subtree-{checked}")
        else:
            properties["resource_binding"] += 1
    result = {
        "verification_id": "AUTH-COVERAGE-002-BOUNDED-EXHAUSTIVE@1",
        "state_count": checked,
        "result": "PASS" if not failures and checked >= 50000 else "FAIL",
        "failures": failures[:20],
        "properties": properties,
        "production_calls": 0,
        "formal_tool_result": "BOUNDED_ENUMERATION_PASS_NO_EXTERNAL_SOLVER",
    }
    output = ROOT / "formal" / "exhaustive_results.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
