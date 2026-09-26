"""Pre-materialization checks for AUTH-COVERAGE-002-PROTOCOL@4."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments/AUTH-COVERAGE-002"
P4 = EXPERIMENT / "protocol4"


def load_governance() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "auth_coverage_002_protocol4_test", P4 / "governance.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def governance() -> ModuleType:
    return load_governance()


def token(governance: ModuleType, split: str = "VALIDATION", **changes: str):
    values = {
        "protocol_id": governance.PROTOCOL_ID,
        "generator_id": governance.GENERATOR_ID,
        "attempt_id": governance.CORPUS_ATTEMPT_ID,
        "split": split,
        "source_sha": "a" * 40,
        "seed_commitment": "b" * 64,
    }
    values.update(changes)
    return governance.Authorization(**values)


def test_protocol4_binds_successor_identities_and_rejects_generator3(
    governance: ModuleType,
) -> None:
    assert governance.PROTOCOL_ID == "AUTH-COVERAGE-002-PROTOCOL@4"
    assert governance.CORPUS_ATTEMPT_ID == "AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1"
    assert governance.GENERATOR_ID == "AUTH-COVERAGE-002-GENERATOR@4"
    with pytest.raises(governance.GovernanceError):
        governance.authorize(
            "NOT_AUTHORIZED",
            token(governance, generator_id="AUTH-COVERAGE-002-GENERATOR@3"),
        )


def test_gate_a_and_gate_b_semantics_are_preserved(governance: ModuleType) -> None:
    with pytest.raises(governance.GovernanceError):
        governance.authorize("NOT_AUTHORIZED", token(governance, "HELD_OUT"))
    held = governance.authorize_held_out(
        "AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE",
        "NOT_AUTHORIZED",
        token(governance, "HELD_OUT"),
    )
    assert held == "AUTHORIZED_ONCE"
    assert not governance.production_authorized(
        "AUTHORIZED_TO_EXECUTE_HELDOUT_PRODUCTION_ONCE", "MATERIALIZED"
    )
    assert governance.production_authorized(
        "AUTHORIZED_TO_EXECUTE_HELDOUT_PRODUCTION_ONCE", "SEALED"
    )


def test_threshold_digest_is_frozen_and_semantic_diff_is_zero() -> None:
    gates = (EXPERIMENT / "protocol3/quantitative_gates.json").read_bytes()
    assert hashlib.sha256(gates).hexdigest() == (
        "a311763dbe8dfa656daf3cc25d1c6d4cc850755d1a4af4691c74b756ddbc0204"
    )
    contract = json.loads((P4 / "protocol_contract.json").read_text())
    changes = json.loads((P4 / "change_manifest.json").read_text())
    assert contract["benchmark_semantic_change"] == 0
    assert contract["quantitative_gates"]["scientific_threshold_change"] == 0
    assert changes["benchmark_semantic_change"] == 0
    assert changes["scientific_threshold_change"] == 0


def test_generator3_is_immutably_bound_and_generator4_is_required() -> None:
    generator = (EXPERIMENT / "protocol3/generator3.py").read_text()
    authority = (EXPERIMENT / "protocol3/authority.py").read_text()
    contract = json.loads((EXPERIMENT / "protocol3/generator3_contract.json").read_text())
    assert 'PROTOCOL_ID = "AUTH-COVERAGE-002-PROTOCOL@3"' in generator
    assert 'REAL_ATTEMPT_ID = "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"' in generator
    assert 'REAL_STATE_ROOT = HERE / "materialization_state"' in generator
    assert 'PROTOCOL_CHECKSUM = "6959866f9ddb298e9cf5153544dc8a4551a83265"' in authority
    assert "REAL_ARTIFACT_DIGESTS" in authority
    assert contract["protocol_id"] == "AUTH-COVERAGE-002-PROTOCOL@3"
    assert contract["corpus_attempt"] == "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"


def test_new_attempt_is_empty_and_no_real_authorities_exist() -> None:
    status = json.loads((P4 / "materialization_status.json").read_text())
    assert {key: status[key] for key in ("DEV", "VALIDATION", "HELD_OUT")} == {
        "DEV": 0,
        "VALIDATION": 0,
        "HELD_OUT": 0,
    }
    assert status["authority_artifacts"] == 0
    assert set(status["production_exposure"].values()) == {0}
    assert not (P4 / "materialization_authority").exists()
    assert not (P4 / "materialization_state").exists()


def test_observed_predecessor_is_registered_as_contamination() -> None:
    registry = json.loads((P4 / "historical_contamination_registry.json").read_text())
    assert registry["observed_attempt"] == "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"
    assert registry["observed_sources"]["DEV"]["count"] == 800
    assert registry["observed_sources"]["VALIDATION"]["count"] == 800
    assert registry["silent_reuse_permitted"] is False


def test_old_attempt_is_permanently_blocked_and_checksum_preserved() -> None:
    path = EXPERIMENT / "protocol3/blocked_attempt_disposition.json"
    disposition = json.loads(path.read_text())
    assert disposition["permanent"] is True
    assert disposition["reopen_permitted"] is False
    assert disposition["canonical_materializations"] == {"DEV": 1, "VALIDATION": 1, "HELD_OUT": 0}


@pytest.mark.parametrize(
    "manifest",
    [
        EXPERIMENT / "substrate2/SUBSTRATE2_SHA256SUMS",
        P4 / "PROTOCOL4_SHA256SUMS",
        EXPERIMENT / "protocol3/BLOCKED_ATTEMPT_SHA256SUMS",
    ],
)
def test_successor_and_blocked_attempt_manifests_verify(manifest: Path) -> None:
    for line in manifest.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
