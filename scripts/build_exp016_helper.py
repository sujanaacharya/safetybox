"""Reproducibly build and record provenance for the EXP-016 native helper."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from pathlib import Path

from safetybox.experiments.exp016_reachability import inspect_elf, sha256_file

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments" / "EXP-016" / "fixture" / "native_helper.c"
BINARY = ROOT / "experiments" / "EXP-016" / "fixture" / "native-helper"
PROVENANCE = ROOT / "experiments" / "EXP-016" / "fixture" / "build_provenance.json"
COMPILER = Path("/usr/bin/cc")
FLAGS = (
    "-std=c11",
    "-O2",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-fno-ident",
    "-Wl,--build-id=none",
)


def main() -> None:
    environment = dict(os.environ)
    environment["SOURCE_DATE_EPOCH"] = "0"
    subprocess.run(
        (str(COMPILER), *FLAGS, str(SOURCE), "-o", str(BINARY)),
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env=environment,
    )
    BINARY.chmod(0o755)
    compiler_version = subprocess.run(
        (str(COMPILER), "--version"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]
    program_headers = subprocess.run(
        ("/usr/bin/readelf", "-lW", str(BINARY)),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    loader_match = re.search(r"Requesting program interpreter: ([^\]]+)", program_headers)
    loader = None if loader_match is None else loader_match.group(1)
    elf = inspect_elf(BINARY)
    record = {
        "artifact_id": "EXP-016-NATIVE-HELPER@1",
        "binary_path": "experiments/EXP-016/fixture/native-helper",
        "binary_sha256": sha256_file(BINARY),
        "compile_flags": list(FLAGS),
        "compiler_path": str(COMPILER),
        "compiler_version": compiler_version,
        "elf": {
            "architecture_compatible": elf.architecture_compatible,
            "byte_order": elf.byte_order,
            "class_bits": elf.elf_class,
            "host_architecture": platform.machine(),
            "machine": elf.machine,
            "machine_name": elf.machine_name,
            "object_type": elf.object_type,
        },
        "linkage": "DYNAMIC" if loader is not None else "STATIC",
        "required_loader": loader,
        "source_date_epoch": "0",
        "source_path": "experiments/EXP-016/fixture/native_helper.c",
        "source_sha256": sha256_file(SOURCE),
    }
    PROVENANCE.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
