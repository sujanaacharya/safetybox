#!/usr/bin/env python3
"""Generator@4 governance bindings over frozen Generator@3 semantics.

Generator@3 is loaded under an isolated module name and is never modified on
disk.  Its governance implementation is rebound in memory to Protocol@4,
Substrate@2, the new attempt/state root, and the verification-only authority
registry.  Semantic generation continues to call frozen Generator@2 directly.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
ROOT = HERE.parents[2]
PROTOCOL_ID = "AUTH-COVERAGE-002-PROTOCOL@4"
PROTOCOL_CHECKSUM = "31f2ee9e504de74f6b93e5a860fd6d92ae5f7fa2"
GENERATOR_ID = "AUTH-COVERAGE-002-GENERATOR@4"
GENERATOR_IDENTITY_CHECKSUM = (
    "db9dd09fa8014f4b1c79fae7b8cd76330fedb7a6162808ab5e5be95bf625be24"
)
SUBSTRATE_ID = "AUTH-COVERAGE-002-SUBSTRATE@2"
SUBSTRATE_CHECKSUM = "d9d827c9544cc4f27bb0d925adf1091a9dd4f6081d8f984b07c8df154739cc60"
REAL_ATTEMPT_ID = "AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1"
GENERATOR2_SHA256 = "36b6ef0b0887b10627053087fdf156b62bdf4ff8caddd7798d1d2d8b1012b0a5"
REAL_STATE_ROOT = HERE / "materialization_state"
CONTAMINATION_REGISTRY = HERE / "historical_contamination_registry.json"
GENERATOR_CONTAMINATION_REGISTRY = HERE / "generator4_contamination_registry.json"
SPLITS = frozenset({"DEV", "VALIDATION", "HELD_OUT"})
ZERO_HASH = "0" * 64


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


authority = _load_module("auth_coverage_002_generator4_authority", HERE / "authority.py")
_base = _load_module(
    "auth_coverage_002_generator4_isolated_generator3",
    HERE.parent / "protocol3" / "generator3.py",
)

# Rebind only governance/runtime identity globals.  Generator@3's files and
# frozen Generator@2 semantic source remain unchanged.
_base.__dict__["PROTOCOL_ID"] = PROTOCOL_ID
_base.__dict__["GENERATOR_ID"] = GENERATOR_ID
_base.__dict__["REAL_ATTEMPT_ID"] = REAL_ATTEMPT_ID
_base.__dict__["GENERATOR_IDENTITY_CHECKSUM"] = GENERATOR_IDENTITY_CHECKSUM
_base.__dict__["REAL_STATE_ROOT"] = REAL_STATE_ROOT
_base.__dict__["authority"] = authority

GovernanceError = _base.GovernanceError
CrashInjected = _base.CrashInjected
MaterializationStore = _base.MaterializationStore
CanonicalMaterializer = _base.CanonicalMaterializer
generator2 = _base.generator2


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def disposable_dev(
    seed: int, count: int = 800, *, template_root_offset: int = 0
) -> list[dict[str, Any]]:
    """Return the exact frozen Generator@3/Generator@2 disposable semantics."""
    return cast(
        list[dict[str, Any]],
        generator2.generate_dev(seed, count, template_root_offset=template_root_offset),
    )


def semantic_instance_digest(record: dict[str, Any]) -> str:
    """Digest one complete semantic authoring record."""
    return _digest(record)


def canonical_input_digest(record: dict[str, Any]) -> str:
    """Digest the runtime authorization input before runtime identifiers exist."""
    return _digest(record["runtime"])


def _historical_inventory() -> tuple[set[str], set[str]]:
    try:
        generator_registry = json.loads(GENERATOR_CONTAMINATION_REGISTRY.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError("Generator@4 contamination registry unavailable") from exc
    if (
        not isinstance(generator_registry, dict)
        or generator_registry.get("status") != "FROZEN_WITH_GENERATOR4"
    ):
        raise GovernanceError("Generator@4 contamination registry is invalid")
    protocol4_binding = generator_registry.get("protocol4_registry")
    if not isinstance(protocol4_binding, dict):
        raise GovernanceError("Protocol@4 contamination binding is missing")
    if (
        ROOT / str(protocol4_binding.get("path")) != CONTAMINATION_REGISTRY
        or _file_digest(CONTAMINATION_REGISTRY) != protocol4_binding.get("sha256")
    ):
        raise GovernanceError("Protocol@4 contamination binding mismatch")
    try:
        registry = json.loads(CONTAMINATION_REGISTRY.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError("historical contamination registry unavailable") from exc
    if (
        not isinstance(registry, dict)
        or registry.get("status") != "FROZEN_BEFORE_NEW_CORPUS_MATERIALIZATION"
        or registry.get("silent_reuse_permitted") is not False
    ):
        raise GovernanceError("historical contamination registry is invalid")
    semantics: set[str] = set()
    inputs: set[str] = set()

    substrate_binding = generator_registry.get("substrate_dev_registry")
    if not isinstance(substrate_binding, dict):
        raise GovernanceError("substrate DEV contamination binding is missing")
    substrate_path = ROOT / str(substrate_binding.get("path"))
    if _file_digest(substrate_path) != substrate_binding.get("sha256"):
        raise GovernanceError("substrate DEV contamination binding mismatch")
    try:
        substrate_registry = json.loads(substrate_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError("substrate DEV contamination registry malformed") from exc
    substrate_digests = substrate_registry.get("canonical_input_digests")
    if (
        not isinstance(substrate_registry, dict)
        or substrate_registry.get("registry_id")
        != "AUTH-COVERAGE-002-DEV-CONTAMINATION-REGISTRY@1"
        or not isinstance(substrate_digests, list)
        or any(not isinstance(item, str) or len(item) != 64 for item in substrate_digests)
    ):
        raise GovernanceError("substrate DEV contamination registry invalid")
    inputs.update(substrate_digests)

    generator2_binding = generator_registry.get("generator2_disposable_registry")
    if not isinstance(generator2_binding, dict):
        raise GovernanceError("Generator@2 contamination binding is missing")
    generator2_path = ROOT / str(generator2_binding.get("path"))
    if _file_digest(generator2_path) != generator2_binding.get("sha256"):
        raise GovernanceError("Generator@2 contamination binding mismatch")
    try:
        generator2_registry = json.loads(generator2_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError("Generator@2 contamination registry malformed") from exc
    if (
        not isinstance(generator2_registry, dict)
        or generator2_registry.get("identity")
        != "AUTH-COVERAGE-002-GENERATOR2-DEV-CONTAMINATION@1"
    ):
        raise GovernanceError("Generator@2 contamination registry invalid")
    sources = registry.get("observed_sources")
    if not isinstance(sources, dict) or set(sources) != {"DEV", "VALIDATION"}:
        raise GovernanceError("historical contamination sources are incomplete")
    for split, binding in sources.items():
        if not isinstance(binding, dict):
            raise GovernanceError("historical contamination source is malformed")
        path = ROOT / str(binding.get("path"))
        if _file_digest(path) != binding.get("sha256"):
            raise GovernanceError("historical contamination source digest mismatch")
        lines = path.read_bytes().splitlines()
        if len(lines) != binding.get("count"):
            raise GovernanceError("historical contamination source count mismatch")
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GovernanceError("historical contamination record malformed") from exc
            if not isinstance(record, dict) or record.get("split") != split:
                raise GovernanceError("historical contamination record binding mismatch")
            semantics.add(semantic_instance_digest(record))
            inputs.add(canonical_input_digest(record))

    protocol1 = generator_registry.get("protocol1_runtime_candidates")
    if not isinstance(protocol1, list) or len(protocol1) != 3:
        raise GovernanceError("Protocol@1 candidate registry is incomplete")
    for binding in protocol1:
        if not isinstance(binding, dict):
            raise GovernanceError("Protocol@1 candidate binding is malformed")
        path = ROOT / str(binding.get("path"))
        if _file_digest(path) != binding.get("sha256"):
            raise GovernanceError("Protocol@1 candidate digest mismatch")
        try:
            scenarios = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise GovernanceError("Protocol@1 candidate package malformed") from exc
        if not isinstance(scenarios, list) or len(scenarios) != binding.get("count"):
            raise GovernanceError("Protocol@1 candidate count mismatch")
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                raise GovernanceError("Protocol@1 candidate scenario malformed")
            runtime = dict(scenario)
            runtime.pop("scenario_id", None)
            inputs.add(_digest(runtime))

    # Generator@2 and Generator@3 disposable proof lanes are parsed from their
    # checksum-bound registry. Regeneration is deterministic and creates no state.
    seed_digests = generator2_registry.get("dev_seed_digests")
    if not isinstance(seed_digests, dict) or set(seed_digests) != {
        str(seed) for seed in generator2.DEV_SEEDS
    }:
        raise GovernanceError("Generator@2 DEV seed registry is incomplete")
    for seed_text, expected_digest in seed_digests.items():
        records = generator2.generate_dev(int(seed_text), 800)
        package_digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
        if package_digest != expected_digest:
            raise GovernanceError("Generator@2 DEV package digest mismatch")
        for record in records:
            semantics.add(semantic_instance_digest(record))
            inputs.add(canonical_input_digest(record))
    capacity_lanes = generator2_registry.get("capacity_lane_digests")
    if not isinstance(capacity_lanes, list) or len(capacity_lanes) != 3:
        raise GovernanceError("Generator@2 capacity registry is incomplete")
    for lane in capacity_lanes:
        if not isinstance(lane, dict):
            raise GovernanceError("Generator@2 capacity binding malformed")
        records = generator2.generate_dev(
            int(lane["seed"]),
            int(lane["count"]),
            template_root_offset=int(lane["template_root_offset"]),
        )
        package_digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
        if package_digest != lane.get("digest"):
            raise GovernanceError("Generator@2 capacity package digest mismatch")
        for record in records:
            semantics.add(semantic_instance_digest(record))
            inputs.add(canonical_input_digest(record))
    return semantics, inputs


def assert_not_historically_contaminated(records: list[dict[str, Any]]) -> None:
    """Reject exact semantic or canonical-input reuse before the first write."""
    historical_semantics, historical_inputs = _historical_inventory()
    semantic_digests = [semantic_instance_digest(record) for record in records]
    input_digests = [canonical_input_digest(record) for record in records]
    if len(semantic_digests) != len(set(semantic_digests)):
        raise GovernanceError("candidate contains duplicate semantic instances")
    if len(input_digests) != len(set(input_digests)):
        raise GovernanceError("candidate contains duplicate canonical inputs")
    if set(semantic_digests) & historical_semantics:
        raise GovernanceError("candidate exactly reuses historical semantic material")
    if set(input_digests) & historical_inputs:
        raise GovernanceError("candidate exactly reuses a historical canonical input")


class _ContaminationCheckedGenerator:
    def generate_authoring(
        self, seed: int, split: str, count: int, *, template_root_offset: int | None = None
    ) -> list[dict[str, Any]]:
        records = cast(
            list[dict[str, Any]],
            generator2.generate_authoring(
                seed, split, count, template_root_offset=template_root_offset
            ),
        )
        assert_not_historically_contaminated(records)
        return records

    def generate_dev(
        self, seed: int, count: int = 800, *, template_root_offset: int = 0
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            generator2.generate_dev(seed, count, template_root_offset=template_root_offset),
        )


_base.__dict__["generator2"] = _ContaminationCheckedGenerator()


def _read_events(self: Any, split: str) -> list[dict[str, Any]]:
    ledger = self.path(split, "materialization-ledger.jsonl")
    events: list[dict[str, Any]] = []
    previous = ZERO_HASH
    try:
        lines = ledger.read_bytes().splitlines()
    except OSError as exc:
        raise GovernanceError("ledger unavailable") from exc
    if not lines:
        raise GovernanceError("empty ledger")
    for index, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GovernanceError("ledger corrupt") from exc
        unsigned = dict(event) if isinstance(event, dict) else {}
        recorded = unsigned.pop("event_hash", None)
        required = {
            "sequence": index,
            "previous_hash": previous,
            "protocol_id": PROTOCOL_ID,
            "protocol_checksum": PROTOCOL_CHECKSUM,
            "generator_id": GENERATOR_ID if not self.synthetic else event.get("generator_id"),
            "generator_checksum": GENERATOR_IDENTITY_CHECKSUM,
            "substrate_id": SUBSTRATE_ID,
            "substrate_checksum": SUBSTRATE_CHECKSUM,
            "attempt": self.attempt_id,
            "split": split,
        }
        if (
            not isinstance(event, dict)
            or recorded != _digest(unsigned)
            or any(unsigned.get(key) != value for key, value in required.items())
        ):
            raise GovernanceError("ledger chain or version binding invalid")
        previous = str(recorded)
        events.append(event)
    return events


def _append(self: Any, split: str, event_type: str, authority_digest: str) -> dict[str, Any]:
    directory = self.split_dir(split)
    directory.mkdir(parents=True, exist_ok=True)
    ledger = self.path(split, "materialization-ledger.jsonl")
    if ledger.exists():
        events = self._read_events(split)
        previous, sequence = events[-1]["event_hash"], len(events) + 1
        generator_id = events[-1]["generator_id"]
    else:
        previous, sequence = ZERO_HASH, 1
        if self.synthetic:
            binding = self._load_json(self.path(split, "authority-binding.json"))
            generator_id = binding.get("generator_id")
            if not isinstance(generator_id, str) or "SYNTHETIC" not in generator_id:
                raise GovernanceError("synthetic ledger generator binding invalid")
        else:
            generator_id = GENERATOR_ID
    unsigned = {
        "sequence": sequence,
        "previous_hash": previous,
        "event": event_type,
        "protocol_id": PROTOCOL_ID,
        "protocol_checksum": PROTOCOL_CHECKSUM,
        "generator_id": generator_id,
        "generator_checksum": GENERATOR_IDENTITY_CHECKSUM,
        "substrate_id": SUBSTRATE_ID,
        "substrate_checksum": SUBSTRATE_CHECKSUM,
        "attempt": self.attempt_id,
        "split": split,
        "authority_artifact_digest": authority_digest,
    }
    event = {**unsigned, "event_hash": _digest(unsigned)}
    with ledger.open("ab") as stream:
        stream.write(_canonical_json(event) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    _base._fsync_directory(directory)
    _base._atomic_json(
        self.path(split, "ledger-anchor.json"),
        {
            "schema": "AUTH-COVERAGE-002-MATERIALIZATION-ANCHOR@2",
            "attempt": self.attempt_id,
            "split": split,
            "ledger_count": sequence,
            "ledger_head": event["event_hash"],
        },
    )
    _base._atomic_json(
        self.path(split, "state.json"),
        {
            "schema": "AUTH-COVERAGE-002-MATERIALIZATION-STATE@2",
            "attempt": self.attempt_id,
            "split": split,
            "authority_artifact_digest": authority_digest,
            "state": event_type,
            "ledger_count": sequence,
            "ledger_head": event["event_hash"],
        },
    )
    return event


MaterializationStore._read_events = _read_events
MaterializationStore._append = _append


def construct_manifest(
    verified: Any, store: Any, records: list[dict[str, Any]]
) -> dict[str, Any]:
    events = store._read_events(verified.split)
    completed_index = next(
        (index for index, event in enumerate(events) if event["event"] == "COMPLETED"), None
    )
    if completed_index is None:
        raise GovernanceError("manifest requires durable COMPLETED state")
    completed = events[completed_index]
    package = store.path(verified.split, "semantic-records.jsonl")
    return {
        "manifest_schema": "AUTH-COVERAGE-002-CANONICAL-MANIFEST@4",
        "protocol_id": verified.protocol_id,
        "protocol_checksum": verified.protocol_checksum,
        "generator_id": verified.generator_id,
        "generator_checksum": verified.generator_checksum,
        "substrate_id": verified.substrate_id,
        "substrate_checksum": verified.substrate_checksum,
        "corpus_attempt_id": verified.corpus_attempt_id,
        "split": verified.split,
        "authority_artifact_digest": verified.artifact_digest,
        "semantic_seed_or_entropy_commitment": verified.semantic_seed_or_entropy_commitment,
        "record_count": len(records),
        "semantic_package_digest": _file_digest(package),
        "ordering_policy": _base.ORDERING_POLICY,
        "runtime_id_policy": _base.RUNTIME_ID_POLICY,
        "source_sha": verified.semantic_source_sha256,
        "ledger_head": completed["event_hash"],
        "ledger_count": completed_index + 1,
        "terminal_state": "SEALED",
    }


def verify_manifest(path: Path, store: Any, split: str) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError("manifest unavailable or malformed") from exc
    if not isinstance(manifest, dict):
        raise GovernanceError("manifest is not an object")
    events = store._read_events(split)
    completed_index = next(
        (index for index, event in enumerate(events) if event["event"] == "COMPLETED"), None
    )
    if completed_index is None:
        raise GovernanceError("manifest has no completed ledger binding")
    completed = events[completed_index]
    binding = store._load_json(store.path(split, "authority-binding.json"))
    unsigned = dict(binding)
    binding_digest = unsigned.pop("artifact_digest", None)
    if binding_digest != _digest(unsigned):
        raise GovernanceError("authority binding artifact digest mismatch")
    if binding_digest != completed["authority_artifact_digest"]:
        raise GovernanceError("authority binding/ledger mismatch")
    if not store.synthetic and authority.real_artifact_digests().get(split) != binding_digest:
        raise GovernanceError("real authority binding is not Protocol@4 provisioned")
    package = store.path(split, "semantic-records.jsonl")
    count, malformed = store._package_observation(split)
    expected = {
        "manifest_schema": "AUTH-COVERAGE-002-CANONICAL-MANIFEST@4",
        "protocol_id": PROTOCOL_ID,
        "protocol_checksum": PROTOCOL_CHECKSUM,
        "generator_id": binding.get("generator_id"),
        "generator_checksum": GENERATOR_IDENTITY_CHECKSUM,
        "substrate_id": SUBSTRATE_ID,
        "substrate_checksum": SUBSTRATE_CHECKSUM,
        "corpus_attempt_id": store.attempt_id,
        "split": split,
        "authority_artifact_digest": binding_digest,
        "semantic_seed_or_entropy_commitment": binding.get(
            "semantic_seed_or_entropy_commitment"
        ),
        "record_count": count,
        "semantic_package_digest": _file_digest(package) if package.exists() else None,
        "ordering_policy": _base.ORDERING_POLICY,
        "runtime_id_policy": _base.RUNTIME_ID_POLICY,
        "source_sha": GENERATOR2_SHA256,
        "ledger_head": completed["event_hash"],
        "ledger_count": completed_index + 1,
        "terminal_state": "SEALED",
    }
    if malformed or set(manifest) != set(expected):
        raise GovernanceError("manifest shape mismatch")
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise GovernanceError("manifest binding mismatch")
    return manifest


_base.__dict__["construct_manifest"] = construct_manifest
_base.__dict__["verify_manifest"] = verify_manifest


def canonical_materialize(
    artifact_path: Path,
    store: Any,
    *,
    verifier: Any | None = None,
    gate_a_path: Path | None = None,
    crash_at: str | None = None,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _base.canonical_materialize(
            artifact_path,
            store,
            verifier=verifier,
            gate_a_path=gate_a_path,
            crash_at=crash_at,
        ),
    )


gate_b_authorizes_materialization = _base.gate_b_authorizes_materialization
gate_a_authorizes_production = _base.gate_a_authorizes_production


def _cli(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generator@4 governance verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify-authority")
    verify.add_argument("split", choices=sorted(SPLITS))
    disposable = subparsers.add_parser("disposable-dev")
    disposable.add_argument("--seed", type=int, required=True)
    disposable.add_argument("--count", type=int, default=800)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    if arguments.command == "verify-authority":
        authority.AuthorityVerifier().load(authority.authority_path(arguments.split))
        return 0
    print(_digest(disposable_dev(arguments.seed, arguments.count)))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
