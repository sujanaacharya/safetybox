from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from safetybox.research.auth_coverage_isolation import IsolationViolation, RuntimeOnlyPackage


def test_runtime_package_rejects_label_artifact_and_analysis_key(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "labels.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(IsolationViolation, match="analysis artifact"):
        RuntimeOnlyPackage(runtime).validate()
    (runtime / "labels.json").unlink()
    (runtime / "scenarios.json").write_text(
        json.dumps({"scenario_id": "opaque", "expected_decision": "ALLOW"}),
        encoding="utf-8",
    )
    with pytest.raises(IsolationViolation, match="analysis keys"):
        RuntimeOnlyPackage(runtime).validate()


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("Labels.json", "{}\n"),
        ("answers.JSON", '{"Expected_Decision":"ALLOW"}\n'),
        ("scenarios.json", '{"family_label":"pressure"}\n'),
        ("scenarios.json", '{"split_derivation_logic":"secret"}\n'),
    ],
)
def test_runtime_package_rejects_case_and_key_aliases(
    tmp_path: Path, name: str, payload: str
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / name).write_text(payload, encoding="utf-8")
    with pytest.raises(IsolationViolation):
        RuntimeOnlyPackage(runtime).validate()


def test_runtime_package_requires_exact_frozen_inventory(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    scenarios = runtime / "scenarios.json"
    scenarios.write_text("[]\n", encoding="utf-8")
    (runtime / "answer_key.bin").write_bytes(b"ALLOW")
    with pytest.raises(IsolationViolation, match="inventory"):
        RuntimeOnlyPackage(runtime).validate_exact((scenarios,))

def test_runtime_package_confines_ordinary_file_access(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "scenarios.json").write_text("[]\n", encoding="utf-8")
    labels = tmp_path / "analysis" / "labels.json"
    labels.parent.mkdir()
    labels.write_text("{}\n", encoding="utf-8")
    package = RuntimeOnlyPackage(runtime)
    assert package.validate() == (runtime / "scenarios.json",)
    with pytest.raises(IsolationViolation, match="outside"):
        package.open_binary("../analysis/labels.json")


def test_fresh_process_gate_blocks_scoring_import_and_label_file_is_absent(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "heldout-runtime"
    runtime.mkdir()
    (runtime / "scenarios.json").write_text("[]\n", encoding="utf-8")
    probe = """
import json
import sys
from pathlib import Path
from safetybox.research.auth_coverage_isolation import (
    IsolationViolation, RuntimeOnlyPackage, install_import_gate,
)
root = Path(sys.argv[1])
RuntimeOnlyPackage(root).validate()
install_import_gate()
blocked = False
try:
    __import__('safetybox.research.auth_coverage_metrics')
except IsolationViolation:
    blocked = True
label_absent = False
try:
    RuntimeOnlyPackage(root).open_binary('labels.json')
except FileNotFoundError:
    label_absent = True
print(json.dumps({'import_blocked': blocked, 'label_absent': label_absent}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe, str(runtime)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {"import_blocked": True, "label_absent": True}


def test_fresh_process_ordinary_open_cannot_read_adjacent_labels(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    output = tmp_path / "output"
    analysis = tmp_path / "analysis"
    runtime.mkdir()
    (runtime / "scenarios.json").write_text("[]\n", encoding="utf-8")
    output.mkdir()
    governance = tmp_path / "governance"
    governance.mkdir()
    ledger = governance / "ledger.jsonl"
    analysis.mkdir()
    labels = governance / "labels.json"
    labels.write_text('{"expected_decision":"ALLOW"}\n', encoding="utf-8")
    probe = """
import sys
from pathlib import Path
from safetybox.research.auth_coverage_isolation import (
    IsolationViolation, install_file_access_gate,
)
install_file_access_gate(
    runtime_files=(Path(sys.argv[1]) / 'scenarios.json',), output_root=Path(sys.argv[2]),
    governance_files=(Path(sys.argv[3]),), implementation_files=(),
)
try:
    Path(sys.argv[4]).read_text()
except IsolationViolation:
    print('BLOCKED')
else:
    raise SystemExit('ordinary file access reached labels')
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            probe,
            str(runtime),
            str(output),
            str(ledger),
            str(labels),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "BLOCKED"
