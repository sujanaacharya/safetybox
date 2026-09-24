"""Development/schema proofs for v2; this file never executes ProcessAdapter."""

from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from safetybox.experiments.exp015_corpus2_schema_v2 import (
    MATERIALIZER_ID,
    RUNTIME_SCHEMA_ID,
    CapabilitySpec,
    CwdFixture,
    CwdKind,
    ExecutableFixture,
    ExecutableKind,
    FaultInjection,
    FaultMode,
    FaultStage,
    HelperBehavior,
    ProcessRequestSpec,
    Route,
    RuntimeScenario,
    SchemaError,
    TaskContractSpec,
    materialize,
    normalized_state,
    validate_runtime_scenario,
)


def proof(
    *,
    request_task: str = "task-A",
    contract_task: str = "task-A",
    identifier: str = "DEV-SCHEMA-A",
    capabilities: tuple[CapabilitySpec, ...] | None = None,
    route: Route = Route.ADAPTER,
    executable: ExecutableFixture | None = None,
    cwd: CwdFixture | None = None,
    fault: FaultInjection | None = None,
) -> RuntimeScenario:
    return RuntimeScenario(
        identifier,
        ProcessRequestSpec(
            "session-9",
            request_task,
            "request-9",
            "actor-9",
            "/controlled/bin/tool",
            ("arg",),
            "/workspace/cwd",
            200,
        ),
        TaskContractSpec(
            contract_task,
            capabilities
            if capabilities is not None
            else (
                CapabilitySpec("process.exec", "/controlled/bin/tool"),
                CapabilitySpec("process.cwd", "/workspace/cwd"),
            ),
        ),
        route,
        executable
        or ExecutableFixture(
            ExecutableKind.REGULAR_EXECUTABLE,
            "/controlled/bin/tool",
            helper=HelperBehavior.EMIT_STDOUT,
        ),
        cwd or CwdFixture(CwdKind.DIRECTORY, "/workspace/cwd"),
        fault_injection=fault,
    )


def authority_oracle(item: RuntimeScenario) -> bool:
    """Independent development oracle shape: both IDs remain separate inputs."""
    if item.request.task_id != item.task_contract.task_id:
        return False
    pairs = {(cap.action, cap.resource) for cap in item.task_contract.capabilities}
    return {("process.exec", item.request.executable), ("process.cwd", item.request.cwd)} <= pairs


def test_matched_and_mismatched_task_binding_are_structurally_valid(tmp_path: Path) -> None:
    matched, mismatched = proof(), proof(request_task="task-B")
    validate_runtime_scenario(matched)
    validate_runtime_scenario(mismatched)
    a, b = (
        materialize(matched, tmp_path / "matched"),
        materialize(mismatched, tmp_path / "mismatched"),
    )
    assert a.request.task_id == a.task_contract.task_id == "task-A"
    assert b.request.task_id == "task-B" and b.task_contract.task_id == "task-A"
    assert a.raw_record_provenance()["request_task_id"] == "task-A"
    assert b.raw_record_provenance()["contract_task_id"] == "task-A"
    assert authority_oracle(matched) and not authority_oracle(mismatched)


def test_task_binding_counterfactual_diff_is_request_task_only(tmp_path: Path) -> None:
    positive, negative = proof(), proof(request_task="task-B")
    assert positive.task_contract == negative.task_contract
    assert replace(positive.request, task_id=negative.request.task_id) == negative.request
    assert normalized_state(materialize(positive, tmp_path / "one")) == normalized_state(
        materialize(negative, tmp_path / "two")
    )


@pytest.mark.parametrize(
    "capabilities",
    [
        (),
        (CapabilitySpec("process.cwd", "/workspace/cwd"),),
        (CapabilitySpec("process.exec", "/controlled/bin/tool"),),
        (
            CapabilitySpec("process.exec", "/other/tool"),
            CapabilitySpec("process.cwd", "/workspace/cwd"),
        ),
        (
            CapabilitySpec("process.exec", "/controlled/bin/tool"),
            CapabilitySpec("process.cwd", "/other/cwd"),
        ),
        tuple(CapabilitySpec("other.action", f"/irrelevant/{index}") for index in range(16)),
        (
            CapabilitySpec("process.exec", "/controlled/bin/tool"),
            CapabilitySpec("process.cwd", "/workspace/cwd"),
        ),
    ],
)
def test_structurally_valid_but_unauthorized_capability_and_resource_matrix(
    capabilities: tuple[CapabilitySpec, ...], tmp_path: Path
) -> None:
    scenario = proof(capabilities=capabilities)
    materialize(scenario, tmp_path)
    assert authority_oracle(scenario) is (
        len(capabilities) == 2
        and all(cap.resource in {"/controlled/bin/tool", "/workspace/cwd"} for cap in capabilities)
    )


