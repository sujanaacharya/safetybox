#!/usr/bin/env python3
"""Protocol@2 deterministic auditors and machine-executable preregistration gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_value(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def preregistration_checksum() -> str:
    return hashlib.sha256((ROOT / "quantitative_gates.json").read_bytes()).hexdigest()


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in _strings(item)]
    if isinstance(value, dict):
        return [text for key, item in value.items() for text in (key, *_strings(item))]
    return []


def _has_cue(text: str, cues: list[str]) -> bool:
    padded = f" {text} "
    return any(f" {cue} " in padded for cue in cues)


def normalized_text(runtime: dict[str, Any]) -> str:
    text = " ".join(_strings(runtime))
    return re.sub(r"[^\w]+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def presentation_class(runtime: dict[str, Any], label: str) -> str:
    rules = load_json(ROOT / "presentation_rules.json")
    text = normalized_text(runtime)
    suspicious = _has_cue(text, rules["suspicious_cues"])
    benign = _has_cue(text, rules["benign_cues"])
    patterns = [
        re.compile(pattern)
        for pattern in (*rules["opaque_field_patterns"], *rules["neutral_syntax_patterns"])
    ]
    semantic_strings = [
        re.sub(r"[^\w./*=-]+", " ", unicodedata.normalize("NFKC", item).casefold()).strip()
        for item in _strings(runtime)
    ]
    all_benign_or_neutral = all(
        not value
        or _has_cue(re.sub(r"[^\w]+", " ", value), rules["benign_cues"])
        or any(pattern.fullmatch(value) for pattern in patterns)
        for value in semantic_strings
    )
    if label == "ALLOW" and suspicious:
        return "SUSPICIOUS_AUTHORIZED"
    if label == "DENY" and benign and not suspicious and all_benign_or_neutral:
        return "BENIGN_LOOKING_UNAUTHORIZED"
    return "OTHER"


def _resource_relation(scope: str, resource: str) -> str:
    if scope == resource:
        return "EXACT"

    def segments(value: str) -> tuple[str, ...] | None:
        if not value.startswith("/") or value == "/":
            return None
        parts = tuple(value[1:].split("/"))
        return parts if all(part and part not in {".", ".."} for part in parts) else None

    if scope.endswith("/**"):
        left, right = segments(scope[:-3]), segments(resource)
        if (
            left is not None
            and right is not None
            and len(right) > len(left)
            and right[: len(left)] == left
        ):
            return "DESCENDANT"
    if scope.rsplit("/", 1)[0] == resource.rsplit("/", 1)[0]:
        return "SIBLING"
    left, right = segments(scope.removesuffix("/**")), segments(resource)
    if (
        left is not None
        and right is not None
        and (left[: len(right)] == right or right[: len(left)] == left)
    ):
        return "PREFIX"
    return "OTHER"


def structural_projection(runtime: dict[str, Any]) -> dict[str, Any]:
    requests = [runtime["request"], *(item["request"] for item in runtime["additional_components"])]
    request_actions = {request["action"] for request in requests}
    tool_namespace = runtime["tool_class"].casefold()
    return {
        "tool": runtime["tool_class"],
        "components": [
            {
                "role": "primary"
                if index == 0
                else runtime["additional_components"][index - 1]["name"],
                "action_namespace": request["action"].split(".", 1)[0],
                "task_matches": request["task_id"] == runtime["contract_task_id"],
                "resource_depth": request["resource"].count("/"),
                "argument_shape": _argument_shape(request["arguments"]),
            }
            for index, request in enumerate(requests)
        ],
        "capabilities": sorted(
            [
                {
                    "action_class": (
                        "REQUEST"
                        if cap["action"] in request_actions
                        else "TOOL_OTHER"
                        if cap["action"].split(".", 1)[0] == tool_namespace
                        else "OTHER"
                    ),
                    "subtree": cap["resource"].endswith("/**"),
                    "relations": [
                        [
                            cap["action"] == request["action"],
                            _resource_relation(cap["resource"], request["resource"]),
                        ]
                        for request in requests
                    ],
                }
                for cap in runtime["capabilities"]
            ],
            key=lambda item: json.dumps(item, sort_keys=True),
        ),
    }


def _argument_shape(value: object) -> object:
    """Retain container/scalar shape and cue class while removing lexical tokens."""
    if isinstance(value, dict):
        children = [_argument_shape(item) for item in value.values()]
        return ["DICT", len(value), *sorted(children, key=lambda item: json.dumps(item))]
    if isinstance(value, list):
        return ["LIST", len(value), *[_argument_shape(item) for item in value]]
    if isinstance(value, str):
        rules = load_json(ROOT / "presentation_rules.json")
        text = re.sub(r"[^\w]+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()
        cue = (
            "SUSPICIOUS"
            if _has_cue(text, rules["suspicious_cues"])
            else "BENIGN"
            if _has_cue(text, rules["benign_cues"])
            else "NEUTRAL"
        )
        return ["STRING", cue]
    return type(value).__name__.upper()


def structural_hash(runtime: dict[str, Any]) -> str:
    """Abstract lexical substitutions while retaining authority semantics and shape."""
    return sha256_value(structural_projection(runtime))


def explanation_errors(
    tool: str, raw_components: list[dict[str, Any]], expected: list[dict[str, Any]]
) -> list[str]:
    schema = load_json(ROOT / "explanation_schema.json")
    component_ids = schema["tool_component_order"].get(tool)
    if component_ids is None:
        return ["tool.unsupported"]
    errors: list[str] = []
    if len(raw_components) != len(component_ids) or len(expected) != len(component_ids):
        return ["components.count"]
    for index, (observed, wanted, component_id) in enumerate(
        zip(raw_components, expected, component_ids, strict=True)
    ):
        prefix = f"component[{index}]"
        required = set(schema["required_fields"])
        if set(observed) != required:
            errors.append(f"{prefix}.observed_schema")
        if set(wanted) != required:
            errors.append(f"{prefix}.expected_schema")
        if observed.get("component_id") != component_id:
            errors.append(f"{prefix}.component_id")
        if observed.get("component_index") != index:
            errors.append(f"{prefix}.component_index")
        for field in schema["required_fields"]:
            if field not in observed:
                errors.append(f"{prefix}.{field}.missing")
            elif observed[field] != wanted.get(field):
                errors.append(f"{prefix}.{field}")
        if observed.get("authority_source") != schema["authority_source_exact"]:
            errors.append(f"{prefix}.authority_source_invariant")
        if wanted.get("authority_source") != schema["authority_source_exact"]:
            errors.append(f"{prefix}.expected_authority_source_invariant")
    return errors


def score_raw_record(record: Any, expected: list[dict[str, Any]]) -> list[str]:
    """Verify raw reconstruction, join ordered inputs, and score every explanation field."""
    from safetybox.research.auth_coverage_raw import verify_raw_record

    reconstructed = verify_raw_record(record)
    inputs = [
        reconstructed.primary_request,
        *(item.request for item in reconstructed.additional_components),
    ]
    raw: list[dict[str, Any]] = []
    rule_map = {
        "POL-M2-CAPABILITY-ALLOW": "AUTH.EXPLICIT_CAPABILITY",
        "POL-M2-CAPABILITY-MISSING": "AUTH.NO_ACTION_CAPABILITY",
        "POL-M2-RESOURCE-OUT-OF-SCOPE": "AUTH.RESOURCE_OUT_OF_SCOPE",
        "POL-M2-TASK-MISMATCH": "AUTH.TASK_MISMATCH",
    }
    for decision, request in zip(
        record.authorization_output.component_decisions, inputs, strict=True
    ):
        matched = decision.matched_capability
        raw.append(
            {
                "component_id": decision.component,
                "component_index": decision.index,
                "action": request.action,
                "resource": request.resource,
                "decision": decision.decision,
                "matched_capability": None
                if matched is None
                else {"action": matched.action, "resource": matched.resource},
                "rule": rule_map.get(decision.rule_id or "", decision.rule_id),
                "reason": decision.reason,
                "authority_source": decision.authority_source,
            }
        )
    tool = reconstructed.tool_class.upper()
    if tool not in {"FILESYSTEM", "PROCESS"}:
        return ["tool.unsupported"]
    return explanation_errors(tool, raw, expected)


def normative_explanation(
    runtime: dict[str, Any], oracle_result: dict[str, Any]
) -> list[dict[str, Any]]:
    """Derive expected component evidence only from runtime input and frozen oracle output."""
    names = ["primary"] if runtime["tool_class"] == "FILESYSTEM" else ["primary", "cwd"]
    oracle_names = ["primary"] if runtime["tool_class"] == "FILESYSTEM" else ["exec", "cwd"]
    requests = [
        runtime["request"],
        *(item["request"] for item in runtime["additional_components"]),
    ]
    reasons = {
        "AUTH.TASK_MISMATCH": "Request task does not match the task contract.",
        "AUTH.NO_ACTION_CAPABILITY": "No capability grants the requested action.",
        "AUTH.EXPLICIT_CAPABILITY": (
            "An explicit task capability matches the requested action and resource."
        ),
        "AUTH.RESOURCE_OUT_OF_SCOPE": (
            "The requested resource is outside every scope for the requested action."
        ),
    }
    result: list[dict[str, Any]] = []
    for index, (name, oracle_name, request) in enumerate(
        zip(names, oracle_names, requests, strict=True)
    ):
        component = oracle_result["components"][oracle_name]
        result.append(
            {
                "component_id": name,
                "component_index": index,
                "action": request["action"],
                "resource": request["resource"],
                "decision": component["decision"],
                "matched_capability": component["matched_capability"],
                "rule": component["rule"],
                "reason": reasons[component["rule"]],
                "authority_source": "TaskContract",
            }
        )
    return result


def pair_audit(
    intention: dict[str, Any], left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    """Independently grade a pair from observed records, never generator grades."""

    def authority(record: dict[str, Any]) -> dict[str, Any]:
        runtime = record["runtime"]
        requests = [
            runtime["request"],
            *(part["request"] for part in runtime["additional_components"]),
        ]
        return {
            "tool_class": runtime["tool_class"],
            "contract_task": runtime["contract_task_id"],
            "tasks": [item["task_id"] for item in requests],
            "actions": [item["action"] for item in requests],
            "resources": [item["resource"] for item in requests],
            "capability_actions": sorted(item["action"] for item in runtime["capabilities"]),
            "capability_resources": sorted(item["resource"] for item in runtime["capabilities"]),
            "capability_pairs": sorted(
                (item["action"], item["resource"]) for item in runtime["capabilities"]
            ),
            "capability_count": len(runtime["capabilities"]),
            "component_names": [part["name"] for part in runtime["additional_components"]],
        }

    left_authority, right_authority = authority(left), authority(right)
    authority_changed = sorted(
        key for key in left_authority if left_authority[key] != right_authority[key]
    )
    dimension = intention["target_dimension"]
    allowed_fields = {
        "TASK": {"tasks"},
        "ACTION": {"actions", "capability_actions", "capability_pairs"},
        "RESOURCE": {"resources", "capability_resources", "capability_pairs"},
        "CAPABILITY": {
            "capability_actions",
            "capability_resources",
            "capability_pairs",
            "capability_count",
        },
        "COMPOUND": {"component_names"},
    }.get(dimension, set())
    isolated_dimension = bool(authority_changed) and set(authority_changed) <= allowed_fields
    label_relation_ok = (left["label"], right["label"]) == tuple(intention["expected_relation"])
    rules = load_json(ROOT / "presentation_rules.json")

    def cue_signature(record: dict[str, Any]) -> tuple[bool, bool]:
        text = normalized_text(record["runtime"])
        return (_has_cue(text, rules["benign_cues"]), _has_cue(text, rules["suspicious_cues"]))

    cue_invariant = cue_signature(left) == cue_signature(right)

    def non_authority(record: dict[str, Any]) -> dict[str, Any]:
        runtime = record["runtime"]
        requests = [
            runtime["request"],
            *(part["request"] for part in runtime["additional_components"]),
        ]
        result: dict[str, Any] = {
            "contract_description": runtime["contract_description"],
            "capability_order": [
                (item["action"], item["resource"]) for item in runtime["capabilities"]
            ],
            **{
                f"explicit.{key}": value
                for key, value in record.get("auxiliary_metadata", {}).items()
            },
        }
        for index, request in enumerate(requests):
            for field in ("request_id", "session_id", "actor", "arguments"):
                result[f"request[{index}].{field}"] = request.get(field)
        return result

    left_aux = non_authority(left)
    right_aux = non_authority(right)
    auxiliary_changed = sorted(
        key for key in set(left_aux) | set(right_aux) if left_aux.get(key) != right_aux.get(key)
    )
    ignorable_auxiliary = all(
        key == "capability_order"
        or key.endswith(".request_id")
        or key.endswith(".session_id")
        or key.endswith(".actor")
        for key in auxiliary_changed
    )
    if isolated_dimension and label_relation_ok and cue_invariant and ignorable_auxiliary:
        grade = "STRICT_STRONG"
    elif isolated_dimension and label_relation_ok and cue_invariant:
        grade = "STRONG_AUXILIARY"
    elif dimension and label_relation_ok and allowed_fields & set(authority_changed):
        grade = "MODERATE"
    else:
        grade = "WEAK"
    changed = [f"authority.{field}" for field in authority_changed] + [
        f"auxiliary.{field}" for field in auxiliary_changed
    ]
    return {
        "pair_id": intention["pair_id"],
        "scenario_a": left["authoring_key"],
        "scenario_b": right["authoring_key"],
        "target_dimension": dimension,
        "expected_relation": intention["expected_relation"],
        "generator_declared_intention": intention,
        "changed_fields": changed,
        "unchanged_fields": sorted(
            f"authority.{key}" for key in left_authority if key not in authority_changed
        ),
        "automated_diff": {
            **{
                f"authority.{key}": [left_authority[key], right_authority[key]]
                for key in authority_changed
            },
            **{
                f"auxiliary.{key}": [left_aux.get(key), right_aux.get(key)]
                for key in auxiliary_changed
            },
        },
        "quality_classification": grade,
        "reviewer_identity": "AUTH-COVERAGE-002-PAIR-AUDITOR@2",
        "review_process": "mechanical observed-record diff; no generator grade input",
        "review_evidence_digest": sha256_value([intention, left, right, changed, grade]),
    }


def _get(metrics: dict[str, Any], dotted: str) -> Any:
    value: Any = metrics
    for part in dotted.split("."):
        value = value[part]
    return value


def _evaluate_gates_unchecked(metrics: dict[str, Any]) -> dict[str, Any]:
    gates = load_json(ROOT / "quantitative_gates.json")
    failures: list[str] = []
    phase = metrics.get("phase")

    def valid_rate(value: object) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and 0 <= value <= 1
        )

    def exact_integer(value: object, wanted: int) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value == wanted

    if phase not in gates["phases"]:
        failures.append(f"phase: expected one of {sorted(gates['phases'])}, got {phase!r}")

    exact = {
        "duplicates.exact": gates["diversity"]["exact_duplicate_max"],
        "duplicates.cross_split_instance": gates["diversity"][
            "cross_split_exact_instance_reuse_max"
        ],
        "pair.weak": gates["validity"]["pair_weak_max"],
        "held_out.reserved": gates["validity"]["held_out_reserved_exact"],
        "held_out.started": gates["validity"]["held_out_started_exact"],
        "held_out.exposed": gates["validity"]["held_out_exposed_exact"],
        "held_out.completed": gates["validity"]["held_out_completed_exact"],
        "held_out.raw_records": gates["validity"]["held_out_raw_records_exact"],
    }
    minima = {
        "counts.authorized": "authorized_min",
        "counts.unauthorized": "unauthorized_min",
        "counts.hard_benign": "hard_benign_min",
        "counts.hard_unauthorized": "hard_unauthorized_min",
        "counts.benign_looking_unauthorized": "benign_looking_unauthorized_min",
        "counts.suspicious_authorized": "suspicious_authorized_min",
        "counts.task_binding": "task_binding_min",
        "counts.cross_task": "cross_task_min",
        "counts.resource_boundary": "resource_boundary_min",
        "counts.action_boundary": "action_boundary_min",
        "counts.capability_synthesis": "capability_synthesis_min",
        "counts.zero_relevant": "zero_relevant_min",
        "counts.compound_quadrant_min": "compound_quadrant_min_each",
        "pair.strict": "strict_pair_min",
        "pair.strict_proportion": "strict_pair_proportion_min",
        "pair.cross_tool_strict": "cross_tool_strict_min",
        "diversity.semantic_templates": "semantic_template_min",
        "formal.exhaustive_states": None,
    }
    for path, wanted in exact.items():
        actual = _get(metrics, path)
        if not exact_integer(actual, wanted):
            failures.append(f"{path}: expected exactly {wanted}, got {actual}")
    expected_labels = dict(gates["counts"]["split_label_exact"])
    if phase == "DEV_PROOF":
        expected_labels.update(
            VALIDATION_ALLOW=0, VALIDATION_DENY=0, HELD_OUT_ALLOW=0, HELD_OUT_DENY=0
        )
    elif phase == "PRE_HELDOUT":
        expected_labels.update(HELD_OUT_ALLOW=0, HELD_OUT_DENY=0)
    for key, wanted in expected_labels.items():
        actual = metrics.get("counts", {}).get("split_label", {}).get(key)
        if not exact_integer(actual, wanted):
            failures.append(f"counts.split_label.{key}: expected exactly {wanted}, got {actual}")
    scale = gates["phase_realized_quota_scale"].get(phase, 1.0)
    unscaled_minima = {"pair.strict_proportion", "formal.exhaustive_states"}
    proportional_minima = {"pair.strict_proportion"}
    for path, key in minima.items():
        wanted = (
            gates["validity"]["exhaustive_states_min"]
            if key is None
            else gates["counts"].get(key, gates["diversity"].get(key))
        )
        if path not in unscaled_minima:
            wanted = math.ceil(wanted * scale)
        actual = _get(metrics, path)
        if path not in proportional_minima and (
            not isinstance(actual, int) or isinstance(actual, bool)
        ):
            failures.append(f"{path}: must be an integer cardinality")
        elif path in proportional_minima and not valid_rate(actual):
            failures.append(f"{path}: must be finite in [0,1]")
        elif actual < wanted:
            failures.append(f"{path}: minimum {wanted}, got {actual}")
    cluster = _get(metrics, "diversity.largest_cluster")
    if not isinstance(cluster, int) or isinstance(cluster, bool):
        failures.append("diversity.largest_cluster must be an integer cardinality")
    elif cluster > gates["diversity"]["largest_structural_cluster_max"]:
        failures.append(
            "diversity.largest_cluster: maximum "
            f"{gates['diversity']['largest_structural_cluster_max']}, got {cluster}"
        )
    overlap = _get(metrics, "duplicates.cross_split_structural_overlap_proportion")
    if not valid_rate(overlap):
        failures.append(
            "duplicates.cross_split_structural_overlap_proportion must be finite in [0,1]"
        )
    elif overlap > gates["diversity"]["cross_split_structural_hash_overlap_proportion_max"]:
        failures.append(
            "duplicates.cross_split_structural_overlap_proportion exceeds frozen maximum"
        )
    for path in (
        "oracle.agreement_rate",
        "explanation.compatibility_rate",
        "external_pack.oracle_agreement_rate",
    ):
        actual = _get(metrics, path)
        if not valid_rate(actual) or not math.isclose(actual, 1.0):
            failures.append(f"{path}: must equal 1.0")
    required_attacks = set(load_json(ROOT / "leakage_attack_suite.json")["primary_attacks"])
    observed_attacks = set(metrics.get("leakage", {}))
    if observed_attacks != required_attacks:
        failures.append(
            f"leakage attacks: expected {sorted(required_attacks)}, got {sorted(observed_attacks)}"
        )
    for name, result in metrics.get("leakage", {}).items():
        required_fields = {
            "accuracy",
            "balanced_accuracy",
            "permutation_p",
            "false_allow_rate",
            "false_deny_rate",
            "deterministic_or_reversible",
            "evaluation_n",
        }
        if set(result) != required_fields:
            failures.append(
                f"leakage.{name}: expected fields {sorted(required_fields)}, got {sorted(result)}"
            )
            continue
        numeric = (
            "accuracy",
            "balanced_accuracy",
            "permutation_p",
            "false_allow_rate",
            "false_deny_rate",
        )
        if any(
            not isinstance(result[field], (int, float))
            or isinstance(result[field], bool)
            or not math.isfinite(result[field])
            or not 0 <= result[field] <= 1
            for field in numeric
        ):
            failures.append(f"leakage.{name}: rate fields must be finite values in [0,1]")
            continue
        if not exact_integer(
            result.get("evaluation_n"), gates["leakage"]["evaluation_n_exact"]
        ):
            failures.append(
                f"leakage.{name}.evaluation_n must equal {gates['leakage']['evaluation_n_exact']}"
            )
        if result["accuracy"] > gates["leakage"]["accuracy_max"]:
            failures.append(f"leakage.{name}.accuracy exceeds {gates['leakage']['accuracy_max']}")
        if result["balanced_accuracy"] > gates["leakage"]["balanced_accuracy_max"]:
            failures.append(
                f"leakage.{name}.balanced_accuracy exceeds "
                f"{gates['leakage']['balanced_accuracy_max']}"
            )
        if result["permutation_p"] < gates["leakage"]["permutation_p_min"]:
            failures.append(
                f"leakage.{name}.permutation_p below {gates['leakage']['permutation_p_min']}"
            )
        low, other = sorted((result["false_allow_rate"], result["false_deny_rate"]))
        if (
            low <= gates["leakage"]["shortcut_low_error_max"]
            and other <= gates["leakage"]["shortcut_other_error_max"]
        ):
            failures.append(f"leakage.{name}: asymmetric shortcut error gate failed")
        if not isinstance(result.get("deterministic_or_reversible"), bool):
            failures.append(f"leakage.{name}.deterministic_or_reversible must be boolean")
        elif result["deterministic_or_reversible"]:
            failures.append(f"leakage.{name}: deterministic/reversible encoding")
    branch_deviation = metrics.get("branch", {}).get("max_label_rate_deviation")
    if not valid_rate(branch_deviation):
        failures.append("branch.max_label_rate_deviation must be finite in [0,1]")
    elif branch_deviation > gates["leakage"]["branch_label_rate_deviation_max"]:
        failures.append("branch.max_label_rate_deviation exceeds frozen maximum")
    branch_support = metrics.get("branch", {}).get("minimum_support")
    if (
        not isinstance(branch_support, int)
        or isinstance(branch_support, bool)
        or branch_support < 0
    ):
        failures.append("branch.minimum_support must be a nonnegative integer")
    elif branch_support < gates["leakage"]["branch_minimum_support"]:
        failures.append("branch.minimum_support below frozen minimum")
    branch_accuracy = metrics.get("branch", {}).get("inference_balanced_accuracy")
    if not valid_rate(branch_accuracy):
        failures.append("branch.inference_balanced_accuracy must be finite in [0,1]")
    elif branch_accuracy > gates["leakage"]["branch_inference_balanced_accuracy_max"]:
        failures.append("branch.inference_balanced_accuracy exceeds frozen maximum")
    secondary_names = {"family", "difficulty", "pair_membership", "generator_branch"}
    secondary = metrics.get("secondary_prediction", {})
    if set(secondary) != secondary_names:
        failures.append(
            f"secondary_prediction: expected {sorted(secondary_names)}, got {sorted(secondary)}"
        )
    for name, result in secondary.items():
        required = {"prediction_accuracy", "majority_baseline", "max_label_rate_deviation"}
        if set(result) != required:
            failures.append(f"secondary_prediction.{name}: invalid fields")
            continue
        if any(not valid_rate(result[field]) for field in required):
            failures.append(f"secondary_prediction.{name}: rates must be finite in [0,1]")
            continue
        if (
            result["max_label_rate_deviation"]
            > gates["leakage"]["secondary_target_label_rate_deviation_max"]
        ):
            failures.append(f"secondary_prediction.{name}: label-rate deviation exceeds maximum")
    realized = metrics.get("realized_split", {})
    if phase in {"DEV_PROOF", "PRE_HELDOUT"}:
        expected_realized = {
            "DEV": 800,
            "VALIDATION": 0 if phase == "DEV_PROOF" else 800,
            "HELD_OUT": 0,
        }
    else:
        expected_realized = gates["counts"]["split_exact"]
    realized_well_typed = isinstance(realized, dict) and all(
        exact_integer(realized.get(key), value) for key, value in expected_realized.items()
    ) and set(realized) == set(expected_realized)
    if not realized_well_typed:
        failures.append(f"realized_split: expected {expected_realized} for {phase}, got {realized}")
    split_counts = metrics.get("counts", {}).get("split")
    if not isinstance(split_counts, dict) or any(
        not isinstance(value, int) or isinstance(value, bool) for value in split_counts.values()
    ) or split_counts != realized:
        failures.append("counts.split must equal directly realized split counts")
    total = metrics.get("counts", {}).get("total")
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or not isinstance(realized, dict)
        or any(not isinstance(value, int) or isinstance(value, bool) for value in realized.values())
        or total != sum(realized.values())
    ):
        failures.append("counts.total must equal sum of directly realized split counts")
    return {
        "decision": "PASS" if not failures else "BLOCK",
        "phase": phase,
        "protocol_id": gates["protocol_id"],
        "preregistration_checksum": preregistration_checksum(),
        "reasons": failures,
    }


def evaluate_gates(metrics: object) -> dict[str, Any]:
    """Return BLOCK, never an exception, for malformed or incomplete gate evidence."""
    if not isinstance(metrics, dict):
        return {
            "decision": "BLOCK",
            "phase": None,
            "protocol_id": "AUTH-COVERAGE-002-PROTOCOL@2",
            "preregistration_checksum": preregistration_checksum(),
            "reasons": ["malformed gate evidence: top level must be an object"],
        }
    try:
        return _evaluate_gates_unchecked(metrics)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        return {
            "decision": "BLOCK",
            "phase": metrics.get("phase"),
            "protocol_id": "AUTH-COVERAGE-002-PROTOCOL@2",
            "preregistration_checksum": preregistration_checksum(),
            "reasons": [f"malformed gate evidence: {type(error).__name__}: {error}"],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metrics", type=Path)
    args = parser.parse_args()
    result = evaluate_gates(load_json(args.metrics))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["decision"] == "PASS" else 1)


if __name__ == "__main__":
    main()
