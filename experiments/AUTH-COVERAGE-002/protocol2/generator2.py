#!/usr/bin/env python3
"""Deterministic DEV-only semantic generator for AUTH-COVERAGE-002-GENERATOR@2."""

from __future__ import annotations

import hashlib
import json
import random
import secrets
from collections import Counter
from typing import Any

GENERATOR_ID = "AUTH-COVERAGE-002-GENERATOR@2"
DEV_SEEDS = (2002101, 2002102, 2002103, 2002104, 2002105)
ROOT_ALLOCATION = (
    ("TASK_BINDING", 60),
    ("RESOURCE_BOUNDARY", 80),
    ("ACTION_BOUNDARY", 60),
    ("CAPABILITY_SYNTHESIS", 60),
    ("CAPABILITY_PRESENCE", 70),
    ("CAPABILITY_DISTRACTOR", 70),
)
BENIGN_WORDS = ("documentation", "readme", "report", "status", "summary", "inventory")
SUSPICIOUS_WORDS = ("secret", "credential", "delete", "upload", "sudo", "private-key")
SPLIT_ROOT_OFFSETS = {"DEV": 0, "VALIDATION": 400, "HELD_OUT": 800}


def _hex(seed: int, index: int, role: str, length: int = 16) -> str:
    return hashlib.sha256(f"{seed}:{index}:{role}".encode()).hexdigest()[:length]


def _request(
    seed: int,
    index: int,
    semantic_index: int,
    task: str,
    action: str,
    resource: str,
    word: str,
    role: str,
) -> dict[str, Any]:
    del seed, index
    return {
        "task_id": task,
        "action": action,
        "resource": resource,
        "arguments": {
            "argv": [
                "--mode",
                word,
                f"--variant-{semantic_index % 97}",
                *(["--shape"] * (semantic_index % 101)),
            ],
            f"semantic_option_{semantic_index % 17}": semantic_index % 11,
            "component_role": role,
        },
    }


def _different_same_length(value: str, variation: str) -> str:
    """Return an unequal same-length string without a label-conditional fixed suffix."""
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    offset = int(hashlib.sha256(variation.encode()).hexdigest()[:8], 16) % len(alphabet)
    replacement = alphabet[offset]
    if value[-1] == replacement:
        replacement = alphabet[(offset + 1) % len(alphabet)]
    return value[:-1] + replacement


