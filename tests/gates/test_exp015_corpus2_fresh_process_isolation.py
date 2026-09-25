"""Non-frozen gate proving Corpus@2 materialization import isolation."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
GATE = ROOT / "scripts/check_exp015_corpus2_import_isolation.py"


def test_exp015_corpus2_integrity_and_import_isolation_in_fresh_process() -> None:
    result = subprocess.run(
        (sys.executable, str(GATE)),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "fresh-process import isolation: PASS" in result.stdout


def test_exp015_corpus2_fresh_process_gate_detects_prohibited_import() -> None:
    result = subprocess.run(
        (sys.executable, str(GATE), "--negative-proof"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "negative proof: PASS" in result.stdout
