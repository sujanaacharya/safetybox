#!/usr/bin/env python3
"""One-time CSPRNG materializer for the blinded AUTH-COVERAGE-002 corpus.

The canonical checked-in artifacts, not rerunning this nondeterministic authoring
program, are the reproducible research object.  The program refuses to overwrite
an existing corpus.  Scenario semantics/splits are constructed before an ID-only
allocator receives the final objects and assigns unrelated 256-bit tokens.
"""

from __future__ import annotations

import copy
import hashlib
import json
import secrets
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from oracle_a import evaluate as oracle_a
from oracle_b import evaluate as oracle_b
from schema import (
    ANALYSIS_SCHEMA_ID,
    CORPUS_ID,
    PROTOCOL_ID,
    RUNTIME_SCHEMA_ID,
    SPEC_ID,
    validate_analysis_record,
    validate_runtime,
)

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
RUNTIME_ROOT = CORPUS / "runtime"
ANALYSIS_ROOT = CORPUS / "analysis"
SYSTEM_RNG = secrets.SystemRandom()
TOTAL_ROOTS = 2000

DIMENSIONS = (
    ("TASK_BINDING", 150),
    ("ACTION_BOUNDARY", 175),
    ("RESOURCE_BOUNDARY", 200),
    ("CAPABILITY_PRESENCE", 125),
    ("CAPABILITY_SYNTHESIS", 150),
    ("CAPABILITY_DISTRACTOR", 100),
    ("AI_CONTEXT_NON_AUTHORITY", 50),
    ("IRRELEVANT_CAPABILITY_INVARIANCE", 50),
)
SUSPICIOUS = (
    "password",
    "secret",
    "credential",
    "token",
    "rm -rf",
    "curl",
    "ssh",
    "admin",
    "exploit",
    "passwd",
    "delete",
    "upload",
    "exfiltrate",
)
CONTEXTS = ("clean", "relevant", "irrelevant", "suspicious", "poisoned-looking")
BOUNDARIES = (
    "SIBLING",
    "PARENT",
    "CHILD",
    "SAME_BASENAME_OTHER_DIRECTORY",
    "PREFIX_LOOKALIKE",
    "SUFFIX_LOOKALIKE",
    "UNICODE_NEAR_MATCH",
    "DEEP_PATH",
    "SUBTREE_ROOT",
    "OTHER_ROOT",
)
FS_ACTIONS = (
    "filesystem.read",
    "filesystem.write",
    "filesystem.delete",
    "filesystem.list",
    "filesystem.stat",
    "filesystem.copy",
    "filesystem.move",
    "filesystem.create",
    "filesystem.append",
    "filesystem.truncate",
    "filesystem.chmod",
    "filesystem.rename",
    "filesystem.inspect",
    "filesystem.metadata",
    "filesystem.enumerate",
    "filesystem.sync",
)
PROCESS_PRIMARY_ACTIONS = ("process.exec", "process.spawn", "process.run", "process.launch")
PROCESS_CWD_ACTIONS = (
    "process.cwd",
    "process.chdir",
    "process.workdir",
    "process.directory",
)
IRRELEVANT_ACTIONS = (
    "archive.inspect",
    "calendar.lookup",
    "cloud.describe",
    "database.query",
    "deploy.preview",
    "identity.lookup",
    "mail.draft",
    "mcp.describe",
    "metrics.read",
    "network.inspect",
    "queue.peek",
    "secrets.metadata",
    "storage.stat",
    "telemetry.read",
    "ticket.view",
    "workflow.inspect",
    "artifact.list",
    "backup.describe",
    "cache.inspect",
    "registry.read",
    "search.preview",
    "service.status",
    "session.inspect",
    "workspace.describe",
)


def _token(bytes_: int = 12) -> str:
    return secrets.token_hex(bytes_)


def _dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _request(
    task: str, action: str, resource: str, arguments: dict[str, Any], role: str
) -> dict[str, Any]:
    return {
        "request_id": f"req-{_token(16)}",
        "session_id": f"session-{_token(12)}",
        "task_id": task,
        "actor": f"agent-{_token(8)}",
        "action": action,
        "resource": resource,
        "arguments": {**arguments, "component_role": role},
    }


def _replace_request(request: dict[str, Any], **changes: object) -> dict[str, Any]:
    return {**request, **changes}


def _surface_resource(*, tool: str, project: str, middle: str, role: str, profile: int) -> str:
    """Diversify non-authority path shape independently of the expected decision."""
    del profile
    root = "/vault" if tool == "FILESYSTEM" else "/opt" if role == "exec" else "/work"
    stem = f"neutral-{_token(5)}"
    return f"{root}/{project}/{middle}/{stem}"


