from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from safetybox.capabilities import Capability
from safetybox.models import ActionRequest
from safetybox.research.auth_coverage_raw import (
    RawImplementationProvenance,
    canonical_sha256,
    capture_authorization_input,
)
from safetybox.research.auth_coverage_runner import (
    RUNNER_ID,
    CanonicalAuthorizationRunner,
    RawRecordWriter,
    RuntimeScenario,
)
from safetybox.research.auth_coverage_scoring import ScoringIsolationError, score_sealed_run
from safetybox.research.auth_coverage_state import (
    RunManifest,
    RunState,
    RunStateStore,
    canonical_json,
    sha256_file,
)
from safetybox.research.exposure_ledger import ExposureLedger


def _sealed_dev_run(tmp_path: Path):
    item = RuntimeScenario(
        scenario_id="opaque-dev-scoring-1",
        tool_class="filesystem",
        contract_task_id="dev-task",
        contract_description="synthetic scoring fixture",
        capabilities=(Capability("filesystem.read", "/dev/**"),),
        request=ActionRequest(
            request_id="dev-request",
            session_id="dev-session",
            task_id="dev-task",
            actor="dev-agent",
            action="filesystem.read",
            resource="/dev/input",
        ),
    )
    input_digest = canonical_sha256(
        capture_authorization_input(
            tool_class=item.tool_class,
            contract_task_id=item.contract_task_id,
            contract_description=item.contract_description,
            received_capabilities=item.capabilities,
            primary_request=item.request,
        )
    )
    binding = {
        "corpus_id": "AUTH-COVERAGE-002-DEV-SCORING@1",
        "split": "DEV",
        "scenario_ids": [item.scenario_id],
        "scenario_input_digests": {item.scenario_id: input_digest},
    }
    runtime = tmp_path / "runtime.json"
    scenarios = tmp_path / "scenarios.json"
    corpus = tmp_path / "corpus.json"
    source = tmp_path / "policy.py"
    scenarios.write_text("[]\n", encoding="utf-8")
    binding["runtime_scenarios_checksum"] = sha256_file(scenarios)
    runtime.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    corpus.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    source.write_text("# synthetic source\n", encoding="utf-8")
    manifest = RunManifest(
        experiment_id="AUTH-COVERAGE-002-DEV",
        protocol_id="AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1",
        corpus_id=binding["corpus_id"],
        split="DEV",
        run_id="dev-scoring-run",
        production_component="TaskContractPolicy.authorize",
        exposure_ledger_path=str(tmp_path / "ledger.jsonl"),
        runtime_package_path=str(runtime),
        runtime_package_checksum=sha256_file(runtime),
        runtime_scenarios_path=str(scenarios),
        runtime_scenarios_checksum=sha256_file(scenarios),
        corpus_manifest_path=str(corpus),
        corpus_manifest_checksum=sha256_file(corpus),
        implementation_sha="1" * 40,
        implementation_artifacts=((str(source), sha256_file(source)),),
        policy_version="TaskContractPolicy@1",
        authorization_spec_version="AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1",
        task_contract_schema_version="TaskContract@1",
        runner_version=RUNNER_ID,
        runner_sha="2" * 64,
        raw_schema_version="AUTH-COVERAGE-002-RAW-SCHEMA@1",
        ledger_version="AUTH-COVERAGE-EXPOSURE-LEDGER@1",
        scenario_count=1,
        scenario_order=(item.scenario_id,),
        scenario_input_digests=((item.scenario_id, input_digest),),
    )
    metadata = tmp_path / "run_metadata.json"
    metadata.write_bytes(canonical_json(manifest.as_dict()) + b"\n")
    state = RunStateStore(tmp_path / "state.json", manifest)
    state.create()
    state.transition(RunState.READY)
    state.transition(RunState.RUNNING_UNEXPOSED)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw = RawRecordWriter(tmp_path / "raw.jsonl")
    implementation = RawImplementationProvenance(
        production_git_sha=manifest.implementation_sha,
        source_artifact_checksums=dict(manifest.implementation_artifacts),
        policy_version=manifest.policy_version,
        authorization_spec_version=manifest.authorization_spec_version,
        task_contract_schema_version=manifest.task_contract_schema_version,
        runner_git_sha=manifest.runner_sha,
        runner_version=manifest.runner_version,
    )
    runner = CanonicalAuthorizationRunner(
        manifest=manifest,
        implementation=implementation,
        state=state,
        ledger=ledger,
        raw_writer=raw,
        implementation_sha_provider=lambda: manifest.implementation_sha,
        purpose="DEV_EXECUTION",
    )
    runner.execute_scenario(item)
    raw_manifest = tmp_path / "raw_manifest.json"
    runner.seal_raw(raw_manifest_path=raw_manifest, run_metadata_path=metadata)

    labels = tmp_path / "labels.json"
    pairs = tmp_path / "pairs.json"
    groups = tmp_path / "groups.json"
    labels.write_text(
        json.dumps(
            [
                {
                    "scenario_id": item.scenario_id,
                    "expected_decision": "ALLOW",
                    "tool_class": "FILESYSTEM",
                    "difficulty": "EASY",
                    "challenge_class": "HARD_BENIGN",
                    "pressure_dimension": "CAPABILITY_MATCH",
                    "tags": [],
                    "compound_class": None,
                    "presentation": None,
                    "pair_quality": None,
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pairs.write_text("[]\n", encoding="utf-8")
    groups.write_text("[]\n", encoding="utf-8")
    return manifest, state, ledger, raw, raw_manifest, metadata, labels, pairs, groups


def test_fresh_scoring_process_consumes_only_sealed_raw(tmp_path: Path) -> None:
    manifest, state, ledger, raw, seal, metadata, labels, pairs, groups = _sealed_dev_run(
        tmp_path
    )
    summary = tmp_path / "summary.json"
    independent = tmp_path / "independent.json"
    scoring_manifest = tmp_path / "scoring_manifest.json"
    command = [
        sys.executable,
        "scripts/score_auth_coverage_002.py",
        "--manifest",
        str(metadata),
        "--state",
        str(state.path),
        "--ledger",
        str(ledger.path),
        "--raw",
        str(raw.path),
        "--raw-manifest",
        str(seal),
        "--run-metadata",
        str(metadata),
        "--labels",
        str(labels),
        "--pairs",
        str(pairs),
        "--cross-tool-groups",
        str(groups),
        "--summary",
        str(summary),
        "--independent",
        str(independent),
        "--scoring-manifest",
        str(scoring_manifest),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert RunStateStore(state.path, manifest).load().state is RunState.COMPLETE
    scoring = json.loads(scoring_manifest.read_text(encoding="utf-8"))
    assert scoring["raw_package_digest"] == sha256_file(raw.path)
    assert scoring["pair_registry_digest"] == sha256_file(pairs)
    assert json.loads(independent.read_text(encoding="utf-8"))["analysis_package_digest"]


class ScoringCrash(BaseException):
    pass


def test_scoring_crash_cannot_restart_and_becomes_invalid(tmp_path: Path) -> None:
    manifest, state, ledger, raw, seal, metadata, labels, pairs, groups = _sealed_dev_run(
        tmp_path
    )
    arguments = {
        "state": state,
        "raw_path": raw.path,
        "raw_manifest_path": seal,
        "ledger": ledger,
        "run_metadata_path": metadata,
        "labels_path": labels,
        "pairs_path": pairs,
        "cross_tool_groups_path": groups,
        "summary_path": tmp_path / "summary.json",
        "independent_path": tmp_path / "independent.json",
        "scoring_manifest_path": tmp_path / "scoring_manifest.json",
    }

    def crash(point: str) -> None:
        if point == "DURING_SCORING":
            raise ScoringCrash

    with pytest.raises(ScoringCrash):
        score_sealed_run(**arguments, crash_hook=crash)
    assert state.load().state is RunState.SCORING
    with pytest.raises(ScoringIsolationError, match="silently restarted"):
        score_sealed_run(**arguments)
    assert state.load().state is RunState.INVALID


def test_scoring_rejects_run_metadata_and_seal_checksum_substitution(
    tmp_path: Path,
) -> None:
    _, state, ledger, raw, seal, metadata, labels, pairs, groups = _sealed_dev_run(
        tmp_path
    )
    metadata_value = json.loads(metadata.read_text(encoding="utf-8"))
    metadata_value["environment"] = [["platform", "substituted"]]
    metadata.write_bytes(canonical_json(metadata_value) + b"\n")
    seal_value = json.loads(seal.read_text(encoding="utf-8"))
    seal_value["run_metadata_checksum"] = sha256_file(metadata)
    seal.write_bytes(canonical_json(seal_value) + b"\n")

    with pytest.raises(ScoringIsolationError, match="seal verification"):
        score_sealed_run(
            state=state,
            raw_path=raw.path,
            raw_manifest_path=seal,
            ledger=ledger,
            run_metadata_path=metadata,
            labels_path=labels,
            pairs_path=pairs,
            cross_tool_groups_path=groups,
            summary_path=tmp_path / "summary.json",
            independent_path=tmp_path / "independent.json",
            scoring_manifest_path=tmp_path / "scoring_manifest.json",
        )


def test_analysis_module_has_no_production_authorizer_entry_point() -> None:
    probe = """
import safetybox.research.auth_coverage_scoring as scoring
assert 'TaskContractPolicy' not in scoring.__dict__
assert 'authorize' not in scoring.__dict__
"""
    subprocess.run([sys.executable, "-c", probe], check=True)
