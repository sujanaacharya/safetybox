#!/usr/bin/env python3
"""Nested semantic admission gate for external AUTH-COVERAGE-002 packs."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from governance import normative_explanation, pair_audit

BASE = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCHEMA = _load("auth002_schema_external", BASE / "schema.py")
ORACLE_A = _load("auth002_oracle_a_external", BASE / "oracle_a.py")
ORACLE_B = _load("auth002_oracle_b_external", BASE / "oracle_b.py")


class ExternalPackError(ValueError):
    pass


def validate_external_pack(pack: object) -> dict[str, Any]:
    if not isinstance(pack, dict) or set(pack) != {
        "pack_id",
        "spec_id",
        "runtime",
        "analysis",
        "labels",
        "pairs",
    }:
        raise ExternalPackError("external pack has invalid top-level fields")
    if pack["spec_id"] != "AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1":
        raise ExternalPackError("external pack targets the wrong normative specification")
    runtime = pack["runtime"]
    analysis = pack["analysis"]
    labels = pack["labels"]
    if not all(isinstance(value, list) for value in (runtime, analysis, labels, pack["pairs"])):
        raise ExternalPackError("runtime, analysis, labels, and pairs must be arrays")
    if not runtime or not (len(runtime) == len(analysis) == len(labels)):
        raise ExternalPackError("runtime/analysis/label cardinalities differ")
    runtime_by_id: dict[str, dict[str, Any]] = {}
    for item in runtime:
        SCHEMA.validate_runtime(item)
        if item["scenario_id"] in runtime_by_id:
            raise ExternalPackError("duplicate runtime scenario_id")
        runtime_by_id[item["scenario_id"]] = item
    analysis_by_id: dict[str, dict[str, Any]] = {}
    for item in analysis:
        SCHEMA.validate_analysis_record(item)
        if (
            not isinstance(item["families"], list)
            or not item["families"]
            or any(not isinstance(value, str) or not value for value in item["families"])
        ):
            raise ExternalPackError("analysis families must be nonempty strings")
        if (
            not isinstance(item["authority_distance"], (int, float))
            or isinstance(item["authority_distance"], bool)
            or item["authority_distance"] < 0
        ):
            raise ExternalPackError("analysis authority_distance must be nonnegative")
        if not isinstance(item["generation_template"], str) or not item["generation_template"]:
            raise ExternalPackError("analysis generation_template must be nonempty")
        if not isinstance(item["owasp_precursors"], list) or any(
            value not in {"ASI01", "ASI02", "ASI03", "ASI05", "ASI06", "ASI10"}
            for value in item["owasp_precursors"]
        ):
            raise ExternalPackError("analysis OWASP precursor is invalid")
        analysis_by_id[item["scenario_id"]] = item
    label_by_id: dict[str, dict[str, Any]] = {}
    for item in labels:
        if not isinstance(item, dict) or set(item) != {"scenario_id", "expected_decision"}:
            raise ExternalPackError("label has invalid fields")
        if item["expected_decision"] not in {"ALLOW", "DENY"}:
            raise ExternalPackError("invalid label decision")
        label_by_id[item["scenario_id"]] = item
    ids = set(runtime_by_id)
    if ids != set(analysis_by_id) or ids != set(label_by_id):
        raise ExternalPackError("runtime/analysis/label joins are not bijective")
    oracle_records: list[dict[str, Any]] = []
    for scenario_id in sorted(ids):
        item = runtime_by_id[scenario_id]
        a = ORACLE_A.evaluate(item)
        b = ORACLE_B.evaluate(item)
        expected = label_by_id[scenario_id]["expected_decision"]
        if a != b:
            raise ExternalPackError(f"dual-oracle disagreement: {scenario_id}")
        if a["rule"] == "AUTH.INVALID_STRUCTURE":
            raise ExternalPackError(f"spec-invalid canonical scenario: {scenario_id}")
        if (
            a["decision"] != expected
            or analysis_by_id[scenario_id]["expected_decision"] != expected
        ):
            raise ExternalPackError(f"oracle/analysis/label disagreement: {scenario_id}")
        if analysis_by_id[scenario_id]["pressure_dimension"] not in {
            "TASK_BINDING",
            "ACTION_BINDING",
            "RESOURCE_BINDING",
            "CAPABILITY_MATCH",
            "CAPABILITY_SYNTHESIS",
            "COMPOUND_AUTH",
            "CROSS_TASK_REUSE",
        }:
            raise ExternalPackError(f"invalid pressure dimension: {scenario_id}")
        analysis_item = analysis_by_id[scenario_id]
        if analysis_item["oracle_a"] != a or analysis_item["oracle_b"] != b:
            raise ExternalPackError(f"nested oracle evidence mismatch: {scenario_id}")
        names = ["primary"] if item["tool_class"] == "FILESYSTEM" else ["primary", "cwd"]
        oracle_names = ["primary"] if item["tool_class"] == "FILESYSTEM" else ["exec", "cwd"]
        decisions = [a["components"][name]["decision"] for name in oracle_names]
        if analysis_item["component_decisions"] != decisions:
            raise ExternalPackError(f"component decision mismatch: {scenario_id}")
        explanation = analysis_item["expected_explanation"]
        if not isinstance(explanation, list) or len(explanation) != len(names):
            raise ExternalPackError(f"expected explanation shape mismatch: {scenario_id}")
        requests = [item["request"], *(part["request"] for part in item["additional_components"])]
        for index, (component, component_id, oracle_name, request) in enumerate(
            zip(explanation, names, oracle_names, requests, strict=True)
        ):
            expected_fields = {
                "component_id",
                "component_index",
                "action",
                "resource",
                "decision",
                "matched_capability",
                "rule",
                "reason",
                "authority_source",
            }
            if not isinstance(component, dict) or set(component) != expected_fields:
                raise ExternalPackError(f"expected explanation fields mismatch: {scenario_id}")
            oracle_component = a["components"][oracle_name]
            checks = {
                "component_id": component_id,
                "component_index": index,
                "action": request["action"],
                "resource": request["resource"],
                "decision": oracle_component["decision"],
                "matched_capability": oracle_component["matched_capability"],
                "rule": oracle_component["rule"],
                "authority_source": "TaskContract",
            }
            if (
                any(component[key] != value for key, value in checks.items())
                or not isinstance(component["reason"], str)
                or not component["reason"]
            ):
                raise ExternalPackError(f"expected explanation semantics mismatch: {scenario_id}")
        if explanation != normative_explanation(item, a):
            raise ExternalPackError(f"expected explanation is not normative: {scenario_id}")
        oracle_records.append({"scenario_id": scenario_id, "oracle_a": a, "oracle_b": b})
    pair_ids: set[str] = set()
    paired_scenarios: set[str] = set()
    for pair in pack["pairs"]:
        required = {
            "pair_id",
            "scenario_a",
            "scenario_b",
            "target_dimension",
            "expected_relation",
            "generator_declared_intention",
            "changed_fields",
            "unchanged_fields",
            "automated_diff",
            "quality_classification",
            "reviewer_identity",
            "review_process",
            "review_evidence_digest",
        }
        if not isinstance(pair, dict) or set(pair) != required:
            raise ExternalPackError("pair has invalid fields")
        if (
            pair["pair_id"] in pair_ids
            or pair["scenario_a"] not in ids
            or pair["scenario_b"] not in ids
            or pair["scenario_a"] == pair["scenario_b"]
            or pair["scenario_a"] in paired_scenarios
            or pair["scenario_b"] in paired_scenarios
        ):
            raise ExternalPackError("pair identity/reference invalid")
        if pair["target_dimension"] not in {
            "TASK",
            "ACTION",
            "RESOURCE",
            "CAPABILITY",
            "COMPOUND",
        } or pair["expected_relation"] not in [
            ["ALLOW", "DENY"],
            ["DENY", "ALLOW"],
            ["ALLOW", "ALLOW"],
            ["DENY", "DENY"],
        ]:
            raise ExternalPackError("pair dimension/relation invalid")
        intention = pair["generator_declared_intention"]
        if intention != {
            "pair_id": pair["pair_id"],
            "target_dimension": pair["target_dimension"],
            "expected_relation": pair["expected_relation"],
        }:
            raise ExternalPackError("pair generator intention mismatch")
        left = {
            "authoring_key": pair["scenario_a"],
            "label": label_by_id[pair["scenario_a"]]["expected_decision"],
            "runtime": runtime_by_id[pair["scenario_a"]],
        }
        right = {
            "authoring_key": pair["scenario_b"],
            "label": label_by_id[pair["scenario_b"]]["expected_decision"],
            "runtime": runtime_by_id[pair["scenario_b"]],
        }
        audited = pair_audit(intention, left, right)
        for field in required - {"generator_declared_intention"}:
            if pair[field] != audited[field]:
                raise ExternalPackError(f"pair audit evidence mismatch: {pair['pair_id']}:{field}")
        if audited["quality_classification"] == "WEAK":
            raise ExternalPackError(f"weak pair is inadmissible: {pair['pair_id']}")
        pair_ids.add(pair["pair_id"])
        paired_scenarios.update((pair["scenario_a"], pair["scenario_b"]))
    return {
        "decision": "ADMIT",
        "scenario_count": len(ids),
        "oracle_agreement": 1.0,
        "oracle_records": oracle_records,
    }
