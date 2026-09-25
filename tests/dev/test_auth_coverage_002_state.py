from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from safetybox.research.auth_coverage_state import (
    LEGAL_TRANSITIONS,
    InvalidTransition,
    ManifestMismatch,
    RunManifest,
    RunState,
    RunStateStore,
    sha256_file,
)


def manifest(tmp_path: Path) -> RunManifest:
    runtime = tmp_path / "dev-runtime.json"
    scenarios = tmp_path / "dev-scenarios.json"
    corpus = tmp_path / "dev-manifest.json"
    source = tmp_path / "dev-policy.py"
    scenarios.write_text("[]\n", encoding="utf-8")
    binding = {
        "corpus_id": "AUTH-COVERAGE-002-DEV-FIXTURES@1",
        "split": "DEV",
        "scenario_ids": ["dev-random-id-one", "dev-random-id-two"],
        "scenario_input_digests": {
            "dev-random-id-one": "d" * 64,
            "dev-random-id-two": "e" * 64,
        },
        "runtime_scenarios_checksum": sha256_file(scenarios),
    }
    runtime.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    corpus.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    source.write_text("# synthetic development artifact\n", encoding="utf-8")
    return RunManifest(
        experiment_id="AUTH-COVERAGE-002-DEV",
        protocol_id="AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1",
        corpus_id="AUTH-COVERAGE-002-DEV-FIXTURES@1",
        split="DEV",
        run_id="dev-run",
        production_component="TaskContractPolicy.authorize",
        exposure_ledger_path=str(tmp_path / "exposure-ledger.jsonl"),
        runtime_package_path=str(runtime),
        runtime_package_checksum=sha256_file(runtime),
        runtime_scenarios_path=str(scenarios),
        runtime_scenarios_checksum=sha256_file(scenarios),
        corpus_manifest_path=str(corpus),
        corpus_manifest_checksum=sha256_file(corpus),
        implementation_sha="a" * 40,
        implementation_artifacts=((str(source), sha256_file(source)),),
        policy_version="TASK-CONTRACT-POLICY@1",
        authorization_spec_version="AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1",
        task_contract_schema_version="TASK-CONTRACT@1",
        runner_version="AUTH-COVERAGE-002-RUNNER@1",
        runner_sha="b" * 64,
        raw_schema_version="AUTH-COVERAGE-002-RAW-SCHEMA@1",
        ledger_version="AUTH-COVERAGE-EXPOSURE-LEDGER@1",
        scenario_count=2,
        scenario_order=("dev-random-id-one", "dev-random-id-two"),
        scenario_input_digests=(
            ("dev-random-id-one", "d" * 64),
            ("dev-random-id-two", "e" * 64),
        ),
    )


def test_manifest_binds_implementation_and_corpus(tmp_path: Path) -> None:
    run_manifest = manifest(tmp_path)
    run_manifest.verify_bound_files(implementation_sha="a" * 40)
    with pytest.raises(ManifestMismatch, match="implementation SHA"):
        run_manifest.verify_bound_files(implementation_sha="c" * 40)

    Path(run_manifest.corpus_manifest_path).write_text('{"changed":true}\n', encoding="utf-8")
    with pytest.raises(ManifestMismatch, match="corpus manifest"):
        run_manifest.verify_bound_files(implementation_sha="a" * 40)


def test_manifest_rejects_duplicate_order_and_parallelism(tmp_path: Path) -> None:
    run_manifest = manifest(tmp_path)
    with pytest.raises(ValueError, match="duplicates"):
        replace(run_manifest, scenario_order=("same", "same"))
    with pytest.raises(ValueError, match="SEQUENTIAL"):
        replace(run_manifest, concurrency_policy="PARALLEL")
    with pytest.raises(ValueError, match="environment"):
        replace(run_manifest, environment=(("expected_decision", "ALLOW"),))
    with pytest.raises(ValueError, match="protocol identity"):
        replace(run_manifest, protocol_id="OTHER-PROTOCOL@1")
    with pytest.raises(ValueError, match="production component"):
        replace(run_manifest, production_component="OtherPolicy.authorize")


def test_canonical_happy_path_and_seal_boundaries(tmp_path: Path) -> None:
    run_manifest = manifest(tmp_path)
    store = RunStateStore(tmp_path / "state.json", run_manifest)
    assert store.create().state is RunState.CREATED
    store.transition(RunState.READY)
    store.transition(RunState.RUNNING_UNEXPOSED)
    store.mark_call_boundary("dev-random-id-one")
    store.transition(RunState.COMPLETED_RAW)
    store.transition(RunState.SEALED_RAW)
    store.require_scoring_allowed()
    with pytest.raises(InvalidTransition, match="additional"):
        store.require_prediction_allowed()
    store.transition(RunState.SCORING)
    assert store.transition(RunState.COMPLETE).state is RunState.COMPLETE


def test_partial_after_prediction_is_terminal_and_cannot_restart(tmp_path: Path) -> None:
    store = RunStateStore(tmp_path / "state.json", manifest(tmp_path))
    store.create()
    store.transition(RunState.READY)
    store.transition(RunState.RUNNING_UNEXPOSED)
    store.mark_call_boundary("dev-random-id-one")
    partial = store.mark_partial("dev-random-id-one", "injected raw persistence failure")
    assert partial.first_prediction_observed
    with pytest.raises(InvalidTransition):
        store.transition(RunState.RUNNING_EXPOSED)


def test_every_unregistered_transition_fails_without_mutation(tmp_path: Path) -> None:
    run_manifest = manifest(tmp_path)
    for source in RunState:
        for target in RunState:
            if target in LEGAL_TRANSITIONS[source]:
                continue
            state_path = tmp_path / f"{source}-{target}.json"
            store = RunStateStore(state_path, run_manifest)
            store.create()
            # Put a synthetic snapshot in each source state to exercise the complete matrix.
            initial = store.load()
            store._write(  # noqa: SLF001 - exhaustive state-machine test seam
                replace(
                    initial,
                    state=source,
                    first_prediction_observed=source
                    in {
                        RunState.RUNNING_EXPOSED,
                        RunState.COMPLETED_RAW,
                        RunState.SEALED_RAW,
                        RunState.SCORING,
                        RunState.COMPLETE,
                        RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE,
                    },
                )
            )
            before = state_path.read_bytes()
            with pytest.raises(InvalidTransition):
                store.transition(target)
            assert state_path.read_bytes() == before


def test_scoring_before_seal_and_prediction_after_abort_are_blocked(tmp_path: Path) -> None:
    store = RunStateStore(tmp_path / "state.json", manifest(tmp_path))
    store.create()
    with pytest.raises(InvalidTransition, match="SEALED_RAW"):
        store.require_scoring_allowed()
    store.transition(RunState.ABORTED_BEFORE_PREDICTION)
    with pytest.raises(InvalidTransition, match="additional"):
        store.require_prediction_allowed()