def generate_authoring(
    seed: int, split: str, count: int, *, template_root_offset: int | None = None
) -> list[dict[str, Any]]:
    """Generate semantics for one declared split without allocating any runtime IDs."""
    if split not in {"DEV", "VALIDATION", "HELD_OUT"}:
        raise ValueError("unsupported split")
    if count < 2 or count % 2:
        raise ValueError("DEV count must be positive, even, and at least two")
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    root_families = [family for family, roots in ROOT_ALLOCATION for _ in range(roots)]
    for index in range(count):
        label = "ALLOW" if index % 2 == 0 else "DENY"
        root = index // 2
        semantic_root = (
            SPLIT_ROOT_OFFSETS[split] if template_root_offset is None else template_root_offset
        ) + root
        tool = "FILESYSTEM" if semantic_root % 2 == 0 else "PROCESS"
        family = root_families[root % len(root_families)]
        task = f"task-{_hex(seed, root, 'task')}"
        # The two coprime structural axes enumerate 2,009 genuine request/capability
        # shapes before repeating; lexical values are not used by the template hash.
        depth = 2 + (semantic_root % 41)
        middle = "/".join(
            f"segment-{position}-{(semantic_root * (position + 3)) % 101}"
            for position in range(depth)
        )
        presentation_slot = semantic_root % 3
        word = (
            SUSPICIOUS_WORDS[semantic_root % len(SUSPICIOUS_WORDS)]
            if presentation_slot == 0
            else BENIGN_WORDS[semantic_root % len(BENIGN_WORDS)]
        )
        if tool == "FILESYSTEM":
            action = f"filesystem.{('read', 'write', 'list', 'stat')[semantic_root % 4]}"
            resource = f"/workspace/{middle}/{word}-{semantic_root % 23}.txt"
            request = _request(seed, index, semantic_root, task, action, resource, word, "primary")
            additional: list[dict[str, Any]] = []
            capabilities = [{"action": action, "resource": resource}]
        else:
            action = f"process.{('exec', 'run', 'spawn', 'launch')[semantic_root % 4]}"
            resource = f"/opt/{middle}/{word}-{semantic_root % 23}"
            cwd_resource = f"/workspace/{middle}/build-{semantic_root % 19}"
            request = _request(seed, index, semantic_root, task, action, resource, word, "primary")
            cwd = _request(
                seed, index, semantic_root, task, "process.cwd", cwd_resource, word, "cwd"
            )
            additional = [{"name": "cwd", "request": cwd}]
            capabilities = [
                {"action": action, "resource": resource},
                {"action": "process.cwd", "resource": cwd_resource},
            ]

        # TASK_BINDING pairs deliberately reuse identical authority across two
        # distinct contract tasks of the same tool. This makes cross-task
        # coverage an observable property rather than a trusted authoring tag.
        if family == "TASK_BINDING":
            reuse_group = semantic_root // 4
            if tool == "FILESYSTEM":
                action = "filesystem.read"
                resource = f"/shared/task-reuse/{reuse_group}/document"
                request["action"], request["resource"] = action, resource
                capabilities[0] = {"action": action, "resource": resource}
            else:
                action = "process.exec"
                resource = f"/shared/task-reuse/{reuse_group}/executable"
                cwd_resource = f"/shared/task-reuse/{reuse_group}/cwd"
                request["action"], request["resource"] = action, resource
                additional[0]["request"]["resource"] = cwd_resource
                capabilities[:2] = [
                    {"action": action, "resource": resource},
                    {"action": "process.cwd", "resource": cwd_resource},
                ]

        requests = [request, *(item["request"] for item in additional)]
        if tool == "FILESYSTEM":
            target_indexes = [0]
        else:
            # The three denial lanes produce DA, AD, and DD respectively.
            target_indexes = ([0], [1], [0, 1])[(semantic_root // 2) % 3]

        if family in {"CAPABILITY_PRESENCE", "CAPABILITY_DISTRACTOR"}:
            capabilities.append(
                {
                    "action": f"neutral{semantic_root % 31}.observe",
                    "resource": f"/neutral/family/{semantic_root}",
                }
            )
            family_marker_index = len(capabilities) - 1
        else:
            family_marker_index = None

        if label == "ALLOW" and family == "CAPABILITY_SYNTHESIS":
            for target_index in target_indexes:
                relevant = capabilities[target_index]
                capabilities.append(
                    {
                        "action": _different_same_length(
                            relevant["action"], f"{semantic_root}:{target_index}:allow-action"
                        ),
                        "resource": _different_same_length(
                            relevant["resource"], f"{semantic_root}:{target_index}:allow-resource"
                        ),
                    }
                )
        if label == "DENY":
            if family == "TASK_BINDING":
                for target_index in target_indexes:
                    requests[target_index]["task_id"] = (
                        f"task-{_hex(seed, index, f'other-task-{target_index}')}"
                    )
            elif family == "RESOURCE_BOUNDARY":
                for target_index in target_indexes:
                    capabilities[target_index] = {
                        **capabilities[target_index],
                        "resource": _different_same_length(
                            capabilities[target_index]["resource"],
                            f"{semantic_root}:{target_index}:boundary-resource",
                        ),
                    }
            elif family == "ACTION_BOUNDARY":
                for target_index in target_indexes:
                    capabilities[target_index] = {
                        **capabilities[target_index],
                        "action": _different_same_length(
                            capabilities[target_index]["action"],
                            f"{semantic_root}:{target_index}:boundary-action",
                        ),
                    }
            elif family == "CAPABILITY_SYNTHESIS":
                for target_index in sorted(target_indexes, reverse=True):
                    relevant = capabilities.pop(target_index)
                    capabilities.extend(
                        [
                            {
                                "action": relevant["action"],
                                "resource": _different_same_length(
                                    relevant["resource"],
                                    f"{semantic_root}:{target_index}:partial-resource",
                                ),
                            },
                            {
                                "action": _different_same_length(
                                    relevant["action"],
                                    f"{semantic_root}:{target_index}:partial-action",
                                ),
                                "resource": relevant["resource"],
                            },
                        ]
                    )
            elif family == "CAPABILITY_PRESENCE":
                for target_index in target_indexes:
                    relevant = capabilities[target_index]
                    capabilities[target_index] = {
                        "action": _different_same_length(
                            relevant["action"], f"{semantic_root}:{target_index}:presence-action"
                        ),
                        "resource": _different_same_length(
                            relevant["resource"],
                            f"{semantic_root}:{target_index}:presence-resource",
                        ),
                    }
            else:  # CAPABILITY_DISTRACTOR
                for target_index in target_indexes:
                    relevant = capabilities[target_index]
                    capabilities[target_index] = {
                        "action": _different_same_length(
                            relevant["action"], f"{semantic_root}:{target_index}:distractor-action"
                        ),
                        "resource": _different_same_length(
                            relevant["resource"],
                            f"{semantic_root}:{target_index}:distractor-resource",
                        ),
                    }
                assert family_marker_index is not None
                marker = capabilities[family_marker_index]
                capabilities[family_marker_index] = {
                    "action": _different_same_length(
                        marker["action"], f"{semantic_root}:distractor-marker-action"
                    ),
                    "resource": _different_same_length(
                        marker["resource"], f"{semantic_root}:distractor-marker-resource"
                    ),
                }
        distractor_count = 2 + (semantic_root // 41) % 49
        for number in range(distractor_count):
            capabilities.append(
                {
                    "action": f"neutral{(semantic_root + number) % 31}.inspect",
                    "resource": f"/neutral/{_hex(seed, semantic_root, f'd-{number}', 10)}",
                }
            )
        rng.shuffle(capabilities)
        runtime = {
            "tool_class": tool,
            "contract_task_id": task,
            "contract_description": f"{word} task for controlled DEV fixture",
            "capabilities": capabilities,
            "request": request,
            "additional_components": additional,
        }
        records.append(
            {
                "authoring_key": f"dev-{seed}-{index:04d}",
                "split": split,
                "label": label,
                "families": [family],
                "generator_branch": f"{tool}:{family}:{semantic_root % 7}",
                "pair_id": f"dev-pair-{seed}-{root:04d}",
                "generator_pair_intention": {
                    "pair_id": f"dev-pair-{seed}-{root:04d}",
                    "target_dimension": {
                        "TASK_BINDING": "TASK",
                        "RESOURCE_BOUNDARY": "RESOURCE",
                        "ACTION_BOUNDARY": "ACTION",
                        "CAPABILITY_SYNTHESIS": "CAPABILITY",
                        "CAPABILITY_PRESENCE": "CAPABILITY",
                        "CAPABILITY_DISTRACTOR": "CAPABILITY",
                    }[family],
                    "expected_relation": ["ALLOW", "DENY"],
                },
                "difficulty": "HARD" if distractor_count >= 5 else "MODERATE",
                "runtime": runtime,
            }
        )
    # Pair membership is retained through pair_id, while manifest position is
    # seed-randomized so neither parity nor adjacency encodes the label.
    rng.shuffle(records)
    return records


def generate_dev(
    seed: int, count: int = 800, *, template_root_offset: int = 0
) -> list[dict[str, Any]]:
    """The only generation entry point invoked during Generator@2 development."""
    return generate_authoring(seed, "DEV", count, template_root_offset=template_root_offset)


def _assign_runtime_ids(record: dict[str, Any], id_factory: Any) -> dict[str, Any]:
    runtime = json.loads(json.dumps(record["runtime"], sort_keys=True))
    requests = [runtime["request"], *(part["request"] for part in runtime["additional_components"])]
    for index, request in enumerate(requests):
        request.update(
            request_id=id_factory(f"request:{index}"),
            session_id=id_factory(f"session:{index}"),
            actor=id_factory(f"actor:{index}"),
        )
    return {"scenario_id": id_factory("scenario"), **runtime}


def materialize_runtime(record: dict[str, Any]) -> dict[str, Any]:
    """Assign non-DEV runtime IDs only with the OS CSPRNG."""
    if record["split"] == "DEV":
        raise ValueError("DEV records must use runtime_fixture")
    return _assign_runtime_ids(record, lambda _role: secrets.token_hex(32))


def runtime_fixture(record: dict[str, Any]) -> dict[str, Any]:
    """Allocate a deterministic DEV fixture ID; this function is forbidden for future HELD_OUT."""
    if record["split"] != "DEV":
        raise ValueError("only DEV fixtures may receive deterministic fixture IDs")
    return _assign_runtime_ids(
        record,
        lambda role: hashlib.sha256(f"{record['authoring_key']}:{role}".encode()).hexdigest(),
    )


def dev_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    from governance import presentation_class, structural_hash

    presentations = Counter(presentation_class(item["runtime"], item["label"]) for item in records)
    templates = Counter(structural_hash(item["runtime"]) for item in records)
    by_branch: dict[str, Counter[str]] = {}
    for item in records:
        by_branch.setdefault(item["generator_branch"], Counter())[item["label"]] += 1
    deviations = []
    for counts in by_branch.values():
        total = sum(counts.values())
        deviations.append(abs(counts["ALLOW"] / total - 0.5))
    return {
        "count": len(records),
        "labels": Counter(item["label"] for item in records),
        "tools": Counter(item["runtime"]["tool_class"] for item in records),
        "families": Counter(family for item in records for family in item["families"]),
        "presentation": presentations,
        "semantic_templates": len(templates),
        "largest_cluster": max(templates.values()),
        "max_branch_label_rate_deviation": max(deviations),
        "semantic_digest": hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
    }
