"""Schema proofs only: this module must never invoke ProcessAdapter."""

from __future__ import annotations

import ast
import inspect
import subprocess
import time
from pathlib import Path

import pytest

from safetybox.experiments.exp015_corpus2_schema import (
    CapabilitySpec,
    CwdFixture,
    CwdKind,
    ExecutableFixture,
    ExecutableKind,
    FaultInjection,
    FaultMode,
    FaultStage,
    HelperBehavior,
    Observations,
    ProcessRequestSpec,
    Route,
    RuntimeScenario,
    SchemaError,
    TaskContractSpec,
    materialize,
    normalized_state,
)
from safetybox.experiments.exp015_corpus2_scoring import (
    PairRecord,
    PairStrength,
    ScoringLabel,
    derive_manifest,
)


def proof(
    executable: ExecutableFixture | None = None,
    cwd: CwdFixture | None = None,
    *,
    identifier: str = "SCHEMA-PROOF-OPAQUE-A",
    route: Route = Route.ADAPTER,
    fault: FaultInjection | None = None,
) -> RuntimeScenario:
    return RuntimeScenario(
        scenario_id=identifier,
        request=ProcessRequestSpec(
            "proof-session",
            "proof-task",
            "proof-request",
            "proof-actor",
            "/controlled/bin/tool",
            ("arg",),
            "/workspace/cwd",
            200,
        ),
        task_contract=TaskContractSpec(
            "proof-task",
            (
                CapabilitySpec("process.exec", "/controlled/bin/tool"),
                CapabilitySpec("process.cwd", "/workspace/cwd"),
            ),
        ),
        route=route,
        executable=executable
        or ExecutableFixture(
            ExecutableKind.REGULAR_EXECUTABLE,
            "/controlled/bin/tool",
            helper=HelperBehavior.EMIT_STDOUT,
        ),
        cwd=cwd or CwdFixture(CwdKind.DIRECTORY, "/workspace/cwd"),
        parent_environment={"CORPUS_SENTINEL_X": "value"},
        observations=Observations(
            marker_paths=("/workspace/marker",), channels=("stdout", "spawn")
        ),
        fault_injection=fault,
    )


@pytest.mark.parametrize("kind", list(ExecutableKind))
def test_schema_proof_materializes_every_executable_fixture(
    kind: ExecutableKind, tmp_path: Path
) -> None:
    kwargs: dict[str, object] = {}
    if kind is ExecutableKind.SYMLINK:
        kwargs["symlink_target"] = "real-tool"
    elif kind not in {ExecutableKind.MISSING, ExecutableKind.DIRECTORY}:
        kwargs["content_utf8"] = "fixture"
    item = materialize(proof(ExecutableFixture(kind, "/controlled/bin/tool", **kwargs)), tmp_path)
    state = normalized_state(item)["executable"]
    assert state["type"] == (
        "MISSING"
        if kind is ExecutableKind.MISSING
        else "SYMLINK"
        if kind is ExecutableKind.SYMLINK
        else "DIRECTORY"
        if kind is ExecutableKind.DIRECTORY
        else "REGULAR"
    )
    if kind is ExecutableKind.NON_EXECUTABLE_REGULAR:
        assert int(state["mode"]) & 0o111 == 0


@pytest.mark.parametrize("kind", list(CwdKind))
def test_schema_proof_materializes_every_cwd_fixture(kind: CwdKind, tmp_path: Path) -> None:
    kwargs = (
        {"symlink_target": "target"}
        if kind is CwdKind.SYMLINK
        else {"content_utf8": "not-directory"}
        if kind is CwdKind.NON_DIRECTORY
        else {}
    )
    item = materialize(proof(cwd=CwdFixture(kind, "/workspace/cwd", **kwargs)), tmp_path)
    state = normalized_state(item)["cwd"]
    assert state["type"] == (
        "MISSING"
        if kind is CwdKind.MISSING
        else "SYMLINK"
        if kind is CwdKind.SYMLINK
        else "REGULAR"
        if kind is CwdKind.NON_DIRECTORY
        else "DIRECTORY"
    )


@pytest.mark.parametrize("behavior", list(HelperBehavior))
def test_every_helper_behavior_is_self_contained(behavior: HelperBehavior, tmp_path: Path) -> None:
    item = materialize(
        proof(
            ExecutableFixture(
                ExecutableKind.REGULAR_EXECUTABLE,
                "/controlled/bin/tool",
                helper=behavior,
                helper_parameters={
                    "marker_path": "/tmp/proof-marker",
                    "code": 17,
                    "duration_ms": 1,
                },
            )
        ),
        tmp_path,
    )
    assert "behavior" in str(normalized_state(item)["executable"])


