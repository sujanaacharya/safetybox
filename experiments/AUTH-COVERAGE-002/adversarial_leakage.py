#!/usr/bin/env python3
"""Preregistered-feature categorical leakage attack on DEV/VALIDATION only."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _shape(resource: str) -> str:
    basename = resource.rsplit("/", 1)[-1]
    prefix = next(
        (
            value
            for value in ("peer-", "child-", "item-", "worker-", "cwd-")
            if basename.startswith(value)
        ),
        "other",
    )
    suffix = ".bak" if basename.endswith(".bak") else "x" if basename.endswith("x") else "other"
    root = (
        "alternate"
        if "/alternate/" in resource
        else "otherroot"
        if "/other/" in resource
        else "other"
    )
    return f"{prefix}:{suffix}:{root}"


def _features(item: dict[str, Any]) -> dict[str, str]:
    requests = [item["request"], *(part["request"] for part in item["additional_components"])]
    return {
        "tool": item["tool_class"],
        "task_eq": str(all(request["task_id"] == item["contract_task_id"] for request in requests)),
        "actions": "|".join(request["action"] for request in requests),
        "shapes": "|".join(_shape(request["resource"]) for request in requests),
        "depths": "|".join(str(request["resource"].count("/")) for request in requests),
        "capcount": str(len(item["capabilities"])),
        "first_action": item["capabilities"][0]["action"],
    }


def _rates(
    predictions: dict[str, str], labels: dict[str, str], ids: list[str]
) -> dict[str, float | int]:
    correct = sum(predictions[item] == labels[item] for item in ids)
    denied = [item for item in ids if labels[item] == "DENY"]
    allowed = [item for item in ids if labels[item] == "ALLOW"]
    false_allows = sum(predictions[item] == "ALLOW" for item in denied)
    false_denies = sum(predictions[item] == "DENY" for item in allowed)
    return {
        "accuracy": correct / len(ids),
        "correct": correct,
        "false_allows": false_allows,
        "false_allow_rate": false_allows / len(denied),
        "false_denies": false_denies,
        "false_deny_rate": false_denies / len(allowed),
    }


def main() -> None:
    labels_records = _load(ROOT / "corpus/analysis/labels.json")
    labels = {item["scenario_id"]: item["expected_decision"] for item in labels_records}
    runtime: dict[str, dict[str, Any]] = {}
    split_ids: dict[str, list[str]] = {}
    for split in ("DEV", "VALIDATION"):
        records = _load(ROOT / f"corpus/runtime/{split}/scenarios.json")
        split_ids[split] = [item["scenario_id"] for item in records]
        runtime.update({item["scenario_id"]: item for item in records})
    features = {key: _features(value) for key, value in runtime.items()}
    train, validation = split_ids["DEV"], split_ids["VALIDATION"]
    classes = ("ALLOW", "DENY")
    class_counts = Counter(labels[item] for item in train)
    counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    vocab: dict[str, set[str]] = defaultdict(set)
    for item in train:
        for name, value in features[item].items():
            counts[(labels[item], name)][value] += 1
            vocab[name].add(value)
    predictions: dict[str, str] = {}
    for item in validation:
        scores: dict[str, float] = {}
        for decision in classes:
            score = math.log(class_counts[decision] / len(train))
            for name, value in features[item].items():
                score += math.log(
                    (counts[(decision, name)][value] + 1)
                    / (class_counts[decision] + len(vocab[name]) + 1)
                )
            scores[decision] = score
        predictions[item] = max(classes, key=lambda decision: scores[decision])
    ablations: dict[str, dict[str, float | int]] = {}
    for name in features[train[0]]:
        majority: dict[str, str] = {}
        by_value: dict[str, Counter[str]] = defaultdict(Counter)
        for item in train:
            by_value[features[item][name]][labels[item]] += 1
        for value, value_counts in by_value.items():
            majority[value] = max(classes, key=lambda decision: value_counts[decision])
        baseline = max(classes, key=lambda decision: class_counts[decision])
        ablation_predictions = {
            item: majority.get(features[item][name], baseline) for item in validation
        }
        ablations[name] = _rates(ablation_predictions, labels, validation)
    result = {
        "audit_id": "AUTH-COVERAGE-002-CATEGORICAL-LEAKAGE@1",
        "training_split": "DEV",
        "evaluation_split": "VALIDATION",
        "features": list(features[train[0]]),
        "inference_label_or_oracle_access": False,
        "categorical_naive_bayes": _rates(predictions, labels, validation),
        "single_feature_majority_lookup": ablations,
        "task_only_composition_baseline": ablations["task_eq"]["accuracy"],
        "excess_over_task_only": (
            _rates(predictions, labels, validation)["accuracy"] - ablations["task_eq"]["accuracy"]
        ),
        "disposition": (
            "PASS"
            if _rates(predictions, labels, validation)["accuracy"]
            <= ablations["task_eq"]["accuracy"] + 0.03
            else "BLOCKING"
        ),
        "production_calls": 0,
    }
    destination = ROOT / "corpus/analysis/adversarial_leakage.json"
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
