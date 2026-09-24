"""Integrity, isolation, coverage, and fixture audits for EXP-014-CORPUS@1.

These tests never import, instantiate, or execute ``FilesystemAdapter``.  They validate
declarative inputs and scoring metadata before the one-shot evaluation.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import fields
from pathlib import Path
from typing import Any

from safetybox.experiments.exp014_corpus import (
    OPERATIONS,
    CorpusLabel,
    CorpusScenario,
    FixtureEntry,
    RequestSpec,
    load_labels,
    load_scenarios,
    validate_corpus,
)

ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "experiments" / "EXP-014" / "corpus"
MODULE = ROOT / "src" / "safetybox" / "experiments" / "exp014_corpus.py"
DEVELOPMENT = ROOT / "tests" / "dev" / "test_exp014_filesystem_adapter.py"
FROZEN_PATHS = (
    ROOT / "src" / "safetybox" / "filesystem",
    ROOT / "src" / "safetybox" / "authorization.py",
)
OPAQUE_ID = re.compile(r"FSH-014-\d{3}\Z")
MUTATIONS = {
    "filesystem.write",
    "filesystem.append",
    "filesystem.create",
    "filesystem.delete",
    "filesystem.rename",
    "filesystem.mkdir",
}
RETRIEVALS = {"filesystem.read", "filesystem.list", "filesystem.stat"}


def _label_map() -> dict[str, CorpusLabel]:
    return {item.scenario_id: item for item in load_labels()}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _materialize(root: Path, entry: FixtureEntry) -> None:
    relative = entry.path.removeprefix("/workspace/")
    target = root / relative
    if entry.type == "directory":
        target.mkdir()
    elif entry.type == "file":
        if entry.content_utf8 is not None:
            target.write_bytes(entry.content_utf8.encode("utf-8"))
        else:
            assert entry.content_hex is not None
            target.write_bytes(bytes.fromhex(entry.content_hex))
    elif entry.type == "symlink":
        assert entry.target is not None
        link_target = entry.target
        if entry.target_kind == "logical_absolute":
            link_target = str(root / entry.target.removeprefix("/workspace/"))
        target.symlink_to(link_target)
    else:
        assert entry.source is not None
        os.link(root / entry.source.removeprefix("/workspace/"), target)


def _snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    records: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        logical = f"/workspace/{path.relative_to(root).as_posix()}"
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            target = os.readlink(path)
            root_text = str(root)
            if target == root_text or target.startswith(f"{root_text}/"):
                target = f"/workspace{target.removeprefix(root_text)}"
            records.append((logical, "symlink", target))
        elif stat.S_ISDIR(mode):
            records.append((logical, "directory", ""))
        else:
            records.append((logical, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(records)


def _feature_values(item: CorpusScenario) -> dict[str, object]:
    path = item.request.resource
    stripped = path.removeprefix("/workspace/").lstrip("/")
    parts = tuple(part for part in stripped.split("/") if part)
    object_types = tuple(sorted({entry.type for entry in item.filesystem_fixture.entries}))
    scalar_length = 7 + len(item.task_contract.capabilities) * 2 + len(
        item.filesystem_fixture.entries
    ) * 2
    return {
        "operation": item.request.operation,
        "path_length": len(path),
        "path_depth": len(parts),
        "relative_vs_absolute": "absolute" if path.startswith("/") else "relative",
        "contains_dot_dot": ".." in path.split("/"),
        "contains_unicode": any(ord(character) > 127 for character in path),
        "root_name": parts[0] if parts else "/workspace",
        "task_category": "not_encoded_in_runtime_input",
        "resource_subtree": parts[0] if parts else "/workspace",
        "capability_count": len(item.task_contract.capabilities),
        "source_destination_presence": item.request.destination is not None,
        "fixture_object_type": object_types,
        "symlink_marker": "symlink" in object_types,
        "hard_link_marker": "hard_link" in object_types,
        "failure_injection_type": (
            item.dependency_injection.type if item.dependency_injection else "none"
        ),
        "scenario_length": scalar_length,
        "fixture_size": len(item.filesystem_fixture.entries),
        "route": item.route,
    }


def _lookup_accuracy(
    scenarios: tuple[CorpusScenario, ...],
    labels: dict[str, CorpusLabel],
    features: tuple[str, ...],
) -> float:
    buckets: dict[tuple[object, ...], Counter[str]] = defaultdict(Counter)
    for item in scenarios:
        values = _feature_values(item)
        key = tuple(values[feature] for feature in features)
        buckets[key][labels[item.scenario_id].expected_terminal_classification] += 1
    return sum(max(bucket.values()) for bucket in buckets.values()) / len(scenarios)


def test_identity_schema_counts_and_taxonomy() -> None:
    scenarios, labels = validate_corpus()
    manifest = _json(CORPUS / "manifest.yaml")
    assert len(scenarios) == len(labels) == manifest["scenario_count"] == 96
    assert manifest["corpus_id"] == "EXP-014-CORPUS@1"
    assert manifest["version"] == 1
    assert manifest["status"] == "READY_FOR_FREEZE"
    assert Counter(item.expected_terminal_classification for item in labels) == {
        "ALLOW_SUCCESS": 36,
        "POLICY_DENY": 28,
        "TARGET_VALIDATION_REJECT": 17,
        "TOOL_ERROR": 6,
        "FAIL_CLOSED": 5,
        "FAIL_INDETERMINATE": 2,
        "EXPECTED_FMED_L1_BYPASS": 2,
    }
    assert {item.scenario_id for item in scenarios} == {item.scenario_id for item in labels}
    assert all(OPAQUE_ID.fullmatch(item.scenario_id) for item in scenarios)


def test_operation_authorization_and_result_coverage() -> None:
    scenarios = load_scenarios()
    labels = _label_map()
    by_operation: dict[str, set[str]] = defaultdict(set)
    for item in scenarios:
        by_operation[item.request.operation].add(
            labels[item.scenario_id].expected_terminal_classification
        )
    assert set(by_operation) == OPERATIONS
    assert all("ALLOW_SUCCESS" in outcomes for outcomes in by_operation.values())
    assert all("POLICY_DENY" in outcomes for outcomes in by_operation.values())
    assert sum(item.request.operation == "filesystem.rename" for item in scenarios) == 16
    assert sum(
        label.expected_terminal_classification == "TARGET_VALIDATION_REJECT"
        for label in labels.values()
    ) == 17


def test_pairs_are_complete_unique_and_quality_audited() -> None:
    labels = load_labels()
    pairs: dict[str, list[CorpusLabel]] = defaultdict(list)
    for label in labels:
        pairs[label.counterfactual_pair_id].append(label)
    assert len(pairs) == 48
    assert all(len(members) == 2 for members in pairs.values())
    assert all({item.pair_role for item in members} == {"A", "B"} for members in pairs.values())
    assert all(len({item.semantic_variable for item in members}) == 1 for members in pairs.values())
    quality = Counter(members[0].pair_strength for members in pairs.values())
    assert quality == {"STRONG": 45, "MODERATE": 1, "WEAK_CONTROL_PAIR": 1, "WEAK": 1}
    assert len({item.scenario_id for members in pairs.values() for item in members}) == 96


def test_hard_negatives_links_failures_and_controls_are_complete() -> None:
    scenarios = load_scenarios()
    labels = _label_map()
    assert sum(item.hard_negative for item in labels.values()) == 23
    assert sum("SYMLINK" in item.family for item in labels.values()) == 20
    assert sum(
        "SYMLINK" in item.family
        and item.expected_terminal_classification == "TARGET_VALIDATION_REJECT"
        for item in labels.values()
    ) == 10
    assert sum("HARD_LINK" in item.family for item in labels.values()) == 14
    assert sum(
        "HARD_LINK" in item.family
        and item.expected_terminal_classification == "TARGET_VALIDATION_REJECT"
        for item in labels.values()
    ) == 7
    assert sum("FAILURE_ERROR" in item.family for item in labels.values()) == 12
    assert Counter(item.route for item in scenarios) == {
        "adapter": 94,
        "direct_os_open": 1,
        "direct_pathlib_write": 1,
    }
    assert all(
        not labels[item.scenario_id].adapter_correctness_denominator
        for item in scenarios
        if item.route != "adapter"
    )


def test_runtime_objects_and_adapter_payloads_have_no_label_fields() -> None:
    prohibited = {
        "label",
        "expected_outcome",
        "expected_result_category",
        "family",
        "pair_id",
        "counterfactual_pair_id",
        "hard_negative",
        "rationale",
        "author_notes",
    }
    assert not prohibited & {field.name for field in fields(CorpusScenario)}
    assert not prohibited & {field.name for field in fields(RequestSpec)}
    for item in load_scenarios():
        assert not prohibited & set(item.request.adapter_payload())
        assert set(item.request.adapter_payload()) <= {
            "session_id",
            "task_id",
            "request_id",
            "actor",
            "operation",
            "resource",
            "destination",
            "data",
        }


def test_denied_retrieval_sentinels_are_absent_from_labels() -> None:
    scenarios = load_scenarios()
    labels = _label_map()
    label_text = (CORPUS / "labels.yaml").read_text(encoding="utf-8")
    checked = Counter[str]()
    for item in scenarios:
        label = labels[item.scenario_id]
        if label.expected_terminal_classification != "POLICY_DENY":
            continue
        operation = item.request.operation
        if operation == "filesystem.read":
            for entry in item.filesystem_fixture.entries:
                if entry.type == "file" and entry.content_utf8 and len(entry.content_utf8) >= 10:
                    assert entry.content_utf8 not in label_text
                    checked["read"] += 1
        elif operation == "filesystem.list":
            requested = item.request.resource.rstrip("/")
            if not requested.startswith("/"):
                requested = f"/workspace/{requested}"
            for entry in item.filesystem_fixture.entries:
                if entry.path.startswith(f"{requested}/"):
                    child = entry.path.removeprefix(f"{requested}/").split("/", maxsplit=1)[0]
                    if child.startswith("hidden-"):
                        assert child not in label_text
                        checked["list"] += 1
        elif operation == "filesystem.stat":
            checked["stat"] += 1
    assert checked["read"] >= 2
    assert checked["list"] >= 2
    assert checked["stat"] == 4


def test_fixture_definitions_materialize_deterministically_in_temporary_roots() -> None:
    for scenario in load_scenarios():
        snapshots: list[tuple[tuple[str, str, str], ...]] = []
        for _ in range(2):
            with tempfile.TemporaryDirectory(prefix="exp014-corpus-") as directory:
                root = Path(directory)
                for entry in scenario.filesystem_fixture.entries:
                    _materialize(root, entry)
                snapshots.append(_snapshot(root))
        assert snapshots[0] == snapshots[1], scenario.scenario_id
        assert len(scenario.filesystem_fixture.sha256) == 64


def test_all_execution_targets_are_isolated_logical_paths() -> None:
    for scenario in load_scenarios():
        assert {"linux", "local_case_sensitive_filesystem"} <= set(
            scenario.environment_requirements
        )
        for entry in scenario.filesystem_fixture.entries:
            assert entry.path.startswith("/workspace/")
            assert not entry.path.startswith(("/etc/", "/home/", "/root/"))
        if scenario.request.resource.startswith("/"):
            assert (
                scenario.request.resource == "/workspace"
                or scenario.request.resource.startswith(
                    ("/workspace/", "/var/tmp/corpus-shadow/")
                )
            )
        if scenario.request.resource.startswith("/var/tmp/"):
            assert _label_map()[scenario.scenario_id].expected_result_category == "FAIL_CLOSED"


def test_static_single_features_and_obvious_pairs_do_not_perfectly_separate() -> None:
    scenarios = load_scenarios()
    labels = _label_map()
    single_features = tuple(_feature_values(scenarios[0]))
    scores = {
        feature: _lookup_accuracy(scenarios, labels, (feature,)) for feature in single_features
    }
    assert all(score < 1.0 for score in scores.values()), scores
    combinations = (
        ("operation", "path_depth"),
        ("operation", "root_name"),
        ("operation", "capability_count"),
        ("fixture_object_type", "failure_injection_type"),
        ("route", "operation"),
    )
    pair_scores = {
        "+".join(features): _lookup_accuracy(scenarios, labels, features)
        for features in combinations
    }
    assert all(score < 1.0 for score in pair_scores.values()), pair_scores


def test_adapter_source_isolation_and_no_execution_surface() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        name.startswith(
            (
                "safetybox.filesystem",
                "safetybox.authorization",
                "safetybox.monitor",
                "safetybox.policy",
            )
        )
        for name in imported
    )
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (MODULE, ROOT / "tests" / "test_exp014_corpus.py")
    )
    adapter_name = "Filesystem" + "Adapter"
    execute_token = "." + "execute("
    canonicalizer_name = "canonicalize" + "_logical_path"
    validator_name = "Physical" + "TargetValidator"
    assert adapter_name not in combined.replace(f"``{adapter_name}``", "")
    assert execute_token not in combined
    assert canonicalizer_name not in combined
    assert validator_name not in combined


def test_no_development_identifier_or_exact_operation_path_duplicate() -> None:
    scenarios = load_scenarios()
    corpus_text = "\n".join(
        (CORPUS / name).read_text(encoding="utf-8")
        for name in ("scenarios.yaml", "labels.yaml")
    )
    assert "DEV-FS-" not in corpus_text
    development_tree = ast.parse(DEVELOPMENT.read_text(encoding="utf-8"))
    development_tuples: set[tuple[str, str, str | None]] = set()
    for node in ast.walk(development_tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "request" or len(node.args) < 2:
            continue
        operation_node, resource_node = node.args[:2]
        if not (
            isinstance(operation_node, ast.Attribute)
            and isinstance(resource_node, ast.Constant)
            and isinstance(resource_node.value, str)
        ):
            continue
        destination: str | None = None
        for keyword in node.keywords:
            if keyword.arg == "destination" and isinstance(keyword.value, ast.Constant):
                destination = keyword.value.value
        development_tuples.add(
            (f"filesystem.{operation_node.attr.lower()}", resource_node.value, destination)
        )
    held_out_tuples = {
        (item.request.operation, item.request.resource, item.request.destination)
        for item in scenarios
    }
    shared_protocol_primitives = {("filesystem.stat", "/workspace", None)}
    assert development_tuples & held_out_tuples == shared_protocol_primitives


def test_requirement_invariant_and_threat_coverage_is_explicit() -> None:
    manifest = _json(CORPUS / "manifest.yaml")
    assert set(manifest["requirement_coverage"]) == {
        f"REQ-{number:03d}" for number in range(1, 33)
    }
    assert set(manifest["invariant_coverage"]) == {
        "INV-016",
        "INV-017",
        "INV-018",
        "INV-019",
    }
    threats = manifest["threat_coverage"]
    assert threats["symlink_swap_and_toctou"]["status"] == "NOT_EVALUATED"
    assert threats["inherited_file_descriptor_bypass"]["status"] == "NOT_EVALUATED"
    assert all(value for value in threats.values())


def test_manifest_counts_match_loaded_data() -> None:
    manifest = _json(CORPUS / "manifest.yaml")
    scenarios = load_scenarios()
    labels = load_labels()
    assert manifest["terminal_classification_counts"] == dict(
        sorted(Counter(item.expected_terminal_classification for item in labels).items())
    )
    assert manifest["operation_counts"] == dict(
        sorted(Counter(item.request.operation for item in scenarios).items())
    )
    assert manifest["pair_count"] == len({item.counterfactual_pair_id for item in labels})
    assert manifest["category_counts"]["hard_negatives"] == sum(
        item.hard_negative for item in labels
    )


def test_corpus_contains_no_predictions_or_result_artifacts() -> None:
    prohibited_names = {"predictions.yaml", "results.yaml", "metrics.yaml", "traces.yaml"}
    assert not prohibited_names & {path.name for path in CORPUS.iterdir()}
    scenario_document = _json(CORPUS / "scenarios.yaml")
    assert "prediction" not in json.dumps(scenario_document).lower()
    assert "true_positive" not in json.dumps(scenario_document).lower()


def test_checksum_inventory_matches_every_frozen_corpus_file() -> None:
    checksum_file = CORPUS / "checksums.sha256"
    lines = [line for line in checksum_file.read_text(encoding="utf-8").splitlines() if line]
    recorded = {}
    for line in lines:
        digest, name = line.split("  ", maxsplit=1)
        recorded[name] = digest
    expected_names = {
        path.name for path in CORPUS.iterdir() if path.is_file() and path.name != "checksums.sha256"
    }
    assert set(recorded) == expected_names
    for name, digest in recorded.items():
        assert hashlib.sha256((CORPUS / name).read_bytes()).hexdigest() == digest


def test_nfc_fixture_names_and_distinct_sessions_requests() -> None:
    scenarios = load_scenarios()
    assert len({item.request.session_id for item in scenarios}) == len(scenarios)
    assert len({item.request.request_id for item in scenarios}) == len(scenarios)
    for scenario in scenarios:
        for entry in scenario.filesystem_fixture.entries:
            assert unicodedata.normalize("NFC", entry.path) == entry.path
