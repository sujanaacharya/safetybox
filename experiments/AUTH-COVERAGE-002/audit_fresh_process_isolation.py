#!/usr/bin/env python3
"""Fresh-process held-out package isolation audit; makes no authorization call."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "corpus/runtime/HELD_OUT-runtime"


def main() -> None:
    probe = r"""
import json, sys
from pathlib import Path
from safetybox.research.auth_coverage_isolation import (
    IsolationViolation,
    RuntimeOnlyPackage,
    install_file_access_gate,
    install_import_gate,
)
runtime=Path(sys.argv[1]); experiment=Path(sys.argv[2]); output_root=Path(sys.argv[3])
names=('scenarios.json','corpus_binding.json','runtime_binding.json','package_manifest.json')
files=RuntimeOnlyPackage(runtime).validate_exact(tuple(runtime/name for name in names))
sys.path.insert(0,str(experiment))
install_import_gate()
install_file_access_gate(
    runtime_files=files,
    output_root=output_root,
    governance_files=(),
    implementation_files=(),
)
blocked_imports=[]
for name in ('oracle_a','oracle_b','build_corpus'):
 try: __import__(name)
 except IsolationViolation: blocked_imports.append(name)
blocked_reads=[]
for relative in (
 'corpus/analysis/labels.json','corpus/analysis/pairs.json',
 'corpus/analysis/difficulty.json','corpus/analysis/analysis.json',
 'oracle_a.py','oracle_b.py','build_corpus.py',
):
 try: (experiment/relative).read_text()
 except IsolationViolation: blocked_reads.append(relative)
print(json.dumps({'file_count':len(files),'blocked_imports':blocked_imports,'blocked_reads':blocked_reads,'production_calls':0}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe, str(RUNTIME), str(ROOT), "/tmp"],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    result.update(
        {
            "audit_id": "AUTH-COVERAGE-002-FRESH-PROCESS-ISOLATION@1",
            "result": "PASS"
            if result
            == {
                "file_count": 4,
                "blocked_imports": ["oracle_a", "oracle_b", "build_corpus"],
                "blocked_reads": [
                    "corpus/analysis/labels.json",
                    "corpus/analysis/pairs.json",
                    "corpus/analysis/difficulty.json",
                    "corpus/analysis/analysis.json",
                    "oracle_a.py",
                    "oracle_b.py",
                    "build_corpus.py",
                ],
                "production_calls": 0,
            }
            else "FAIL",
        }
    )
    (ROOT / "corpus/analysis/fresh_process_isolation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
