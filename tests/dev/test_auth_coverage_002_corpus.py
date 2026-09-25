"""Static AUTH-COVERAGE-002 corpus gates; never calls production authorization."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments/AUTH-COVERAGE-002"
CORPUS = EXPERIMENT / "corpus"


def _json(path: Path):  # type: ignore[no-untyped-def]
    return json.loads(path.read_text(encoding="utf-8"))


def test_preregistered_protocol_and_spec_checksums_are_still_frozen() -> None:
    for line in (EXPERIMENT / "PROTOCOL_SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_corpus_target_counts_and_independent_pair_audit() -> None:
    report = _json(CORPUS / "analysis/audit_report.json")
    assert report["scenario_count"] == 4000
    assert report["split_counts"] == {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 2400}
    assert report["decision_counts"] == {"ALLOW": 2000, "DENY": 2000}
    assert report["tool_counts"] == {"FILESYSTEM": 2000, "PROCESS": 2000}
    assert report["pair_quality_counts"] == {"STRICT_STRONG": 1600, "STRONG_AUXILIARY": 400}
    assert report["cross_tool_quality_counts"] == {"STRICTLY_COMPARABLE": 250}
    assert report["normalized_semantic_templates"] >= 1500
    assert report["largest_normalized_cluster"] <= 8
    assert report["exact_duplicates"] == report["cross_split_duplicates"] == 0
    assert report["cross_split_near_templates"] == 0
    assert report["oracle_agreement"] == {"agreed": 4000, "total": 4000}
    assert report["runtime_nonauthority_leakage_peak"] < 0.65


def test_family_and_compound_targets_are_met() -> None:
    report = _json(CORPUS / "analysis/audit_report.json")
    families = report["family_counts"]
    assert families["HARD_BENIGN"] >= 1000
    assert families["HARD_UNAUTHORIZED"] >= 1000
    assert families["SUSPICIOUS_BENIGN"] >= 500
    assert families["BENIGN_LOOKING_UNAUTHORIZED"] >= 500
    assert families["TASK_BINDING"] >= 600
    assert families["CROSS_TASK_REUSE"] >= 300
    assert families["RESOURCE_BOUNDARY"] >= 400
    assert families["CAPABILITY_SYNTHESIS"] >= 300
    assert families["CAPABILITY_DISTRACTOR"] >= 500
    assert families["ZERO_RELEVANT"] >= 300
    assert all(report["compound_quadrants"][name] >= 200 for name in ("AA", "AD", "DA", "DD"))


def test_runtime_analysis_one_to_one_and_no_prohibited_runtime_keys() -> None:
    prohibited = {
        "expected_decision",
        "family",
        "difficulty",
        "pair_id",
        "oracle_a",
        "oracle_b",
        "authority_distance",
        "generation_template",
        "pressure_dimension",
    }
    runtime: list[dict[str, object]] = []
    for directory in ("DEV", "VALIDATION", "HELD_OUT-runtime"):
        package = CORPUS / "runtime" / directory
        assert {path.name for path in package.iterdir()} == {
            "scenarios.json",
            "corpus_binding.json",
            "runtime_binding.json",
            "package_manifest.json",
        }
        values = _json(package / "scenarios.json")
        runtime.extend(values)
        assert not any(prohibited & set(value) for value in values)
    analysis = _json(CORPUS / "analysis/analysis.json")["records"]
    runtime_ids = [item["scenario_id"] for item in runtime]
    analysis_ids = [item["scenario_id"] for item in analysis]
    assert len(runtime_ids) == len(set(runtime_ids)) == 4000
    assert set(runtime_ids) == set(analysis_ids)
    assert all(len(item) == 64 and set(item) <= set("0123456789abcdef") for item in runtime_ids)


def test_dev_validation_runner_parse_and_raw_input_bindings() -> None:
    # HELD_OUT is deliberately excluded from ordinary regression parsing.
    probe = """
import json, sys
from pathlib import Path
from safetybox.research.auth_coverage_runner import runtime_scenario_from_mapping
from safetybox.research.auth_coverage_raw import capture_authorization_input, canonical_sha256
root=Path(sys.argv[1])
for name in ('DEV','VALIDATION'):
 p=root/name
 values=json.loads((p/'scenarios.json').read_text())
 binding=json.loads((p/'runtime_binding.json').read_text())
 for value in values:
  item=runtime_scenario_from_mapping(value)
  captured=capture_authorization_input(tool_class=item.tool_class,contract_task_id=item.contract_task_id,contract_description=item.contract_description,received_capabilities=item.capabilities,primary_request=item.request,additional_components=item.additional_components)
  assert canonical_sha256(captured)==binding['scenario_input_digests'][item.scenario_id]
print('PASS')
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe, str(CORPUS / "runtime")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "PASS"


def test_exhaustive_model_and_invalid_controls_are_separate() -> None:
    result = _json(EXPERIMENT / "formal/exhaustive_results.json")
    controls = _json(CORPUS / "analysis/invalid_structure_controls.json")
    assert result["state_count"] >= 50000 and result["result"] == "PASS"
    assert result["production_calls"] == 0
    assert controls["case_count"] == 48
    assert controls["primary_accuracy_denominator"] is False
    assert len(controls["cases"]) == 48
    assert all(
        item["schema_rejected"] and item["oracle_a"] == item["oracle_b"]
        for item in controls["cases"]
    )