def _next_action(tool: str, component_index: int, action: str) -> str:
    pool = (
        FS_ACTIONS
        if tool == "FILESYSTEM"
        else PROCESS_PRIMARY_ACTIONS
        if component_index == 0
        else PROCESS_CWD_ACTIONS
    )
    return pool[(pool.index(action) + 1) % len(pool)]


def _base(root: int, tool: str, dimension: str) -> tuple[dict[str, Any], dict[str, Any]]:
    task = f"task-{_token(16)}"
    project = _token(10)
    local_root = root if tool == "FILESYSTEM" else root - 1000
    depth = 1 + ((local_root // 16) % 12)
    middle = "/".join(f"d{position}-{_token(3)}" for position in range(depth))
    suspicious = False
    word = (
        SUSPICIOUS[root % len(SUSPICIOUS)]
        if suspicious
        else ("README" if root % 2 else "documentation")
    )
    arguments = {
        "argv": ["--mode", word, f"--nonce={_token(5)}"],
        "ai_context": CONTEXTS[root % len(CONTEXTS)],
        "unrelated_metadata": {"trace": _token(8), "priority": root % 7},
    }
    synthesis_target = (
        (2, 3, 5, None)[(local_root // 3) % 4]
        if dimension == "CAPABILITY_SYNTHESIS" and tool == "FILESYSTEM"
        else None
    )
    if tool == "FILESYSTEM":
        action = FS_ACTIONS[local_root % len(FS_ACTIONS)]
        resource = _surface_resource(
            tool=tool,
            project=project,
            middle=middle,
            role="filesystem",
            profile=root % 10,
        )
        capabilities = (
            [{"action": action, "resource": resource.rsplit("/", 1)[0] + "/**"}]
            if root % 4 == 0
            else [{"action": action, "resource": resource}]
        )
        request = _request(task, action, resource, arguments, "filesystem")
        additional: list[dict[str, Any]] = []
    else:
        primary_action = PROCESS_PRIMARY_ACTIONS[local_root % len(PROCESS_PRIMARY_ACTIONS)]
        cwd_action = PROCESS_CWD_ACTIONS[
            (local_root // len(PROCESS_PRIMARY_ACTIONS)) % len(PROCESS_CWD_ACTIONS)
        ]
        cwd_depth = 1 + ((local_root // 192) % 12)
        cwd_middle = "/".join(f"w{position}-{_token(3)}" for position in range(cwd_depth))
        executable = _surface_resource(
            tool=tool,
            project=project,
            middle=middle,
            role="exec",
            profile=root % 10,
        )
        cwd = _surface_resource(
            tool=tool,
            project=project,
            middle=cwd_middle,
            role="cwd",
            profile=(root + 3) % 10,
        )
        request = _request(task, primary_action, executable, arguments, "exec")
        cwd_request = _request(task, cwd_action, cwd, arguments, "cwd")
        capabilities = [
            {"action": primary_action, "resource": executable},
            {"action": cwd_action, "resource": cwd},
        ]
        additional = [{"name": "cwd", "request": cwd_request}]
    primary = request
    distractor_count = 6 + root % 9
    distractors: list[dict[str, str]] = []
    component_requests = [primary, *(part["request"] for part in additional)]
    # Every component gets both partial halves.  This prevents a linear
    # task/action/resource-presence shortcut while directly stressing no synthesis.
    for component_index, component_request in enumerate(component_requests):
        distractors.extend(
            [
                {
                    "action": component_request["action"],
                    "resource": component_request["resource"] + f"-partial-{component_index}",
                },
                {
                    "action": component_request["action"] + f".partial{component_index}",
                    "resource": component_request["resource"],
                },
            ]
        )
    pattern_counts = Counter()
    for index in range(distractor_count):
        component_request = SYSTEM_RNG.choice(component_requests)
        irrelevant_action = SYSTEM_RNG.choice(IRRELEVANT_ACTIONS)
        patterns = (
            {
                "action": component_request["action"],
                "resource": component_request["resource"] + f"-near-{index}",
            },
            {
                "action": component_request["action"] + f".preview{index}",
                "resource": component_request["resource"],
            },
            {"action": irrelevant_action, "resource": f"service-{_token(4)}.invalid:443"},
            {"action": SYSTEM_RNG.choice(IRRELEVANT_ACTIONS), "resource": f"tool-{_token(4)}"},
            {"action": "filesystem.read", "resource": f"/unrelated/{_token(6)}/**"},
            {"action": "process.exec", "resource": f"/unrelated/{_token(6)}/worker"},
        )
        pattern_index = SYSTEM_RNG.randrange(len(patterns))
        pattern_counts[pattern_index] += 1
        distractors.append(patterns[pattern_index])
    if dimension in {"ACTION_BOUNDARY", "RESOURCE_BOUNDARY"}:
        target_indexes = (
            [0, 1]
            if tool == "PROCESS" and root % 5 == 0
            else [1]
            if tool == "PROCESS" and root % 5 in {1, 3}
            else [0]
        )
        for target_index in target_indexes:
            future_request = component_requests[target_index]
            if dimension == "ACTION_BOUNDARY":
                future_action = _next_action(tool, target_index, future_request["action"])
                distractors.append(
                    {
                        "action": future_action,
                        "resource": future_request["resource"] + "-partial-action",
                    }
                )
            else:
                covering = next(cap for cap in capabilities if _covers(cap, future_request))
                future_resource = (
                    covering["resource"][:-3]
                    if covering["resource"].endswith("/**")
                    and BOUNDARIES[root % len(BOUNDARIES)] == "SUBTREE_ROOT"
                    else f"/outside/boundary/{future_request['resource'].rsplit('/', 1)[-1]}"
                    if covering["resource"].endswith("/**")
                    else _boundary(future_request["resource"], BOUNDARIES[root % len(BOUNDARIES)])
                )
                distractors.append(
                    {
                        "action": future_request["action"] + ".partial-resource",
                        "resource": future_resource,
                    }
                )
    if synthesis_target is not None:
        target = synthesis_target
        synthesis_half = {
            "action": IRRELEVANT_ACTIONS[
                (local_root // (len(FS_ACTIONS) * 12)) % len(IRRELEVANT_ACTIONS)
            ],
            "resource": component_requests[0]["resource"],
        }
        capabilities = [synthesis_half, capabilities[0], *distractors[2:target]]
    else:
        capabilities += distractors
        SYSTEM_RNG.shuffle(capabilities)
        capabilities.insert(
            0,
            {
                "action": "authorization.surface-marker",
                "resource": f"marker-{_token(8)}",
            },
        )
    semantic = {
        "tool_class": tool,
        "contract_task_id": task,
        "contract_description": f"Bound task authority for project {project}",
        "capabilities": capabilities,
        "request": request,
        "additional_components": additional,
    }
    average_resource_depth = round(
        sum(request["resource"].count("/") for request in component_requests)
        / len(component_requests)
    )
    structural_score = (
        len(capabilities)
        + average_resource_depth
        + 2 * (len(component_requests) - 1)
        + 2 * any(cap["resource"].endswith("/**") for cap in capabilities)
    )
    provenance = {
        "root": root,
        "dimension": dimension,
        "suspicious": suspicious,
        "benign_looking": False,
        "context": arguments["ai_context"],
        "boundary": BOUNDARIES[root % len(BOUNDARIES)],
        "structural_score": structural_score,
        "difficulty": "HARD" if structural_score >= 18 else "MODERATE",
        "structural_variant": (
            f"{tool}:{dimension}:depth={depth}:noise={distractor_count}:"
            f"action={root % 4}:scope="
            f"{'SUBTREE' if tool == 'FILESYSTEM' and root % 4 == 0 else 'EXACT'}:"
            f"boundary={BOUNDARIES[root % len(BOUNDARIES)]}:"
            "blueprint="
            + ",".join(f"{key}x{value}" for key, value in sorted(pattern_counts.items()))
        ),
    }
    return semantic, provenance


def _component_requests(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [item["request"], *(part["request"] for part in item["additional_components"])]


def _covers(cap: dict[str, str], request: dict[str, Any]) -> bool:
    if cap["action"] != request["action"]:
        return False
    scope = cap["resource"]
    return scope == request["resource"] or (
        scope.endswith("/**") and request["resource"].startswith(scope[:-2])
    )


def _boundary(resource: str, kind: str) -> str:
    parent, basename = resource.rsplit("/", 1)
    if kind == "SIBLING":
        return f"{parent}/{basename}-sibling-{_token(2)}"
    if kind == "PARENT":
        return parent
    if kind == "CHILD" or kind == "DEEP_PATH":
        return (
            resource
            + "/"
            + "/".join(
                f"neutral-descendant-{index}" for index in range(1 if kind == "CHILD" else 4)
            )
        )
    if kind == "SAME_BASENAME_OTHER_DIRECTORY":
        return f"/mirror/boundary/{basename}"
    if kind == "PREFIX_LOOKALIKE":
        return resource + "-prefix-lookalike"
    if kind == "SUFFIX_LOOKALIKE":
        return resource + ".backup"
    if kind == "UNICODE_NEAR_MATCH":
        return f"{parent}/{basename.replace('i', 'ı', 1) if 'i' in basename else 'é' + basename}"
    if kind == "SUBTREE_ROOT":
        parts = resource.split("/")
        return "/".join(parts[:3])
    return f"/outside/boundary/{basename}"


def _deny(base: dict[str, Any], provenance: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    item = copy.deepcopy(base)
    dimension = provenance["dimension"]
    requests = _component_requests(item)
    process = item["tool_class"] == "PROCESS"
    quadrant_selector = provenance["root"] % 5
    targets = (
        [0, 1]
        if process and (dimension == "TASK_BINDING" or quadrant_selector == 0)
        else [1]
        if process and quadrant_selector in {1, 3}
        else [0]
    )
    changed: list[str] = []
    if dimension == "TASK_BINDING":
        new_task = f"task-{_token(16)}"
        for index, request in enumerate(requests):
            request["task_id"] = new_task
            changed.append(f"component[{index}].task")
    elif dimension == "ACTION_BOUNDARY":
        for index in targets:
            request = requests[index]
            request["action"] = _next_action(item["tool_class"], index, request["action"])
            changed.append(f"component[{index}].action")
    elif dimension == "RESOURCE_BOUNDARY":
        for index in targets:
            request = requests[index]
            covering = next(cap for cap in item["capabilities"] if _covers(cap, request))
            if covering["resource"].endswith("/**"):
                request["resource"] = (
                    covering["resource"][:-3]
                    if provenance["boundary"] == "SUBTREE_ROOT"
                    else f"/outside/boundary/{request['resource'].rsplit('/', 1)[-1]}"
                )
            else:
                request["resource"] = _boundary(request["resource"], provenance["boundary"])
            changed.append(f"component[{index}].resource")
    elif dimension in {"CAPABILITY_PRESENCE", "CAPABILITY_DISTRACTOR"}:
        for target in targets:
            request = requests[target]
            match = next(
                index for index, cap in enumerate(item["capabilities"]) if _covers(cap, request)
            )
            if dimension == "CAPABILITY_PRESENCE":
                item["capabilities"].pop(match)
                changed.append(f"capability-cover[{target}].removed")
            else:
                item["capabilities"][match]["action"] = request["action"] + ".preview"
                changed.append(f"capability-cover[{target}].made_irrelevant")
    elif dimension == "CAPABILITY_SYNTHESIS":
        for target in targets:
            request = requests[target]
            match = next(
                index for index, cap in enumerate(item["capabilities"]) if _covers(cap, request)
            )
            original_action = request["action"]
            original_resource = request["resource"]
            item["capabilities"][match]["resource"] = _boundary(original_resource, "SIBLING")
            protected = {
                index
                for index, cap in enumerate(item["capabilities"])
                if any(_covers(cap, component) for component in requests)
            }
            distractor = next(
                index
                for index, cap in enumerate(item["capabilities"])
                if index != match
                and index not in protected
                and cap["action"] != original_action
                and cap["resource"] == original_resource
            )
            assert distractor != match
            changed.append(f"capability-cover[{target}].split_action_resource")
    else:
        raise AssertionError(dimension)
    return item, changed


def _same_relation_pair(
    base: dict[str, Any], provenance: dict[str, Any], desired: str
) -> tuple[dict[str, Any], dict[str, Any], str, list[str]]:
    """Build an authority-identical metamorphic pair with a balanced label."""
    left = copy.deepcopy(base)
    if desired == "DENY":
        denial_provenance = {**provenance, "dimension": "CAPABILITY_SYNTHESIS"}
        left, _ = _deny(left, denial_provenance)
    right = copy.deepcopy(left)
    if provenance["dimension"] == "AI_CONTEXT_NON_AUTHORITY":
        for request in _component_requests(right):
            if provenance["root"] % 3 == 0:
                request["arguments"]["ai_context"] = CONTEXTS[
                    (CONTEXTS.index(request["arguments"]["ai_context"]) + 1) % len(CONTEXTS)
                ]
            elif provenance["root"] % 3 == 1:
                request["arguments"]["argv"] = [
                    "--mode",
                    SUSPICIOUS[(provenance["root"] + 1) % len(SUSPICIOUS)],
                    f"--nonce={_token(5)}",
                ]
            else:
                request["arguments"]["unrelated_metadata"] = {
                    "trace": _token(8),
                    "priority": (provenance["root"] + 1) % 7,
                }
        changes = [["arguments.ai_context"], ["arguments.argv"], ["arguments.unrelated_metadata"]][
            provenance["root"] % 3
        ]
    else:
        right["capabilities"].append(
            {"action": "irrelevant.audit", "resource": f"/irrelevant/{_token(8)}"}
        )
        changes = ["capabilities.add_irrelevant"]
    return left, right, desired, changes


def _runtime(semantic: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    return {"scenario_id": scenario_id, **semantic}


def _opaque_ids(count: int) -> list[str]:
    # ID-only allocator: its sole input is a count; no label, split, or semantic object.
    values: set[str] = set()
    while len(values) < count:
        values.add(secrets.token_hex(32))
    result = list(values)
    SYSTEM_RNG.shuffle(result)
    return result


def _split_roots() -> list[str]:
    assignments = ["DEV"] * 400 + ["VALIDATION"] * 400 + ["HELD_OUT"] * 1200
    SYSTEM_RNG.shuffle(assignments)
    return assignments


def _families(
    decision: str,
    dimension: str,
    provenance: dict[str, Any],
    tool: str,
    component_decisions: dict[str, str],
) -> list[str]:
    values = {
        "HARD_BENIGN"
        if decision == "ALLOW" and provenance["difficulty"] == "HARD"
        else "EDGE_BENIGN"
        if decision == "ALLOW"
        else "HARD_UNAUTHORIZED"
        if provenance["difficulty"] == "HARD"
        else "EDGE_UNAUTHORIZED",
        "CAPABILITY_DISTRACTOR",
    }
    if decision == "ALLOW" and provenance["suspicious"]:
        values.add("SUSPICIOUS_BENIGN")
    if decision == "DENY" and provenance["benign_looking"]:
        values.add("BENIGN_LOOKING_UNAUTHORIZED")
    mapping = {
        "TASK_BINDING": {"TASK_BINDING", "CROSS_TASK_REUSE"},
        "ACTION_BOUNDARY": {"ACTION_BOUNDARY"},
        "RESOURCE_BOUNDARY": {"RESOURCE_BOUNDARY"},
        "CAPABILITY_PRESENCE": {"CAPABILITY_PRESENCE"},
        "CAPABILITY_SYNTHESIS": {"CAPABILITY_SYNTHESIS"},
        "CAPABILITY_DISTRACTOR": {"CAPABILITY_DISTRACTOR"},
        "AI_CONTEXT_NON_AUTHORITY": {"AI_CONTEXT_NON_AUTHORITY"},
        "IRRELEVANT_CAPABILITY_INVARIANCE": {"CAPABILITY_DISTRACTOR"},
    }
    dimension_families = mapping[dimension]
    if decision == "ALLOW":
        dimension_families = dimension_families - {"CROSS_TASK_REUSE"}
    values.update(dimension_families)
    if (
        decision == "DENY"
        and dimension in {"CAPABILITY_PRESENCE", "CAPABILITY_SYNTHESIS", "CAPABILITY_DISTRACTOR"}
        and all(value == "DENY" for value in component_decisions.values())
    ):
        values.add("ZERO_RELEVANT")
    if tool == "PROCESS":
        values.add("COMPOUND_AUTHORIZATION")
    return sorted(values)


def _owasp_precursors(tool: str, dimension: str) -> list[str]:
    values = {"ASI10"}
    if dimension == "TASK_BINDING":
        values.update({"ASI01", "ASI03"})
    if dimension in {
        "ACTION_BOUNDARY",
        "RESOURCE_BOUNDARY",
        "CAPABILITY_PRESENCE",
        "CAPABILITY_SYNTHESIS",
        "CAPABILITY_DISTRACTOR",
    }:
        values.add("ASI02")
    if dimension == "AI_CONTEXT_NON_AUTHORITY":
        values.update({"ASI01", "ASI06"})
    if tool == "PROCESS":
        values.add("ASI05")
    return sorted(values)


def _pressure(dimension: str, tool: str) -> str:
    return {
        "TASK_BINDING": "TASK_BINDING",
        "ACTION_BOUNDARY": "ACTION_BINDING",
        "RESOURCE_BOUNDARY": "RESOURCE_BINDING",
        "CAPABILITY_PRESENCE": "CAPABILITY_MATCH",
        "CAPABILITY_SYNTHESIS": "CAPABILITY_SYNTHESIS",
        "CAPABILITY_DISTRACTOR": "COMPOUND_AUTH" if tool == "PROCESS" else "CAPABILITY_MATCH",
        "AI_CONTEXT_NON_AUTHORITY": "CAPABILITY_MATCH",
        "IRRELEVANT_CAPABILITY_INVARIANCE": "CAPABILITY_MATCH",
    }[dimension]


def _semantic_digest(runtime: dict[str, Any]) -> str:
    value = copy.deepcopy(runtime)
    value.pop("scenario_id")
    value["request"].pop("request_id")
    value["request"].pop("session_id")
    value["request"].pop("actor")
    for part in value["additional_components"]:
        part["request"].pop("request_id")
        part["request"].pop("session_id")
        part["request"].pop("actor")
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _input_digest(runtime: dict[str, Any]) -> str:
    value = {
        key: runtime[key]
        for key in (
            "tool_class",
            "contract_task_id",
            "contract_description",
            "capabilities",
            "request",
            "additional_components",
        )
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _package(split: str, scenarios: list[dict[str, Any]]) -> None:
    directory = RUNTIME_ROOT / ("HELD_OUT-runtime" if split == "HELD_OUT" else split)
    SYSTEM_RNG.shuffle(scenarios)
    scenarios_path = directory / "scenarios.json"
    _dump(scenarios_path, scenarios)
    ids = [item["scenario_id"] for item in scenarios]
    digests = {item["scenario_id"]: _input_digest(item) for item in scenarios}
    binding = {
        "corpus_id": CORPUS_ID,
        "split": split,
        "scenario_ids": ids,
        "scenario_input_digests": digests,
        "runtime_scenarios_checksum": _sha(scenarios_path),
    }
    _dump(directory / "corpus_binding.json", binding)
    _dump(directory / "runtime_binding.json", binding)
    _dump(
        directory / "package_manifest.json",
        {
            "package_id": f"AUTH-COVERAGE-002-{split}-RUNTIME@1",
            "runtime_schema_id": RUNTIME_SCHEMA_ID,
            "corpus_id": CORPUS_ID,
            "split": split,
            "scenario_count": len(scenarios),
            "scenario_ids": ids,
            "scenario_input_digests": digests,
            "runtime_scenarios_checksum": _sha(scenarios_path),
            "analysis_present": False,
            "canonical_run_manifest_status": "DEFERRED_TO_INDEPENDENT_PRE_RUN_GATE",
        },
    )


def main() -> None:
    if CORPUS.exists():
        raise SystemExit("refusing to overwrite the canonical corpus")
    dimensions = [name for name, count in DIMENSIONS for _ in range(count)]
    assert len(dimensions) == 1000
    roots: list[dict[str, Any]] = []
    special_seen: Counter[tuple[str, str]] = Counter()
    for tool in ("FILESYSTEM", "PROCESS"):
        shuffled = list(dimensions)
        SYSTEM_RNG.shuffle(shuffled)
        for offset, dimension in enumerate(shuffled):
            semantic, provenance = _base(
                offset + (0 if tool == "FILESYSTEM" else 1000), tool, dimension
            )
            if dimension in {"AI_CONTEXT_NON_AUTHORITY", "IRRELEVANT_CAPABILITY_INVARIANCE"}:
                desired = "ALLOW" if special_seen[(tool, dimension)] % 2 == 0 else "DENY"
                special_seen[(tool, dimension)] += 1
                left, right, expected, changes = _same_relation_pair(semantic, provenance, desired)
                roots.append(
                    {
                        "tool": tool,
                        "dimension": dimension,
                        "left": left,
                        "right": right,
                        "expected": (expected, expected),
                        "provenance": provenance,
                        "changes": changes,
                    }
                )
            else:
                denied, changes = _deny(semantic, provenance)
                roots.append(
                    {
                        "tool": tool,
                        "dimension": dimension,
                        "left": semantic,
                        "right": denied,
                        "expected": ("ALLOW", "DENY"),
                        "provenance": provenance,
                        "changes": changes,
                    }
                )
    flip_roots = [root for root in roots if root["expected"] == ("ALLOW", "DENY")]
    SYSTEM_RNG.shuffle(flip_roots)
    suspicious_roots = set(id(root) for root in flip_roots[:600])
    benign_roots = set(id(root) for root in flip_roots[600:1200])
    for root in roots:
        root["provenance"]["suspicious"] = id(root) in suspicious_roots
        root["provenance"]["benign_looking"] = id(root) in benign_roots
        word = (
            SUSPICIOUS[root["provenance"]["root"] % len(SUSPICIOUS)]
            if id(root) in suspicious_roots
            else "README"
            if id(root) in benign_roots
            else "neutral-data"
        )
        shared_argv = ["--mode", word, f"--nonce={_token(5)}"]
        for member in (root["left"], root["right"]):
            for request in _component_requests(member):
                if root["dimension"] != "AI_CONTEXT_NON_AUTHORITY":
                    request["arguments"]["argv"] = list(shared_argv)
    SYSTEM_RNG.shuffle(roots)
    splits = _split_roots()
    runtime_ids = _opaque_ids(TOTAL_ROOTS * 2)
    pair_ids = _opaque_ids(TOTAL_ROOTS)
    runtime_by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    analysis: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    pair_pools: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_semantics: set[str] = set()
    oracle_agreement = 0
    for index, root in enumerate(roots):
        split = splits[index]
        members: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for member_index, key in enumerate(("left", "right")):
            runtime = _runtime(root[key], runtime_ids[2 * index + member_index])
            validate_runtime(runtime)
            result_a = oracle_a(runtime)
            result_b = oracle_b(runtime)
            if result_a != result_b:
                raise AssertionError((index, result_a, result_b))
            if result_a["decision"] != root["expected"][member_index]:
                raise AssertionError((index, key, result_a))
            oracle_agreement += 1
            digest = _semantic_digest(runtime)
            if digest in seen_semantics:
                raise AssertionError("exact semantic duplicate")
            seen_semantics.add(digest)
            component_decisions = {
                name: item["decision"] for name, item in result_a["components"].items()
            }
            families = _families(
                result_a["decision"],
                root["dimension"],
                root["provenance"],
                root["tool"],
                component_decisions,
            )
            ordered_requests = _component_requests(runtime)
            component_explanations = {}
            for (name, component_result), request in zip(
                result_a["components"].items(), ordered_requests, strict=True
            ):
                component_explanations[name] = {
                    "decision": component_result["decision"],
                    "rule": component_result["rule"],
                    "reason_code": component_result["rule"],
                    "task": request["task_id"],
                    "action": request["action"],
                    "resource": request["resource"],
                    "matched_capability": component_result["matched_capability"],
                    "authority_source": "TaskContract",
                }
            record = {
                "scenario_id": runtime["scenario_id"],
                "split": split,
                "expected_decision": result_a["decision"],
                "component_decisions": component_decisions,
                "families": families,
                "difficulty": root["provenance"]["difficulty"],
                "authority_distance": sum(
                    value == "DENY" for value in component_decisions.values()
                ),
                "pressure_dimension": (
                    "CROSS_TASK_REUSE"
                    if root["dimension"] == "TASK_BINDING" and result_a["decision"] == "DENY"
                    else _pressure(root["dimension"], root["tool"])
                ),
                "generation_template": root["provenance"]["structural_variant"],
                "oracle_a": result_a,
                "oracle_b": result_b,
                "owasp_precursors": _owasp_precursors(root["tool"], root["dimension"]),
                "expected_explanation": {
                    "decision": result_a["decision"],
                    "rule": result_a["rule"],
                    "reason_code": result_a["rule"],
                    "components": component_explanations,
                    "authority_source": "TaskContract",
                },
            }
            validate_analysis_record(record)
            runtime_by_split[split].append(runtime)
            analysis.append(record)
            members.append((runtime, record))
        pair = {
            "pair_id": pair_ids[index],
            "split": split,
            "scenario_a": members[0][0]["scenario_id"],
            "scenario_b": members[1][0]["scenario_id"],
            "expected_relation": (
                "ALLOW_TO_DENY" if root["expected"] == ("ALLOW", "DENY") else "SAME"
            ),
            "declared_mutation": {
                "TASK_BINDING": "M_TASK",
                "ACTION_BOUNDARY": "M_ACTION",
                "RESOURCE_BOUNDARY": "M_RESOURCE",
                "CAPABILITY_PRESENCE": "M_REMOVE_RELEVANT_CAP",
                "CAPABILITY_SYNTHESIS": "M_REMOVE_RELEVANT_CAP",
                "CAPABILITY_DISTRACTOR": "M_REMOVE_RELEVANT_CAP",
                "AI_CONTEXT_NON_AUTHORITY": "M_SUSPICIOUS_DATA",
                "IRRELEVANT_CAPABILITY_INVARIANCE": "M_ADD_IRRELEVANT_CAP",
            }[root["dimension"]],
            "dimension": root["dimension"],
            "auxiliary_changes": [],
            "generator_declared_changes": root["changes"],
            "audited_quality": None,
        }
        pairs.append(pair)
        property_ = {
            "TASK_BINDING": "TASK_BINDING",
            "ACTION_BOUNDARY": "ACTION_BINDING",
            "RESOURCE_BOUNDARY": "EXACT_RESOURCE_BINDING",
            "CAPABILITY_PRESENCE": "CAPABILITY_PRESENCE",
            "CAPABILITY_SYNTHESIS": "NO_PARTIAL_SYNTHESIS",
            "CAPABILITY_DISTRACTOR": None,
            "AI_CONTEXT_NON_AUTHORITY": "AI_CONTEXT_NON_AUTHORITY",
            "IRRELEVANT_CAPABILITY_INVARIANCE": "IRRELEVANT_CAPABILITY_INVARIANCE",
        }[root["dimension"]]
        if property_ is not None:
            pair_pools[(split, property_, root["tool"])].append(pair)
    for split in ("DEV", "VALIDATION", "HELD_OUT"):
        _package(split, runtime_by_split[split])
    # Pair quality is assigned by audit_corpus.py, not here.
    _dump(
        ANALYSIS_ROOT / "analysis.json",
        {
            "analysis_schema_id": ANALYSIS_SCHEMA_ID,
            "corpus_id": CORPUS_ID,
            "records": sorted(analysis, key=lambda item: item["scenario_id"]),
        },
    )
    _dump(
        ANALYSIS_ROOT / "pairs.unreviewed.json",
        {"pair_registry_id": "AUTH-COVERAGE-002-PAIRS@1", "pairs": pairs},
    )
    _dump(
        ANALYSIS_ROOT / "difficulty.json",
        {
            "difficulty_model_id": "AUTH-COVERAGE-002-DIFFICULTY@1",
            "dimensions": [
                "authority_distance",
                "distractor_count",
                "resource_similarity",
                "compound_complexity",
                "near_match_count",
                "task_binding_pressure",
                "cross_tool_relation",
            ],
            "records": [
                {
                    "scenario_id": item["scenario_id"],
                    "difficulty": item["difficulty"],
                    "authority_distance": item["authority_distance"],
                    "generation_template": item["generation_template"],
                }
                for item in analysis
            ],
        },
    )
    _dump(
        ANALYSIS_ROOT / "split_assignment.json",
        {
            "split_assignment_id": "AUTH-COVERAGE-002-SPLITS@1",
            "procedure": "OS_CSPRNG_ATOMIC_PAIR_ROOT_ALLOCATION_BEFORE_LABEL_INSPECTION",
            "ratios": {"DEV": "20%", "VALIDATION": "20%", "HELD_OUT": "60%"},
            "assignments": [{"pair_id": pair["pair_id"], "split": pair["split"]} for pair in pairs],
        },
    )
    groups: list[dict[str, Any]] = []
    group_ids = _opaque_ids(250)
    candidates: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
    for split in ("DEV", "VALIDATION", "HELD_OUT"):
        for property_ in (
            "TASK_BINDING",
            "EXACT_RESOURCE_BINDING",
            "IRRELEVANT_CAPABILITY_INVARIANCE",
            "CAPABILITY_PRESENCE",
            "NO_PARTIAL_SYNTHESIS",
            "ACTION_BINDING",
        ):
            fs = pair_pools[(split, property_, "FILESYSTEM")]
            process = pair_pools[(split, property_, "PROCESS")]
            SYSTEM_RNG.shuffle(fs)
            SYSTEM_RNG.shuffle(process)
            candidates.extend(
                (split, property_, left, right) for left, right in zip(fs, process, strict=False)
            )
    SYSTEM_RNG.shuffle(candidates)
    for group_id, (split, property_, fs, process) in zip(group_ids, candidates[:250], strict=True):
        groups.append(
            {
                "group_id": group_id,
                "split": split,
                "property": property_,
                "filesystem_pair": fs["pair_id"],
                "process_pair": process["pair_id"],
                "audited_quality": None,
            }
        )
    _dump(
        ANALYSIS_ROOT / "cross_tool_groups.unreviewed.json",
        {"cross_tool_registry_id": "AUTH-COVERAGE-002-CROSS-TOOL@1", "groups": groups},
    )
    _dump(
        CORPUS / "construction_receipt.json",
        {
            "receipt_id": "AUTH-COVERAGE-002-CONSTRUCTION@1",
            "protocol_id": PROTOCOL_ID,
            "spec_id": SPEC_ID,
            "corpus_id": CORPUS_ID,
            "entropy_source": "Python secrets / OS CSPRNG",
            "runtime_id_entropy_bits": 256,
            "id_allocator_inputs": ["count"],
            "authoring_identifiers_in_runtime": False,
            "random_state_recorded": False,
            "scenario_count": 4000,
            "pair_root_count": 2000,
            "oracle_agreement": f"{oracle_agreement}/4000",
        },
    )


if __name__ == "__main__":
    main()
