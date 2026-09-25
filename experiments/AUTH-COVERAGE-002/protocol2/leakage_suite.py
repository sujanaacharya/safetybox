#!/usr/bin/env python3
"""Frozen executable label-inference adversary for Protocol@2."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from itertools import pairwise
from typing import Any

ATTACKS = (
    "id_only",
    "position_order",
    "serialization_size",
    "capability_count",
    "resource_depth",
    "resource_length",
    "keyword",
    "digest_prefix",
    "logistic",
    "small_tree",
    "linear",
    "categorical",
)
KEYWORDS = (
    "admin",
    "credential",
    "delete",
    "exfiltrate",
    "exploit",
    "passwd",
    "password",
    "private key",
    "root",
    "secret",
    "ssh",
    "sudo",
    "token",
    "upload",
)
NUMERIC = (
    "id",
    "position",
    "bytes",
    "fields",
    "path_depth",
    "path_length",
    "cap_count",
    "digest",
    "key_order",
    "cap_order",
    "keyword",
)


def _walk(value: object) -> int:
    if isinstance(value, dict):
        return len(value) + sum(_walk(item) for item in value.values())
    if isinstance(value, list):
        return len(value) + sum(_walk(item) for item in value)
    return 1


def _key_order(value: object) -> object:
    if isinstance(value, dict):
        return [list(value), *[_key_order(item) for item in value.values()]]
    if isinstance(value, list):
        return [_key_order(item) for item in value]
    return None


def features(runtime: dict[str, Any], position: int, digest: str) -> dict[str, float | str]:
    requests = [runtime["request"], *(item["request"] for item in runtime["additional_components"])]
    canonical = json.dumps(runtime, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    resources = [item["resource"] for item in requests]
    capabilities = runtime["capabilities"]
    key_order = hashlib.sha256(json.dumps(_key_order(runtime)).encode()).hexdigest()
    cap_order = hashlib.sha256(json.dumps(capabilities, separators=(",", ":")).encode()).hexdigest()
    return {
        "id": int(runtime["scenario_id"][:4], 16) / 65535,
        "position": float(position),
        "bytes": float(len(canonical.encode())),
        "fields": float(_walk(runtime)),
        "path_depth": float(sum(item.count("/") for item in resources)),
        "path_length": float(sum(len(item) for item in resources)),
        "cap_count": float(len(capabilities)),
        "digest": int(digest[:4], 16) / 65535,
        "key_order": int(key_order[:4], 16) / 65535,
        "cap_order": int(cap_order[:4], 16) / 65535,
        "keyword": float(any(word in canonical.casefold() for word in KEYWORDS)),
        "tool": runtime["tool_class"],
        "actions": "|".join(item["action"] for item in requests),
        "shapes": "|".join(str(item.count("/")) for item in resources),
    }


def _threshold_train(
    rows: list[dict[str, Any]], labels: list[int], field: str
) -> tuple[float, bool]:
    values = sorted({float(row[field]) for row in rows})
    thresholds = [
        values[0] - 1.0,
        *[(a + b) / 2 for a, b in pairwise(values)],
        values[-1] + 1.0,
    ]
    best = (-1, 0.0, False)
    for threshold in thresholds:
        for reverse in (False, True):
            predictions = [int((float(row[field]) >= threshold) ^ reverse) for row in rows]
            correct = sum(a == b for a, b in zip(predictions, labels, strict=True))
            candidate = (correct, -threshold, not reverse)
            if candidate > (best[0], -best[1], not best[2]):
                best = (correct, threshold, reverse)
    return best[1], best[2]


def _categorical_train(
    rows: list[dict[str, Any]], labels: list[int], fields: tuple[str, ...]
) -> dict[tuple[str, ...], int]:
    groups: dict[tuple[str, ...], Counter[int]] = defaultdict(Counter)
    for row, label in zip(rows, labels, strict=True):
        groups[tuple(str(row[field]) for field in fields)][label] += 1
    return {key: int(counts[1] > counts[0]) for key, counts in groups.items()}


def _standardize(
    train: list[dict[str, Any]], other: list[dict[str, Any]]
) -> tuple[list[list[float]], list[list[float]]]:
    means = [sum(float(row[field]) for row in train) / len(train) for field in NUMERIC]
    deviations = [
        math.sqrt(sum((float(row[field]) - mean) ** 2 for row in train) / len(train)) or 1.0
        for field, mean in zip(NUMERIC, means, strict=True)
    ]

    def apply(rows: list[dict[str, Any]]) -> list[list[float]]:
        return [
            [
                1.0,
                *[
                    (float(row[field]) - mean) / dev
                    for field, mean, dev in zip(NUMERIC, means, deviations, strict=True)
                ],
            ]
            for row in rows
        ]

    return apply(train), apply(other)


def _gradient_model(x: list[list[float]], labels: list[int], logistic: bool) -> list[float]:
    weights = [0.0] * len(x[0])
    for _ in range(500):
        gradient = [0.0] * len(weights)
        for row, label in zip(x, labels, strict=True):
            score = sum(a * b for a, b in zip(weights, row, strict=True))
            prediction = 1 / (1 + math.exp(-max(-30.0, min(30.0, score)))) if logistic else score
            for index, value in enumerate(row):
                gradient[index] += (prediction - label) * value
        for index in range(len(weights)):
            penalty = 0.0 if index == 0 else weights[index]
            weights[index] -= 0.05 * (gradient[index] / len(x) + penalty / len(x))
    return weights


def _tree_train(rows: list[dict[str, Any]], labels: list[int], depth: int = 0) -> dict[str, Any]:
    majority = int(sum(labels) > len(labels) / 2)
    if depth == 3 or len(rows) < 80 or len(set(labels)) == 1:
        return {"label": majority}
    best: tuple[float, str, float, list[int], list[int]] | None = None
    for field in NUMERIC:
        values = sorted({float(row[field]) for row in rows})
        for threshold in [(a + b) / 2 for a, b in pairwise(values)]:
            left = [index for index, row in enumerate(rows) if float(row[field]) < threshold]
            right = [index for index in range(len(rows)) if index not in set(left)]
            if min(len(left), len(right)) < 40:
                continue

            def gini(indexes: list[int]) -> float:
                rate = sum(labels[index] for index in indexes) / len(indexes)
                return 2 * rate * (1 - rate)

            score = (len(left) * gini(left) + len(right) * gini(right)) / len(rows)
            candidate = (score, field, threshold, left, right)
            if best is None or candidate[:3] < best[:3]:
                best = candidate
    if best is None:
        return {"label": majority}
    _, field, threshold, left, right = best
    return {
        "field": field,
        "threshold": threshold,
        "left": _tree_train([rows[i] for i in left], [labels[i] for i in left], depth + 1),
        "right": _tree_train([rows[i] for i in right], [labels[i] for i in right], depth + 1),
    }


def _tree_predict(tree: dict[str, Any], row: dict[str, Any]) -> int:
    while "label" not in tree:
        tree = tree["left"] if float(row[tree["field"]]) < tree["threshold"] else tree["right"]
    return int(tree["label"])


def _rates(predictions: list[int], labels: list[int]) -> dict[str, float]:
    positives = sum(labels)
    negatives = len(labels) - positives
    false_allow = (
        sum(
            prediction == 1 and label == 0
            for prediction, label in zip(predictions, labels, strict=True)
        )
        / negatives
    )
    false_deny = (
        sum(
            prediction == 0 and label == 1
            for prediction, label in zip(predictions, labels, strict=True)
        )
        / positives
    )
    accuracy = sum(a == b for a, b in zip(predictions, labels, strict=True)) / len(labels)
    return {
        "accuracy": accuracy,
        "balanced_accuracy": 1 - (false_allow + false_deny) / 2,
        "false_allow_rate": false_allow,
        "false_deny_rate": false_deny,
    }


def _deterministic(values: list[object], labels: list[int]) -> bool:
    groups: dict[object, set[int]] = defaultdict(set)
    support: Counter[object] = Counter(values)
    for value, label in zip(values, labels, strict=True):
        groups[value].add(label)
    eligible = [value for value in groups if support[value] >= 2]
    return bool(eligible) and all(len(groups[value]) == 1 for value in eligible)


def _prefix_deterministic(values: list[str], labels: list[int]) -> bool:
    return any(
        _deterministic([value[: bits // 4] for value in values], labels)
        for bits in (4, 8, 12, 16, 20, 24, 32)
    )


def _order_model(train_labels: list[int], evaluation_n: int) -> tuple[list[int], int]:
    """Fit the strongest frozen periodic manifest-order shortcut (moduli 2..32)."""
    best: tuple[int, int, dict[int, int]] | None = None
    for modulus in range(2, 33):
        counts: dict[int, Counter[int]] = defaultdict(Counter)
        for position, label in enumerate(train_labels):
            counts[position % modulus][label] += 1
        lookup = {
            residue: int(values[1] > values[0]) for residue, values in counts.items()
        }
        correct = sum(
            lookup[position % modulus] == label
            for position, label in enumerate(train_labels)
        )
        candidate = (correct, -modulus, lookup)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    assert best is not None
    modulus = -best[1]
    return [best[2][position % modulus] for position in range(evaluation_n)], modulus


def run_suite(
    train_records: list[dict[str, Any]],
    validation_records: list[dict[str, Any]],
    permutations: int = 10000,
) -> dict[str, dict[str, Any]]:
    if len(validation_records) != 800:
        raise ValueError("canonical leakage evaluation requires exactly 800 VALIDATION records")
    train_rows = [
        features(item["runtime"], index, item["input_digest"])
        for index, item in enumerate(train_records)
    ]
    val_rows = [
        features(item["runtime"], index, item["input_digest"])
        for index, item in enumerate(validation_records)
    ]
    train_labels = [int(item["label"] == "ALLOW") for item in train_records]
    val_labels = [int(item["label"] == "ALLOW") for item in validation_records]
    if Counter(val_labels) != {0: 400, 1: 400}:
        raise ValueError("VALIDATION labels must be exactly 400 ALLOW and 400 DENY")
    standardized_train, standardized_val = _standardize(train_rows, val_rows)
    predictions: dict[str, list[int]] = {}
    fields = {
        "id_only": "id",
        "serialization_size": "bytes",
        "capability_count": "cap_count",
        "resource_depth": "path_depth",
        "resource_length": "path_length",
        "keyword": "keyword",
        "digest_prefix": "digest",
    }
    for name, field in fields.items():
        threshold, reverse = _threshold_train(train_rows, train_labels, field)
        predictions[name] = [int((float(row[field]) >= threshold) ^ reverse) for row in val_rows]
    predictions["position_order"], order_modulus = _order_model(train_labels, len(val_labels))
    for name, logistic in (("logistic", True), ("linear", False)):
        weights = _gradient_model(standardized_train, train_labels, logistic)
        predictions[name] = [
            int(sum(a * b for a, b in zip(weights, row, strict=True)) >= (0.0 if logistic else 0.5))
            for row in standardized_val
        ]
    tree = _tree_train(train_rows, train_labels)
    predictions["small_tree"] = [_tree_predict(tree, row) for row in val_rows]
    categorical_fields = ("tool", "actions", "shapes", "cap_count", "keyword")
    lookup = _categorical_train(train_rows, train_labels, categorical_fields)
    predictions["categorical"] = [
        lookup.get(tuple(str(row[field]) for field in categorical_fields), 0) for row in val_rows
    ]
    rng = random.Random(2002099)
    result: dict[str, dict[str, Any]] = {}
    for name in ATTACKS:
        rates = _rates(predictions[name], val_labels)
        observed = rates["balanced_accuracy"]
        extreme = 0
        shuffled = val_labels[:]
        for _ in range(permutations):
            rng.shuffle(shuffled)
            if _rates(predictions[name], shuffled)["balanced_accuracy"] >= observed:
                extreme += 1
        source_field = fields.get(name)
        if name == "id_only":
            deterministic = _prefix_deterministic(
                [item["runtime"]["scenario_id"] for item in validation_records], val_labels
            )
        elif name == "digest_prefix":
            deterministic = _prefix_deterministic(
                [item["input_digest"] for item in validation_records], val_labels
            )
        elif name == "position_order":
            deterministic = _deterministic(
                [position % order_modulus for position in range(len(val_labels))], val_labels
            )
        else:
            deterministic = (
                _deterministic([row[source_field] for row in val_rows], val_labels)
                if source_field
                else False
            )
        result[name] = {
            **rates,
            "permutation_p": (1 + extreme) / (permutations + 1),
            "deterministic_or_reversible": deterministic,
            "evaluation_n": 800,
        }
    return result


def run_secondary_targets(
    train_records: list[dict[str, Any]], validation_records: list[dict[str, Any]]
) -> dict[str, dict[str, float]]:
    """Predict frozen metadata targets and quantify their causal label pathway."""
    targets = ("family", "difficulty", "pair_membership", "generator_branch")

    def target(record: dict[str, Any], name: str) -> str:
        if name == "family":
            return "|".join(sorted(record["families"]))
        if name == "pair_membership":
            return str(bool(record.get("pair_id")))
        if name == "generator_branch":
            parts = record["generator_branch"].split(":")
            return ":".join(parts[:2])
        return str(record[name])

    def signature(record: dict[str, Any], position: int) -> tuple[str, ...]:
        row = features(record["runtime"], position, record["input_digest"])
        return tuple(
            str(row[field]) for field in ("tool", "actions", "shapes", "cap_count", "keyword")
        )

    output: dict[str, dict[str, float]] = {}
    for name in targets:
        global_counts = Counter(target(record, name) for record in train_records)
        global_majority = min(global_counts, key=lambda value: (-global_counts[value], value))
        lookup_counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
        for position, record in enumerate(train_records):
            lookup_counts[signature(record, position)][target(record, name)] += 1
        lookup = {
            key: min(counts, key=lambda value: (-counts[value], value))
            for key, counts in lookup_counts.items()
        }
        wanted = [target(record, name) for record in validation_records]
        predicted = [
            lookup.get(signature(record, position), global_majority)
            for position, record in enumerate(validation_records)
        ]
        accuracy = sum(a == b for a, b in zip(predicted, wanted, strict=True)) / len(wanted)
        baseline = global_counts[global_majority] / sum(global_counts.values())
        labels_by_group: dict[str, list[int]] = defaultdict(list)
        for record in validation_records:
            labels_by_group[target(record, name)].append(int(record["label"] == "ALLOW"))
        deviations = [
            abs(sum(labels) / len(labels) - 0.5)
            for labels in labels_by_group.values()
            if len(labels) >= 40
        ]
        output[name] = {
            "prediction_accuracy": accuracy,
            "majority_baseline": baseline,
            "max_label_rate_deviation": max(deviations, default=0.0),
        }
    return output


def branch_inference_balanced_accuracy(
    train_records: list[dict[str, Any]], validation_records: list[dict[str, Any]]
) -> float:
    """Measure label inference through the fixed parent generator branch."""
    label_by_branch: dict[str, Counter[int]] = defaultdict(Counter)
    for record in train_records:
        branch = ":".join(record["generator_branch"].split(":")[:2])
        label_by_branch[branch][int(record["label"] == "ALLOW")] += 1
    predictions = [
        int(
            label_by_branch[":".join(record["generator_branch"].split(":")[:2])][1]
            > label_by_branch[":".join(record["generator_branch"].split(":")[:2])][0]
        )
        for record in validation_records
    ]
    labels = [int(record["label"] == "ALLOW") for record in validation_records]
    return _rates(predictions, labels)["balanced_accuracy"]
