#!/usr/bin/env python3
"""Bind frozen runtime scenarios to the frozen raw-first input representation.

This integration step imports only runner/raw schema adapters.  It does not import
labels, analysis metadata, oracles, the generator, or production authorization and
cannot make a prediction.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from safetybox.research.auth_coverage_raw import canonical_sha256, capture_authorization_input
from safetybox.research.auth_coverage_runner import runtime_scenario_from_mapping

ROOT = Path(__file__).resolve().parent / "corpus" / "runtime"
CORPUS_ID = "AUTH-COVERAGE-002-CORPUS@1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    for directory_name, split in (
        ("DEV", "DEV"),
        ("VALIDATION", "VALIDATION"),
        ("HELD_OUT-runtime", "HELD_OUT"),
    ):
        directory = ROOT / directory_name
        scenarios_path = directory / "scenarios.json"
        values = json.loads(scenarios_path.read_text(encoding="utf-8"))
        parsed = [runtime_scenario_from_mapping(value) for value in values]
        digests = {
            item.scenario_id: canonical_sha256(
                capture_authorization_input(
                    tool_class=item.tool_class,
                    contract_task_id=item.contract_task_id,
                    contract_description=item.contract_description,
                    received_capabilities=item.capabilities,
                    primary_request=item.request,
                    additional_components=item.additional_components,
                )
            )
            for item in parsed
        }
        binding = {
            "corpus_id": CORPUS_ID,
            "split": split,
            "scenario_ids": [item.scenario_id for item in parsed],
            "scenario_input_digests": digests,
            "runtime_scenarios_checksum": sha(scenarios_path),
        }
        dump(directory / "corpus_binding.json", binding)
        dump(directory / "runtime_binding.json", binding)
        manifest_path = directory / "package_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["scenario_input_digests"] = digests
        manifest["runner_parse_count"] = len(parsed)
        manifest["raw_input_reconstruction"] = "PASS"
        dump(manifest_path, manifest)


if __name__ == "__main__":
    main()
