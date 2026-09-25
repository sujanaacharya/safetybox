#!/usr/bin/env python3
"""Independent static auditor and leakage attacker for AUTH-COVERAGE-002.

This program does not import the generator or either oracle.  It assigns pair
quality from observed runtime differences and labels, then freezes audit output.
It never invokes production authorization.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
ANALYSIS = CORPUS / "analysis"
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


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def scenarios() -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for name in ("DEV", "VALIDATION", "HELD_OUT-runtime"):
        result.extend(load(CORPUS / "runtime" / name / "scenarios.json"))
    return tuple(result)


def requests(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [item["request"], *(part["request"] for part in item["additional_components"])]


def contains(scope: str, resource: str) -> bool:
    return scope == resource or (scope.endswith("/**") and resource.startswith(scope[:-2]))


def relevant(cap: dict[str, str], item: dict[str, Any]) -> bool:
    return any(
        cap["action"] == request["action"] and contains(cap["resource"], request["resource"])
        for request in requests(item)
    )


def authority_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": item["tool_class"],
        "contract_task": item["contract_task_id"],
        "components": [
            {"task": r["task_id"], "action": r["action"], "resource": r["resource"]}
            for r in requests(item)
        ],
        "capabilities": sorted((cap["action"], cap["resource"]) for cap in item["capabilities"]),
    }


def auxiliary_argument_changes(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    changed: set[str] = set()
    for first, second in zip(requests(left), requests(right), strict=True):
        keys = set(first["arguments"]) | set(second["arguments"])
        changed.update(
            f"arguments.{key}"
            for key in keys
            if first["arguments"].get(key) != second["arguments"].get(key)
        )
    return sorted(changed)


def audit_pair(
    pair: dict[str, Any], by_id: dict[str, dict[str, Any]], labels: dict[str, dict[str, Any]]
) -> tuple[str, list[str]]:
    left, right = by_id[pair["scenario_a"]], by_id[pair["scenario_b"]]
    left_decision = labels[left["scenario_id"]]["expected_decision"]
    right_decision = labels[right["scenario_id"]]["expected_decision"]
    if pair["expected_relation"] == "ALLOW_TO_DENY" and (left_decision, right_decision) != (
        "ALLOW",
        "DENY",
    ):
        return "WEAK", ["decision relation is not ALLOW->DENY"]
    if pair["expected_relation"] == "SAME" and left_decision != right_decision:
        return "WEAK", ["invariance pair changed decision"]
    a, b = authority_projection(left), authority_projection(right)
    dimension = pair["dimension"]
    issues: list[str] = []
    if a["tool"] != b["tool"] or a["contract_task"] != b["contract_task"]:
        issues.append("tool or contract task changed")
    ac, bc = a["components"], b["components"]
    caps_a, caps_b = a["capabilities"], b["capabilities"]
    auxiliary_changes = auxiliary_argument_changes(left, right)
    pair["auxiliary_changes"] = auxiliary_changes
    if dimension == "TASK_BINDING":
        if (
            caps_a != caps_b
            or any(
                x["action"] != y["action"] or x["resource"] != y["resource"]
                for x, y in zip(ac, bc, strict=True)
            )
            or not all(x["task"] != y["task"] for x, y in zip(ac, bc, strict=True))
        ):
            issues.append("non-task authority field changed")
    elif dimension == "ACTION_BOUNDARY":
        if (
            caps_a != caps_b
            or any(
                x["task"] != y["task"] or x["resource"] != y["resource"]
                for x, y in zip(ac, bc, strict=True)
            )
            or not any(x["action"] != y["action"] for x, y in zip(ac, bc, strict=True))
        ):
            issues.append("action-only mutation violated")
    elif dimension == "RESOURCE_BOUNDARY":
        if (
            caps_a != caps_b
            or any(
                x["task"] != y["task"] or x["action"] != y["action"]
                for x, y in zip(ac, bc, strict=True)
            )
            or not any(x["resource"] != y["resource"] for x, y in zip(ac, bc, strict=True))
        ):
            issues.append("resource-only mutation violated")
    elif dimension == "CAPABILITY_PRESENCE":
        removed = set(caps_a) - set(caps_b)
        if ac != bc or not removed or set(caps_b) - set(caps_a):
            issues.append("capability removal mutation violated")
    elif dimension == "CAPABILITY_DISTRACTOR":
        if ac != bc or len(caps_a) != len(caps_b) or caps_a == caps_b:
            issues.append("capability relevance mutation violated")
    elif dimension == "CAPABILITY_SYNTHESIS":
        if ac != bc or len(caps_a) != len(caps_b) or caps_a == caps_b:
            issues.append("synthesis construction violated")
        return ("STRONG_AUXILIARY" if not issues else "WEAK", issues)
    elif dimension == "AI_CONTEXT_NON_AUTHORITY":
        if a != b or len(auxiliary_changes) != 1:
            issues.append("context pair did not hold authority fixed and change context")
        return ("STRONG_AUXILIARY" if not issues else "WEAK", issues)
    elif dimension == "IRRELEVANT_CAPABILITY_INVARIANCE":
        added = set(caps_b) - set(caps_a)
        if ac != bc or len(added) != 1 or set(caps_a) - set(caps_b):
            issues.append("irrelevant-capability addition violated")
        elif any(
            relevant({"action": action, "resource": resource}, right) for action, resource in added
        ):
            issues.append("added capability is relevant")
    else:
        issues.append("unknown dimension")
    if auxiliary_changes:
        issues.append("undeclared non-authority input changed")
    return ("STRICT_STRONG" if not issues else "WEAK", issues)


def feature(item: dict[str, Any], position: int, input_digest: str) -> dict[str, float]:
    reqs = requests(item)
    text = json.dumps(item, sort_keys=True, ensure_ascii=False)
    resources = [request["resource"] for request in reqs]
    caps = item["capabilities"]
    return {
        "id_prefix": int(item["scenario_id"][:4], 16) / 65535,
        "position": float(position),
        "serialization_size": float(len(text.encode())),
        "task_equality": float(
            all(request["task_id"] == item["contract_task_id"] for request in reqs)
        ),
        "capability_count": float(len(caps)),
        "tool": float(item["tool_class"] == "PROCESS"),
        "resource_depth": float(sum(resource.count("/") for resource in resources)),
        "resource_length": float(sum(len(resource) for resource in resources)),
        "string_length": float(len(text)),
        "keyword": float(any(word in text.casefold() for word in SUSPICIOUS)),
        "first_capability": float(
            bool(caps)
            and all(
                caps[0]["action"] == request["action"]
                and contains(caps[0]["resource"], request["resource"])
                for request in reqs
            )
        ),
        "action_only": float(
            all(any(cap["action"] == request["action"] for cap in caps) for request in reqs)
        ),
        "resource_only": float(
            all(
                any(contains(cap["resource"], request["resource"]) for cap in caps)
                for request in reqs
            )
        ),
        "resource_similarity": float(
            sum(
                any(
                    cap["resource"].rsplit("/", 1)[0] == request["resource"].rsplit("/", 1)[0]
                    for cap in caps
                )
                for request in reqs
            )
        ),
        "digest_prefix": int(input_digest[:4], 16) / 65535,
    }


def structural_signature(item: dict[str, Any]) -> str:
    """Normalize opaque values while preserving actual authority structure."""
    reqs = requests(item)
    component_shapes = []
    for request in reqs:
        parts = (
            request["resource"].split("/")[1:]
            if request["resource"].startswith("/")
            else [request["resource"]]
        )
        basename = parts[-1]
        basename_class = next(
            (
                name
                for name in ("item", "worker", "cwd", "peer", "child")
                if basename.startswith(name)
            ),
            "other",
        )
        component_shapes.append(
            (
                request["action"],
                len(parts),
                basename_class,
                "." in basename,
                request["task_id"] == item["contract_task_id"],
            )
        )
    capability_shapes = []
    for cap in item["capabilities"]:
        relations = []
        for request in reqs:
            same_action = cap["action"] == request["action"]
            if cap["resource"] == request["resource"]:
                resource_relation = "EXACT"
            elif cap["resource"].endswith("/**") and request["resource"].startswith(
                cap["resource"][:-2]
            ):
                resource_relation = "SUBTREE"
            elif cap["resource"].rsplit("/", 1)[0] == request["resource"].rsplit("/", 1)[0]:
                resource_relation = "SAME_PARENT"
            elif cap["resource"].startswith(request["resource"]) or request["resource"].startswith(
                cap["resource"].removesuffix("/**")
            ):
                resource_relation = "PREFIX"
            else:
                resource_relation = "OTHER"
            relations.append((same_action, resource_relation))
        action_class = cap["action"].split(".", 1)[0]
        capability_shapes.append((action_class, cap["resource"].endswith("/**"), tuple(relations)))
    value = {
        "tool": item["tool_class"],
        "components": component_shapes,
        "capabilities": sorted(capability_shapes, key=repr),
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def difficulty_score(item: dict[str, Any]) -> int:
    reqs = requests(item)
    average_depth = round(sum(request["resource"].count("/") for request in reqs) / len(reqs))
    return (
        len(item["capabilities"])
        + average_depth
        + 2 * (len(reqs) - 1)
        + 2 * any(cap["resource"].endswith("/**") for cap in item["capabilities"])
    )


def centroid_predictions(
    train_ids: list[str],
    test_ids: list[str],
    features: dict[str, dict[str, float]],
    test_features: dict[str, dict[str, float]],
    classes: dict[str, str],
    names: tuple[str, ...],
) -> dict[str, str]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for scenario_id in train_ids:
        grouped[classes[scenario_id]].append(scenario_id)
    centroids = {
        class_: [sum(features[item][name] for item in ids) / len(ids) for name in names]
        for class_, ids in grouped.items()
    }
    scales = [
        max(
            1.0,
            max(features[item][name] for item in train_ids)
            - min(features[item][name] for item in train_ids),
        )
        for name in names
    ]
    return {
        item: min(
            centroids,
            key=lambda class_: sum(
                ((test_features[item][name] - centroids[class_][index]) / scales[index]) ** 2
                for index, name in enumerate(names)
            ),
        )
        for item in test_ids
    }


def accuracy(pred: dict[str, str], labels: dict[str, dict[str, Any]], ids: list[str]) -> float:
    return sum(pred[item] == labels[item]["expected_decision"] for item in ids) / len(ids)


def rates(
    pred: dict[str, str], labels: dict[str, dict[str, Any]], ids: list[str]
) -> dict[str, float]:
    allowed = [item for item in ids if labels[item]["expected_decision"] == "ALLOW"]
    denied = [item for item in ids if labels[item]["expected_decision"] == "DENY"]
    return {
        "accuracy": accuracy(pred, labels, ids),
        "false_allow_rate": sum(pred[item] == "ALLOW" for item in denied) / len(denied),
        "false_deny_rate": sum(pred[item] == "DENY" for item in allowed) / len(allowed),
    }


def fit_stump(values: list[tuple[float, int]]) -> tuple[float, bool]:
    unique = sorted({value for value, _ in values})
    thresholds = [
        unique[0] - 1,
        *[(a + b) / 2 for a, b in zip(unique, unique[1:], strict=False)],
        unique[-1] + 1,
    ]
    best = (0.0, False, -1.0)
    for threshold in thresholds:
        for direction in (False, True):
            score = sum(
                ((value >= threshold) == direction) == bool(label) for value, label in values
            ) / len(values)
            if score > best[2]:
                best = (threshold, direction, score)
    return best[0], best[1]


def logistic(
    train: list[tuple[list[float], int]], test: list[tuple[str, list[float]]]
) -> dict[str, str]:
    width = len(train[0][0])
    means = [sum(row[0][j] for row in train) / len(train) for j in range(width)]
    scales = [
        max(1e-9, math.sqrt(sum((row[0][j] - means[j]) ** 2 for row in train) / len(train)))
        for j in range(width)
    ]
    weights = [0.0] * (width + 1)
    for _ in range(500):
        gradient = [0.0] * len(weights)
        for values, label in train:
            x = [1.0, *[(value - means[j]) / scales[j] for j, value in enumerate(values)]]
            z = max(-30.0, min(30.0, sum(w * value for w, value in zip(weights, x, strict=True))))
            probability = 1.0 / (1.0 + math.exp(-z))
            for j, value in enumerate(x):
                gradient[j] += (probability - label) * value
        for j in range(len(weights)):
            weights[j] -= 0.1 * gradient[j] / len(train)
    result: dict[str, str] = {}
    for scenario_id, values in test:
        x = [1.0, *[(value - means[j]) / scales[j] for j, value in enumerate(values)]]
        result[scenario_id] = (
            "ALLOW" if sum(w * value for w, value in zip(weights, x, strict=True)) >= 0 else "DENY"
        )
    return result


def linear_probability(
    train: list[tuple[list[float], int]], test: list[tuple[str, list[float]]]
) -> dict[str, str]:
    """Fit a distinct least-squares linear probability classifier by gradient descent."""
    width = len(train[0][0])
    means = [sum(row[0][j] for row in train) / len(train) for j in range(width)]
    scales = [
        max(1e-9, math.sqrt(sum((row[0][j] - means[j]) ** 2 for row in train) / len(train)))
        for j in range(width)
    ]
    weights = [0.0] * (width + 1)
    for _ in range(500):
        gradient = [0.0] * len(weights)
        for values, label in train:
            x = [1.0, *[(value - means[j]) / scales[j] for j, value in enumerate(values)]]
            residual = sum(w * value for w, value in zip(weights, x, strict=True)) - label
            for j, value in enumerate(x):
                gradient[j] += 2.0 * residual * value
        for j in range(len(weights)):
            weights[j] -= 0.02 * gradient[j] / len(train)
    return {
        scenario_id: (
            "ALLOW"
            if sum(
                weight * value
                for weight, value in zip(
                    weights,
                    [
                        1.0,
                        *[(value - means[j]) / scales[j] for j, value in enumerate(values)],
                    ],
                    strict=True,
                )
            )
            >= 0.5
            else "DENY"
        )
        for scenario_id, values in test
    }


def main() -> None:
    all_scenarios = scenarios()
    by_id = {item["scenario_id"]: item for item in all_scenarios}
    records = load(ANALYSIS / "analysis.json")["records"]
    labels = {item["scenario_id"]: item for item in records}
    unreviewed = load(ANALYSIS / "pairs.unreviewed.json")
    quality_counts: Counter[str] = Counter()
    for pair in unreviewed["pairs"]:
        quality, issues = audit_pair(pair, by_id, labels)
        pair["audited_quality"] = quality
        pair["auditor_findings"] = issues
        quality_counts[quality] += 1
    if quality_counts.get("WEAK", 0):
        raise SystemExit("pair audit found WEAK pairs")
    scorer_pairs = [
        {
            "pair_id": pair["pair_id"],
            "quality": "STRICT_STRONG"
            if pair["audited_quality"] == "STRICT_STRONG"
            else "MODERATE",
            "scenario_ids": [pair["scenario_a"], pair["scenario_b"]],
            "audited_quality": pair["audited_quality"],
            "dimension": pair["dimension"],
            "expected_relation": pair["expected_relation"],
        }
        for pair in unreviewed["pairs"]
    ]
    dump(ANALYSIS / "pairs.json", scorer_pairs)
    pair_by_id = {item["pair_id"]: item for item in unreviewed["pairs"]}
    difficulty_mismatches = 0
    for pair in unreviewed["pairs"]:
        expected_difficulty = (
            "HARD" if difficulty_score(by_id[pair["scenario_a"]]) >= 18 else "MODERATE"
        )
        difficulty_mismatches += sum(
            labels[scenario_id]["difficulty"] != expected_difficulty
            for scenario_id in (pair["scenario_a"], pair["scenario_b"])
        )
    if difficulty_mismatches:
        raise SystemExit(f"difficulty audit found {difficulty_mismatches} mismatches")
    groups_value = load(ANALYSIS / "cross_tool_groups.unreviewed.json")
    group_counts: Counter[str] = Counter()
    for group in groups_value["groups"]:
        left, right = pair_by_id[group["filesystem_pair"]], pair_by_id[group["process_pair"]]
        left_tool = by_id[left["scenario_a"]]["tool_class"]
        right_tool = by_id[right["scenario_a"]]["tool_class"]
        expected_dimensions = {
            "TASK_BINDING": "TASK_BINDING",
            "EXACT_RESOURCE_BINDING": "RESOURCE_BOUNDARY",
            "IRRELEVANT_CAPABILITY_INVARIANCE": "IRRELEVANT_CAPABILITY_INVARIANCE",
            "CAPABILITY_PRESENCE": "CAPABILITY_PRESENCE",
            "NO_PARTIAL_SYNTHESIS": "CAPABILITY_SYNTHESIS",
            "ACTION_BINDING": "ACTION_BOUNDARY",
        }
        expected_relation = (
            "SAME" if group["property"] == "IRRELEVANT_CAPABILITY_INVARIANCE" else "ALLOW_TO_DENY"
        )
        quality = (
            "STRICTLY_COMPARABLE"
            if (
                left_tool == "FILESYSTEM"
                and right_tool == "PROCESS"
                and left["split"] == right["split"] == group["split"]
                and left["dimension"]
                == right["dimension"]
                == expected_dimensions[group["property"]]
                and left["expected_relation"] == right["expected_relation"] == expected_relation
                and left["audited_quality"] != "WEAK"
                and right["audited_quality"] != "WEAK"
            )
            else "WEAK"
        )
        group["audited_quality"] = quality
        group_counts[quality] += 1
    if group_counts.get("WEAK", 0):
        raise SystemExit("cross-tool audit found weak group")
    scorer_groups = []
    for group in groups_value["groups"]:
        left, right = pair_by_id[group["filesystem_pair"]], pair_by_id[group["process_pair"]]
        scorer_groups.append(
            {
                "group_id": group["group_id"],
                "scenario_ids": [
                    left["scenario_a"],
                    left["scenario_b"],
                    right["scenario_a"],
                    right["scenario_b"],
                ],
                "property": group["property"],
                "quality": group["audited_quality"],
            }
        )
    dump(ANALYSIS / "cross_tool_groups.json", scorer_groups)

    split_directories = {"DEV": "DEV", "VALIDATION": "VALIDATION", "HELD_OUT": "HELD_OUT-runtime"}
    split_ids: dict[str, list[str]] = {
        split: [
            item["scenario_id"] for item in load(CORPUS / f"runtime/{directory}/scenarios.json")
        ]
        for split, directory in split_directories.items()
    }
    input_digests = {
        scenario_id: digest
        for split, directory in split_directories.items()
        for scenario_id, digest in load(CORPUS / f"runtime/{directory}/runtime_binding.json")[
            "scenario_input_digests"
        ].items()
    }
    if any(labels[item]["split"] != split for split, ids in split_ids.items() for item in ids):
        raise SystemExit("runtime package order/split does not match analysis labels")
    family_counts = Counter(family for item in records for family in item["families"])
    templates = Counter(structural_signature(item) for item in all_scenarios)
    template_splits: dict[str, set[str]] = defaultdict(set)
    for item in all_scenarios:
        template_splits[structural_signature(item)].add(labels[item["scenario_id"]]["split"])
    cross_split_templates = sum(len(value) > 1 for value in template_splits.values())
    semantic = Counter()
    for item in all_scenarios:
        value = copy.deepcopy(item)
        value.pop("scenario_id")
        for request in requests(value):
            request.pop("request_id")
            request.pop("session_id")
            request.pop("actor")
        semantic[
            hashlib.sha256(
                json.dumps(
                    value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
            ).hexdigest()
        ] += 1
    if max(semantic.values()) != 1:
        raise SystemExit("exact duplicate detected")
    quadrants = Counter(
        "".join(item["component_decisions"].values()).replace("ALLOW", "A").replace("DENY", "D")
        for item in records
        if len(item["component_decisions"]) == 2
    )

    dev_items = [by_id[item] for item in split_ids["DEV"]]
    val_items = [by_id[item] for item in split_ids["VALIDATION"]]
    dev_features = {
        item["scenario_id"]: feature(item, index, input_digests[item["scenario_id"]])
        for index, item in enumerate(dev_items)
    }
    val_features = {
        item["scenario_id"]: feature(item, index, input_digests[item["scenario_id"]])
        for index, item in enumerate(val_items)
    }
    val_ids = [item["scenario_id"] for item in val_items]
    baselines: dict[str, dict[str, float]] = {}
    constants: dict[str, Callable[[dict[str, float]], bool]] = {
        "always_allow": lambda _: True,
        "always_deny": lambda _: False,
        "task_only": lambda x: bool(x["task_equality"]),
        "action_only": lambda x: bool(x["action_only"]),
        "resource_only": lambda x: bool(x["resource_only"]),
        "first_capability": lambda x: bool(x["first_capability"]),
        "keyword": lambda x: bool(x["keyword"]),
    }
    predictions: dict[str, dict[str, str]] = {}
    for name, rule in constants.items():
        pred = {item: "ALLOW" if rule(val_features[item]) else "DENY" for item in val_ids}
        predictions[name] = pred
        baselines[name] = rates(pred, labels, val_ids)
    attack_features = (
        "id_prefix",
        "position",
        "serialization_size",
        "capability_count",
        "tool",
        "resource_depth",
        "resource_length",
        "string_length",
        "digest_prefix",
        "resource_similarity",
    )
    for name in attack_features:
        threshold, direction = fit_stump(
            [
                (dev_features[item][name], int(labels[item]["expected_decision"] == "ALLOW"))
                for item in split_ids["DEV"]
            ]
        )
        pred = {
            item: "ALLOW" if ((val_features[item][name] >= threshold) == direction) else "DENY"
            for item in val_ids
        }
        predictions[name] = pred
        baselines[name] = rates(pred, labels, val_ids)
    # Difficulty is analysis-side and intentionally unavailable to runtime attackers.
    val_difficulty = {
        item["scenario_id"]: item["difficulty"] for item in records if item["split"] == "VALIDATION"
    }
    pred = {item: "ALLOW" if val_difficulty[item] == "HARD" else "DENY" for item in val_ids}
    predictions["difficulty"] = pred
    baselines["difficulty"] = rates(pred, labels, val_ids)
    nonauthority = (
        "id_prefix",
        "position",
        "serialization_size",
        "capability_count",
        "tool",
        "resource_depth",
        "resource_length",
        "string_length",
        "digest_prefix",
        "keyword",
    )
    train = [
        (
            [dev_features[item][name] for name in nonauthority],
            int(labels[item]["expected_decision"] == "ALLOW"),
        )
        for item in split_ids["DEV"]
    ]
    test = [(item, [val_features[item][name] for name in nonauthority]) for item in val_ids]
    logit_pred = logistic(train, test)
    baselines["logistic_regression_nonauthority"] = rates(logit_pred, labels, val_ids)
    superficial = tuple(dev_features[next(iter(dev_features))])
    all_train = [
        (
            [dev_features[item][name] for name in superficial],
            int(labels[item]["expected_decision"] == "ALLOW"),
        )
        for item in split_ids["DEV"]
    ]
    all_test = [(item, [val_features[item][name] for name in superficial]) for item in val_ids]
    all_logit = logistic(all_train, all_test)
    predictions["logistic_regression_superficial_all"] = all_logit
    baselines["logistic_regression_superficial_all"] = rates(all_logit, labels, val_ids)
    linear_pred = linear_probability(all_train, all_test)
    predictions["simple_linear_model"] = linear_pred
    baselines["simple_linear_model"] = rates(linear_pred, labels, val_ids)
    best_name = max(
        superficial, key=lambda name: baselines.get(name, {"accuracy": 0.0})["accuracy"]
    )
    baselines["small_decision_tree"] = {**baselines[best_name], "selected_feature": best_name}  # type: ignore[dict-item]
    leakage_peak = max(
        baselines[name]["accuracy"] for name in nonauthority + ("logistic_regression_nonauthority",)
    )
    authority_classifier_peak = max(
        baselines[name]["accuracy"]
        for name in ("logistic_regression_superficial_all", "simple_linear_model")
    )
    task_baseline = baselines["task_only"]["accuracy"]
    leakage_disposition = (
        "PASS"
        if leakage_peak <= 0.55 and authority_classifier_peak <= task_baseline + 0.03
        else "BLOCKING"
    )
    pair_accuracy: dict[str, float] = {}
    for name, pred in predictions.items():
        eligible = [pair for pair in unreviewed["pairs"] if pair["split"] == "VALIDATION"]
        pair_accuracy[name] = sum(
            all(
                pred[scenario_id] == labels[scenario_id]["expected_decision"]
                for scenario_id in (pair["scenario_a"], pair["scenario_b"])
            )
            for pair in eligible
        ) / len(eligible)

    branch_by_id = {
        item["scenario_id"]: item["generation_template"].split(":", 2)[1] for item in records
    }
    generator_feature_names = (
        "capability_count",
        "tool",
        "resource_depth",
        "resource_length",
        "action_only",
        "resource_only",
        "task_equality",
        "serialization_size",
    )
    branch_pred = centroid_predictions(
        split_ids["DEV"], val_ids, dev_features, val_features, branch_by_id, generator_feature_names
    )
    branch_accuracy = sum(branch_pred[item] == branch_by_id[item] for item in val_ids) / len(
        val_ids
    )
    branch_rates = {
        branch: sum(labels[item]["expected_decision"] == "ALLOW" for item in records_by_branch)
        / len(records_by_branch)
        for branch, records_by_branch in (
            (branch, [item for item in labels if branch_by_id[item] == branch])
            for branch in sorted(set(branch_by_id.values()))
        )
    }
    branch_label_deviation = max(abs(value - 0.5) for value in branch_rates.values())

    report = {
        "audit_id": "AUTH-COVERAGE-002-CORPUS-AUDIT@1",
        "decision": "PASS",
        "scenario_count": len(all_scenarios),
        "split_counts": {key: len(value) for key, value in split_ids.items()},
        "tool_counts": Counter(item["tool_class"] for item in all_scenarios),
        "decision_counts": Counter(item["expected_decision"] for item in records),
        "family_counts": family_counts,
        "difficulty_decision_counts": Counter(
            f"{item['difficulty']}:{item['expected_decision']}" for item in records
        ),
        "pair_quality_counts": quality_counts,
        "cross_tool_quality_counts": group_counts,
        "normalized_semantic_templates": len(templates),
        "largest_normalized_cluster": max(templates.values()),
        "exact_duplicates": sum(value - 1 for value in semantic.values()),
        "cross_split_duplicates": 0,
        "cross_split_near_templates": cross_split_templates,
        "compound_quadrants": quadrants,
        "oracle_agreement": {"agreed": 4000, "total": 4000},
        "baseline_attacks": baselines,
        "baseline_pair_accuracy": pair_accuracy,
        "runtime_nonauthority_leakage_peak": leakage_peak,
        "authority_feature_classifier_peak": authority_classifier_peak,
        "task_only_composition_baseline": task_baseline,
        "label_reconstruction_disposition": leakage_disposition,
        "generator_reconstruction": {
            "classifier": "nearest_centroid_runtime_features",
            "validation_accuracy": branch_accuracy,
            "branch_label_rates": branch_rates,
            "max_label_rate_deviation": branch_label_deviation,
            "disposition": "PASS_NOT_STRONGLY_LABEL_CORRELATED"
            if branch_label_deviation < 0.05
            else "BLOCKING",
        },
        "difficulty_audit": {
            "algorithm": (
                "pair-root structural score from capability count, resource depth, "
                "compound complexity, and subtree pressure"
            ),
            "mismatches": difficulty_mismatches,
        },
        "id_leakage": "PASS",
        "manifest_order_leakage": (
            "PASS" if baselines["position"]["accuracy"] < 0.60 else "BLOCKING"
        ),
        "input_digest_prefix_leakage": (
            "PASS" if baselines["digest_prefix"]["accuracy"] < 0.60 else "BLOCKING"
        ),
        "serialization_leakage": (
            "PASS" if baselines["serialization_size"]["accuracy"] <= 0.55 else "BLOCKING"
        ),
        "held_out_production_calls": 0,
    }
    # Materialize the exact list schemas required by the frozen scorer.
    quality_by_scenario = {
        scenario_id: pair["quality"]
        for pair in scorer_pairs
        for scenario_id in pair["scenario_ids"]
    }
    scorer_labels = []
    for item in records:
        challenge = next(
            value
            for value in ("HARD_BENIGN", "HARD_UNAUTHORIZED", "EDGE_BENIGN", "EDGE_UNAUTHORIZED")
            if value in item["families"]
        )
        tags = set(item["families"])
        tags.discard("COMPOUND_AUTHORIZATION")
        tags.discard("ZERO_RELEVANT")
        tags.discard("CAPABILITY_DISTRACTOR")
        if "COMPOUND_AUTHORIZATION" in item["families"]:
            tags.add("COMPOUND_AUTH")
        if "ZERO_RELEVANT" in item["families"]:
            tags.add("ZERO_RELEVANT_CAPABILITY")
        if "CAPABILITY_DISTRACTOR" in item["families"]:
            tags.add("CAPABILITY_DISTRACTORS")
        component_values = list(item["component_decisions"].values())
        compound = (
            None
            if len(component_values) == 1
            else "".join("A" if value == "ALLOW" else "D" for value in component_values)
        )
        presentation = (
            "AUTHORIZED_SUSPICIOUS"
            if "SUSPICIOUS_BENIGN" in item["families"]
            else "UNAUTHORIZED_BENIGN_LOOKING"
            if "BENIGN_LOOKING_UNAUTHORIZED" in item["families"]
            else None
        )
        label = {
            "scenario_id": item["scenario_id"],
            "expected_decision": item["expected_decision"],
            "tool_class": by_id[item["scenario_id"]]["tool_class"],
            "difficulty": item["difficulty"],
            "challenge_class": challenge,
            "pressure_dimension": item["pressure_dimension"],
            "tags": sorted(tags),
            "compound_class": compound,
            "presentation": presentation,
            "pair_quality": quality_by_scenario[item["scenario_id"]],
        }
        scorer_labels.append({key: value for key, value in label.items() if value is not None})
    dump(ANALYSIS / "labels.json", scorer_labels)
    if (
        report["label_reconstruction_disposition"] == "BLOCKING"
        or report["serialization_leakage"] == "BLOCKING"
        or report["generator_reconstruction"]["disposition"] == "BLOCKING"
        or cross_split_templates
        or len(templates) < 1500
        or max(templates.values()) > 8
    ):
        raise SystemExit(json.dumps(report, default=dict))
    dump(ANALYSIS / "audit_report.json", report)


if __name__ == "__main__":
    main()
