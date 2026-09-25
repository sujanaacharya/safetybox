#!/usr/bin/env python3
"""Fresh-interpreter import boundary gate for ``EXP-015-CORPUS@2``.

This is deliberately outside the checksum-covered Corpus@2 artifact.  It runs
the frozen offline integrity/materialization path in a new Python interpreter,
then checks that the import contract held in that interpreter.  It never
creates an executor or a ``ProcessAdapter``.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
# These are the runtime modules named by the frozen v2 materialization contract.
# The scoring module owns the Corpus@2 labels and pair registry; there is no
# separate runtime pair-registry module in this repository.
PROHIBITED_MODULE_PREFIXES = (
    "safetybox.process",
    "safetybox.authorization",
    "safetybox.experiments.exp015_corpus2_scoring",
)

_CHILD = r'''
import os
import runpy
import sys
from pathlib import Path

root = Path(os.environ["EXP015_ISOLATION_REPOSITORY_ROOT"])
prohibited = tuple(os.environ["EXP015_ISOLATION_PROHIBITED_PREFIXES"].split("\x1f"))

if os.environ.get("EXP015_ISOLATION_NEGATIVE_PROOF") == "1":
    import safetybox.process.adapter  # deliberate development-only contamination

def violations():
    return sorted(
        name for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".") for prefix in prohibited)
    )

before = violations()
if before:
    raise SystemExit(
        "EXP-015 Corpus@2 import isolation violation before gate: " + ", ".join(before)
    )

runpy.run_path(root / "experiments/EXP-015/corpus2/integrity_check.py", run_name="__main__")

after = violations()
if after:
    raise SystemExit("EXP-015 Corpus@2 import isolation violation after gate: " + ", ".join(after))

print("EXP-015 Corpus@2 fresh-process import isolation: PASS")
'''


def run_child(*, negative_proof: bool) -> subprocess.CompletedProcess[str]:
    """Run the frozen offline gate in an interpreter with no inherited modules."""
    environment = os.environ.copy()
    environment["EXP015_ISOLATION_REPOSITORY_ROOT"] = str(REPOSITORY_ROOT)
    environment["EXP015_ISOLATION_PROHIBITED_PREFIXES"] = "\x1f".join(
        PROHIBITED_MODULE_PREFIXES
    )
    if negative_proof:
        environment["EXP015_ISOLATION_NEGATIVE_PROOF"] = "1"
    else:
        environment.pop("EXP015_ISOLATION_NEGATIVE_PROOF", None)
    return subprocess.run(
        (sys.executable, "-c", _CHILD),
        cwd=REPOSITORY_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--negative-proof",
        action="store_true",
        help="prove detection using a deliberately contaminated disposable child process",
    )
    arguments = parser.parse_args()
    result = run_child(negative_proof=arguments.negative_proof)
    if arguments.negative_proof:
        if result.returncode == 0 or "import isolation violation before gate" not in result.stderr:
            raise SystemExit(
                "negative proof failed: deliberate prohibited import was not detected\n"
                + result.stdout
                + result.stderr
            )
        print("EXP-015 Corpus@2 fresh-process import isolation negative proof: PASS")
        return
    if result.returncode:
        raise SystemExit(result.stdout + result.stderr)
    print(result.stdout, end="")


if __name__ == "__main__":
    main()
