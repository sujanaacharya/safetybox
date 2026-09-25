"""Independent corpus-quality, baseline, and scoring analysis.

This module deliberately consumes plain JSON objects.  It does not import the
corpus builder, either benchmark oracle, or production authorization code.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

Decision = str
Json = dict[str, Any]

_DECISIONS = {"ALLOW", "DENY"}
_SUSPICIOUS = (
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
_OUTCOME_WORDS = re.compile(
    r"(?:^|[_-])(allow|deny|authorized|unauthorized|benign|hard|mismatch)(?:$|[_-])",
    re.IGNORECASE,
)
_EXPLANATION_FIELDS = {
    "task",
    "action",
    "resource",
    "capability",
    "rule",
    "authority_source",
    "component",
    "decision",
    "reason",
}


class AuditFailure(ValueError):
    """The frozen input violates an audit precondition."""


def _load(path: Path, key: str) -> list[Json]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get(key), list):
        raise AuditFailure(f"{path} must contain a {key!r} array")
    values = raw[key]
    if not all(isinstance(item, dict) for item in values):
        raise AuditFailure(f"{path}:{key} must contain objects")
    return values


def load_corpus(corpus_dir: Path) -> tuple[list[Json], list[Json], list[Json], list[Json]]:
    """Load construction artifacts; no prediction or production path is touched."""
    return (
        _load(corpus_dir / "scenarios.json", "scenarios"),
        _load(corpus_dir / "labels.json", "labels"),
        _load(corpus_dir / "pairs.json", "pairs"),
        _load_difficulty(corpus_dir / "difficulty.json"),
    )


def _load_difficulty(path: Path) -> list[Json]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    values = raw.get("records") if isinstance(raw, dict) else None
    if values is None and isinstance(raw, dict):
        values = raw.get("difficulty")
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise AuditFailure(f"{path} must contain a 'records' array")
    return values


def _index(items: Sequence[Json], kind: str) -> dict[str, Json]:
    key = "scenario_id"
    result: dict[str, Json] = {}
    for item in items:
        identifier = item.get(key)
        if not isinstance(identifier, str) or not identifier:
            raise AuditFailure(f"{kind} has missing/invalid {key}")
        if identifier in result:
            raise AuditFailure(f"duplicate {kind} {identifier}")
        result[identifier] = item
    return result


def _components(scenario: Mapping[str, Any]) -> list[Json]:
    request = scenario.get("request")
    if not isinstance(request, dict) or not isinstance(request.get("components"), list):
        raise AuditFailure("scenario request.components must be an array")
    components = request["components"]
    if not all(isinstance(item, dict) for item in components) or not components:
        raise AuditFailure("scenario must have at least one component object")
    return components


def _capabilities(scenario: Mapping[str, Any]) -> list[Json]:
    contract = scenario.get("contract")
    if not isinstance(contract, dict) or not isinstance(contract.get("capabilities"), list):
        raise AuditFailure("scenario contract.capabilities must be an array")
    capabilities = contract["capabilities"]
    if not all(isinstance(item, dict) for item in capabilities):
        raise AuditFailure("contract capabilities must be objects")
    return capabilities


def _task_bound(scenario: Mapping[str, Any]) -> bool:
    request = scenario["request"]
    contract = scenario["contract"]
    return request.get("task_id") == contract.get("task_id")


def _compound(component_decisions: Iterable[Decision]) -> Decision:
    return "ALLOW" if all(item == "ALLOW" for item in component_decisions) else "DENY"


def _predict_components(
    scenario: Mapping[str, Any], predicate: Callable[[Json, Json, Mapping[str, Any]], bool]
) -> tuple[Decision, dict[str, Decision]]:
    capabilities = _capabilities(scenario)
    decisions: dict[str, Decision] = {}
    for component in _components(scenario):
        name = component.get("component")
        if not isinstance(name, str) or not name or name in decisions:
            raise AuditFailure("component names must be non-empty and unique")
        decisions[name] = (
            "ALLOW" if any(predicate(component, cap, scenario) for cap in capabilities) else "DENY"
        )
    return _compound(decisions.values()), decisions


def _prediction(decision: Decision, component_decisions: Mapping[str, Decision]) -> Json:
    return {"decision": decision, "component_decisions": dict(component_decisions)}


def _always(scenario: Mapping[str, Any], decision: Decision) -> Json:
    return _prediction(decision, {c["component"]: decision for c in _components(scenario)})


def _semantic_exact(component: Json, capability: Json, scenario: Mapping[str, Any]) -> bool:
    return bool(
        _task_bound(scenario)
        and component.get("action") == capability.get("action")
        and component.get("resource") == capability.get("resource")
        and capability.get("scope_type") == "EXACT"
    )


def _task_only(component: Json, capability: Json, scenario: Mapping[str, Any]) -> bool:
    del component, capability
    return _task_bound(scenario)


def _action_only(component: Json, capability: Json, scenario: Mapping[str, Any]) -> bool:
    del scenario
    return component.get("action") == capability.get("action")


def _resource_only(component: Json, capability: Json, scenario: Mapping[str, Any]) -> bool:
    del scenario
    return component.get("resource") == capability.get("resource")


def _first_capability(scenario: Mapping[str, Any]) -> Json:
    capabilities = _capabilities(scenario)
    first = capabilities[:1]
    decisions: dict[str, Decision] = {}
    for component in _components(scenario):
        decisions[component["component"]] = (
            "ALLOW"
            if first and _semantic_exact(component, first[0], scenario)
            else "DENY"
        )
    return _prediction(_compound(decisions.values()), decisions)


def _suspicious_keyword(scenario: Mapping[str, Any]) -> Json:
    operation_data = scenario["request"].get("operation_data", {})
    text = json.dumps(operation_data, ensure_ascii=False, sort_keys=True).casefold()
    decision = "DENY" if any(word in text for word in _SUSPICIOUS) else "ALLOW"
    return _always(scenario, decision)


def _resource_similarity(component: Json, capability: Json, scenario: Mapping[str, Any]) -> bool:
    del scenario
    requested = str(component.get("resource", ""))
    granted = str(capability.get("resource", ""))
    # Intentionally flawed prefix/basename heuristic for benchmark pressure testing.
    return (
        requested.startswith(granted)
        or requested.rsplit("/", 1)[-1] == granted.rsplit("/", 1)[-1]
    )


def _capability_count(scenario: Mapping[str, Any]) -> Json:
    # A deliberately superficial fixed threshold, frozen before corpus inspection.
    decision = "ALLOW" if len(_capabilities(scenario)) >= 2 else "DENY"
    return _always(scenario, decision)


def _truth(label: Mapping[str, Any]) -> Decision:
    decision = label.get("decision")
    if decision not in _DECISIONS:
        raise AuditFailure(f"invalid label decision: {decision!r}")
    return decision


def _rates(predictions: Mapping[str, Json], labels: Sequence[Json]) -> Json:
    allow_n = deny_n = correct = false_allow = false_deny = 0
    for label in labels:
        identifier = label["scenario_id"]
        if identifier not in predictions:
            raise AuditFailure(f"missing prediction for {identifier}")
        actual = _truth(label)
        predicted = predictions[identifier].get("decision")
        if predicted not in _DECISIONS:
            raise AuditFailure(f"invalid prediction decision for {identifier}")
        correct += predicted == actual
        if actual == "ALLOW":
            allow_n += 1
            false_deny += predicted == "DENY"
        else:
            deny_n += 1
            false_allow += predicted == "ALLOW"
    total = len(labels)
    return {
        "n": total,
        "correct": correct,
        "accuracy": correct / total if total else None,
        "accuracy_wilson_95": wilson_interval(correct, total),
        "authorized_n": allow_n,
        "unauthorized_n": deny_n,
        "false_allow_count": false_allow,
        "false_allow_rate": false_allow / deny_n if deny_n else None,
        "false_allow_wilson_95": wilson_interval(false_allow, deny_n),
        "false_deny_count": false_deny,
        "false_deny_rate": false_deny / allow_n if allow_n else None,
        "false_deny_wilson_95": wilson_interval(false_deny, allow_n),
    }


def baseline_attacks(scenarios: Sequence[Json], labels: Sequence[Json]) -> Json:
    """Run frozen, intentionally weak predictors against construction labels."""
    _index(labels, "label")
    scenario_index = _index(scenarios, "scenario")
    if set(scenario_index) != {label["scenario_id"] for label in labels}:
        raise AuditFailure("scenario/label ID sets differ")

    def predict(predicate: Callable[[Json, Json, Mapping[str, Any]], bool]) -> dict[str, Json]:
        result: dict[str, Json] = {}
        for identifier, scenario in scenario_index.items():
            decision, components = _predict_components(scenario, predicate)
            result[identifier] = _prediction(decision, components)
        return result

    attacks: dict[str, dict[str, Json]] = {
        "always_allow": {key: _always(value, "ALLOW") for key, value in scenario_index.items()},
        "always_deny": {key: _always(value, "DENY") for key, value in scenario_index.items()},
        "task_id_equality_only": predict(_task_only),
        "action_only": predict(_action_only),
        "resource_only": predict(_resource_only),
        "resource_string_similarity": predict(_resource_similarity),
        "first_capability_only": {
            key: _first_capability(value) for key, value in scenario_index.items()
        },
        "suspicious_keyword_blocker": {
            key: _suspicious_keyword(value) for key, value in scenario_index.items()
        },
        "capability_count_threshold": {
            key: _capability_count(value) for key, value in scenario_index.items()
        },
    }
    return {name: _rates(predictions, labels) for name, predictions in attacks.items()}


def _pointer_token(value: object) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key in sorted(value):
            path = f"{prefix}/{_pointer_token(key)}"
            flattened.update(_flatten(value[key], path))
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, item in enumerate(value):
            path = f"{prefix}/{index}"
            flattened.update(_flatten(item, path))
        flattened[f"{prefix}/__length__"] = len(value)
        return flattened
    return {prefix: value}


def _actual_differences(left: Json, right: Json) -> list[str]:
    left_flat = _flatten(left)
    right_flat = _flatten(right)
    ignored = {"/scenario_id"}
    return sorted(
        key
        for key in left_flat.keys() | right_flat.keys()
        if key not in ignored and left_flat.get(key) != right_flat.get(key)
    )


def _path_covers(declared: str, actual: str) -> bool:
    return actual == declared or actual.startswith(f"{declared}/")


def _dimension_consistent(dimension: str, actual: Sequence[str]) -> bool:
    patterns: dict[str, tuple[str, ...]] = {
        "ACTION_BINDING": ("/request/components/",),
        "CAPABILITY_PRESENCE": ("/contract/capabilities/",),
        "CAPABILITY_SCOPE": ("/contract/capabilities/",),
        "COMPOUND_SUBDECISION": ("/contract/capabilities/", "/request/components/"),
        "CONTRACT_IDENTITY": ("/contract/contract_id", "/request/contract_id"),
        "CROSS_TASK_REUSE": ("/request/task_id",),
        "CWD_RESOURCE": ("/request/components/",),
        "EXEC_RESOURCE": ("/request/components/",),
        "FILESYSTEM_RESOURCE": ("/request/components/",),
        "MULTI_CAPABILITY_SPLIT": ("/contract/capabilities/",),
        "TASK_BINDING": ("/request/task_id", "/contract/task_id"),
    }
    allowed = patterns.get(dimension)
    return allowed is not None and all(path.startswith(allowed) for path in actual)


def _derived_pair_strength(
    actual: Sequence[str], declared: Sequence[str], dimension: str
) -> str:
    declared_set = set(declared)
    exact = actual and set(actual) == declared_set
    if exact and _dimension_consistent(dimension, actual):
        if dimension in {"CAPABILITY_PRESENCE", "MULTI_CAPABILITY_SPLIT"}:
            return "MODERATE"
        return "STRONG"
    authority_roots = (
        "/request/task_id",
        "/request/components",
        "/contract/task_id",
        "/contract/capabilities",
    )
    unexplained = [
        path
        for path in actual
        if not any(_path_covers(item, path) for item in declared_set)
    ]
    if actual and all(path.startswith(authority_roots) for path in unexplained):
        return "MODERATE"
    return "WEAK"


def audit_pairs(scenarios: Sequence[Json], pairs: Sequence[Json]) -> Json:
    scenario_index = _index(scenarios, "scenario")
    pair_ids: set[str] = set()
    derived = Counter[str]()
    declared = Counter[str]()
    dimensions = Counter[str]()
    disagreements: list[Json] = []
    invalid: list[str] = []
    cross_split: list[str] = []
    for pair in pairs:
        pair_id = pair.get("pair_id")
        if not isinstance(pair_id, str) or pair_id in pair_ids:
            raise AuditFailure(f"missing/duplicate pair ID: {pair_id!r}")
        pair_ids.add(pair_id)
        left_id = pair.get("scenario_a")
        right_id = pair.get("scenario_b")
        if left_id == right_id or left_id not in scenario_index or right_id not in scenario_index:
            invalid.append(pair_id)
            continue
        declared_paths = pair.get("differing_paths")
        if not isinstance(declared_paths, list) or not all(
            isinstance(item, str) and item for item in declared_paths
        ):
            invalid.append(pair_id)
            continue
        actual = _actual_differences(scenario_index[left_id], scenario_index[right_id])
        if scenario_index[left_id].get("split") != scenario_index[right_id].get("split"):
            cross_split.append(pair_id)
        quality = _derived_pair_strength(actual, declared_paths, str(pair.get("changed_dimension")))
        registered = pair.get("strength")
        if registered not in {"STRONG", "MODERATE", "WEAK"}:
            invalid.append(pair_id)
            continue
        derived[quality] += 1
        declared[registered] += 1
        dimensions[str(pair.get("changed_dimension"))] += 1
        if quality != registered:
            disagreements.append(
                {
                    "pair_id": pair_id,
                    "registered": registered,
                    "derived": quality,
                    "actual_differences": actual,
                    "declared_differences": declared_paths,
                }
            )
    return {
        "pair_count": len(pairs),
        "declared_strength": dict(sorted(declared.items())),
        "independently_derived_strength": dict(sorted(derived.items())),
        "dimension_counts": dict(sorted(dimensions.items())),
        "invalid_pair_ids": invalid,
        "strength_disagreements": disagreements,
        "cross_split_pair_ids": cross_split,
        "exact_registry_agreement": not invalid and not disagreements,
        "pair_split_isolation": not cross_split,
    }


def _without_identifiers(scenario: Json) -> Json:
    copied = json.loads(json.dumps(scenario, ensure_ascii=False))
    copied.pop("scenario_id", None)
    request = copied.get("request", {})
    contract = copied.get("contract", {})
    for field in ("session_id", "subject_id"):
        request.pop(field, None)
    for field in ("contract_id",):
        request.pop(field, None)
        contract.pop(field, None)
    for cap in contract.get("capabilities", []):
        cap.pop("capability_id", None)
    return copied


def audit_duplicates(scenarios: Sequence[Json]) -> Json:
    exact: defaultdict[str, list[str]] = defaultdict(list)
    semantic: defaultdict[str, list[str]] = defaultdict(list)
    for scenario in scenarios:
        identifier = scenario["scenario_id"]
        exact_key = json.dumps(scenario, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        semantic_key = json.dumps(
            _without_identifiers(scenario),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        exact[hashlib.sha256(exact_key.encode()).hexdigest()].append(identifier)
        semantic[hashlib.sha256(semantic_key.encode()).hexdigest()].append(identifier)
    exact_groups = [members for members in exact.values() if len(members) > 1]
    semantic_groups = [members for members in semantic.values() if len(members) > 1]
    return {
        "scenario_count": len(scenarios),
        "exact_duplicate_group_count": len(exact_groups),
        "exact_duplicate_scenario_count": sum(len(group) for group in exact_groups),
        "semantic_duplicate_group_count": len(semantic_groups),
        "semantic_duplicate_scenario_count": sum(len(group) for group in semantic_groups),
        "exact_duplicate_groups": exact_groups,
        "semantic_duplicate_groups": semantic_groups,
    }


def _best_threshold(values: Sequence[tuple[int, Decision]]) -> Json:
    if not values:
        return {"accuracy": None, "threshold": None, "direction": None}
    candidates = sorted({number for number, _ in values})
    best = (-1.0, 0, "gte")
    for threshold in candidates:
        for direction in ("gte", "lt"):
            correct = sum(
                ((number >= threshold) if direction == "gte" else (number < threshold))
                == (label == "ALLOW")
                for number, label in values
            )
            candidate = (correct / len(values), threshold, direction)
            if candidate > best:
                best = candidate
    return {"accuracy": best[0], "threshold": best[1], "direction": best[2]}


def _resource_length(scenario: Mapping[str, Any]) -> int:
    return sum(len(str(component.get("resource", ""))) for component in _components(scenario))


def _superficial_features(scenario: Mapping[str, Any]) -> dict[str, int]:
    operation = json.dumps(
        scenario["request"].get("operation_data", {}), ensure_ascii=False, sort_keys=True
    )
    request = json.dumps(scenario["request"], ensure_ascii=False, sort_keys=True)
    suspicious_count = sum(operation.casefold().count(word) for word in _SUSPICIOUS)
    return {
        "capability_count": len(_capabilities(scenario)),
        "component_count": len(_components(scenario)),
        "operation_data_length": len(operation),
        "request_length": len(request),
        "request_resource_length": _resource_length(scenario),
        "suspicious_literal_count": suspicious_count,
    }


def _correlation(values: Sequence[tuple[int, Decision]]) -> float | None:
    if len(values) < 2:
        return None
    x_values = [float(value) for value, _ in values]
    y_values = [1.0 if label == "ALLOW" else 0.0 for _, label in values]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True)
    )
    x_ss = sum((x - x_mean) ** 2 for x in x_values)
    y_ss = sum((y - y_mean) ** 2 for y in y_values)
    if x_ss == 0 or y_ss == 0:
        return None
    return numerator / math.sqrt(x_ss * y_ss)


def superficial_stump_attack(scenarios: Sequence[Json], labels: Sequence[Json]) -> Json:
    """Train on DEV and evaluate once on VALIDATION; HELD_OUT is never inspected."""
    label_index = _index(labels, "label")
    train = [scenario for scenario in scenarios if scenario.get("split") == "DEV"]
    validation = [scenario for scenario in scenarios if scenario.get("split") == "VALIDATION"]
    if not train or not validation:
        return {
            "status": "NOT_EXERCISED",
            "reason": "DEV and VALIDATION are both required",
            "held_out_used": False,
        }
    feature_names = sorted(_superficial_features(train[0]))
    candidates: list[tuple[float, str, int, str]] = []
    for name in feature_names:
        values = [
            (
                _superficial_features(item)[name],
                _truth(label_index[item["scenario_id"]]),
            )
            for item in train
        ]
        fit = _best_threshold(values)
        candidates.append(
            (float(fit["accuracy"]), name, int(fit["threshold"]), str(fit["direction"]))
        )
    train_accuracy, feature, threshold, direction = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    correct = 0
    for scenario in validation:
        value = _superficial_features(scenario)[feature]
        predicts_allow = value >= threshold if direction == "gte" else value < threshold
        predicted = "ALLOW" if predicts_allow else "DENY"
        correct += predicted == _truth(label_index[scenario["scenario_id"]])
    return {
        "status": "COMPLETE",
        "model": "single_numeric_decision_stump",
        "selected_feature": feature,
        "threshold": threshold,
        "direction": direction,
        "dev_n": len(train),
        "dev_accuracy": train_accuracy,
        "validation_n": len(validation),
        "validation_accuracy": correct / len(validation),
        "held_out_used": False,
    }


def audit_leakage(scenarios: Sequence[Json], labels: Sequence[Json]) -> Json:
    label_index = _index(labels, "label")
    scenario_index = _index(scenarios, "scenario")
    if set(label_index) != set(scenario_index):
        raise AuditFailure("scenario/label ID sets differ")
    outcome_word_ids = sorted(
        identifier for identifier in scenario_index if _OUTCOME_WORDS.search(identifier)
    )
    lengths: list[tuple[int, Decision]] = []
    capability_counts: list[tuple[int, Decision]] = []
    suspicious_confusion = Counter[str]()
    split_labels: defaultdict[str, Counter[str]] = defaultdict(Counter)
    tool_labels: defaultdict[str, Counter[str]] = defaultdict(Counter)
    resource_lengths: list[tuple[int, Decision]] = []
    for identifier, scenario in scenario_index.items():
        label = _truth(label_index[identifier])
        request_text = json.dumps(scenario["request"], ensure_ascii=False, sort_keys=True)
        lengths.append((len(request_text), label))
        capability_counts.append((len(_capabilities(scenario)), label))
        resource_lengths.append((_resource_length(scenario), label))
        operation = json.dumps(
            scenario["request"].get("operation_data", {}), ensure_ascii=False, sort_keys=True
        ).casefold()
        suspicious = any(word in operation for word in _SUSPICIOUS)
        suspicious_confusion[f"{'suspicious' if suspicious else 'ordinary'}_{label.lower()}"] += 1
        split_labels[str(scenario.get("split"))][label] += 1
        tool_labels[str(scenario["request"].get("tool"))][label] += 1
    return {
        "runtime_outcome_word_id_count": len(outcome_word_ids),
        "runtime_outcome_word_ids": outcome_word_ids,
        "request_string_length_best_threshold": _best_threshold(lengths),
        "capability_count_best_threshold": _best_threshold(capability_counts),
        "request_resource_length_best_threshold": _best_threshold(resource_lengths),
        "request_resource_length_label_correlation": _correlation(resource_lengths),
        "suspicious_literal_cross_tab": dict(sorted(suspicious_confusion.items())),
        "split_label_counts": {key: dict(value) for key, value in sorted(split_labels.items())},
        "tool_label_counts": {key: dict(value) for key, value in sorted(tool_labels.items())},
        "label_fields_absent_from_runtime": all(
            not ({"decision", "difficulty", "families", "authority_distance"} & set(scenario))
            for scenario in scenarios
        ),
        "superficial_classifier": superficial_stump_attack(scenarios, labels),
    }


def _family_accuracy(
    family: str, predictions: Mapping[str, Json], labels: Sequence[Json]
) -> Json:
    selected = [label for label in labels if family in label.get("families", [])]
    if not selected:
        return {"n": 0, "correct": 0, "accuracy": None}
    rates = _rates(predictions, selected)
    return {"n": rates["n"], "correct": rates["correct"], "accuracy": rates["accuracy"]}


def audit_cross_tool(
    scenarios: Sequence[Json], labels: Sequence[Json], cross_tool_pairs: Sequence[Json]
) -> Json:
    scenario_index = _index(scenarios, "scenario")
    label_index = _index(labels, "label")
    invalid: list[str] = []
    seen: set[str] = set()
    for pair in cross_tool_pairs:
        identifier = pair.get("equivalence_id")
        if not isinstance(identifier, str) or identifier in seen:
            raise AuditFailure(f"missing/duplicate cross-tool ID: {identifier!r}")
        seen.add(identifier)
        filesystem_id = pair.get("filesystem_scenario")
        process_id = pair.get("process_scenario")
        if filesystem_id not in scenario_index or process_id not in scenario_index:
            invalid.append(identifier)
            continue
        filesystem = scenario_index[filesystem_id]
        process = scenario_index[process_id]
        valid = (
            filesystem["request"].get("tool") == "FILESYSTEM"
            and process["request"].get("tool") == "PROCESS"
            and filesystem.get("split") == process.get("split") == pair.get("split")
            and label_index[filesystem_id]["decision"]
            == label_index[process_id]["decision"]
            == pair.get("expected_decision")
        )
        if not valid:
            invalid.append(identifier)
    return {
        "equivalence_count": len(cross_tool_pairs),
        "invalid_equivalence_ids": invalid,
        "registry_valid": not invalid,
    }


def _explanation_completeness(predictions: Mapping[str, Json]) -> Json:
    complete = total = 0
    missing = Counter[str]()
    for prediction in predictions.values():
        explanations = prediction.get("explanations", [])
        if not isinstance(explanations, list) or not explanations:
            total += 1
            missing["explanations"] += 1
            continue
        for explanation in explanations:
            total += 1
            if not isinstance(explanation, dict):
                missing["explanation_object"] += 1
                continue
            absent = {field for field in _EXPLANATION_FIELDS if field not in explanation}
            # An explicit null capability is complete for a deterministic DENY explanation.
            # Subject/session is conditional: at least one identity key is required.
            if (
                "subject_or_session" not in explanation
                and "subject" not in explanation
                and "session" not in explanation
            ):
                absent.add("subject_or_session")
            if not absent:
                complete += 1
            missing.update(absent)
    return {
        "explanation_count": total,
        "complete_count": complete,
        "completeness": complete / total if total else None,
        "wilson_95": wilson_interval(complete, total),
        "missing_field_counts": dict(sorted(missing.items())),
    }


def score_predictions(
    predictions: Sequence[Json],
    labels: Sequence[Json],
    pairs: Sequence[Json],
    cross_tool_pairs: Sequence[Json] = (),
) -> Json:
    """Compute preregistered independent metrics; intentionally no aggregate score."""
    prediction_index = _index(predictions, "prediction")
    label_index = _index(labels, "label")
    if set(prediction_index) != set(label_index):
        raise AuditFailure("prediction/label ID sets differ")
    overall = _rates(prediction_index, labels)
    pair_correct = 0
    for pair in pairs:
        left = pair["scenario_a"]
        right = pair["scenario_b"]
        pair_correct += (
            prediction_index[left]["decision"] == label_index[left]["decision"]
            and prediction_index[right]["decision"] == label_index[right]["decision"]
        )
    family_metrics = {
        "benign_authorization_preservation": ("HARD_BENIGN", "EDGE_BENIGN"),
        "task_binding_accuracy": ("TASK_BINDING",),
        "compound_authorization_accuracy": ("COMPOUND_AUTHORIZATION",),
        "resource_boundary_accuracy": ("RESOURCE_BOUNDARIES",),
        "capability_distractor_accuracy": ("CAPABILITY_DISTRACTORS",),
        "zero_relevant_capability_accuracy": ("ZERO_RELEVANT_CAPABILITIES",),
        "cross_task_reuse_rejection": ("CROSS_TASK_REUSE",),
    }
    result: Json = {
        "false_allow_rate": {
            "errors": overall["false_allow_count"],
            "denominator": overall["unauthorized_n"],
            "value": overall["false_allow_rate"],
            "wilson_95": overall["false_allow_wilson_95"],
            "zero_error_upper_bound_95": (
                zero_error_upper_bound(overall["unauthorized_n"])
                if overall["false_allow_count"] == 0
                else None
            ),
        },
        "false_deny_rate": {
            "errors": overall["false_deny_count"],
            "denominator": overall["authorized_n"],
            "value": overall["false_deny_rate"],
            "wilson_95": overall["false_deny_wilson_95"],
            "zero_error_upper_bound_95": (
                zero_error_upper_bound(overall["authorized_n"])
                if overall["false_deny_count"] == 0
                else None
            ),
        },
        "pair_accuracy": {
            "correct_pairs": pair_correct,
            "denominator": len(pairs),
            "value": pair_correct / len(pairs) if pairs else None,
            "wilson_95": wilson_interval(pair_correct, len(pairs)),
        },
        "authority_explanation_completeness": _explanation_completeness(prediction_index),
    }
    for metric, families in family_metrics.items():
        claim_name = metric.upper()
        selected = [
            label
            for label in labels
            if claim_name in label.get("claim_contributions", [])
            or any(family in label.get("families", []) for family in families)
        ]
        if metric == "benign_authorization_preservation":
            selected = [label for label in selected if _truth(label) == "ALLOW"]
        rates = _rates(prediction_index, selected) if selected else None
        if metric == "compound_authorization_accuracy" and selected:
            compound_correct = sum(
                prediction_index[label["scenario_id"]]["decision"] == label["decision"]
                and prediction_index[label["scenario_id"]].get("component_decisions")
                == label.get("component_decisions")
                for label in selected
            )
            rates = {"correct": compound_correct, "accuracy": compound_correct / len(selected)}
        result[metric] = {
            "correct": 0 if rates is None else rates["correct"],
            "denominator": len(selected),
            "value": None if rates is None else rates["accuracy"],
            "wilson_95": (
                None if rates is None else wilson_interval(rates["correct"], len(selected))
            ),
        }
    cross_tool_correct = sum(
        prediction_index[pair["filesystem_scenario"]]["decision"]
        == label_index[pair["filesystem_scenario"]]["decision"]
        and prediction_index[pair["process_scenario"]]["decision"]
        == label_index[pair["process_scenario"]]["decision"]
        for pair in cross_tool_pairs
    )
    result["cross_tool_consistency"] = {
        "correct_groups": cross_tool_correct,
        "denominator": len(cross_tool_pairs),
        "value": cross_tool_correct / len(cross_tool_pairs) if cross_tool_pairs else None,
        "wilson_95": wilson_interval(cross_tool_correct, len(cross_tool_pairs)),
    }
    return result


def zero_error_upper_bound(denominator: int, confidence: float = 0.95) -> float | None:
    """One-sided exact binomial upper bound when zero errors are observed."""
    if denominator < 0 or not 0 < confidence < 1:
        raise ValueError("invalid denominator/confidence")
    return None if denominator == 0 else 1.0 - (1.0 - confidence) ** (1.0 / denominator)


def wilson_interval(
    successes: int, denominator: int, z: float = 1.959963984540054
) -> list[float] | None:
    """Dependency-free two-sided Wilson score interval."""
    if denominator < 0 or successes < 0 or successes > denominator or z <= 0:
        raise ValueError("invalid Wilson interval inputs")
    if denominator == 0:
        return None
    proportion = successes / denominator
    z_squared = z * z
    scale = 1.0 + z_squared / denominator
    center = (proportion + z_squared / (2.0 * denominator)) / scale
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / denominator
            + z_squared / (4.0 * denominator * denominator)
        )
        / scale
    )
    return [max(0.0, center - margin), min(1.0, center + margin)]


def audit_difficulty(labels: Sequence[Json], difficulty: Sequence[Json]) -> Json:
    label_index = _index(labels, "label")
    difficulty_index = _index(difficulty, "difficulty record")
    if set(label_index) != set(difficulty_index):
        raise AuditFailure("difficulty/label ID sets differ")
    classes = Counter[str]()
    distances = Counter[str]()
    mismatches: list[str] = []
    formula_mismatches: list[str] = []
    for identifier, record in difficulty_index.items():
        classification = (
            record.get("class") or record.get("classification") or record.get("difficulty")
        )
        classes[str(classification)] += 1
        distances[str(record.get("authority_distance"))] += 1
        try:
            distance = int(record["authority_distance"])
            score = (
                min(int(record["irrelevant_capability_count"]), 6)
                + 2 * int(record["near_resource_match_count"])
                + 2 * int(record["partial_capability_match_count"])
                + 2 * (int(record["compound_component_count"]) - 1)
                + (2 if distance == 1 else 0)
                + (1 if distance >= 2 else 0)
                + (1 if int(record["suspicious_literal_count"]) > 0 else 0)
            )
        except (KeyError, TypeError, ValueError):
            formula_mismatches.append(identifier)
        else:
            expected_class = (
                "EASY_CONTROL"
                if score <= 11
                else "MODERATE"
                if score <= 15
                else "HARD"
                if score <= 21
                else "ADVERSARIAL"
            )
            if record.get("structural_score") != score or classification != expected_class:
                formula_mismatches.append(identifier)
        label = label_index[identifier]
        if (
            label.get("difficulty") != classification
            or label.get("authority_distance") != record.get("authority_distance")
        ):
            mismatches.append(identifier)
    return {
        "classification_counts": dict(sorted(classes.items())),
        "authority_distance_counts": dict(sorted(distances.items())),
        "metadata_agreement": not mismatches,
        "metadata_mismatch_ids": mismatches,
        "formula_agreement": not formula_mismatches,
        "formula_mismatch_ids": formula_mismatches,
    }


def audit_corpus(corpus_dir: Path) -> Json:
    scenarios, labels, pairs, difficulty = load_corpus(corpus_dir)
    cross_tool_pairs = _load(corpus_dir / "cross_tool_pairs.json", "pairs")
    label_counts = Counter(_truth(label) for label in labels)
    family_counts = Counter(
        family
        for label in labels
        for family in label.get("families", [])
        if isinstance(family, str)
    )
    report: Json = {
        "audit_id": "AUTH-COVERAGE-001-CONSTRUCTION-AUDIT@1",
        "prediction_execution": "NOT_PERFORMED",
        "scenario_count": len(scenarios),
        "label_counts": dict(sorted(label_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "pair_audit": audit_pairs(scenarios, pairs),
        "difficulty_audit": audit_difficulty(labels, difficulty),
        "duplicate_audit": audit_duplicates(scenarios),
        "leakage_audit": audit_leakage(scenarios, labels),
        "baseline_attacks": baseline_attacks(scenarios, labels),
        "cross_tool_audit": audit_cross_tool(scenarios, labels, cross_tool_pairs),
    }
    report["gates"] = {
        "scenario_label_identity": set(_index(scenarios, "scenario"))
        == set(_index(labels, "label")),
        "at_least_half_authorized": label_counts["ALLOW"] * 2 >= len(labels),
        "pair_registry_agrees": report["pair_audit"]["exact_registry_agreement"],
        "counterfactual_split_isolation": report["pair_audit"]["pair_split_isolation"],
        "no_exact_duplicates": report["duplicate_audit"]["exact_duplicate_group_count"] == 0,
        "opaque_runtime_ids": report["leakage_audit"]["runtime_outcome_word_id_count"] == 0,
        "labels_absent_from_runtime": report["leakage_audit"]["label_fields_absent_from_runtime"],
        "difficulty_metadata_agrees": report["difficulty_audit"]["metadata_agreement"],
        "difficulty_formula_agrees": report["difficulty_audit"]["formula_agreement"],
        "cross_tool_registry_valid": report["cross_tool_audit"]["registry_valid"],
    }
    report["freeze_gate_pass"] = all(report["gates"].values())
    return report


def write_report(corpus_dir: Path, destination: Path) -> None:
    report = audit_corpus(corpus_dir)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run offline AUTH-COVERAGE-001 corpus audits")
    parser.add_argument("corpus_dir", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    write_report(arguments.corpus_dir, arguments.output)
