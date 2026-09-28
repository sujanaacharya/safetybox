"""Provisioning and forgery checks for the Protocol@4 authority package."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments/AUTH-COVERAGE-002"
P4 = EXPERIMENT / "protocol4"
AUTHORITY_ROOT = P4 / "materialization_authority"
G4_PATH = P4 / "generator4.py"
ATTEMPT = "AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1"


def load_generator4() -> ModuleType:
    name = "auth_coverage_002_authority4_test"
    spec = importlib.util.spec_from_file_location(name, G4_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def generator4() -> ModuleType:
    return load_generator4()


def read(split: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((AUTHORITY_ROOT / f"{split.lower()}-authority.json").read_text()),
    )


def allow_working_tree_provisioning(
    generator4: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        generator4.authority.AuthorityVerifier,
        "_assert_repository_provisioned",
        staticmethod(lambda _path: None),
    )


def test_exact_registry_and_authority_set(generator4: ModuleType) -> None:
    registry = json.loads((AUTHORITY_ROOT / "authority-registry.json").read_text())
    unsigned = dict(registry)
    recorded = unsigned.pop("artifact_digest")
    assert recorded == generator4.authority.digest(unsigned)
    assert registry["generator_freeze_sha"] == "97c4b594f61634d49937d128c67d7e8b0b348be6"
    assert registry["generator_manifest_sha256"] == (
        "fc109c3f1a0ee712de0d7fe0b7a04c0ea853d02bf14392829f8bbd7e68be7d88"
    )
    assert registry["use_status"] == {
        "DEV": "PROVISIONED_NOT_CONSUMED",
        "VALIDATION": "PROVISIONED_NOT_CONSUMED",
        "HELD_OUT": "NOT_AUTHORIZED_FOR_USE",
    }
    assert {
        path.name for path in AUTHORITY_ROOT.glob("*-authority.json")
    } == {"dev-authority.json", "validation-authority.json", "held_out-authority.json"}
    for split, expected in registry["artifacts"].items():
        artifact = read(split)
        unsigned_artifact = dict(artifact)
        assert unsigned_artifact.pop("artifact_digest") == expected
        assert expected == generator4.authority.digest(unsigned_artifact)
        assert hashlib.sha256(
            (AUTHORITY_ROOT / f"{split.lower()}-authority.json").read_bytes()
        ).hexdigest() == registry["authority_file_sha256"][split]


def test_real_dev_and_validation_load_but_remain_unused(
    generator4: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    allow_working_tree_provisioning(generator4, monkeypatch)
    verifier = generator4.authority.AuthorityVerifier()
    for split in ("DEV", "VALIDATION"):
        verified = verifier.load(generator4.authority.authority_path(split))
        verifier.assert_loaded(verified)
        assert verified.allowed_use_count == 1
        assert verified.status == "PROVISIONED_NOT_CONSUMED"
    assert not generator4.REAL_STATE_ROOT.exists()


def test_held_out_is_unusable_without_gate_a(
    generator4: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    allow_working_tree_provisioning(generator4, monkeypatch)
    with pytest.raises(generator4.authority.AuthorityError, match="requires Gate A"):
        generator4.authority.AuthorityVerifier().load(
            generator4.authority.authority_path("HELD_OUT")
        )
    assert not (AUTHORITY_ROOT / "gate-a-approval.json").exists()
    assert not (AUTHORITY_ROOT / "gate-a-evidence.json").exists()
    assert not generator4.REAL_STATE_ROOT.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol_id", "AUTH-COVERAGE-002-PROTOCOL@3"),
        ("protocol_checksum", "0" * 40),
        ("substrate_id", "AUTH-COVERAGE-002-SUBSTRATE@1"),
        ("substrate_checksum", "0" * 64),
        ("generator_id", "AUTH-COVERAGE-002-GENERATOR@3"),
        ("generator_checksum", "0" * 64),
        ("corpus_attempt_id", "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"),
        ("split", "VALIDATION"),
        ("semantic_seed_or_entropy_commitment", "f" * 64),
        ("semantic_source_sha256", "0" * 64),
        ("record_count", 802),
        ("artifact_digest", "0" * 64),
    ],
)
def test_independent_authority_mutations_reject(
    generator4: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    allow_working_tree_provisioning(generator4, monkeypatch)
    target = AUTHORITY_ROOT / "dev-authority.json"
    raw = json.loads(target.read_text())
    raw[field] = value
    if field != "artifact_digest":
        raw.pop("artifact_digest")
        raw["artifact_digest"] = generator4.authority.digest(raw)
    forged = tmp_path / "dev-authority.json"
    forged.write_bytes(generator4.authority.canonical_json(raw) + b"\n")
    # A reconstructed artifact outside the fixed governance root always rejects.
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.authority.AuthorityVerifier().load(forged)
    # Even at the fixed path, a recomputed object digest is not a registry member.
    original_read_text = Path.read_text

    def substituted_read_text(path: Path) -> str:
        if path.resolve() == target.resolve():
            return forged.read_text()
        return original_read_text(path)

    monkeypatch.setattr(Path, "read_text", substituted_read_text)
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.authority.AuthorityVerifier().load(target)


def test_mutations_with_recomputed_digest_fail_registry_membership(
    generator4: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    allow_working_tree_provisioning(generator4, monkeypatch)
    copied = tmp_path / "authority"
    shutil.copytree(AUTHORITY_ROOT, copied)
    raw = json.loads((copied / "dev-authority.json").read_text())
    raw["record_count"] = 802
    raw.pop("artifact_digest")
    raw["artifact_digest"] = generator4.authority.digest(raw)
    (copied / "dev-authority.json").write_bytes(
        generator4.authority.canonical_json(raw) + b"\n"
    )
    verifier = generator4.authority.AuthorityVerifier.for_synthetic(
        attempt_id="AUTH-COVERAGE-002-SYNTHETIC-FORGERY-ATTEMPT",
        generator_id="AUTH-COVERAGE-002-SYNTHETIC-FORGERY-GENERATOR@4",
        approved_digests={"DEV": read("DEV")["artifact_digest"]},
        authority_root=copied,
    )
    with pytest.raises(generator4.authority.AuthorityError, match="not provisioned"):
        verifier.load(copied / "dev-authority.json")


def test_registry_mutation_redirect_and_manual_reconstruction_reject(
    generator4: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    allow_working_tree_provisioning(generator4, monkeypatch)
    registry = json.loads((AUTHORITY_ROOT / "authority-registry.json").read_text())
    mutations: tuple[Callable[[dict[str, Any]], None], ...] = (
        lambda value: value["artifacts"].__setitem__("DEV", "f" * 64),
        lambda value: value.__setitem__("generator_freeze_sha", "0" * 40),
    )
    for mutation in mutations:
        forged = copy.deepcopy(registry)
        mutation(forged)
        path = tmp_path / f"registry-{len(list(tmp_path.iterdir()))}.json"
        path.write_text(json.dumps(forged) + "\n")
        monkeypatch.setattr(generator4.authority, "REAL_REGISTRY_PATH", path)
        with pytest.raises(generator4.authority.AuthorityError):
            generator4.authority.real_artifact_digests()
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.authority.AuthorityVerifier(authority_root=tmp_path)


def test_old_authorities_all_reject(generator4: ModuleType) -> None:
    old = EXPERIMENT / "protocol3/materialization_authority"
    verifier = generator4.authority.AuthorityVerifier()
    for split in ("dev", "validation", "held_out"):
        with pytest.raises(generator4.authority.AuthorityError):
            verifier.load(old / f"{split}-authority.json")


def test_synthetic_factory_isolation_and_single_use(
    generator4: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.authority.provision_synthetic_authority(
            tmp_path,
            attempt_id=ATTEMPT,
            generator_id="AUTH-COVERAGE-002-SYNTHETIC-GENERATOR@4",
            split="DEV",
            commitment="a" * 64,
        )
    attempt = "AUTH-COVERAGE-002-SYNTHETIC-SINGLE-USE-ATTEMPT"
    generator = "AUTH-COVERAGE-002-SYNTHETIC-SINGLE-USE-GENERATOR@4"
    authority_root = tmp_path / "synthetic-authority"
    path, digest = generator4.authority.provision_synthetic_authority(
        authority_root,
        attempt_id=attempt,
        generator_id=generator,
        split="DEV",
        commitment="b" * 64,
        record_count=4,
    )
    verifier = generator4.authority.AuthorityVerifier.for_synthetic(
        attempt_id=attempt,
        generator_id=generator,
        approved_digests={"DEV": digest},
        authority_root=authority_root,
    )
    store = generator4.MaterializationStore(tmp_path / "state", attempt, synthetic=True)
    verified = verifier.load(path)
    generator4.CanonicalMaterializer(verifier, store).materialize(verified)
    with pytest.raises(generator4.GovernanceError):
        generator4.CanonicalMaterializer(verifier, store).materialize(verified)


def test_exact_commitment_capacity_and_contamination_exclusion(generator4: ModuleType) -> None:
    semantic: set[str] = set()
    canonical_input: set[str] = set()
    for split in ("DEV", "VALIDATION", "HELD_OUT"):
        raw = read(split)
        authority = type("Authority", (), raw)()
        seed = generator4._base._registered_seed(authority)
        records = generator4.generator2.generate_authoring(seed, split, raw["record_count"])
        generator4.assert_not_historically_contaminated(records)
        new_semantic = {generator4.semantic_instance_digest(item) for item in records}
        new_inputs = {generator4.canonical_input_digest(item) for item in records}
        assert len(new_semantic) == len(records)
        assert len(new_inputs) == len(records)
        assert not semantic & new_semantic
        assert not canonical_input & new_inputs
        semantic |= new_semantic
        canonical_input |= new_inputs
    assert len(semantic) == len(canonical_input) == 4000


def test_preheldout_exact_key_regression(generator4: ModuleType) -> None:
    spec = importlib.util.spec_from_file_location(
        "auth_coverage_002_authority_substrate", EXPERIMENT / "substrate2/candidate_audit.py"
    )
    assert spec and spec.loader
    substrate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = substrate
    spec.loader.exec_module(substrate)
    historical = json.loads(
        (EXPERIMENT / "protocol3/gate_a_evidence/machine-audit.json").read_text()
    )["metrics"]
    historical["realized_split"] = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}
    assert substrate.evaluate_gates(historical)["decision"] == "PASS"
    missing = copy.deepcopy(historical)
    missing["realized_split"].pop("HELD_OUT")
    assert substrate.evaluate_gates(missing)["decision"] == "BLOCK"
    extra = copy.deepcopy(historical)
    extra["realized_split"]["UNEXPECTED"] = 0
    assert substrate.evaluate_gates(extra)["decision"] == "BLOCK"


def test_no_materialization_or_production_state_exists() -> None:
    status = json.loads((AUTHORITY_ROOT / "authority-status.json").read_text())
    assert status["canonical_counts"] == {"DEV": 0, "VALIDATION": 0, "HELD_OUT": 0}
    assert set(status["production_exposure"].values()) == {0}
    assert not (P4 / "materialization_state").exists()


def test_pre_materialization_decision_is_exactly_bound(generator4: ModuleType) -> None:
    decision_path = AUTHORITY_ROOT / "pre-materialization-decision.json"
    evidence_path = AUTHORITY_ROOT / "pre-gate-evidence.json"
    decision = json.loads(decision_path.read_text())
    unsigned = dict(decision)
    recorded = unsigned.pop("artifact_digest")
    assert recorded == generator4.authority.digest(unsigned)
    assert decision["decision"] == (
        "AUTHORIZED_TO_MATERIALIZE_CORPUS4_DEV_AND_VALIDATION_ONCE"
    )
    assert decision["authorized_splits"] == ["DEV", "VALIDATION"]
    assert decision["held_out_authorized"] is False
    assert decision["production_authorized"] is False
    assert decision["pre_gate_evidence_digest"] == hashlib.sha256(
        evidence_path.read_bytes()
    ).hexdigest()
    registry = json.loads((AUTHORITY_ROOT / "authority-registry.json").read_text())
    assert decision["authority_registry_digest"] == registry["artifact_digest"]
    assert decision["dev_authority_digest"] == registry["artifacts"]["DEV"]
    assert decision["validation_authority_digest"] == registry["artifacts"]["VALIDATION"]
    review = json.loads((AUTHORITY_ROOT / "independent-review.json").read_text())
    assert review["blocking_findings"] == 0
    assert review["status"] == "PASS_NO_BLOCKING"