@pytest.mark.parametrize("kind", list(ExecutableKind))
def test_validation_fixture_representability(kind: ExecutableKind, tmp_path: Path) -> None:
    kwargs: dict[str, object] = {"content_utf8": "fixture"}
    if kind is ExecutableKind.SYMLINK:
        kwargs = {"symlink_target": "real-tool"}
    if kind in {ExecutableKind.MISSING, ExecutableKind.DIRECTORY}:
        kwargs = {}
    materialize(
        proof(executable=ExecutableFixture(kind, "/controlled/bin/tool", **kwargs)), tmp_path
    )


@pytest.mark.parametrize("kind", list(CwdKind))
def test_cwd_validation_fixture_representability(kind: CwdKind, tmp_path: Path) -> None:
    kwargs = (
        {"symlink_target": "target"}
        if kind is CwdKind.SYMLINK
        else {"content_utf8": "file"}
        if kind is CwdKind.NON_DIRECTORY
        else {}
    )
    materialize(proof(cwd=CwdFixture(kind, "/workspace/cwd", **kwargs)), tmp_path)


@pytest.mark.parametrize("behavior", list(HelperBehavior))
@pytest.mark.parametrize("stage", list(FaultStage))
@pytest.mark.parametrize("mode", list(FaultMode))
def test_failure_recipes_are_runtime_data_not_execution(
    behavior: HelperBehavior, stage: FaultStage, mode: FaultMode, tmp_path: Path
) -> None:
    item = materialize(
        proof(
            executable=ExecutableFixture(
                ExecutableKind.REGULAR_EXECUTABLE, "/controlled/bin/tool", helper=behavior
            ),
            fault=FaultInjection(stage, mode),
        ),
        tmp_path,
    )
    assert item.fault_injection == FaultInjection(stage, mode)


@pytest.mark.parametrize("route", list(Route))
def test_both_routes_are_structurally_representable(route: Route, tmp_path: Path) -> None:
    assert materialize(proof(route=route), tmp_path).route is route


@pytest.mark.parametrize(
    "scenario",
    [
        replace(proof(), schema_id="EXP-015-RUNTIME-SCHEMA@1"),
        replace(proof(), request=replace(proof().request, task_id="")),
        replace(proof(), request=replace(proof().request, timeout_ms=True)),
        replace(proof(), request=replace(proof().request, argv=("ok", 1))),  # type: ignore[arg-type]
        replace(proof(), route="INVALID"),  # type: ignore[arg-type]
        replace(proof(), task_contract=TaskContractSpec("task-A", (CapabilitySpec("", "/x"),))),
    ],
)
def test_structurally_invalid_data_is_rejected(scenario: RuntimeScenario) -> None:
    with pytest.raises(SchemaError):
        validate_runtime_scenario(scenario)


def test_determinism_and_scenario_id_independence(tmp_path: Path) -> None:
    first = normalized_state(materialize(proof(identifier="DEV-SCHEMA-A"), tmp_path / "one"))
    second = normalized_state(materialize(proof(identifier="DEV-SCHEMA-B"), tmp_path / "two"))
    third = normalized_state(materialize(proof(), tmp_path / "three"))
    assert first == second == third


def test_materializer_has_no_authority_or_adapter_import_boundary() -> None:
    source = inspect.getsource(
        __import__("safetybox.experiments.exp015_corpus2_schema_v2", fromlist=["*"])
    )
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = (
        "adapter",
        "authorization",
        "labels",
        "scoring",
        "pair",
        "validation",
        "canonicalization",
    )
    assert not any(word in name.lower() for name in imports for word in forbidden)
    assert "safetybox.process" not in source and "task_id !=" not in source
    assert MATERIALIZER_ID in source and RUNTIME_SCHEMA_ID in source


def test_labels_pairs_and_manifest_are_not_runtime_fields() -> None:
    fields = set(RuntimeScenario.__dataclass_fields__)
    assert not {"label", "pair_id", "manifest", "expected", "allow", "deny"} & fields
