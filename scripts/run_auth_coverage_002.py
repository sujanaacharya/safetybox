#!/usr/bin/env python3
"""Fresh-process canonical execution entry point for AUTH-COVERAGE-002."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from safetybox.research.auth_coverage_isolation import (
    RuntimeOnlyPackage,
    install_file_access_gate,
    install_import_gate,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--implementation-sha", required=True)
    parser.add_argument("--dev-rehearsal", action="store_true")
    args = parser.parse_args()

    runtime_root = args.manifest.resolve().parent
    RuntimeOnlyPackage(runtime_root).validate()
    os.environ["SAFETYBOX_CANONICAL_EXECUTION_PROCESS"] = "1"
    install_import_gate()

    # Imports after the gate are execution-only.  Scoring/oracle namespaces are
    # unavailable in this interpreter.
    from safetybox.research.auth_coverage_raw import (
        RawImplementationProvenance,
        canonical_sha256,
        capture_authorization_input,
    )
    from safetybox.research.auth_coverage_runner import (
        CanonicalAuthorizationRunner,
        RawRecordWriter,
        runtime_scenario_from_mapping,
    )
    from safetybox.research.auth_coverage_state import (
        RunManifest,
        RunState,
        RunStateStore,
        sha256_file,
    )
    from safetybox.research.exposure_ledger import ExposureLedger

    manifest_value = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest_value, dict):
        raise SystemExit("run manifest must be a JSON object")
    manifest = RunManifest.from_dict(manifest_value)
    runtime_files = (
        args.manifest,
        Path(manifest.runtime_package_path),
        Path(manifest.runtime_scenarios_path),
        Path(manifest.corpus_manifest_path),
    )
    RuntimeOnlyPackage(runtime_root).validate_exact(runtime_files)
    if manifest.split == "HELD_OUT":
        purpose = "CANONICAL_RUN"
    elif manifest.split == "DEV" and args.dev_rehearsal:
        purpose = "DEV_EXECUTION"
    else:
        raise SystemExit("entry point requires HELD_OUT or explicit DEV rehearsal")
    if args.state.exists() or args.raw.exists() or args.raw_manifest.exists():
        raise SystemExit("canonical execution outputs must not preexist")
    manifest.verify_bound_files(implementation_sha=args.implementation_sha)
    if args.scenarios.resolve() != Path(manifest.runtime_scenarios_path).resolve():
        raise SystemExit("scenario file is not the one bound by the run manifest")

    scenarios_value = json.loads(args.scenarios.read_text(encoding="utf-8"))
    if not isinstance(scenarios_value, list):
        raise SystemExit("runtime scenarios must be a JSON array")
    scenarios = tuple(
        runtime_scenario_from_mapping(value)
        for value in scenarios_value
    )
    identifiers = tuple(item.scenario_id for item in scenarios)
    digests = tuple(
        (
            item.scenario_id,
            canonical_sha256(
                capture_authorization_input(
                    tool_class=item.tool_class,
                    contract_task_id=item.contract_task_id,
                    contract_description=item.contract_description,
                    received_capabilities=item.capabilities,
                    primary_request=item.request,
                    additional_components=item.additional_components,
                )
            ),
        )
        for item in scenarios
    )
    if identifiers != manifest.scenario_order or digests != manifest.scenario_input_digests:
        raise SystemExit("complete scenario package differs from frozen order/input digests")

    if args.ledger.resolve() != Path(manifest.exposure_ledger_path).resolve():
        raise SystemExit("ledger path differs from the persistent frozen governance path")
    output_paths = (args.state, args.raw, args.raw_manifest)
    output_parents = {path.resolve().parent for path in output_paths}
    if len(output_parents) != 1:
        raise SystemExit("canonical outputs must share one isolated result directory")
    output_root = output_parents.pop()
    if output_root == runtime_root or not output_root.is_dir() or any(output_root.iterdir()):
        raise SystemExit("canonical result directory must be separate, existing, and empty")
    governance_root = args.ledger.resolve().parent
    if governance_root in {runtime_root, output_root} or not governance_root.is_dir():
        raise SystemExit("ledger requires a separate persistent governance directory")
    allowed_governance_names = {
        args.ledger.name,
        f"{args.ledger.name}.anchor.json",
    }
    if any(path.name not in allowed_governance_names for path in governance_root.iterdir()):
        raise SystemExit("governance directory contains an unexpected artifact")

    if manifest.split == "HELD_OUT":
        repository = Path(__file__).resolve().parents[1]
        measured_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if measured_head != args.implementation_sha or measured_head != manifest.implementation_sha:
            raise SystemExit("measured production Git SHA differs from frozen manifest")
        runner_sources = (
            repository / "scripts/run_auth_coverage_002.py",
            repository / "src/safetybox/research/auth_coverage_runner.py",
            repository / "src/safetybox/research/auth_coverage_state.py",
            repository / "src/safetybox/research/auth_coverage_raw.py",
            repository / "src/safetybox/research/exposure_ledger.py",
            repository / "src/safetybox/research/auth_coverage_isolation.py",
        )
        measured_runner = canonical_sha256(
            {str(path.relative_to(repository)): sha256_file(path) for path in runner_sources}
        )
        if measured_runner != manifest.runner_sha:
            raise SystemExit("measured runner source digest differs from frozen manifest")
        required_production = {
            repository / "src/safetybox/policy.py",
            repository / "src/safetybox/capabilities.py",
            repository / "src/safetybox/contracts.py",
            repository / "src/safetybox/models.py",
            repository / "src/safetybox/authorization.py",
            repository / "src/safetybox/protocols.py",
        }
        frozen_production = {
            Path(path).resolve() for path, _ in manifest.implementation_artifacts
        }
        if frozen_production != {path.resolve() for path in required_production}:
            raise SystemExit("production artifact set differs from the frozen required set")

        def implementation_sha_provider() -> str:
            return subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

    else:

        def implementation_sha_provider() -> str:
            return str(args.implementation_sha)

    install_file_access_gate(
        runtime_files=runtime_files,
        output_root=output_root,
        governance_files=(
            args.ledger,
            args.ledger.with_name(f"{args.ledger.name}.anchor.json"),
        ),
        implementation_files=tuple(Path(path) for path, _ in manifest.implementation_artifacts),
    )

    state = RunStateStore(args.state, manifest)
    state.create()
    state.transition(RunState.READY)
    state.transition(RunState.RUNNING_UNEXPOSED)
    implementation = RawImplementationProvenance(
        production_git_sha=manifest.implementation_sha,
        source_artifact_checksums=dict(manifest.implementation_artifacts),
        policy_version=manifest.policy_version,
        task_contract_schema_version=manifest.task_contract_schema_version,
        authorization_spec_version=manifest.authorization_spec_version,
        runner_git_sha=manifest.runner_sha,
        runner_version=manifest.runner_version,
    )
    runner = CanonicalAuthorizationRunner(
        manifest=manifest,
        implementation=implementation,
        state=state,
        ledger=ExposureLedger(args.ledger),
        raw_writer=RawRecordWriter(args.raw),
        implementation_sha_provider=implementation_sha_provider,
        purpose=purpose,
    )
    for scenario in scenarios:
        runner.execute_scenario(scenario)
    runner.seal_raw(raw_manifest_path=args.raw_manifest, run_metadata_path=args.manifest)
if __name__ == "__main__":
    main()
