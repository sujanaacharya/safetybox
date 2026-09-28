"""Executable parity and adversarial tests for Generator@4."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments/AUTH-COVERAGE-002"
G4_PATH = EXPERIMENT / "protocol4/generator4.py"
G3_PATH = EXPERIMENT / "protocol3/generator3.py"
REAL_ATTEMPT = "AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1"
OLD_ATTEMPT = "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def generator4() -> ModuleType:
    return load("auth_coverage_002_generator4_test", G4_PATH)


def synthetic(
    generator4: ModuleType,
    tmp_path: Path,
    *,
    suffix: str = "TEST",
    split: str = "VALIDATION",
    count: int = 4,
) -> tuple[Any, Any, Path, Any]:
    attempt = f"AUTH-COVERAGE-002-SYNTHETIC-{suffix}-ATTEMPT"
    generator = f"AUTH-COVERAGE-002-SYNTHETIC-{suffix}-GENERATOR@4"
    root = tmp_path / suffix / "authority"
    path, digest = generator4.authority.provision_synthetic_authority(
        root,
        attempt_id=attempt,
        generator_id=generator,
        split=split,
        commitment=hashlib.sha256(f"{attempt}:{split}".encode()).hexdigest(),
        record_count=count,
    )
    verifier = generator4.authority.AuthorityVerifier.for_synthetic(
        attempt_id=attempt,
        generator_id=generator,
        approved_digests={split: digest},
        authority_root=root,
    )
    store = generator4.MaterializationStore(tmp_path / suffix / "state", attempt, synthetic=True)
    return verifier, store, path, verifier.load(path)


def materialize(generator4: ModuleType, tmp_path: Path, suffix: str = "MAT") -> tuple[Any, ...]:
    verifier, store, path, verified = synthetic(generator4, tmp_path, suffix=suffix)
    manifest = generator4.CanonicalMaterializer(verifier, store).materialize(verified)
    return verifier, store, path, verified, manifest


def test_exact_identity_and_frozen_bindings(generator4: ModuleType) -> None:
    assert generator4.PROTOCOL_ID == "AUTH-COVERAGE-002-PROTOCOL@4"
    assert generator4.PROTOCOL_CHECKSUM == "31f2ee9e504de74f6b93e5a860fd6d92ae5f7fa2"
    assert generator4.GENERATOR_ID == "AUTH-COVERAGE-002-GENERATOR@4"
    assert generator4.SUBSTRATE_ID == "AUTH-COVERAGE-002-SUBSTRATE@2"
    assert generator4.REAL_ATTEMPT_ID == REAL_ATTEMPT
    assert generator4.REAL_STATE_ROOT == EXPERIMENT / "protocol4/materialization_state"
    assert generator4.authority.REAL_ARTIFACT_DIGESTS == {}


def test_benchmark_semantic_diff_zero_executable(generator4: ModuleType) -> None:
    generator3 = load("auth_coverage_002_generator3_parity", G3_PATH)
    for seed, count, offset in ((7, 8, 0), (2002101, 800, 0), (3002102, 800, 400)):
        assert generator4.disposable_dev(seed, count, template_root_offset=offset) == (
            generator3.disposable_dev(seed, count, template_root_offset=offset)
        )
    assert json.loads((EXPERIMENT / "protocol4/generator4_contract.json").read_text())[
        "semantic_diff"
    ] == 0


def test_threshold_classifier_leakage_and_normalizer_parity() -> None:
    assert (EXPERIMENT / "protocol2/quantitative_gates.json").read_bytes() == (
        EXPERIMENT / "protocol3/quantitative_gates.json"
    ).read_bytes()
    assert hashlib.sha256(
        (EXPERIMENT / "protocol3/quantitative_gates.json").read_bytes()
    ).hexdigest() == "a311763dbe8dfa656daf3cc25d1c6d4cc850755d1a4af4691c74b756ddbc0204"
    contract = json.loads((EXPERIMENT / "protocol4/generator4_contract.json").read_text())
    assert contract["scientific_threshold_diff"] == 0
    p2 = (EXPERIMENT / "protocol2/PROTOCOL2_SHA256SUMS").read_text()
    for required in ("leakage_suite.py", "leakage_attack_suite.json", "governance.py"):
        assert required in p2


def test_oracle_pair_presentation_and_capacity_parity(generator4: ModuleType) -> None:
    oracle_a = load("auth_coverage_002_g4_oracle_a", EXPERIMENT / "oracle_a.py")
    oracle_b = load("auth_coverage_002_g4_oracle_b", EXPERIMENT / "oracle_b.py")
    governance = load(
        "auth_coverage_002_g4_frozen_governance", EXPERIMENT / "protocol2/governance.py"
    )
    records = generator4.disposable_dev(2002101, 800)
    decisions = []
    families: set[str] = set()
    presentations: set[str] = set()
    pair_counts: dict[str, int] = {}
    for record in records:
        runtime = generator4.generator2.runtime_fixture(record)
        left, right = oracle_a.evaluate(runtime), oracle_b.evaluate(runtime)
        decisions.append(left == right and left["decision"] == record["label"])
        families.update(record["families"])
        presentations.add(governance.presentation_class(record["runtime"], record["label"]))
        pair_counts[record["pair_id"]] = pair_counts.get(record["pair_id"], 0) + 1
    assert all(decisions) and len(decisions) == 800
    assert families == {
        "TASK_BINDING",
        "RESOURCE_BOUNDARY",
        "ACTION_BOUNDARY",
        "CAPABILITY_SYNTHESIS",
        "CAPABILITY_PRESENCE",
        "CAPABILITY_DISTRACTOR",
    }
    assert set(pair_counts.values()) == {2}
    assert presentations == {"BENIGN_LOOKING_UNAUTHORIZED", "OTHER", "SUSPICIOUS_AUTHORIZED"}


def test_substrate2_preheldout_exact_key_integration(generator4: ModuleType) -> None:
    substrate = load(
        "auth_coverage_002_g4_substrate2", EXPERIMENT / "substrate2/candidate_audit.py"
    )
    records = generator4.generator2.generate_authoring(41, "DEV", 8) + (
        generator4.generator2.generate_authoring(43, "VALIDATION", 8)
    )
    assert substrate.construct_realized_split(records) == {
        "DEV": 8,
        "VALIDATION": 8,
        "HELD_OUT": 0,
    }
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol_id", "AUTH-COVERAGE-002-PROTOCOL@3"),
        ("protocol_checksum", "0" * 40),
        ("generator_checksum", "0" * 64),
        ("substrate_id", "AUTH-COVERAGE-002-SUBSTRATE@1"),
        ("substrate_checksum", "0" * 64),
        ("corpus_attempt_id", OLD_ATTEMPT),
        ("split", "DEV"),
        ("semantic_seed_or_entropy_commitment", "f" * 64),
        ("semantic_source_sha256", "0" * 64),
    ],
)
def test_authority_binding_mutations_reject(
    generator4: ModuleType, tmp_path: Path, field: str, value: str
) -> None:
    verifier, _store, path, _verified = synthetic(generator4, tmp_path, suffix=field.upper())
    raw = json.loads(path.read_text())
    raw[field] = value
    raw.pop("artifact_digest")
    raw["artifact_digest"] = generator4.authority.digest(raw)
    path.write_text(json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(generator4.authority.AuthorityError):
        verifier.load(path)


def test_old_attempt_authority_manifest_and_state_root_reject(
    generator4: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.authority.AuthorityVerifier(attempt_id=OLD_ATTEMPT)
    for name in ("dev-authority.json", "validation-authority.json", "held_out-authority.json"):
        with pytest.raises(generator4.authority.AuthorityError):
            generator4.authority.AuthorityVerifier().load(
                EXPERIMENT / "protocol3/materialization_authority" / name
            )
    with pytest.raises(generator4.GovernanceError):
        generator4.MaterializationStore(tmp_path, OLD_ATTEMPT)
    old_manifest = EXPERIMENT / (
        "protocol3/materialization_state/AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1/"
        "DEV/manifest.json"
    )
    store = generator4.MaterializationStore(
        tmp_path / "synthetic", "AUTH-COVERAGE-002-SYNTHETIC-OLD-MANIFEST", synthetic=True
    )
    with pytest.raises(generator4.GovernanceError):
        generator4.verify_manifest(old_manifest, store, "DEV")


def test_real_authority_cannot_be_minted_redirected_or_consumed(
    generator4: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.authority.provision_synthetic_authority(
            tmp_path,
            attempt_id=REAL_ATTEMPT,
            generator_id="AUTH-COVERAGE-002-SYNTHETIC-GENERATOR@4",
            split="DEV",
            commitment="a" * 64,
        )
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.authority.AuthorityVerifier(
            approved_digests={"DEV": "f" * 64}, authority_root=tmp_path
        )
    store = generator4.MaterializationStore(generator4.REAL_STATE_ROOT, REAL_ATTEMPT)
    assert store.reconcile("DEV") == "NOT_STARTED"
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.canonical_materialize(generator4.authority.authority_path("DEV"), store)
    assert not generator4.REAL_STATE_ROOT.exists()


def test_real_registry_contract_is_fixed_and_git_provisioned(
    generator4: ModuleType,
) -> None:
    assert generator4.authority.REAL_REGISTRY_PATH == (
        EXPERIMENT / "protocol4/materialization_authority/authority-registry.json"
    )
    registry = json.loads(generator4.authority.REAL_REGISTRY_PATH.read_text())
    assert registry["artifacts"] == {
        "DEV": "ad9b0260772f538b87bdf9e164a67c83141642b3ded45518c5afdf5c5c6e9751",
        "VALIDATION": "ae37e7cfe72c6948dd4a455239354459d22d8f83235b0a61b381f78e1a4cbd03",
        "HELD_OUT": "40f4733d763dd9b922119edecec7a7b4a91ab4b5f708013cc40c2480af139818",
    }
    # The verifier deliberately rejects the uncommitted working-tree package.
    with pytest.raises(generator4.authority.AuthorityError, match="repository provisioned"):
        generator4.authority.real_artifact_digests()
    assert generator4.authority.REAL_RECORD_COUNTS == {
        "DEV": 800,
        "VALIDATION": 800,
        "HELD_OUT": 2400,
    }


def test_manual_duck_subclass_shadow_redirect_and_canonical_false_reject(
    generator4: ModuleType, tmp_path: Path
) -> None:
    verifier, store, path, verified = synthetic(generator4, tmp_path, suffix="REDTEAM")
    with pytest.raises(generator4.authority.AuthorityError):
        generator4.CanonicalMaterializer(verifier, store).materialize(
            replace(verified, _load_proof=object())
        )

    class Duck:
        pass

    with pytest.raises(generator4.GovernanceError):
        generator4.CanonicalMaterializer(Duck(), store)

    class SubVerifier(generator4.authority.AuthorityVerifier):
        pass

    with pytest.raises(generator4.GovernanceError):
        generator4.CanonicalMaterializer(
            SubVerifier.for_synthetic(
                attempt_id=verifier.attempt_id,
                generator_id=verifier.generator_id,
                approved_digests=verifier.approved_digests,
                authority_root=path.parent,
            ),
            store,
        )
    verifier.assert_loaded = lambda _value: None
    with pytest.raises(generator4.GovernanceError):
        generator4.CanonicalMaterializer(verifier, store)
    verifier, store, path, _verified = synthetic(generator4, tmp_path, suffix="REDIRECT")
    materializer = generator4.CanonicalMaterializer(verifier, store)
    store.root = tmp_path / "redirected"
    with pytest.raises(generator4.GovernanceError):
        materializer.materialize(_verified)
    with pytest.raises(TypeError):
        generator4.canonical_materialize(
            path, store, verifier=verifier, canonical=False  # type: ignore[call-arg]
        )


def test_synthetic_materialization_ledger_manifest_and_single_use(
    generator4: ModuleType, tmp_path: Path
) -> None:
    verifier, store, path, verified, manifest = materialize(generator4, tmp_path)
    assert store.reconcile("VALIDATION") == "SEALED"
    assert manifest["manifest_schema"] == "AUTH-COVERAGE-002-CANONICAL-MANIFEST@4"
    assert manifest["protocol_checksum"] == generator4.PROTOCOL_CHECKSUM
    assert manifest["substrate_id"] == generator4.SUBSTRATE_ID
    assert manifest["substrate_checksum"] == generator4.SUBSTRATE_CHECKSUM
    events = store._read_events("VALIDATION")
    assert {event["protocol_id"] for event in events} == {generator4.PROTOCOL_ID}
    assert {event["substrate_id"] for event in events} == {generator4.SUBSTRATE_ID}
    with pytest.raises(generator4.GovernanceError):
        generator4.CanonicalMaterializer(verifier, store).materialize(verified)
    restarted = generator4.MaterializationStore(store.root, store.attempt_id, synthetic=True)
    with pytest.raises(generator4.GovernanceError):
        generator4.canonical_materialize(path, restarted, verifier=verifier)


def test_gate_a_evidence_digest_mismatch_rejects(
    generator4: ModuleType, tmp_path: Path
) -> None:
    attempt = "AUTH-COVERAGE-002-SYNTHETIC-GATE-ATTEMPT"
    generator = "AUTH-COVERAGE-002-SYNTHETIC-GATE-GENERATOR@4"
    authority_root = tmp_path / "gate-authority"
    authority_root.mkdir()
    evidence_path = authority_root / "gate-a-evidence.json"
    evidence_path.write_text('{"evidence":"current"}\n')

    class Store:
        @staticmethod
        def sealed_digest(split: str) -> str:
            return {"DEV": "d" * 64, "VALIDATION": "v" * 64}[split]

    gate = {
        "protocol_id": generator4.PROTOCOL_ID,
        "generator_id": generator,
        "corpus_attempt_id": attempt,
        "decision": "AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE",
        "canonical_dev_digest": "d" * 64,
        "canonical_validation_digest": "v" * 64,
        "evidence_digest": "0" * 64,
        "governance_source": "AUTH-COVERAGE-002-GATE-A-INDEPENDENT-AUDIT",
    }
    gate["artifact_digest"] = generator4.authority.digest(gate)
    gate_path = authority_root / "gate-a-approval.json"
    gate_path.write_text(json.dumps(gate, sort_keys=True, separators=(",", ":")) + "\n")
    verifier = generator4.authority.AuthorityVerifier.for_synthetic(
        attempt_id=attempt,
        generator_id=generator,
        approved_digests={"HELD_OUT": "a" * 64},
        authority_root=authority_root,
    )
    with pytest.raises(generator4.authority.AuthorityError, match="evidence binding"):
        verifier._verify_gate_a(
            {"decision": "AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE"}, gate_path, Store()
        )


@pytest.mark.parametrize(
    ("crash_at", "expected"),
    [
        ("after_authority_consumption", "STARTED_UNOBSERVED"),
        ("after_first_fsync", "PARTIAL_OBSERVED_BLOCKED"),
        ("after_completed", "COMPLETED_UNSEALED"),
        ("after_sealed", "SEALED"),
    ],
)
def test_crash_state_parity(
    generator4: ModuleType, tmp_path: Path, crash_at: str, expected: str
) -> None:
    verifier, store, path, _verified = synthetic(generator4, tmp_path, suffix=crash_at.upper())
    with pytest.raises(generator4.CrashInjected):
        generator4.canonical_materialize(path, store, verifier=verifier, crash_at=crash_at)
    restarted = generator4.MaterializationStore(store.root, store.attempt_id, synthetic=True)
    assert restarted.reconcile("VALIDATION") == expected


def test_contamination_reuse_rejects_and_novel_capacity_passes(generator4: ModuleType) -> None:
    old_path = EXPERIMENT / (
        "protocol3/materialization_state/AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1/"
        "DEV/semantic-records.jsonl"
    )
    old = [json.loads(line) for line in old_path.read_text().splitlines()]
    with pytest.raises(generator4.GovernanceError):
        generator4.assert_not_historically_contaminated(old[:2])
    disposable = generator4.generator2.generate_authoring(919191, "DEV", 800)
    generator4.assert_not_historically_contaminated(disposable)
    assert len({generator4.semantic_instance_digest(item) for item in disposable}) == 800
    assert len({generator4.canonical_input_digest(item) for item in disposable}) == 800


@pytest.mark.parametrize(
    ("seed", "count", "offset"),
    [(3002101, 800, 0), (3002102, 800, 400), (3002103, 2400, 800)],
)
def test_registered_capacity_lane_reuse_rejects(
    generator4: ModuleType, seed: int, count: int, offset: int
) -> None:
    registered = generator4.generator2.generate_dev(
        seed, count, template_root_offset=offset
    )
    with pytest.raises(generator4.GovernanceError):
        generator4.assert_not_historically_contaminated(registered)


def test_protocol1_candidate_input_reuse_rejects(generator4: ModuleType) -> None:
    scenarios = json.loads(
        (EXPERIMENT / "corpus/runtime/DEV/scenarios.json").read_text()
    )
    runtime = dict(scenarios[0])
    runtime.pop("scenario_id")
    candidate = generator4.generator2.generate_authoring(818181, "DEV", 2)
    candidate[0]["runtime"] = runtime
    with pytest.raises(generator4.GovernanceError):
        generator4.assert_not_historically_contaminated(candidate)


def test_substrate_dev_registry_is_checksum_bound_and_inventoried(
    generator4: ModuleType,
) -> None:
    _semantics, inputs = generator4._historical_inventory()
    registry = json.loads((EXPERIMENT / "dev/contamination_registry.json").read_text())
    assert set(registry["canonical_input_digests"]) <= inputs


def test_import_cli_and_disposable_isolation() -> None:
    before = sorted(str(path) for path in (EXPERIMENT / "protocol4").rglob("materialization_state"))
    result = subprocess.run(
        [sys.executable, "-c", f"import runpy; runpy.run_path({str(G4_PATH)!r})"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    after = sorted(str(path) for path in (EXPERIMENT / "protocol4").rglob("materialization_state"))
    assert result.returncode == 0 and before == after
    help_result = subprocess.run(
        [sys.executable, str(G4_PATH), "--help"], cwd=ROOT, text=True, capture_output=True
    )
    assert help_result.returncode == 0 and "materialize" not in help_result.stdout
    assert not {
        "--force",
        "--reset",
        "--ignore-ledger",
        "--new-seed",
        "--retry",
        "--canonical",
    } & set(help_result.stdout.split())


def test_canonical_api_has_no_seed_split_records_or_downgrade(generator4: ModuleType) -> None:
    assert set(inspect.signature(generator4.CanonicalMaterializer.materialize).parameters) == {
        "self",
        "verified",
        "crash_at",
    }
    forbidden = {"seed", "split", "records", "canonical", "force", "retry"}
    assert not forbidden & set(inspect.signature(generator4.canonical_materialize).parameters)


def test_new_attempt_remains_unused_and_production_zero() -> None:
    status = json.loads((EXPERIMENT / "protocol4/materialization_status.json").read_text())
    assert {key: status[key] for key in ("DEV", "VALIDATION", "HELD_OUT")} == {
        "DEV": 0,
        "VALIDATION": 0,
        "HELD_OUT": 0,
    }
    assert set(status["production_exposure"].values()) == {0}
    assert not (EXPERIMENT / "protocol4/materialization_state").exists()
    authority_root = EXPERIMENT / "protocol4/materialization_authority"
    registry = json.loads((authority_root / "authority-registry.json").read_text())
    assert registry["use_status"] == {
        "DEV": "PROVISIONED_NOT_CONSUMED",
        "VALIDATION": "PROVISIONED_NOT_CONSUMED",
        "HELD_OUT": "NOT_AUTHORIZED_FOR_USE",
    }
