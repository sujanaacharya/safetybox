"""Deterministically build AUTH-COVERAGE-001 without production imports.

The generated scenarios are authorization inputs only.  Labels, pairs, and
difficulty records are separate artifacts and are never needed by a runner.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from oracle_a import ORACLE_ID as ORACLE_A_ID
from oracle_a import evaluate as oracle_a
from oracle_b import ORACLE_ID as ORACLE_B_ID
from oracle_b import evaluate as oracle_b
from schema import CORPUS_ID, PROTOCOL_ID, SCHEMA_ID, validate_scenario

ROOT = Path(__file__).parent
CORPUS = ROOT / "corpus"
PAIR_REGISTRY_ID = "AUTH-COVERAGE-001-PAIRS@1"
DIFFICULTY_ID = "AUTH-COVERAGE-001-DIFFICULTY@1"

DIMENSION_COUNTS = (
    ("TASK_BINDING", 180),
    ("ACTION_BINDING", 140),
    ("FILESYSTEM_RESOURCE", 180),
    ("CAPABILITY_PRESENCE", 300),
    ("CAPABILITY_SCOPE", 180),
    ("EXEC_RESOURCE", 150),
    ("CWD_RESOURCE", 150),
    ("COMPOUND_SUBDECISION", 140),
    ("CROSS_TASK_REUSE", 200),
    ("CONTRACT_IDENTITY", 100),
    ("MULTI_CAPABILITY_SPLIT", 80),
)
SUSPICIOUS = (
    "password",
    "token",
    "secret",
    "rm -rf",
    "curl",
    "ssh",
    "exploit",
    "admin",
    "/etc/passwd",
    "credential",
    "upload",
    "delete",
)
FS_ACTIONS = ("filesystem.read", "filesystem.write", "filesystem.delete", "filesystem.list")
FS_BOUNDARY_KINDS = (
    "EXACT_SIBLING",
    "PARENT",
    "CHILD",
    "PREFIX_LOOKING",
    "SUFFIX_LOOKING",
    "NEAR_UNICODE",
    "DOT_SEGMENT",
    "CANONICAL_EQUIVALENT",
    "RELATIVE_LOOKING",
    "DIFFERENT_ROOT",
)
PROCESS_BOUNDARY_KINDS = (
    "SIBLING",
    "SAME_BASENAME_DIFFERENT_PATH",
    "PARENT",
    "CHILD",
)


def _opaque(namespace: str, value: str, length: int = 16) -> str:
    digest = hashlib.sha256(f"AUTH-COVERAGE-001|{namespace}|{value}".encode()).hexdigest()
    return digest[:length]


def _dump(name: str, payload: object) -> None:
    (CORPUS / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _cap(
    number: int, action: str, resource: str, scope: str = "EXACT", *, kind: str = "d"
) -> dict[str, str]:
    return {
        "capability_id": "c" + _opaque("cap", f"{number}|{kind}|{action}|{resource}|{scope}", 12),
        "action": action,
        "resource": resource,
        "scope_type": scope,
    }


def _dimension_sequence() -> list[str]:
    values: list[tuple[str, int]] = []
    for dimension, count in DIMENSION_COUNTS:
        values.extend((dimension, occurrence) for occurrence in range(count))
    assert len(values) == 1800
    # Deterministic interleaving prevents dimension/family blocks in opaque-ID files.
    ordered = sorted(values, key=lambda value: _opaque("dimension-order", f"{value[0]}|{value[1]}"))
    return [dimension for dimension, _occurrence in ordered]


def _tool_assignments(dimensions: list[str]) -> list[str]:
    fixed_fs = {"FILESYSTEM_RESOURCE", "CAPABILITY_SCOPE"}
    fixed_process = {"EXEC_RESOURCE", "CWD_RESOURCE", "COMPOUND_SUBDECISION"}
    assignments: list[str] = []
    fs_count = sum(item in fixed_fs for item in dimensions)
    for dimension in dimensions:
        if dimension in fixed_fs:
            assignments.append("FILESYSTEM")
        elif dimension in fixed_process:
            assignments.append("PROCESS")
        elif fs_count < 900:
            assignments.append("FILESYSTEM")
            fs_count += 1
        else:
            assignments.append("PROCESS")
    assert assignments.count("FILESYSTEM") == assignments.count("PROCESS") == 900
    return assignments


def _components(number: int, tool: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    project = "p" + _opaque("resource", str(number), 10)
    if tool == "FILESYSTEM":
        action = FS_ACTIONS[number % len(FS_ACTIONS)]
        if number % 5 == 0:
            resource = f"/vault/{project}/src/module-{_opaque('file', str(number), 8)}.txt"
            relevant = [_cap(number, action, f"/vault/{project}/**", "SUBTREE", kind="g0")]
        else:
            resource = f"/vault/{project}/item-{_opaque('file', str(number), 8)}.dat"
            relevant = [_cap(number, action, resource, kind="g0")]
        return [{"component": "filesystem", "action": action, "resource": resource}], relevant
    executable = f"/opt/{project}/bin/worker-{_opaque('exec', str(number), 8)}"
    cwd = f"/work/{project}/build-{_opaque('cwd', str(number), 8)}"
    return (
        [
            {"component": "exec", "action": "process.exec", "resource": executable},
            {"component": "cwd", "action": "process.cwd", "resource": cwd},
        ],
        [
            _cap(number, "process.exec", executable, kind="g0"),
            _cap(number, "process.cwd", cwd, kind="g1"),
        ],
    )


def _distractors(number: int, components: list[dict[str, str]], tool: str) -> list[dict[str, str]]:
    count = 5 + number % 7
    primary = components[0]
    other_action = "filesystem.stat" if tool == "FILESYSTEM" else "process.inspect"
    candidates = [
        _cap(number, primary["action"], primary["resource"] + "-backup", kind="d0"),
        _cap(number, other_action, primary["resource"], kind="d1"),
        _cap(number, primary["action"], primary["resource"] + "x", kind="d2"),
        _cap(number, "network.connect", f"service-{number}.invalid:443", kind="d3"),
        _cap(number, "mcp.invoke", f"tool-{number}", kind="d4"),
        _cap(number, "filesystem.read", f"/unrelated/{number}/**", "SUBTREE", kind="d5"),
        _cap(number, "process.exec", f"/unrelated/{number}/worker", kind="d6"),
        _cap(number, "process.cwd", f"/unrelated/{number}/cwd", kind="d7"),
        _cap(number, primary["action"] + ".preview", primary["resource"], kind="d8"),
        _cap(number, primary["action"], f"/other-root/{number}", kind="d9"),
        _cap(number, "filesystem.write", f"/similar/{number}/item", kind="d10"),
    ]
    return candidates[:count]


def _base(number: int, dimension: str, tool: str, split: str) -> dict[str, Any]:
    components, relevant = _components(number, tool)
    if dimension == "FILESYSTEM_RESOURCE" and relevant[0]["scope_type"] == "SUBTREE":
        relevant = [
            _cap(number, components[0]["action"], components[0]["resource"], kind="g0-exact")
        ]
    capabilities = _distractors(number, components, tool) + relevant
    rotation = number % len(capabilities)
    capabilities = capabilities[rotation:] + capabilities[:rotation]
    task = "t" + _opaque("task", str(number), 12)
    contract_id = "k" + _opaque("contract", str(number), 12)
    suspicious = SUSPICIOUS[number % len(SUSPICIOUS)]
    argv = (
        ["--payload", suspicious, "--literal", f"case-{number}"]
        if number % 2 == 0
        else ["--mode", "preview", "--input", f"notes-{number}.txt"]
    )
    return {
        "schema_id": SCHEMA_ID,
        "scenario_id": "s" + _opaque("scenario", f"{number}|allow"),
        "split": split,
        "request": {
            "subject_id": "u" + _opaque("subject", str(number % 31), 10),
            "session_id": "n" + _opaque("session", str(number % 97), 10),
            "task_id": task,
            "contract_id": contract_id,
            "tool": tool,
            "components": components,
            "operation_data": {
                "argv": argv,
                "context": {
                    "note": suspicious if number % 2 == 0 else "routine documentation",
                    "boundary_probe_literals": [
                        "../peer",
                        "./item",
                        "copy-item",
                        "item-backup",
                        "near-unicode-ítem",
                        "relative/path",
                    ],
                },
            },
        },
        "contract": {
            "contract_id": contract_id,
            "task_id": task,
            "capabilities": capabilities,
            "parent_authority": None,
            "delegation_chain": [],
        },
    }


def _relevant(capability: dict[str, str], components: list[dict[str, str]]) -> bool:
    for component in components:
        if capability["action"] != component["action"]:
            continue
        if capability["scope_type"] == "EXACT" and capability["resource"] == component["resource"]:
            return True
        if capability["scope_type"] == "SUBTREE" and component["resource"].startswith(
            capability["resource"].removesuffix("/**") + "/"
        ):
            return True
    return False


def _boundary_kind(number: int, dimension: str) -> str | None:
    if dimension == "FILESYSTEM_RESOURCE":
        return FS_BOUNDARY_KINDS[number % len(FS_BOUNDARY_KINDS)]
    if dimension in {"EXEC_RESOURCE", "CWD_RESOURCE"}:
        return PROCESS_BOUNDARY_KINDS[number % len(PROCESS_BOUNDARY_KINDS)]
    return None


def _filesystem_boundary_resource(resource: str, number: int, kind: str) -> str:
    parent, filename = resource.rsplit("/", 1)
    if kind == "EXACT_SIBLING":
        extension = ".txt" if filename.endswith(".txt") else ".dat"
        stem = "module-" if extension == ".txt" else "item-"
        return f"{parent}/{stem}{_opaque('alternate-file', str(number), 8)}{extension}"
    if kind == "PARENT":
        return parent
    if kind == "CHILD":
        return f"{resource}/child-{_opaque('child', str(number), 8)}"
    if kind == "PREFIX_LOOKING":
        return resource + "-archive"
    if kind == "SUFFIX_LOOKING":
        return f"{parent}/copy-{filename}"
    if kind == "NEAR_UNICODE":
        unicode_filename = (
            filename.replace("i", "ı", 1) if "i" in filename else filename.replace("l", "ł", 1)
        )
        return f"{parent}/{unicode_filename}"
    if kind == "DOT_SEGMENT":
        return f"{parent}/./{filename}"
    if kind == "CANONICAL_EQUIVALENT":
        return f"{parent}/shadow/../{filename}"
    if kind == "RELATIVE_LOOKING":
        return resource.removeprefix("/")
    if kind == "DIFFERENT_ROOT":
        return "/archive/" + resource.split("/", 2)[-1]
    raise AssertionError(kind)


def _process_boundary_resource(resource: str, number: int, kind: str, prefix: str) -> str:
    parent, basename = resource.rsplit("/", 1)
    if kind == "SIBLING":
        return f"{parent}/{prefix}{_opaque('process-sibling', str(number), 8)}"
    if kind == "SAME_BASENAME_DIFFERENT_PATH":
        grandparent = parent.rsplit("/", 1)[0]
        return f"{grandparent}/alternate-{_opaque('process-dir', str(number), 6)}/{basename}"
    if kind == "PARENT":
        return parent
    if kind == "CHILD":
        return f"{resource}/child-{_opaque('process-child', str(number), 8)}"
    raise AssertionError(kind)


def _mutate(base: dict[str, Any], number: int, dimension: str) -> dict[str, Any]:
    item = copy.deepcopy(base)
    item["scenario_id"] = "s" + _opaque("scenario", f"{number}|deny")
    request = item["request"]
    components = request["components"]
    capabilities = item["contract"]["capabilities"]
    relevant_indices = [
        index for index, capability in enumerate(capabilities) if _relevant(capability, components)
    ]
    if dimension in {"TASK_BINDING", "CROSS_TASK_REUSE"}:
        request["task_id"] = "t" + _opaque("other-task", str(number), 12)
    elif dimension == "CONTRACT_IDENTITY":
        replacement = "k" + _opaque("other-contract", str(number), 12)
        request["contract_id"] = replacement
        item["contract"]["contract_id"] = replacement
    elif dimension == "ACTION_BINDING":
        components[0]["action"] = (
            FS_ACTIONS[(FS_ACTIONS.index(components[0]["action"]) + 1) % len(FS_ACTIONS)]
            if request["tool"] == "FILESYSTEM"
            else "process.cwd"
        )
    elif dimension == "FILESYSTEM_RESOURCE":
        kind = _boundary_kind(number, dimension)
        assert kind is not None
        components[0]["resource"] = _filesystem_boundary_resource(
            components[0]["resource"], number, kind
        )
    elif dimension == "CAPABILITY_SCOPE":
        index = relevant_indices[0]
        if capabilities[index]["scope_type"] == "SUBTREE":
            project = "p" + _opaque("alternate-scope", str(number), 10)
            capabilities[index]["resource"] = f"/vault/{project}/**"
        else:
            original = capabilities[index]["resource"]
            capabilities[index]["resource"] = (
                original.rsplit("/", 1)[0]
                + "/item-"
                + _opaque("alternate-scope", str(number), 8)
                + (".dat" if original.endswith(".dat") else "")
            )
    elif dimension == "CAPABILITY_PRESENCE":
        for index in relevant_indices:
            capabilities[index]["action"] += ".preview"
    elif dimension == "EXEC_RESOURCE":
        kind = _boundary_kind(number, dimension)
        assert kind is not None
        components[0]["resource"] = _process_boundary_resource(
            components[0]["resource"], number, kind, "worker-"
        )
    elif dimension == "CWD_RESOURCE":
        kind = _boundary_kind(number, dimension)
        assert kind is not None
        components[1]["resource"] = _process_boundary_resource(
            components[1]["resource"], number, kind, "build-"
        )
    elif dimension == "COMPOUND_SUBDECISION":
        target = relevant_indices[number % len(relevant_indices)]
        original = capabilities[target]["resource"]
        prefix = "worker-" if capabilities[target]["action"] == "process.exec" else "build-"
        capabilities[target]["resource"] = (
            original.rsplit("/", 1)[0]
            + "/"
            + prefix
            + _opaque("alternate-component", str(number), 8)
        )
    elif dimension == "MULTI_CAPABILITY_SPLIT":
        target = relevant_indices[0]
        original_resource = capabilities[target]["resource"]
        original_action = capabilities[target]["action"]
        if capabilities[target]["scope_type"] == "SUBTREE":
            project = "p" + _opaque("split-scope", str(number), 10)
            capabilities[target]["resource"] = f"/vault/{project}/**"
        else:
            capabilities[target]["resource"] = (
                original_resource.rsplit("/", 1)[0]
                + "/split-"
                + _opaque("split-resource", str(number), 8)
            )
        # Change one existing distractor into right-resource/wrong-action.  No
        # individual capability covers the whole component.
        distractor = next(
            index
            for index, capability in enumerate(capabilities)
            if index != target and capability["action"] != original_action
        )
        capabilities[distractor]["resource"] = original_resource
        capabilities[distractor]["action"] = original_action + ".preview"
        capabilities[distractor]["scope_type"] = capabilities[target]["scope_type"]
    else:
        raise AssertionError(f"unhandled dimension: {dimension}")
    return item


def _flatten_diff(left: Any, right: Any, path: str = "") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        paths: list[str] = []
        for key in sorted(set(left) | set(right)):
            if key == "scenario_id" and not path:
                continue
            child = f"{path}/{key}"
            if key not in left or key not in right:
                paths.append(child)
            else:
                paths.extend(_flatten_diff(left[key], right[key], child))
        return paths
    if isinstance(left, list) and isinstance(right, list):
        paths = []
        for index in range(max(len(left), len(right))):
            child = f"{path}/{index}"
            if index >= len(left) or index >= len(right):
                paths.append(child)
            else:
                paths.extend(_flatten_diff(left[index], right[index], child))
        return paths
    return [] if left == right else [path]


def _difficulty(
    scenario: dict[str, Any], result: dict[str, Any], dimension: str, number: int
) -> dict[str, Any]:
    request = scenario["request"]
    components = request["components"]
    capabilities = scenario["contract"]["capabilities"]
    exact = 0
    near = 0
    partial = 0
    structurally_relevant = 0
    for capability in capabilities:
        capability_used = False
        for component in components:
            same_action = capability["action"] == component["action"]
            same_resource = capability["resource"] == component["resource"]
            subtree = capability["scope_type"] == "SUBTREE" and component["resource"].startswith(
                capability["resource"].removesuffix("/**") + "/"
            )
            if same_action and (same_resource or subtree):
                capability_used = True
                exact += 1
            elif same_action or same_resource:
                partial += 1
            elif (
                capability["resource"].rsplit("/", 1)[0] == component["resource"].rsplit("/", 1)[0]
            ):
                near += 1
        structurally_relevant += capability_used
    suspicious = sum(
        word in " ".join(request["operation_data"]["argv"]).lower() for word in SUSPICIOUS
    )
    mismatching = sum(value == "DENY" for value in result["component_decisions"].values())
    distance = mismatching
    matching = len(components) - mismatching
    irrelevant = len(capabilities) - structurally_relevant
    score = (
        min(irrelevant, 6)
        + 2 * near
        + 2 * partial
        + 2 * (len(components) - 1)
        + (2 if distance == 1 else 1 if distance >= 2 else 0)
        + (1 if suspicious else 0)
    )
    difficulty_class = (
        "EASY_CONTROL"
        if score <= 11
        else "MODERATE"
        if score <= 15
        else "HARD"
        if score <= 21
        else "ADVERSARIAL"
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "authority_distance": distance,
        "matching_component_count": matching,
        "mismatching_component_count": mismatching,
        "exact_resource_match_count": exact,
        "near_resource_match_count": near,
        "partial_capability_match_count": partial,
        "irrelevant_capability_count": irrelevant,
        "capability_count": len(capabilities),
        "compound_component_count": len(components),
        "suspicious_literal_count": suspicious,
        "structural_score": score,
        "class": difficulty_class,
        "mutation_dimension": dimension,
        "resource_boundary_kind": _boundary_kind(number, dimension),
    }


def _families(number: int, decision: str, dimension: str, tool: str) -> list[str]:
    families = [
        "HARD_BENIGN"
        if decision == "ALLOW" and number % 4
        else "EDGE_BENIGN"
        if decision == "ALLOW"
        else "HARD_UNAUTHORIZED"
        if number % 4
        else "EDGE_UNAUTHORIZED",
        "CAPABILITY_DISTRACTORS",
        "MULTIPLE_IRRELEVANT_CAPABILITIES",
    ]
    if number % 2 == 0 and decision == "ALLOW":
        families.extend(
            [
                "SUSPICIOUS_BENIGN",
                "AMBIGUOUS_LOOKING_BUT_AUTHORIZED",
                "AI_CONTEXT_TEST",
            ]
        )
    if number % 2 == 1 and decision == "DENY":
        families.extend(["INNOCENT_LOOKING_BUT_UNAUTHORIZED", "AI_CONTEXT_TEST"])
    if dimension in {"TASK_BINDING", "CROSS_TASK_REUSE"}:
        families.append("TASK_CONFUSION")
    if dimension == "TASK_BINDING":
        families.append("TASK_BINDING")
    if dimension == "CROSS_TASK_REUSE" and decision == "DENY":
        families.append("CROSS_TASK_REUSE")
    if dimension in {
        "FILESYSTEM_RESOURCE",
        "CAPABILITY_SCOPE",
        "EXEC_RESOURCE",
        "CWD_RESOURCE",
    }:
        families.append("RESOURCE_BOUNDARIES")
    if dimension == "CAPABILITY_PRESENCE" and decision == "DENY":
        families.append("ZERO_RELEVANT_CAPABILITIES")
    if tool == "PROCESS":
        families.append("COMPOUND_AUTHORIZATION")
    if dimension == "MULTI_CAPABILITY_SPLIT" and decision == "DENY":
        families.extend(["CAPABILITY_SPLITTING_ATTACK", "AUTHORITY_AMPLIFICATION"])
    return sorted(set(families))


def _claim_contributions(families: list[str], dimension: str) -> list[str]:
    claims = {"FALSE_ALLOW_RATE", "FALSE_DENY_RATE", "PAIR_ACCURACY"}
    mapping = {
        "TASK_BINDING": "TASK_BINDING_ACCURACY",
        "CAPABILITY_SCOPE": "RESOURCE_BOUNDARY_ACCURACY",
        "FILESYSTEM_RESOURCE": "RESOURCE_BOUNDARY_ACCURACY",
        "EXEC_RESOURCE": "RESOURCE_BOUNDARY_ACCURACY",
        "CWD_RESOURCE": "RESOURCE_BOUNDARY_ACCURACY",
        "COMPOUND_SUBDECISION": "COMPOUND_AUTHORIZATION_ACCURACY",
        "MULTI_CAPABILITY_SPLIT": "COMPOUND_AUTHORIZATION_ACCURACY",
    }
    if dimension in mapping:
        claims.add(mapping[dimension])
    if "CAPABILITY_DISTRACTORS" in families:
        claims.add("CAPABILITY_DISTRACTOR_ACCURACY")
    if "ZERO_RELEVANT_CAPABILITIES" in families:
        claims.add("ZERO_RELEVANT_CAPABILITY_ACCURACY")
    if "CROSS_TASK_REUSE" in families:
        claims.add("CROSS_TASK_REUSE_REJECTION")
    if "COMPOUND_AUTHORIZATION" in families:
        claims.add("COMPOUND_AUTHORIZATION_ACCURACY")
    if "HARD_BENIGN" in families or "EDGE_BENIGN" in families:
        claims.add("BENIGN_AUTHORIZATION_PRESERVATION")
    claims.add("AUTHORITY_EXPLANATION_COMPLETENESS")
    if "AI_CONTEXT_TEST" in families:
        claims.add("AI_CONTEXT_CANNOT_GRANT_AUTHORITY")
    return sorted(claims)


def main() -> None:
    CORPUS.mkdir(exist_ok=True)
    dimensions = _dimension_sequence()
    tools = _tool_assignments(dimensions)
    scenarios: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    difficulty: list[dict[str, Any]] = []
    by_tool_decision_split: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    dimension_seen: Counter[str] = Counter()
    oracle_agreements = 0
    for number, (dimension, tool) in enumerate(zip(dimensions, tools, strict=True), 1):
        dimension_seen[dimension] += 1
        split = "DEV" if number % 10 < 2 else "VALIDATION" if number % 10 < 4 else "HELD_OUT"
        allowed = _base(number, dimension, tool, split)
        if dimension == "CONTRACT_IDENTITY" and dimension_seen[dimension] % 2:
            for capability in allowed["contract"]["capabilities"]:
                if _relevant(capability, allowed["request"]["components"]):
                    capability["action"] += ".preview"
        denied = _mutate(allowed, number, dimension)
        pair_results: list[dict[str, Any]] = []
        for scenario in (allowed, denied):
            validate_scenario(scenario)
            result_a = oracle_a(scenario)
            result_b = oracle_b(scenario)
            if result_a != result_b:
                raise AssertionError((scenario["scenario_id"], result_a, result_b))
            oracle_agreements += 1
            pair_results.append(result_a)
            families = _families(number, result_a["decision"], dimension, tool)
            record = {
                **result_a,
                "families": families,
                "difficulty": None,
                "authority_distance": sum(
                    value == "DENY" for value in result_a["component_decisions"].values()
                ),
                "claim_contributions": _claim_contributions(families, dimension),
                "generation_provenance": [
                    "PROPERTY_BASED_TEMPLATE",
                    "SINGLE_AUTHORITY_DIMENSION_MUTATION",
                ],
                "resource_boundary_kind": _boundary_kind(number, dimension),
            }
            diff_record = _difficulty(scenario, result_a, dimension, number)
            record["difficulty"] = diff_record["class"]
            scenarios.append(scenario)
            labels.append(record)
            difficulty.append(diff_record)
            by_tool_decision_split[(tool, result_a["decision"], split)].append(
                scenario["scenario_id"]
            )
        expected_relation = "SAME" if dimension == "CONTRACT_IDENTITY" else "FLIP"
        decisions = [item["decision"] for item in pair_results]
        if expected_relation == "FLIP" and decisions != ["ALLOW", "DENY"]:
            raise AssertionError(f"counterfactual pair failed to flip: {number}")
        if expected_relation == "SAME" and decisions[0] != decisions[1]:
            raise AssertionError(f"identity-only pair changed authority: {number}")
        strength = (
            "MODERATE"
            if dimension in {"CAPABILITY_PRESENCE", "MULTI_CAPABILITY_SPLIT"}
            else "STRONG"
        )
        pairs.append(
            {
                "pair_id": "p" + _opaque("pair", str(number)),
                "scenario_a": allowed["scenario_id"],
                "scenario_b": denied["scenario_id"],
                "changed_dimension": dimension,
                "strength": strength,
                "expected_relation": expected_relation,
                "resource_boundary_kind": _boundary_kind(number, dimension),
                "differing_paths": _flatten_diff(allowed, denied),
            }
        )
    assert len(scenarios) == len(labels) == len(difficulty) == 3600
    assert len(pairs) == 1800
    assert Counter(item["decision"] for item in labels) == {"ALLOW": 1800, "DENY": 1800}
    assert sum(item["strength"] == "STRONG" for item in pairs) == 1420
    assert oracle_agreements == 3600
    # Equivalent-tool registry is label-balanced and does not enter the
    # opposite-label counterfactual pair metric.
    cross_tool: list[dict[str, str]] = []
    for split in ("DEV", "VALIDATION", "HELD_OUT"):
        for decision in ("ALLOW", "DENY"):
            fs_ids = by_tool_decision_split[("FILESYSTEM", decision, split)]
            process_ids = by_tool_decision_split[("PROCESS", decision, split)]
            for index, (fs_id, process_id) in enumerate(
                zip(fs_ids[:100], process_ids[:100], strict=True)
            ):
                cross_tool.append(
                    {
                        "equivalence_id": "x"
                        + _opaque("cross-tool", f"{split}|{decision}|{index}"),
                        "filesystem_scenario": fs_id,
                        "process_scenario": process_id,
                        "expected_decision": decision,
                        "split": split,
                        "property": "TASK_AND_EXACT_AUTHORITY_SEMANTICS",
                    }
                )
    label_by_id = {item["scenario_id"]: item for item in labels}
    for group in cross_tool:
        for field in ("filesystem_scenario", "process_scenario"):
            label = label_by_id[group[field]]
            label["families"] = sorted(set(label["families"] + ["CROSS_TOOL_EQUIVALENCE"]))
            label["claim_contributions"] = sorted(
                set(label["claim_contributions"] + ["CROSS_TOOL_CONSISTENCY"])
            )
    scenario_order = sorted(scenarios, key=lambda item: item["scenario_id"])
    label_order = sorted(labels, key=lambda item: item["scenario_id"])
    difficulty_order = sorted(difficulty, key=lambda item: item["scenario_id"])
    pair_order = sorted(pairs, key=lambda item: item["pair_id"])
    _dump(
        "scenarios.json",
        {"corpus_id": CORPUS_ID, "schema_id": SCHEMA_ID, "scenarios": scenario_order},
    )
    _dump("labels.json", {"corpus_id": CORPUS_ID, "labels": label_order})
    _dump("pairs.json", {"pair_registry_id": PAIR_REGISTRY_ID, "pairs": pair_order})
    _dump("difficulty.json", {"difficulty_model_id": DIFFICULTY_ID, "records": difficulty_order})
    _dump(
        "cross_tool_pairs.json",
        {"cross_tool_registry_id": "AUTH-COVERAGE-001-CROSS-TOOL@1", "pairs": cross_tool},
    )
    family_counts = Counter(family for item in labels for family in item["families"])
    dimension_counts = Counter(item["changed_dimension"] for item in pairs)
    compound_counts = Counter()
    scenario_by_id = {item["scenario_id"]: item for item in scenarios}
    for label in labels:
        scenario = scenario_by_id[label["scenario_id"]]
        if scenario["request"]["tool"] == "PROCESS":
            statuses = label["component_decisions"]
            compound_counts[statuses["exec"][0] + statuses["cwd"][0]] += 1
    manifest = {
        "protocol_id": PROTOCOL_ID,
        "corpus_id": CORPUS_ID,
        "schema_id": SCHEMA_ID,
        "pair_registry_id": PAIR_REGISTRY_ID,
        "difficulty_model_id": DIFFICULTY_ID,
        "oracle_a": ORACLE_A_ID,
        "oracle_b": ORACLE_B_ID,
        "oracle_agreement": {"agreed": oracle_agreements, "total": len(scenarios)},
        "scenario_count": len(scenarios),
        "tool_counts": Counter(item["request"]["tool"] for item in scenarios),
        "decision_counts": Counter(item["decision"] for item in labels),
        "split_counts": Counter(item["split"] for item in scenarios),
        "family_counts": family_counts,
        "pair_counts": Counter(item["strength"] for item in pairs),
        "pair_dimension_counts": dimension_counts,
        "resource_boundary_kind_counts": Counter(
            f"{item['changed_dimension']}:{item['resource_boundary_kind']}"
            for item in pairs
            if item["resource_boundary_kind"] is not None
        ),
        "compound_quadrants": compound_counts,
        "difficulty_counts": Counter(item["class"] for item in difficulty),
        "cross_tool_equivalence_count": len(cross_tool),
        "property_generated_case_count": len(scenarios),
        "mutation_check_count": sum(item["expected_relation"] == "FLIP" for item in pairs),
        "metamorphic_check_count": sum(item["expected_relation"] == "SAME" for item in pairs),
        "held_out_predictions_exposed": False,
        "generated_by": "build_corpus.py",
    }
    _dump("manifest.json", manifest)
    checksummed = sorted(path for path in CORPUS.iterdir() if path.name != "CHECKSUMS.sha256")
    (CORPUS / "CHECKSUMS.sha256").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in checksummed
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
