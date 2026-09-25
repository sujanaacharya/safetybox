#!/usr/bin/env python3
"""Derive Protocol@2 metrics from candidate records instead of trusting summaries."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from external_pack import validate_external_pack
from governance import (
    evaluate_gates,
    normative_explanation,
    pair_audit,
    presentation_class,
    score_raw_record,
    structural_hash,
)
from leakage_suite import (
    branch_inference_balanced_accuracy,
    run_secondary_targets,
    run_suite,
)
from oracle_a import evaluate as oracle_a
from oracle_b import evaluate as oracle_b
from schema import validate_runtime

from safetybox.authorization import AuthorizationComponent
from safetybox.capabilities import Capability
from safetybox.models import ActionRequest
from safetybox.research.auth_coverage_raw import (
    canonical_sha256,
    capture_authorization_input,
    raw_record_from_json,
)


def _requests(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    return [runtime["request"], *(item["request"] for item in runtime["additional_components"])]


def _covers(scope: str, resource: str) -> bool:
    if scope == resource:
        return True
    if not scope.endswith("/**"):
        return False
    left, right = scope[:-3].split("/"), resource.split("/")
    return len(right) > len(left) and right[: len(left)] == left


def _predicates(runtime: dict[str, Any]) -> dict[str, bool | int]:
    requests = _requests(runtime)
    capabilities = runtime["capabilities"]
    relevant = [
        (capability, request)
        for capability in capabilities
        for request in requests
        if capability["action"] == request["action"]
        and _covers(capability["resource"], request["resource"])
    ]
    task = any(request["task_id"] != runtime["contract_task_id"] for request in requests)
    resource = any(
        capability["action"] == request["action"]
        and not _covers(capability["resource"], request["resource"])
        for capability in capabilities
        for request in requests
    )
    action = any(
        capability["resource"] == request["resource"] and capability["action"] != request["action"]
        for capability in capabilities
        for request in requests
    )
    synthesis = any(
        not any(
            capability["action"] == request["action"]
            and _covers(capability["resource"], request["resource"])
            for capability in capabilities
        )
        and any(capability["action"] == request["action"] for capability in capabilities)
        and any(_covers(capability["resource"], request["resource"]) for capability in capabilities)
        for request in requests
    )
    difficulty = (
        (2 if len(capabilities) >= 3 else 0)
        + (2 if max(request["resource"].count("/") for request in requests) >= 4 else 0)
        + (1 if all(bool(request["arguments"]) for request in requests) else 0)
        + (1 if len(requests) == 2 else 0)
    )
    return {
        "task_binding": task,
        "resource_boundary": resource,
        "action_boundary": action,
        "capability_synthesis": synthesis,
        "zero_relevant": not relevant,
        "difficulty": difficulty,
    }


def _semantic_instance(runtime: dict[str, Any]) -> str:
    """Remove opaque per-record IDs while retaining task equality and all semantic values."""
    value = json.loads(json.dumps(runtime, sort_keys=True))
    value.pop("scenario_id", None)
    contract_task = value["contract_task_id"]
    value["contract_task_id"] = "TASK_CONTRACT"
    requests = [value["request"], *(item["request"] for item in value["additional_components"])]
    other_tasks: dict[str, str] = {}
    for request in requests:
        for field in ("request_id", "session_id", "actor"):
            request.pop(field, None)
        task = request["task_id"]
        if task == contract_task:
            request["task_id"] = "TASK_CONTRACT"
        else:
            request["task_id"] = other_tasks.setdefault(task, f"TASK_OTHER_{len(other_tasks)}")
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _production_input_digest(runtime: dict[str, Any]) -> str:
    def request(value: dict[str, Any]) -> ActionRequest:
        return ActionRequest(
            request_id=value["request_id"],
            session_id=value["session_id"],
            task_id=value["task_id"],
            actor=value["actor"],
            action=value["action"],
            resource=value["resource"],
            arguments=value["arguments"],
        )

    captured = capture_authorization_input(
        tool_class=runtime["tool_class"],
        contract_task_id=runtime["contract_task_id"],
        contract_description=runtime["contract_description"],
        received_capabilities=tuple(
            Capability(item["action"], item["resource"]) for item in runtime["capabilities"]
        ),
        primary_request=request(runtime["request"]),
        additional_components=tuple(
            AuthorizationComponent(item["name"], request(item["request"]))
            for item in runtime["additional_components"]
        ),
    )
    return canonical_sha256(captured)


def derive_metrics(candidate: dict[str, Any]) -> dict[str, Any]:
    records = candidate["records"]
    if len({item["scenario_id"] for item in records}) != len(records):
        raise ValueError("scenario IDs are not unique")
    for item in records:
        validate_runtime(item["runtime"])
        if item["scenario_id"] != item["runtime"]["scenario_id"]:
            raise ValueError("outer scenario_id does not match runtime scenario_id")
    labels = Counter(item["label"] for item in records)
    splits = Counter(item["split"] for item in records)
    split_labels = Counter(f"{item['split']}_{item['label']}" for item in records)
    presentations = Counter(presentation_class(item["runtime"], item["label"]) for item in records)
    predicates = {item["scenario_id"]: _predicates(item["runtime"]) for item in records}
    oracle_results: dict[str, dict[str, Any]] = {}
    oracle_agreed = 0
    quadrants: Counter[str] = Counter()
    for item in records:
        a, b = oracle_a(item["runtime"]), oracle_b(item["runtime"])
        if a["rule"] == "AUTH.INVALID_STRUCTURE" or b["rule"] == "AUTH.INVALID_STRUCTURE":
            raise ValueError("spec-invalid scenario cannot be canonical")
        oracle_results[item["scenario_id"]] = a
        oracle_agreed += a == b and a["decision"] == item["label"]
        decisions = "".join(value["decision"][0] for value in a["components"].values())
        if len(decisions) == 2:
            quadrants[decisions] += 1
    cross_task_values: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in records:
        for capability in item["runtime"]["capabilities"]:
            cross_task_values[(capability["action"], capability["resource"])].add(
                item["runtime"]["contract_task_id"]
            )
    cross_task = sum(
        any(
            len(cross_task_values[(cap["action"], cap["resource"])]) > 1
            for cap in item["runtime"]["capabilities"]
        )
        for item in records
    )
    semantic = [_semantic_instance(item["runtime"]) for item in records]
    structural = [structural_hash(item["runtime"]) for item in records]
    dev_hashes = {
        value for value, item in zip(structural, records, strict=True) if item["split"] == "DEV"
    }
    validation_hashes = {
        value
        for value, item in zip(structural, records, strict=True)
        if item["split"] == "VALIDATION"
    }
    split_semantic: dict[str, set[str]] = defaultdict(set)
    for digest, item in zip(semantic, records, strict=True):
        split_semantic[item["split"]].add(digest)
    cross_instances = sum(
        len(split_semantic[left] & split_semantic[right])
        for left, right in (("DEV", "VALIDATION"), ("DEV", "HELD_OUT"), ("VALIDATION", "HELD_OUT"))
    )
    by_id = {item["scenario_id"]: item for item in records}
    pair_evidence = []
    family_by_scenario: dict[str, str] = {}
    seen_scenarios: set[str] = set()
    seen_pair_ids: set[str] = set()
    for intention in candidate["pair_intentions"]:
        if intention["pair_id"] in seen_pair_ids:
            raise ValueError("pair_id is not unique")
        seen_pair_ids.add(intention["pair_id"])
        if intention["scenario_a"] in seen_scenarios or intention["scenario_b"] in seen_scenarios:
            raise ValueError("a scenario occurs in more than one pair")
        seen_scenarios.update((intention["scenario_a"], intention["scenario_b"]))
        left, right = by_id[intention["scenario_a"]], by_id[intention["scenario_b"]]
        audit_intention = {
            key: intention[key] for key in ("pair_id", "target_dimension", "expected_relation")
        }
        pair_evidence.append(
            pair_audit(
                audit_intention,
                {"authoring_key": left["scenario_id"], **left},
                {"authoring_key": right["scenario_id"], **right},
            )
        )
        dimension = intention["target_dimension"]
        if dimension == "TASK":
            family = "TASK_BINDING"
        elif dimension == "RESOURCE":
            family = "RESOURCE_BOUNDARY"
        elif dimension == "ACTION":
            family = "ACTION_BOUNDARY"
        elif dimension == "CAPABILITY":
            allow = left if left["label"] == "ALLOW" else right
            deny = right if left["label"] == "ALLOW" else left
            if bool(_predicates(deny["runtime"])["capability_synthesis"]):
                family = "CAPABILITY_SYNTHESIS"
            else:
                allow_caps = Counter(
                    (cap["action"], cap["resource"])
                    for cap in allow["runtime"]["capabilities"]
                )
                deny_caps = Counter(
                    (cap["action"], cap["resource"])
                    for cap in deny["runtime"]["capabilities"]
                )
                additions = list((deny_caps - allow_caps).elements())
                denied_components = sum(
                    component["decision"] == "DENY"
                    for component in oracle_results[deny["scenario_id"]]["components"].values()
                )
                if len(additions) == denied_components:
                    family = "CAPABILITY_PRESENCE"
                elif len(additions) == denied_components + 1:
                    family = "CAPABILITY_DISTRACTOR"
                else:
                    raise ValueError("capability pair does not identify a frozen family")
        else:
            raise ValueError("COMPOUND pairs are not a Generator@2 family")
        for scenario_id in (intention["scenario_a"], intention["scenario_b"]):
            family_by_scenario[scenario_id] = family
    pair_counts = Counter(item["quality_classification"] for item in pair_evidence)
    pair_by_id = {item["pair_id"]: item for item in pair_evidence}
    cross_tool_strict = 0
    used_cross_tool_pairs: set[str] = set()
    for group in candidate["cross_tool_groups"]:
        group_pair_ids = {group["filesystem_pair_id"], group["process_pair_id"]}
        if used_cross_tool_pairs & group_pair_ids:
            raise ValueError("cross-tool pair reused across groups")
        used_cross_tool_pairs.update(group_pair_ids)
        filesystem = pair_by_id[group["filesystem_pair_id"]]
        process = pair_by_id[group["process_pair_id"]]
        endpoints = {
            filesystem["scenario_a"],
            filesystem["scenario_b"],
            process["scenario_a"],
            process["scenario_b"],
        }
        if (
            len(endpoints) == 4
            and filesystem["quality_classification"] == "STRICT_STRONG"
            and process["quality_classification"] == "STRICT_STRONG"
            and filesystem["target_dimension"] == process["target_dimension"]
            and filesystem["expected_relation"] == process["expected_relation"]
            and all(
                by_id[scenario]["runtime"]["tool_class"] == "FILESYSTEM"
                for scenario in (filesystem["scenario_a"], filesystem["scenario_b"])
            )
            and all(
                by_id[scenario]["runtime"]["tool_class"] == "PROCESS"
                for scenario in (process["scenario_a"], process["scenario_b"])
            )
        ):
            cross_tool_strict += 1
    explanation_complete = 0
    for item in records:
        payload = candidate.get("raw_records", {}).get(item["scenario_id"])
        expected = normative_explanation(item["runtime"], oracle_results[item["scenario_id"]])
        if payload is not None and not score_raw_record(raw_record_from_json(payload), expected):
            explanation_complete += 1
    prepared = []
    for item in records:
        scenario_id = item["scenario_id"]
        family = family_by_scenario.get(scenario_id)
        if family is None:
            raise ValueError("every canonical scenario must belong to one audited pair")
        parts = item.get("generator_branch", "").split(":")
        expected_parent = f"{item['runtime']['tool_class']}:{family}"
        if (
            len(parts) != 3
            or ":".join(parts[:2]) != expected_parent
            or parts[2] not in {str(value) for value in range(7)}
            or item.get("families") != [family]
        ):
            raise ValueError("generator metadata disagrees with audited semantics")
        digest = _production_input_digest(item["runtime"])
        prepared.append(
            {
                **item,
                "families": [family],
                "difficulty": "HARD"
                if predicates[scenario_id]["difficulty"] >= 5
                else "MODERATE",
                "input_digest": digest,
            }
        )
    dev = [item for item in prepared if item["split"] == "DEV"]
    validation = [item for item in prepared if item["split"] == "VALIDATION"]
    leakage = (
        run_suite(dev, validation)
        if len(dev) == len(validation) == 800
        else candidate.get("dev_proof_leakage", {})
    )
    secondary = run_secondary_targets(dev, validation) if len(dev) == len(validation) == 800 else {}
    branches: dict[str, Counter[str]] = defaultdict(Counter)
    leaves: dict[str, Counter[str]] = defaultdict(Counter)
    for item in prepared:
        parent = ":".join(item["generator_branch"].split(":")[:2])
        branches[parent][item["label"]] += 1
        leaves[item["generator_branch"]][item["label"]] += 1
    registered_parents = {
        f"{tool}:{family}"
        for tool in ("FILESYSTEM", "PROCESS")
        for family in (
            "TASK_BINDING",
            "RESOURCE_BOUNDARY",
            "ACTION_BOUNDARY",
            "CAPABILITY_SYNTHESIS",
            "CAPABILITY_PRESENCE",
            "CAPABILITY_DISTRACTOR",
        )
    }
    if set(branches) != registered_parents:
        raise ValueError("observed generator parents do not equal the frozen registry")
    registered_leaves = {
        f"{parent}:{lane}" for parent in registered_parents for lane in range(7)
    }
    if set(leaves) != registered_leaves:
        raise ValueError("observed generator leaves do not equal the frozen registry")
    evaluated_branches: list[Counter[str]] = []
    for leaf, counts in leaves.items():
        parent = ":".join(leaf.split(":")[:2])
        evaluated_branches.append(counts if sum(counts.values()) >= 40 else branches[parent])
    branch_support = [sum(counts.values()) for counts in evaluated_branches]
    branch_metrics = {
        "max_label_rate_deviation": max(
            (
                abs(counts["ALLOW"] / sum(counts.values()) - 0.5)
                for counts in evaluated_branches
            ),
            default=1.0,
        ),
        "minimum_support": min(branch_support, default=0),
        "inference_balanced_accuracy": branch_inference_balanced_accuracy(dev, validation)
        if len(dev) == len(validation) == 800
        else 1.0,
    }
    external_results = [validate_external_pack(pack) for pack in candidate["external_packs"]]
    total_pairs = len(pair_evidence)
    strict = pair_counts["STRICT_STRONG"]
    metric = {
        "phase": candidate["phase"],
        "realized_split": dict(splits),
        "counts": {
            "total": len(records),
            "split": {name: splits[name] for name in ("DEV", "VALIDATION", "HELD_OUT")},
            "split_label": {
                key: split_labels[key]
                for key in (
                    "DEV_ALLOW",
                    "DEV_DENY",
                    "VALIDATION_ALLOW",
                    "VALIDATION_DENY",
                    "HELD_OUT_ALLOW",
                    "HELD_OUT_DENY",
                )
            },
            "authorized": labels["ALLOW"],
            "unauthorized": labels["DENY"],
            "hard_benign": sum(
                item["label"] == "ALLOW" and predicates[item["scenario_id"]]["difficulty"] >= 5
                for item in records
            ),
            "hard_unauthorized": sum(
                item["label"] == "DENY" and predicates[item["scenario_id"]]["difficulty"] >= 5
                for item in records
            ),
            "benign_looking_unauthorized": presentations["BENIGN_LOOKING_UNAUTHORIZED"],
            "suspicious_authorized": presentations["SUSPICIOUS_AUTHORIZED"],
            "task_binding": sum(
                family == "TASK_BINDING" for family in family_by_scenario.values()
            ),
            "cross_task": cross_task,
            "resource_boundary": sum(
                family == "RESOURCE_BOUNDARY" for family in family_by_scenario.values()
            ),
            "action_boundary": sum(
                family == "ACTION_BOUNDARY" for family in family_by_scenario.values()
            ),
            "capability_synthesis": sum(
                family == "CAPABILITY_SYNTHESIS" for family in family_by_scenario.values()
            ),
            "zero_relevant": sum(bool(value["zero_relevant"]) for value in predicates.values()),
            "compound_quadrant_min": min(quadrants.values(), default=0),
        },
        "duplicates": {
            "exact": len(semantic) - len(set(semantic)),
            "cross_split_instance": cross_instances,
            "cross_split_structural_overlap_proportion": len(dev_hashes & validation_hashes)
            / len(validation_hashes)
            if validation_hashes
            else 0.0,
        },
        "pair": {
            "strict": strict,
            "strict_proportion": strict / total_pairs if total_pairs else 0.0,
            "cross_tool_strict": cross_tool_strict,
            "weak": pair_counts["WEAK"],
        },
        "diversity": {
            "semantic_templates": len(set(structural)),
            "largest_cluster": max(Counter(structural).values(), default=0),
        },
        "held_out": candidate["exposure"],
        "formal": candidate["formal"],
        "oracle": {"agreement_rate": oracle_agreed / len(records) if records else 0.0},
        "explanation": {
            "compatibility_rate": explanation_complete / len(records) if records else 0.0
        },
        "external_pack": {
            "oracle_agreement_rate": 1.0
            if all(result["oracle_agreement"] == 1.0 for result in external_results)
            else 0.0
        },
        "branch": branch_metrics,
        "secondary_prediction": secondary,
        "leakage": leakage,
    }
    return metric


def audit_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return evaluate_gates(derive_metrics(candidate))
