"""Independent oracle conformance tests with no production matcher imports."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "experiments/AUTH-COVERAGE-002"


def _module(name: str):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, DIRECTORY / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scenario() -> dict[str, object]:
    request = {
        "request_id": "r",
        "session_id": "s",
        "task_id": "task",
        "actor": "a",
        "action": "filesystem.read",
        "resource": "/root/child",
        "arguments": {},
    }
    return {
        "scenario_id": "0" * 64,
        "tool_class": "FILESYSTEM",
        "contract_task_id": "task",
        "contract_description": "test",
        "capabilities": [{"action": "filesystem.read", "resource": "/root/**"}],
        "request": request,
        "additional_components": [],
    }


def test_oracles_do_not_import_production_or_each_other() -> None:
    before = set(sys.modules)
    oracle_a = _module("oracle_a")
    after_a = set(sys.modules) - before
    oracle_b = _module("oracle_b")
    after_b = set(sys.modules) - before
    assert not any(name.startswith("safetybox") for name in after_a | after_b)
    assert oracle_a.ORACLE_ID != oracle_b.ORACLE_ID


def test_oracles_agree_on_scope_task_empty_and_synthesis_boundaries() -> None:
    oracle_a, oracle_b = _module("oracle_a"), _module("oracle_b")
    scenario = _scenario()
    cases: list[tuple[dict[str, object], str]] = [(scenario, "ALLOW")]
    root = _scenario()
    root["request"] = {**root["request"], "resource": "/root"}  # type: ignore[arg-type]
    cases.append((root, "DENY"))
    prefix = _scenario()
    prefix["request"] = {**prefix["request"], "resource": "/rootish/child"}  # type: ignore[arg-type]
    cases.append((prefix, "DENY"))
    task = _scenario()
    task["request"] = {**task["request"], "task_id": "other"}  # type: ignore[arg-type]
    cases.append((task, "DENY"))
    empty = _scenario()
    empty["capabilities"] = []
    cases.append((empty, "DENY"))
    split = _scenario()
    split["capabilities"] = [
        {"action": "filesystem.read", "resource": "/other"},
        {"action": "filesystem.write", "resource": "/root/child"},
    ]
    cases.append((split, "DENY"))
    for value, expected in cases:
        assert oracle_a.evaluate(value) == oracle_b.evaluate(value)
        assert oracle_a.evaluate(value)["decision"] == expected


def test_oracle_b_invalid_structure_fails_closed_under_optimized_python() -> None:
    scenario = _scenario()
    scenario["tool_class"] = "NETWORK"
    code = (
        "import json,sys; import oracle_b; print(oracle_b.evaluate(json.load(sys.stdin))['rule'])"
    )
    completed = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=DIRECTORY,
        input=json.dumps(scenario),
        text=True,
        capture_output=True,
        check=True,
    )
    assert completed.stdout.strip() == "AUTH.INVALID_STRUCTURE"
