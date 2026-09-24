"""Offline integrity and two-pass materialization gate for EXP-015-CORPUS@2.

Only the frozen structure/materializer module is imported.  This file neither
imports scoring nor loads labels until all fixture-only checks have completed.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from safetybox.experiments.exp015_corpus2_schema_v2 import (
    AdditionalObject, CapabilitySpec, CwdFixture, CwdKind, ExecutableFixture,
    ExecutableKind, FaultInjection, FaultMode, FaultStage, HelperBehavior,
    Observations, ProcessRequestSpec, Route, RuntimeScenario, TaskContractSpec,
    materialize, normalized_state,
)

ROOT = Path(__file__).parent


def decode(raw: dict[str, object]) -> RuntimeScenario:
    request = raw["request"]
    contract = raw["task_contract"]
    executable = raw["executable"]
    cwd = raw["cwd"]
    assert all(isinstance(x, dict) for x in (request, contract, executable, cwd))
    fault_raw = raw["fault_injection"]
    observations = raw["observations"]
    assert isinstance(observations, dict)
    fault = None if fault_raw is None else FaultInjection(FaultStage(fault_raw["stage"]), FaultMode(fault_raw["mode"]), fault_raw["parameters"])
    return RuntimeScenario(
        raw["scenario_id"],
        ProcessRequestSpec(request["session_id"], request["task_id"], request["request_id"], request["actor"], request["executable"], tuple(request["argv"]), request["cwd"], request["timeout_ms"]),
        TaskContractSpec(contract["task_id"], tuple(CapabilitySpec(x["action"], x["resource"]) for x in contract["capabilities"]), contract["description"]),
        Route(raw["route"]),
        ExecutableFixture(ExecutableKind(executable["kind"]), executable["path"], executable.get("mode"), executable.get("content_utf8"), executable.get("symlink_target"), None if executable.get("helper") is None else HelperBehavior(executable["helper"]), executable.get("helper_parameters", {})),
        CwdFixture(CwdKind(cwd["kind"]), cwd["path"], cwd.get("mode"), cwd.get("symlink_target"), cwd.get("content_utf8")),
        tuple(AdditionalObject(x["path"], x["kind"], x.get("mode"), x.get("content_utf8"), x.get("symlink_target")) for x in raw["additional_objects"]),
        raw["parent_environment"], fault,
        Observations(tuple(observations["marker_paths"]), tuple(observations["output_sentinels"]), tuple(observations["environment_keys"]), tuple(observations["channels"])), raw["schema_id"],
    )


def fixture_oracle(item: RuntimeScenario, root: Path) -> None:
    """Inspect materialized filesystem objects, independent of return claims."""
    for fixture in (item.executable, item.cwd):
        host = root.joinpath(*Path(fixture.path).parts[1:])
        if fixture.kind.value == "MISSING":
            assert not os.path.lexists(host)
        elif fixture.kind.value == "SYMLINK":
            assert host.is_symlink() and os.readlink(host) == fixture.symlink_target
        elif fixture.kind.value == "DIRECTORY":
            assert host.is_dir()
        else:
            assert stat.S_ISREG(host.lstat().st_mode)
            if fixture.kind.value == "NON_EXECUTABLE_REGULAR":
                assert not (host.stat().st_mode & stat.S_IXUSR)


def oracle(item: RuntimeScenario) -> tuple[str, str, str]:
    """Independent frozen exact task/action/resource authority computation."""
    pairs = {(cap.action, cap.resource) for cap in item.task_contract.capabilities}
    bound = item.request.task_id == item.task_contract.task_id
    execute = bound and ("process.exec", item.request.executable) in pairs
    cwd = bound and ("process.cwd", item.request.cwd) in pairs
    return ("ALLOW" if execute else "DENY", "ALLOW" if cwd else "DENY", "ALLOW" if execute and cwd else "DENY")


def main() -> None:
    raw_scenarios = json.loads((ROOT / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    scenarios = [decode(item) for item in raw_scenarios]
    assert len(scenarios) == 120 and len({x.scenario_id for x in scenarios}) == 120
    assert "safetybox.process.adapter" not in sys.modules
    first: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="exp015-c2-pass1-") as root:
        root_path = Path(root)
        for scenario in scenarios:
            result = materialize(scenario, root_path / scenario.scenario_id)
            fixture_oracle(scenario, result.root)
            first[scenario.scenario_id] = normalized_state(result)
    with tempfile.TemporaryDirectory(prefix="exp015-c2-pass2-") as root:
        root_path = Path(root)
        for scenario in scenarios:
            result = materialize(scenario, root_path / scenario.scenario_id)
            assert first[scenario.scenario_id] == normalized_state(result)
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))["labels"]
    by_id = {x["scenario_id"]: x for x in labels}
    assert len(by_id) == 120
    for scenario in scenarios:
        expected = by_id[scenario.scenario_id]
        assert oracle(scenario) == (expected["expected_exec_authority"], expected["expected_cwd_authority"], expected["expected_compound_authority"])
    pairs = json.loads((ROOT / "pairs.json").read_text(encoding="utf-8"))["pairs"]
    assert len(pairs) == len({x["pair_id"] for x in pairs}) == 36
    assert sum(x["strength"] == "STRONG" for x in pairs) >= 32
    assert sum(x["difficulty"] == "HARD_BENIGN" for x in labels) >= 36
    assert sum(x["difficulty"] == "HARD_UNAUTHORIZED" for x in labels) >= 36
    assert sum(x["expected_validation"] == "REJECT" for x in labels) >= 16
    assert sum("FAILURE" in x["tags"] for x in labels) >= 12
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    recomputed = {
        "scenario_count": len(scenarios),
        "authorization_positive": sum(x["expected_compound_authority"] == "ALLOW" for x in labels),
        "authorization_negative": sum(x["expected_compound_authority"] == "DENY" for x in labels),
        "hard_benign": sum(x["difficulty"] == "HARD_BENIGN" for x in labels),
        "hard_unauthorized": sum(x["difficulty"] == "HARD_UNAUTHORIZED" for x in labels),
        "validation_case_count": sum(x["expected_validation"] == "REJECT" for x in labels),
        "execution_failure_count": sum("FAILURE" in x["tags"] for x in labels),
        "pair_count": len(pairs),
        "strong_pair_count": sum(x["strength"] == "STRONG" for x in pairs),
    }
    assert {key: manifest[key] for key in recomputed} == recomputed
    frozen_runtime_text = (ROOT / "scenarios.json").read_text(encoding="utf-8")
    assert not any(word in frozen_runtime_text for word in ("expected_", "pair_id", "hard_benign", "ground_truth"))
    corpus_one = (ROOT.parent / "corpus" / "scenarios.json").read_text(encoding="utf-8")
    assert not any(item["scenario_id"] in corpus_one for item in raw_scenarios)
    assert not (Path("results") / "EXP-015").exists()
    print("EXP-015-CORPUS@2 integrity: PASS (120; materialized twice; adapter untouched)")


if __name__ == "__main__":
    main()
