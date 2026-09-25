"""Analysis-side sealed-raw adapter and scoring process implementation.

This module intentionally imports the metric contract and is therefore denied
by the execution-process import gate.  It has no production authorizer import
and no code path that can create an authorization prediction.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

from safetybox.research.auth_coverage_metrics import (
    canonical_digest,
    independent_recompute_headline,
    score_authorization,
)
from safetybox.research.auth_coverage_raw import (
    RawAuthorizationRecord,
    raw_record_from_json,
)
from safetybox.research.auth_coverage_reconcile import verify_complete_sealed_evidence
from safetybox.research.auth_coverage_state import (
    RunManifest,
    RunState,
    RunStateStore,
    canonical_json,
    exclusive_run_lock,
    sha256_file,
)
from safetybox.research.exposure_ledger import ExposureLedger

SCORING_PROCESS_ID = "AUTH-COVERAGE-002-SCORING-PROCESS@1"


class ScoringIsolationError(RuntimeError):
    """Raised when analysis is attempted before a valid raw seal."""


def no_scoring_crash(_: str) -> None:
    """Default scoring fault hook."""


def _raw_for_metrics(record: RawAuthorizationRecord) -> dict[str, object]:
    output = record.authorization_output
    primary = record.authorization_input.primary.request
    matched: object = None
    if output.matched_capability is not None:
        matched = {
            "capability_digest": output.matched_capability.capability_digest,
            "action": output.matched_capability.action,
            "resource": output.matched_capability.resource,
            "task_binding": output.matched_capability.task_binding,
        }
    explanation = {
        "decision": output.final_decision,
        "rule": output.rule_id,
        "component": (
            output.component_decisions[0].component if output.component_decisions else None
        ),
        "matched_capability": matched,
        "authority_source": output.authority_source,
        "task": primary.task_id,
        "action": primary.action,
        "resource": primary.resource,
        "reason_code": output.reason_code,
    }
    return {
        "scenario_id": record.scenario_id,
        "final_decision": output.final_decision,
        "evaluated_input": {
            "request_task_id": primary.task_id,
            "action": primary.action,
            "resource": primary.resource,
        },
        "explanation": explanation,
        "infrastructure_errors": (
            []
            if output.error is None
            else [
                "RUNNER_ERROR"
                if output.error.error_type == "RunnerError"
                else "PRODUCTION_AUTHORIZATION_ERROR"
            ]
        ),
    }


def _load_sequence(path: Path) -> list[Mapping[str, object]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ScoringIsolationError(f"analysis package must contain a JSON array: {path}")
    return cast(list[Mapping[str, object]], value)


def _write_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical_json(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _read_raw(path: Path) -> tuple[RawAuthorizationRecord, ...]:
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise ScoringIsolationError("raw JSONL ends with an incomplete record")
    return tuple(raw_record_from_json(line) for line in data.splitlines())


def _verify_raw_seal(
    *,
    state: RunStateStore,
    raw_manifest_path: Path,
    raw_path: Path,
    ledger: ExposureLedger,
    run_metadata_path: Path,
) -> bool:
    """Analysis-local seal verification with no runner/production import."""
    del ledger  # Scoring verifies the immutable snapshot named by the raw seal.
    try:
        value = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("raw_manifest_id") != (
            "AUTH-COVERAGE-002-RAW-MANIFEST@1"
        ):
            return False
        records = _read_raw(raw_path)
        manifest = state.manifest
        metadata_value = json.loads(run_metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata_value, dict):
            return False
        metadata_manifest = RunManifest.from_dict(metadata_value)
        if metadata_manifest.digest != manifest.digest:
            return False
        if value.get("run_manifest_digest") != manifest.digest:
            return False
        expected_inputs = dict(manifest.scenario_input_digests)
        expected_artifacts = dict(manifest.implementation_artifacts)
        if any(
            record.experiment_id != manifest.experiment_id
            or record.run_id != manifest.run_id
            or record.schema_id != manifest.raw_schema_version
            or record.input_digest != expected_inputs.get(record.scenario_id)
            or record.implementation.production_git_sha != manifest.implementation_sha
            or dict(record.implementation.source_artifact_checksums) != expected_artifacts
            or record.implementation.policy_version != manifest.policy_version
            or record.implementation.authorization_spec_version
            != manifest.authorization_spec_version
            or record.implementation.task_contract_schema_version
            != manifest.task_contract_schema_version
            or record.implementation.runner_git_sha != manifest.runner_sha
            or record.implementation.runner_version != manifest.runner_version
            for record in records
        ):
            return False
        snapshot_name = value["ledger_snapshot"]
        if not isinstance(snapshot_name, str) or Path(snapshot_name).name != snapshot_name:
            return False
        sealed_ledger = ExposureLedger(raw_manifest_path.parent / snapshot_name)
        integrity = sealed_ledger.verify_integrity(
            expected_head=str(value["ledger_head"]),
            expected_event_count=int(value["ledger_event_count"]),
        )
        return (
            integrity.valid
            and len(records) == value["record_count"]
            and sha256_file(raw_path) == value["raw_package_checksum"]
            and sha256_file(sealed_ledger.path) == value["ledger_checksum"]
            and sha256_file(sealed_ledger.anchor_path) == value["ledger_anchor_checksum"]
            and sha256_file(run_metadata_path) == value["run_metadata_checksum"]
            and verify_complete_sealed_evidence(
                manifest=manifest,
                records=records,
                ledger=sealed_ledger,
            )
        )
    except (KeyError, OSError, TypeError, ValueError):
        return False


def score_sealed_run(
    *,
    state: RunStateStore,
    raw_path: Path,
    raw_manifest_path: Path,
    ledger: ExposureLedger,
    run_metadata_path: Path,
    labels_path: Path,
    pairs_path: Path,
    cross_tool_groups_path: Path,
    summary_path: Path,
    independent_path: Path,
    scoring_manifest_path: Path,
    crash_hook: Callable[[str], None] = no_scoring_crash,
) -> tuple[dict[str, object], dict[str, object]]:
    with exclusive_run_lock(state.path):
        return _score_sealed_run_locked(
            state=state,
            raw_path=raw_path,
            raw_manifest_path=raw_manifest_path,
            ledger=ledger,
            run_metadata_path=run_metadata_path,
            labels_path=labels_path,
            pairs_path=pairs_path,
            cross_tool_groups_path=cross_tool_groups_path,
            summary_path=summary_path,
            independent_path=independent_path,
            scoring_manifest_path=scoring_manifest_path,
            crash_hook=crash_hook,
        )


def _score_sealed_run_locked(
    *,
    state: RunStateStore,
    raw_path: Path,
    raw_manifest_path: Path,
    ledger: ExposureLedger,
    run_metadata_path: Path,
    labels_path: Path,
    pairs_path: Path,
    cross_tool_groups_path: Path,
    summary_path: Path,
    independent_path: Path,
    scoring_manifest_path: Path,
    crash_hook: Callable[[str], None],
) -> tuple[dict[str, object], dict[str, object]]:
    """Join labels only after verifying the immutable raw seal."""
    if state.load().state is RunState.SCORING:
        state.transition(RunState.INVALID, reason="SCORING_PROCESS_RESTART_FORBIDDEN")
        raise ScoringIsolationError("interrupted scoring cannot be silently restarted")
    state.require_scoring_allowed()
    if not _verify_raw_seal(
        state=state,
        raw_manifest_path=raw_manifest_path,
        raw_path=raw_path,
        ledger=ledger,
        run_metadata_path=run_metadata_path,
    ):
        raise ScoringIsolationError("raw package seal verification failed")

    records = _read_raw(raw_path)
    raw = [_raw_for_metrics(record) for record in records]
    labels = _load_sequence(labels_path)
    pairs = _load_sequence(pairs_path)
    cross_tool_groups = _load_sequence(cross_tool_groups_path)
    raw_digest = cast(
        str,
        json.loads(raw_manifest_path.read_text(encoding="utf-8"))["raw_package_checksum"],
    )
    label_digest = sha256_file(labels_path)
    state.transition(RunState.SCORING)
    crash_hook("DURING_SCORING")
    try:
        summary = score_authorization(
            raw,
            labels,
            pairs=pairs,
            cross_tool_groups=cross_tool_groups,
            raw_package_digest=raw_digest,
            label_package_digest=label_digest,
        )
        independent: dict[str, object] = {
            "recomputation_id": "AUTH-COVERAGE-002-INDEPENDENT-RECOMPUTATION@1",
            "scorer_version": "AUTH-COVERAGE-002-SCORER@1",
            "scoring_process_id": SCORING_PROCESS_ID,
            "scoring_adapter_source_digest": sha256_file(Path(__file__)),
            "raw_package_digest": raw_digest,
            "label_package_digest": label_digest,
            "pair_registry_digest": sha256_file(pairs_path),
            "cross_tool_groups_digest": sha256_file(cross_tool_groups_path),
            "analysis_package_digest": canonical_digest(
                {
                    "labels": label_digest,
                    "pairs": sha256_file(pairs_path),
                    "cross_tool_groups": sha256_file(cross_tool_groups_path),
                }
            ),
            "headline_counts": independent_recompute_headline(raw, labels, pairs=pairs),
        }
        manifest = summary.get("scoring_manifest")
        if not isinstance(manifest, dict):
            raise ScoringIsolationError("canonical scorer omitted its scoring manifest")
        manifest.update(
            {
                "pair_registry_digest": sha256_file(pairs_path),
                "cross_tool_groups_digest": sha256_file(cross_tool_groups_path),
                "analysis_package_digest": canonical_digest(
                    {
                        "labels": label_digest,
                        "pairs": sha256_file(pairs_path),
                        "cross_tool_groups": sha256_file(cross_tool_groups_path),
                    }
                ),
                "scoring_process_id": SCORING_PROCESS_ID,
                "scoring_adapter_source_digest": sha256_file(Path(__file__)),
            }
        )
        _write_new(scoring_manifest_path, manifest)
        _write_new(summary_path, summary)
        _write_new(independent_path, independent)
    except Exception:
        state.transition(RunState.INVALID, reason="SCORING_ERROR")
        raise
    state.transition(RunState.COMPLETE)
    return summary, independent


def scoring_package_layout() -> dict[str, str]:
    """Freeze the future result-package filenames without creating a held-out package."""
    return {
        "run_metadata": "run_metadata.json",
        "exposure_ledger": "exposure_ledger.jsonl",
        "raw_decisions": "raw_decisions.jsonl",
        "raw_manifest": "raw_manifest.json",
        "raw_checksums": "raw_SHA256SUMS",
        "scoring_manifest": "scoring_manifest.json",
        "summary": "summary.json",
        "independent_recomputation": "independent_recomputation.json",
    }
