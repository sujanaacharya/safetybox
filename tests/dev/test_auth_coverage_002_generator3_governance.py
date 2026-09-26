"""Adversarial, synthetic-only checks for Generator@3 governance."""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]
G3_PATH = ROOT / "experiments/AUTH-COVERAGE-002/protocol3/generator3.py"
REAL_ATTEMPT = "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"


@pytest.fixture()
def generator3():
    spec = importlib.util.spec_from_file_location("generator3_test", G3_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def synthetic(generator3: Any, tmp_path: Path, split: str = "VALIDATION", *,
              suffix: str = "TEST", store: Any | None = None) -> tuple[Any, Any, Path, Any]:
    attempt = f"AUTH-COVERAGE-002-SYNTHETIC-{suffix}-ATTEMPT"
    protocol = f"AUTH-COVERAGE-002-SYNTHETIC-{suffix}-PROTOCOL@3"
    generator = f"AUTH-COVERAGE-002-SYNTHETIC-{suffix}-GENERATOR@3"
    authority_root = tmp_path / "authority"
    requirement = None
    if split == "HELD_OUT":
        requirement = {
            "decision": "AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE",
            "required_bindings": ["protocol_id", "generator_id", "corpus_attempt_id",
                                  "canonical_dev_digest", "canonical_validation_digest",
                                  "evidence_digest"],
        }
    path, digest = generator3.authority.provision_synthetic_authority(
        authority_root, attempt_id=attempt, protocol_id=protocol, generator_id=generator,
        split=split, commitment=hashlib.sha256(f"{attempt}:{split}".encode()).hexdigest(),
        gate_a_requirement=requirement, record_count=4,
    )
    verifier = generator3.authority.AuthorityVerifier.synthetic(
        attempt_id=attempt, protocol_id=protocol, generator_id=generator,
        approved_digests={split: digest}, authority_root=authority_root,
    )
    selected_store = store or generator3.MaterializationStore(
        tmp_path / "state", attempt, synthetic=True
    )
    loaded = verifier.load(path) if split != "HELD_OUT" else None
    return verifier, selected_store, path, loaded


def materialize(generator3: Any, tmp_path: Path) -> tuple[Any, ...]:
    verifier, store, path, loaded = synthetic(generator3, tmp_path)
    result = generator3.CanonicalMaterializer(verifier, store).materialize(loaded)
    return verifier, store, path, loaded, result


def test_benchmark_semantic_diff_is_zero(generator3: Any) -> None:
    for seed in (2002101, 2002105):
        assert generator3.disposable_dev(seed, 8) == generator3.generator2.generate_dev(seed, 8)
    contract = ROOT / "experiments/AUTH-COVERAGE-002/protocol3/generator3_contract.json"
    assert json.loads(contract.read_text())["semantic_diff"] == 0


def test_generator3_disposable_oracle_proof_is_100_percent(generator3: Any) -> None:
    experiment = ROOT / "experiments/AUTH-COVERAGE-002"

    def load(name: str) -> Any:
        spec = importlib.util.spec_from_file_location(
            f"generator3_{name}", experiment / f"{name}.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    oracle_a, oracle_b = load("oracle_a"), load("oracle_b")
    records = generator3.disposable_dev(2002101, 800)
    agreement = 0
    for record in records:
        runtime = generator3.generator2.runtime_fixture(record)
        left, right = oracle_a.evaluate(runtime), oracle_b.evaluate(runtime)
        agreement += left == right and left["decision"] == record["label"]
    assert agreement == len(records) == 800


def test_real_attempt_cannot_be_minted_or_redirected(generator3: Any, tmp_path: Path) -> None:
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.provision_synthetic_authority(
            tmp_path, attempt_id=REAL_ATTEMPT,
            protocol_id="AUTH-COVERAGE-002-SYNTHETIC-PROTOCOL@3",
            generator_id="AUTH-COVERAGE-002-SYNTHETIC-GENERATOR@3", split="DEV",
            commitment="a" * 64,
        )
    with pytest.raises(generator3.GovernanceError):
        generator3.MaterializationStore(tmp_path, REAL_ATTEMPT)
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.AuthorityVerifier(attempt_id=f"{REAL_ATTEMPT[:-1]}2")
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.AuthorityVerifier(
            approved_digests={"DEV": "f" * 64}, authority_root=tmp_path
        )
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.AuthorityVerifier.synthetic(
            attempt_id="AUTH-COVERAGE-002-SYNTHETIC-ATTEMPT",
            protocol_id="not-synthetic",
            generator_id="not-synthetic",
            approved_digests={},
            authority_root=tmp_path,
        )
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.authority_path("PRODUCTION")


def test_real_attempt_guard_from_fresh_external_process(tmp_path: Path) -> None:
    program = r"""
import importlib.util, sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('g3_real_guard',Path(sys.argv[1]))
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
try:
 module.authority.provision_synthetic_authority(
  Path(sys.argv[2]),attempt_id='AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1',
  protocol_id='AUTH-COVERAGE-002-SYNTHETIC-PROTOCOL@3',
  generator_id='AUTH-COVERAGE-002-SYNTHETIC-GENERATOR@3',split='DEV',commitment='a'*64)
except module.authority.AuthorityError: print('REJECTED'); raise SystemExit(0)
raise SystemExit(9)
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(G3_PATH), str(tmp_path)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert (result.returncode, result.stdout.strip()) == (0, "REJECTED")


def test_manual_and_modified_authority_objects_reject(generator3: Any, tmp_path: Path) -> None:
    verifier, store, _path, loaded = synthetic(generator3, tmp_path)
    forged = replace(loaded, semantic_seed_or_entropy_commitment="f" * 64)
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.CanonicalMaterializer(verifier, store).materialize(forged)
    manual = replace(loaded, _load_proof=object())
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.CanonicalMaterializer(verifier, store).materialize(manual)
    object.__setattr__(loaded, "semantic_seed_or_entropy_commitment", "e" * 64)
    with pytest.raises(generator3.authority.AuthorityError):
        verifier.assert_loaded(loaded)


def test_duck_typed_and_method_shadowed_verifiers_and_stores_reject(
    generator3: Any, tmp_path: Path
) -> None:
    verifier, store, path, loaded = synthetic(generator3, tmp_path)

    class DuckVerifier:
        synthetic = True

        def assert_loaded(self, _loaded: Any) -> None:
            return None

    class DuckStore:
        synthetic = True

    with pytest.raises(generator3.GovernanceError):
        generator3.CanonicalMaterializer(DuckVerifier(), store)
    with pytest.raises(generator3.GovernanceError):
        generator3.CanonicalMaterializer(verifier, DuckStore())
    verifier.assert_loaded = lambda _loaded: None
    with pytest.raises(generator3.GovernanceError):
        generator3.CanonicalMaterializer(verifier, store)
    verifier, store, _path, _loaded = synthetic(generator3, tmp_path, suffix="STORE-SHADOW")
    store.reconcile = lambda _split: "NOT_STARTED"
    with pytest.raises(generator3.GovernanceError):
        generator3.CanonicalMaterializer(verifier, store)
    verifier, store, _path, loaded = synthetic(generator3, tmp_path, suffix="ROOT-MUTATION")
    materializer = generator3.CanonicalMaterializer(verifier, store)
    store.root = tmp_path / "redirected"
    with pytest.raises(generator3.GovernanceError):
        materializer.materialize(loaded)
    real_store_for_mutation = generator3.MaterializationStore(
        generator3.REAL_STATE_ROOT, REAL_ATTEMPT
    )
    real_store_for_mutation.root = tmp_path / "redirected-real"
    with pytest.raises(generator3.GovernanceError):
        generator3.CanonicalMaterializer(
            generator3.authority.AuthorityVerifier(), real_store_for_mutation
        )
    real_store = generator3.MaterializationStore(
        generator3.REAL_STATE_ROOT, REAL_ATTEMPT
    )
    with pytest.raises(generator3.GovernanceError):
        generator3.canonical_materialize(path, real_store, verifier=verifier)
    real_verifier = generator3.authority.AuthorityVerifier()
    real_store = generator3.MaterializationStore(generator3.REAL_STATE_ROOT, REAL_ATTEMPT)
    real_verifier.synthetic = True
    real_store.synthetic = True
    real_store.root = tmp_path / "domain-flip"
    with pytest.raises(generator3.GovernanceError):
        generator3.CanonicalMaterializer(real_verifier, real_store)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol_id", "wrong"),
        ("record_count", 3),
        ("semantic_seed_or_entropy_commitment", "short"),
        ("provisioned_at", "not-utc"),
        ("gate_a_requirement", {"decision": "wrong"}),
    ],
)
def test_authority_bound_field_mutations_reject(
    generator3: Any, tmp_path: Path, field: str, value: Any
) -> None:
    verifier, _store, path, _loaded = synthetic(generator3, tmp_path)
    raw = json.loads(path.read_text())
    raw[field] = value
    raw.pop("artifact_digest")
    raw["artifact_digest"] = generator3.authority.digest(raw)
    path.write_text(json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n")
    verifier.approved_digests["VALIDATION"] = raw["artifact_digest"]
    with pytest.raises(generator3.authority.AuthorityError):
        verifier.load(path)


def test_authority_path_shape_and_digest_fail_closed(generator3: Any, tmp_path: Path) -> None:
    verifier, _store, path, _loaded = synthetic(generator3, tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    with pytest.raises(generator3.authority.AuthorityError):
        verifier.load(outside)
    path.write_text("not-json")
    with pytest.raises(generator3.authority.AuthorityError):
        verifier.load(path)
    path.write_text("[]")
    with pytest.raises(generator3.authority.AuthorityError):
        verifier.load(path)


def test_authority_digest_and_approval_registry_fail_closed(
    generator3: Any, tmp_path: Path
) -> None:
    verifier, _store, path, _loaded = synthetic(generator3, tmp_path)
    raw = json.loads(path.read_text())
    raw["semantic_seed_or_entropy_commitment"] = "f" * 64
    path.write_text(json.dumps(raw))
    with pytest.raises(generator3.authority.AuthorityError):
        verifier.load(path)
    raw.pop("artifact_digest")
    raw["artifact_digest"] = generator3.authority.digest(raw)
    path.write_text(json.dumps(raw))
    with pytest.raises(generator3.authority.AuthorityError):
        verifier.load(path)


def test_real_authority_requires_repository_provisioning(generator3: Any) -> None:
    verifier = generator3.authority.AuthorityVerifier()
    loaded = verifier.load(generator3.authority.authority_path("VALIDATION"))
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch",
         "experiments/AUTH-COVERAGE-002/protocol3/materialization_authority/validation-authority.json"],
        cwd=ROOT, capture_output=True, check=False,
    ).returncode == 0
    if tracked:
        verifier.assert_loaded(loaded)
    else:
        with pytest.raises(generator3.authority.AuthorityError):
            verifier.assert_loaded(loaded)


def test_synthetic_factory_rejects_invalid_split_commitment_and_gate_shape(
    generator3: Any, tmp_path: Path
) -> None:
    common = {
        "attempt_id": "AUTH-COVERAGE-002-SYNTHETIC-BAD-ATTEMPT",
        "protocol_id": "AUTH-COVERAGE-002-SYNTHETIC-BAD-PROTOCOL@3",
        "generator_id": "AUTH-COVERAGE-002-SYNTHETIC-BAD-GENERATOR@3",
    }
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.provision_synthetic_authority(
            tmp_path, split="PRODUCTION", commitment="a" * 64, **common
        )
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.provision_synthetic_authority(
            tmp_path, split="VALIDATION", commitment="short", **common
        )
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.authority.provision_synthetic_authority(
            tmp_path, split="HELD_OUT", commitment="a" * 64, **common
        )


def test_invalid_store_domains_reject(generator3: Any, tmp_path: Path) -> None:
    with pytest.raises(generator3.GovernanceError):
        generator3.MaterializationStore(tmp_path, REAL_ATTEMPT, synthetic=True)
    with pytest.raises(generator3.GovernanceError):
        generator3.MaterializationStore(
            tmp_path, "AUTH-COVERAGE-002-SYNTHETIC-NOFLAG-ATTEMPT"
        )


def test_no_seed_split_records_or_canonical_downgrade_arguments(generator3: Any) -> None:
    signature = inspect.signature(generator3.CanonicalMaterializer.materialize)
    assert set(signature.parameters) == {"self", "verified", "crash_at"}
    entry = inspect.signature(generator3.canonical_materialize)
    forbidden = {"seed", "split", "records", "canonical", "force", "retry"}
    assert not forbidden & set(entry.parameters)


def test_heldout_without_gate_rejects_before_generation(generator3: Any, tmp_path: Path) -> None:
    verifier, store, path, _loaded = synthetic(generator3, tmp_path, "HELD_OUT")
    calls = 0
    original = generator3.generator2.generate_authoring

    def spy(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    generator3.generator2.generate_authoring = spy
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.canonical_materialize(path, store, verifier=verifier)
    assert calls == 0
    assert store.reconcile("HELD_OUT") == "NOT_STARTED"


def test_heldout_canonical_false_rejects_before_consumption_or_generation(
    generator3: Any, tmp_path: Path
) -> None:
    verifier, store, path, _loaded = synthetic(generator3, tmp_path, "HELD_OUT")
    with pytest.raises(TypeError):
        generator3.canonical_materialize(
            path, store, verifier=verifier, canonical=False  # type: ignore[call-arg]
        )
    assert store.reconcile("HELD_OUT") == "NOT_STARTED"


def test_authority_replay_rejects_and_consumption_survives_restart(
    generator3: Any, tmp_path: Path
) -> None:
    verifier, store, path, loaded, _result = materialize(generator3, tmp_path)
    restarted = generator3.MaterializationStore(store.root, store.attempt_id, synthetic=True)
    assert restarted.reconcile("VALIDATION") == "SEALED"
    with pytest.raises(generator3.GovernanceError):
        generator3.CanonicalMaterializer(verifier, restarted).materialize(loaded)
    with pytest.raises(generator3.GovernanceError):
        generator3.canonical_materialize(path, restarted, verifier=verifier)


FRESH_PROCESS_PROGRAM = r"""
import hashlib, importlib.util, json, sys
from pathlib import Path
root, split, g3_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
spec=importlib.util.spec_from_file_location('g3_fresh_probe',g3_path)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
attempt='AUTH-COVERAGE-002-SYNTHETIC-FRESH-ATTEMPT'
protocol='AUTH-COVERAGE-002-SYNTHETIC-FRESH-PROTOCOL@3'
generator='AUTH-COVERAGE-002-SYNTHETIC-FRESH-GENERATOR@3'
authority_root=root/'authority'; requirement=None
if split == 'HELD_OUT':
 requirement={'decision':'AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE','required_bindings':['protocol_id','generator_id','corpus_attempt_id','canonical_dev_digest','canonical_validation_digest','evidence_digest']}
path=authority_root/f'{split.lower()}-authority.json'
if not path.exists():
 path,digest=module.authority.provision_synthetic_authority(authority_root,attempt_id=attempt,protocol_id=protocol,generator_id=generator,split=split,commitment=hashlib.sha256(f'{attempt}:{split}'.encode()).hexdigest(),gate_a_requirement=requirement,record_count=4)
else: digest=json.loads(path.read_text())['artifact_digest']
verifier=module.authority.AuthorityVerifier.synthetic(attempt_id=attempt,protocol_id=protocol,generator_id=generator,approved_digests={split:digest},authority_root=authority_root)
store=module.MaterializationStore(root/'state',attempt,synthetic=True)
try: module.canonical_materialize(path,store,verifier=verifier)
except Exception as exc: print(type(exc).__name__); raise SystemExit(17)
print(store.reconcile(split))
"""


def test_duplicate_validation_rejects_in_fresh_process(tmp_path: Path) -> None:
    command = [sys.executable, "-c", FRESH_PROCESS_PROGRAM, str(tmp_path),
               "VALIDATION", str(G3_PATH)]
    first = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    second = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert (first.returncode, first.stdout.strip()) == (0, "SEALED")
    assert second.returncode == 17 and "GovernanceError" in second.stdout


FRESH_REPLAY_PROGRAM = r"""
import importlib.util, json, sys
from pathlib import Path
g3_path, artifact, state_root, attempt, protocol, generator, gate = sys.argv[1:]
spec=importlib.util.spec_from_file_location('g3_replay_probe',Path(g3_path))
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
path=Path(artifact); digest=json.loads(path.read_text())['artifact_digest']
verifier=module.authority.AuthorityVerifier.synthetic(
 attempt_id=attempt,protocol_id=protocol,generator_id=generator,
 approved_digests={'HELD_OUT':digest},authority_root=path.parent)
store=module.MaterializationStore(Path(state_root),attempt,synthetic=True)
try: module.canonical_materialize(path,store,verifier=verifier,gate_a_path=Path(gate))
except Exception as exc: print(type(exc).__name__); raise SystemExit(17)
"""


def test_duplicate_heldout_rejects_in_fresh_process(generator3: Any, tmp_path: Path) -> None:
    suffix = "FRESH-HELD"
    store, verifier, path, gate = gate_fixture(generator3, tmp_path, suffix)
    gate_path = write_gate(generator3, path, gate)
    generator3.canonical_materialize(path, store, verifier=verifier, gate_a_path=gate_path)
    command = [sys.executable, "-c", FRESH_REPLAY_PROGRAM, str(G3_PATH), str(path),
               str(store.root), store.attempt_id, verifier.protocol_id, verifier.generator_id,
               str(gate_path)]
    replay = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert replay.returncode == 17 and "GovernanceError" in replay.stdout


CRASH_CASES = {
    "before_authority_verification": "NOT_STARTED",
    "after_authority_verification": "NOT_STARTED",
    "after_authority_consumption": "STARTED_UNOBSERVED",
    "after_started": "STARTED_UNOBSERVED", "before_first_write": "STARTED_UNOBSERVED",
    "during_first_write": "STARTED_UNOBSERVED",
    "after_first_fsync": "PARTIAL_OBSERVED_BLOCKED",
    "after_observation_boundary_event": "PARTIAL_OBSERVED_BLOCKED",
    "mid_generation": "PARTIAL_OBSERVED_BLOCKED",
    "after_last_record": "PARTIAL_OBSERVED_BLOCKED",
    "before_completed": "PARTIAL_OBSERVED_BLOCKED",
    "after_completed": "COMPLETED_UNSEALED", "before_manifest": "COMPLETED_UNSEALED",
    "after_manifest": "COMPLETED_UNSEALED",
    "during_manifest_verification": "COMPLETED_UNSEALED",
    "before_sealed": "COMPLETED_UNSEALED", "after_sealed": "SEALED",
}


FRESH_CRASH_PROGRAM = r"""
import hashlib, importlib.util, json, sys
from pathlib import Path
root, crash_at, g3_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
spec=importlib.util.spec_from_file_location('g3_crash_probe',g3_path)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
attempt='AUTH-COVERAGE-002-SYNTHETIC-FRESH-CRASH-ATTEMPT'
protocol='AUTH-COVERAGE-002-SYNTHETIC-FRESH-CRASH-PROTOCOL@3'
generator='AUTH-COVERAGE-002-SYNTHETIC-FRESH-CRASH-GENERATOR@3'
authority_root=root/'authority'
path,digest=module.authority.provision_synthetic_authority(
 authority_root,attempt_id=attempt,protocol_id=protocol,generator_id=generator,
 split='VALIDATION',commitment=hashlib.sha256(crash_at.encode()).hexdigest(),record_count=4)
verifier=module.authority.AuthorityVerifier.synthetic(
 attempt_id=attempt,protocol_id=protocol,generator_id=generator,
 approved_digests={'VALIDATION':digest},authority_root=authority_root)
store=module.MaterializationStore(root/'state',attempt,synthetic=True)
module.canonical_materialize(path,store,verifier=verifier,crash_at=crash_at)
"""

FRESH_RECONCILE_PROGRAM = r"""
import importlib.util, sys
from pathlib import Path
root, g3_path = Path(sys.argv[1]), Path(sys.argv[2])
spec=importlib.util.spec_from_file_location('g3_reconcile_probe',g3_path)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
attempt='AUTH-COVERAGE-002-SYNTHETIC-FRESH-CRASH-ATTEMPT'
store=module.MaterializationStore(root/'state',attempt,synthetic=True)
print(store.reconcile('VALIDATION'))
"""


@pytest.mark.parametrize(("crash_at", "expected"), CRASH_CASES.items())
def test_complete_crash_matrix_in_fresh_process(
    tmp_path: Path, crash_at: str, expected: str
) -> None:
    crash = subprocess.run(
        [sys.executable, "-c", FRESH_CRASH_PROGRAM, str(tmp_path), crash_at, str(G3_PATH)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert crash.returncode != 0
    reconcile = subprocess.run(
        [sys.executable, "-c", FRESH_RECONCILE_PROGRAM, str(tmp_path), str(G3_PATH)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert reconcile.returncode == 0
    assert reconcile.stdout.strip() == expected


@pytest.mark.parametrize(("crash_at", "expected"), CRASH_CASES.items())
def test_complete_crash_matrix(
    generator3: Any, tmp_path: Path, crash_at: str, expected: str
) -> None:
    verifier, store, path, _loaded = synthetic(generator3, tmp_path, suffix=crash_at.upper())
    with pytest.raises(generator3.CrashInjected):
        generator3.canonical_materialize(path, store, verifier=verifier, crash_at=crash_at)
    restarted = generator3.MaterializationStore(store.root, store.attempt_id, synthetic=True)
    assert restarted.reconcile("VALIDATION") == expected


@pytest.mark.parametrize("crash_at", ["after_authority_consumption", "during_first_write"])
def test_pre_observation_retry_reuses_same_authority(
    generator3: Any, tmp_path: Path, crash_at: str
) -> None:
    verifier, store, path, _loaded = synthetic(generator3, tmp_path, suffix=crash_at.upper())
    with pytest.raises(generator3.CrashInjected):
        generator3.canonical_materialize(path, store, verifier=verifier, crash_at=crash_at)
    generator3.canonical_materialize(path, store, verifier=verifier)
    assert store.reconcile("VALIDATION") == "SEALED"
    events = store._read_events("VALIDATION")
    assert sum(event["event"] == "AUTHORITY_CONSUMED" for event in events) == 1
    assert sum(event["event"] == "STARTED" for event in events) == 1


def test_ledger_deletion_truncation_and_rollback_fail_closed(
    generator3: Any, tmp_path: Path
) -> None:
    _verifier, store, _path, _loaded, _result = materialize(generator3, tmp_path)
    ledger = store.path("VALIDATION", "materialization-ledger.jsonl")
    complete = ledger.read_bytes()
    lines = complete.splitlines(keepends=True)
    ledger.write_bytes(b"".join(lines[:-1]))
    assert store.reconcile("VALIDATION") == "ANCHOR_MISMATCH"
    ledger.write_bytes(complete)
    assert store.reconcile("VALIDATION") == "SEALED"
    ledger.write_bytes(b"".join(lines[:2]))
    assert store.reconcile("VALIDATION") == "ANCHOR_MISMATCH"
    ledger.unlink()
    assert store.reconcile("VALIDATION") == "LEDGER_MISSING"


MANIFEST_FIELDS = ("manifest_schema", "protocol_id", "protocol_checksum", "generator_id",
                   "generator_checksum", "corpus_attempt_id", "split",
                   "authority_artifact_digest", "semantic_seed_or_entropy_commitment",
                   "record_count", "semantic_package_digest", "ordering_policy",
                   "runtime_id_policy", "source_sha", "ledger_head", "ledger_count",
                   "terminal_state")


@pytest.mark.parametrize("field", MANIFEST_FIELDS)
def test_every_manifest_binding_mutation_fails(
    generator3: Any, tmp_path: Path, field: str
) -> None:
    _verifier, store, _path, _loaded, _result = materialize(generator3, tmp_path)
    manifest_path = store.path("VALIDATION", "manifest.json")
    manifest = json.loads(manifest_path.read_text())
    manifest[field] = manifest[field] + 1 if isinstance(manifest[field], int) else "mutated"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(generator3.GovernanceError):
        generator3.verify_manifest(manifest_path, store, "VALIDATION")


def test_manifest_deletion_after_seal_fails_closed(generator3: Any, tmp_path: Path) -> None:
    _verifier, store, _path, _loaded, _result = materialize(generator3, tmp_path)
    store.path("VALIDATION", "manifest.json").unlink()
    assert store.reconcile("VALIDATION") == "MANIFEST_MISMATCH"


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("ledger", "LEDGER_CORRUPT"),
        ("anchor-delete", "ANCHOR_MISMATCH"),
        ("anchor-corrupt", "ANCHOR_MISMATCH"),
        ("state-delete", "STATE_INCONSISTENT"),
        ("state-corrupt", "STATE_INCONSISTENT"),
        ("state-mutate", "STATE_INCONSISTENT"),
    ],
)
def test_reconciliation_corruption_classes(
    generator3: Any, tmp_path: Path, target: str, expected: str
) -> None:
    suffix = target.upper()
    verifier, store, path, _loaded = synthetic(generator3, tmp_path, suffix=suffix)
    with pytest.raises(generator3.CrashInjected):
        generator3.canonical_materialize(path, store, verifier=verifier, crash_at="after_started")
    ledger = store.path("VALIDATION", "materialization-ledger.jsonl")
    anchor = store.path("VALIDATION", "ledger-anchor.json")
    state = store.path("VALIDATION", "state.json")
    if target == "ledger":
        ledger.write_text("not-json\n")
    elif target == "anchor-delete":
        anchor.unlink()
    elif target == "anchor-corrupt":
        anchor.write_text("not-json")
    elif target == "state-delete":
        state.unlink()
    elif target == "state-corrupt":
        state.write_text("[]")
    else:
        value = json.loads(state.read_text())
        value["ledger_count"] = 99
        state.write_text(json.dumps(value))
    assert store.reconcile("VALIDATION") == expected


def test_unsealed_digest_and_invalid_split_fail_closed(generator3: Any, tmp_path: Path) -> None:
    _verifier, store, _path, _loaded = synthetic(generator3, tmp_path)
    with pytest.raises(generator3.GovernanceError):
        store.sealed_digest("VALIDATION")
    with pytest.raises(generator3.GovernanceError):
        store.reconcile("PRODUCTION")


def seal_support(generator3: Any, tmp_path: Path, split: str, suffix: str, store: Any) -> None:
    verifier, _store, _path, loaded = synthetic(
        generator3, tmp_path, split, suffix=suffix, store=store
    )
    generator3.CanonicalMaterializer(verifier, store).materialize(loaded)


def gate_fixture(generator3: Any, tmp_path: Path, suffix: str) -> tuple[Any, ...]:
    attempt = f"AUTH-COVERAGE-002-SYNTHETIC-{suffix}-ATTEMPT"
    store = generator3.MaterializationStore(tmp_path / "state", attempt, synthetic=True)
    seal_support(generator3, tmp_path, "DEV", suffix, store)
    seal_support(generator3, tmp_path, "VALIDATION", suffix, store)
    verifier, _store, path, _loaded = synthetic(
        generator3, tmp_path, "HELD_OUT", suffix=suffix, store=store
    )
    evidence_path = path.parent / "gate-a-evidence.json"
    evidence_path.write_text('{"synthetic_gate_a_evidence":true}\n')
    evidence_digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    gate = {"protocol_id": verifier.protocol_id, "generator_id": verifier.generator_id,
            "corpus_attempt_id": verifier.attempt_id,
            "decision": "AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE",
            "canonical_dev_digest": store.sealed_digest("DEV"),
            "canonical_validation_digest": store.sealed_digest("VALIDATION"),
            "evidence_digest": evidence_digest,
            "governance_source": "AUTH-COVERAGE-002-GATE-A-INDEPENDENT-AUDIT"}
    return store, verifier, path, gate


def write_gate(generator3: Any, path: Path, gate: dict[str, Any]) -> Path:
    gate["artifact_digest"] = generator3.authority.digest(gate)
    gate_path = path.parent / "gate-a-approval.json"
    gate_path.write_text(json.dumps(gate, sort_keys=True, separators=(",", ":")) + "\n")
    return gate_path


def test_gate_a_exact_bindings_and_gate_b_separation(generator3: Any, tmp_path: Path) -> None:
    store, verifier, path, gate = gate_fixture(generator3, tmp_path, "GATE")
    gate_path = write_gate(generator3, path, gate)
    generator3.canonical_materialize(path, store, verifier=verifier, gate_a_path=gate_path)
    assert store.reconcile("HELD_OUT") == "SEALED"
    assert generator3.gate_a_authorizes_production(gate) is False
    assert generator3.gate_b_authorizes_materialization(
        "AUTHORIZED_TO_EXECUTE_HELDOUT_PRODUCTION_ONCE"
    ) is False


@pytest.mark.parametrize("field", ["protocol_id", "generator_id", "corpus_attempt_id",
                                    "decision", "canonical_dev_digest",
                                    "canonical_validation_digest", "evidence_digest"])
def test_gate_a_forgery_rejects(generator3: Any, tmp_path: Path, field: str) -> None:
    store, verifier, path, gate = gate_fixture(generator3, tmp_path, f"FORGE-{field.upper()}")
    gate[field] = "f" * 64 if field == "evidence_digest" else "forged"
    gate_path = write_gate(generator3, path, gate)
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.canonical_materialize(path, store, verifier=verifier, gate_a_path=gate_path)
    assert store.reconcile("HELD_OUT") == "NOT_STARTED"


@pytest.mark.parametrize("failure", ["malformed", "digest", "evidence-missing"])
def test_gate_a_artifact_integrity_failures(
    generator3: Any, tmp_path: Path, failure: str
) -> None:
    store, verifier, path, gate = gate_fixture(generator3, tmp_path, failure.upper())
    gate_path = write_gate(generator3, path, gate)
    if failure == "malformed":
        gate_path.write_text("not-json")
    elif failure == "digest":
        changed = json.loads(gate_path.read_text())
        changed["artifact_digest"] = "f" * 64
        gate_path.write_text(json.dumps(changed))
    else:
        (path.parent / "gate-a-evidence.json").unlink()
    with pytest.raises(generator3.authority.AuthorityError):
        generator3.canonical_materialize(path, store, verifier=verifier, gate_a_path=gate_path)


def test_import_has_no_governance_side_effect() -> None:
    before = sorted(str(path.relative_to(ROOT)) for path in ROOT.rglob("materialization_state/*"))
    completed = subprocess.run(
        [sys.executable, "-c", f"import runpy; runpy.run_path({str(G3_PATH)!r})"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    after = sorted(str(path.relative_to(ROOT)) for path in ROOT.rglob("materialization_state/*"))
    assert completed.returncode == 0 and before == after


def test_cli_has_no_canonical_materialization_or_bypass_options(generator3: Any) -> None:
    result = subprocess.run([sys.executable, str(G3_PATH), "--help"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0 and "materialize" not in result.stdout
    forbidden = {"--force", "--ignore-ledger", "--retry", "--reset", "--new-seed"}
    assert not forbidden & set(result.stdout.split())
    assert generator3._cli(["verify-authority", "VALIDATION"]) == 0
    assert generator3._cli(["disposable-dev", "--seed", "7", "--count", "4"]) == 0


def test_lower_level_generation_is_not_canonical(generator3: Any, tmp_path: Path) -> None:
    assert len(generator3.generator2.generate_authoring(42, "HELD_OUT", 4)) == 4
    assert not list(tmp_path.rglob("materialization-ledger.jsonl"))
    assert not list(tmp_path.rglob("manifest.json"))


def test_protocol3_and_predecessor_checksums_are_unchanged() -> None:
    files = ("experiments/AUTH-COVERAGE-002/protocol3/PROTOCOL3_SHA256SUMS",
             "experiments/AUTH-COVERAGE-002/protocol2/PROTOCOL2_SHA256SUMS",
             "experiments/AUTH-COVERAGE-002/protocol2/GENERATOR2_SHA256SUMS",
             "experiments/AUTH-COVERAGE-002/SUBSTRATE_SHA256SUMS")
    for name in files:
        completed = subprocess.run(["sha256sum", "--check", name], cwd=ROOT,
                                   capture_output=True, text=True, check=False)
        assert completed.returncode == 0, completed.stdout + completed.stderr


def test_anchor_copy_cannot_hide_ledger_rollback(generator3: Any, tmp_path: Path) -> None:
    verifier, store, path, _loaded = synthetic(generator3, tmp_path, suffix="ROLLBACK")
    with pytest.raises(generator3.CrashInjected):
        generator3.canonical_materialize(path, store, verifier=verifier,
                                         crash_at="after_started")
    ledger = store.path("VALIDATION", "materialization-ledger.jsonl")
    old_ledger = tmp_path / "old-ledger"
    shutil.copyfile(ledger, old_ledger)
    generator3.canonical_materialize(path, store, verifier=verifier)
    shutil.copyfile(old_ledger, ledger)
    assert store.reconcile("VALIDATION") == "ANCHOR_MISMATCH"