@pytest.mark.parametrize(
    ("behavior", "parameters", "returncode"),
    [
        (HelperBehavior.EXIT_CODE, {"code": 17}, 17),
        (HelperBehavior.SELF_SIGNAL, {"signal": 15}, -15),
        (HelperBehavior.SLEEP, {"duration_ms": 20}, 0),
    ],
)
def test_selected_helper_behaviors_run_directly_not_through_adapter(
    behavior: HelperBehavior,
    parameters: dict[str, int],
    returncode: int,
    tmp_path: Path,
) -> None:
    item = materialize(
        proof(
            ExecutableFixture(
                ExecutableKind.REGULAR_EXECUTABLE,
                "/controlled/bin/tool",
                helper=behavior,
                helper_parameters=parameters,
            )
        ),
        tmp_path,
    )
    started = time.monotonic()
    completed = subprocess.run((str(item.executable_host_path),), check=False, capture_output=True)
    assert completed.returncode == returncode
    if behavior is HelperBehavior.SLEEP:
        assert time.monotonic() - started >= 0.015


@pytest.mark.parametrize("stage", list(FaultStage))
@pytest.mark.parametrize("mode", list(FaultMode))
def test_fault_configuration_is_runtime_data(
    stage: FaultStage, mode: FaultMode, tmp_path: Path
) -> None:
    item = materialize(proof(fault=FaultInjection(stage, mode, {"token": "proof"})), tmp_path)
    assert normalized_state(item)["fault"] == {
        "stage": stage.value,
        "mode": mode.value,
        "parameters": {"token": "proof"},
    }


def test_determinism_and_opaque_identifier_independence(tmp_path: Path) -> None:
    first = normalized_state(materialize(proof(identifier="SCHEMA-PROOF-A"), tmp_path / "one"))
    second = normalized_state(materialize(proof(identifier="SCHEMA-PROOF-B"), tmp_path / "two"))
    assert first == second


def test_label_pair_and_manifest_independence(tmp_path: Path) -> None:
    """Scoring-side mutations cannot reach a materializer API with scenario-only input."""

    label = ScoringLabel(
        "SCHEMA-PROOF-OPAQUE-A",
        "ALLOW",
        "ALLOW",
        "ALLOW",
        "SUCCEEDED",
        "PROCESS_EXIT_0",
        "YES",
        "PRESERVED",
        "MINIMAL",
        "COMPLETE",
        "NONE",
        "HARD_BENIGN",
        "EDGE_CASE",
        (),
        (),
    )
    pairs = (
        PairRecord(
            "PAIR-PROOF", label.scenario_id, "other", "EXEC_CAPABILITY", PairStrength.STRONG
        ),
    )
    summary = derive_manifest((label,), pairs)
    before = normalized_state(materialize(proof(), tmp_path / "one"))
    del label, pairs, summary
    after = normalized_state(materialize(proof(), tmp_path / "two"))
    assert before == after


def test_route_and_observations_are_explicit_runtime_configuration(tmp_path: Path) -> None:
    item = materialize(proof(route=Route.DIRECT_CONTROL), tmp_path)
    assert item.route is Route.DIRECT_CONTROL
    assert item.observations.channels == ("stdout", "spawn")


def test_schema_rejects_missing_runtime_facts(tmp_path: Path) -> None:
    scenario = proof(ExecutableFixture(ExecutableKind.SYMLINK, "/controlled/bin/tool"))
    with pytest.raises(SchemaError, match="symlink_target"):
        materialize(scenario, tmp_path)


def test_materializer_has_no_adapter_label_pair_or_id_dispatch_imports() -> None:
    source = inspect.getsource(
        __import__("safetybox.experiments.exp015_corpus2_schema", fromlist=["*"])
    )
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = ("adapter", "labels", "scoring", "pair", "canonicalization", "validation")
    assert not any(part in name.lower() for name in imported for part in forbidden)
    assert "scenario_id ==" not in source and "match scenario_id" not in source
    assert "ProcessAdapter" not in source


def test_runtime_schema_has_no_outcome_field_names() -> None:
    fields = (
        set(RuntimeScenario.__dataclass_fields__)
        | set(ExecutableFixture.__dataclass_fields__)
        | set(CwdFixture.__dataclass_fields__)
        | set(Observations.__dataclass_fields__)
    )
    forbidden = (
        "allow",
        "deny",
        "expected",
        "success",
        "failure_result",
        "should_spawn",
        "hard_benign",
        "hard_unauthorized",
    )
    assert not any(word in field.lower() for field in fields for word in forbidden)


def test_manifest_counts_are_mechanical() -> None:
    labels = (
        ScoringLabel(
            "a",
            "ALLOW",
            "ALLOW",
            "ALLOW",
            "SUCCEEDED",
            "PROCESS_EXIT_0",
            "YES",
            "OK",
            "OK",
            "OK",
            "NONE",
            "HARD_BENIGN",
            "EDGE_CASE",
            (),
            (),
        ),
        ScoringLabel(
            "b",
            "DENY",
            "ALLOW",
            "DENY",
            "REJECTED",
            "FAIL_CLOSED",
            "NO",
            "OK",
            "OK",
            "OK",
            "NONE",
            "HARD_UNAUTHORIZED",
            "HARD_UNAUTHORIZED",
            (),
            (),
        ),
    )
    summary = derive_manifest(
        labels, (PairRecord("p", "a", "b", "EXEC_CAPABILITY", PairStrength.STRONG),)
    )
    assert summary["scenario_count"] == 2
    assert summary["authorization_positive"] == summary["authorization_negative"] == 1
    assert summary["pair_count"] == summary["strong_pair_count"] == 1
