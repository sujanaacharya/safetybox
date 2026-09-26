"""Verification-only authority boundary for Generator@4.

No real authority artifacts are provisioned in this freeze.  The synthetic
factory is restricted to explicit synthetic attempts and generator identities.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL_ID = "AUTH-COVERAGE-002-PROTOCOL@4"
PROTOCOL_CHECKSUM = "31f2ee9e504de74f6b93e5a860fd6d92ae5f7fa2"
GENERATOR_ID = "AUTH-COVERAGE-002-GENERATOR@4"
GENERATOR_IDENTITY_CHECKSUM = (
    "db9dd09fa8014f4b1c79fae7b8cd76330fedb7a6162808ab5e5be95bf625be24"
)
SUBSTRATE_ID = "AUTH-COVERAGE-002-SUBSTRATE@2"
SUBSTRATE_CHECKSUM = "d9d827c9544cc4f27bb0d925adf1091a9dd4f6081d8f984b07c8df154739cc60"
REAL_ATTEMPT_ID = "AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1"
AUTHORITY_SCHEMA = "AUTH-COVERAGE-002-MATERIALIZATION-AUTHORITY@2"
PURPOSE = "CANONICAL_MATERIALIZATION"
SPLITS = frozenset({"DEV", "VALIDATION", "HELD_OUT"})
REAL_RECORD_COUNTS = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 2400}
GENERATOR2_SHA256 = "36b6ef0b0887b10627053087fdf156b62bdf4ff8caddd7798d1d2d8b1012b0a5"
AUTHORITY_ROOT = Path(__file__).resolve().parent / "materialization_authority"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

# Intentionally empty until the separately governed authority-provisioning task.
REAL_ARTIFACT_DIGESTS: dict[str, str] = {}
REAL_REGISTRY_PATH = AUTHORITY_ROOT / "authority-registry.json"
_LOAD_PROOF = object()


class AuthorityError(ValueError):
    """An authority artifact or verifier failed closed."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def real_artifact_digests() -> dict[str, str]:
    """Load a future fixed-path, Git-provisioned registry; fail closed while absent."""
    AuthorityVerifier._assert_repository_provisioned(REAL_REGISTRY_PATH)
    try:
        raw = json.loads(REAL_REGISTRY_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityError("real authority registry unavailable or malformed") from exc
    if not isinstance(raw, dict):
        raise AuthorityError("real authority registry is not an object")
    unsigned = dict(raw)
    recorded = unsigned.pop("artifact_digest", None)
    if recorded != digest(unsigned):
        raise AuthorityError("real authority registry digest mismatch")
    expected = {
        "schema": "AUTH-COVERAGE-002-AUTHORITY-REGISTRY@4",
        "protocol_id": PROTOCOL_ID,
        "protocol_checksum": PROTOCOL_CHECKSUM,
        "generator_id": GENERATOR_ID,
        "generator_checksum": GENERATOR_IDENTITY_CHECKSUM,
        "substrate_id": SUBSTRATE_ID,
        "substrate_checksum": SUBSTRATE_CHECKSUM,
        "corpus_attempt_id": REAL_ATTEMPT_ID,
        "status": "PROVISIONED_NOT_CONSUMED",
    }
    if any(raw.get(key) != value for key, value in expected.items()):
        raise AuthorityError("real authority registry binding mismatch")
    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != SPLITS:
        raise AuthorityError("real authority registry split set mismatch")
    if any(not isinstance(value, str) or len(value) != 64 for value in artifacts.values()):
        raise AuthorityError("real authority registry contains an invalid digest")
    return {str(key): str(value) for key, value in artifacts.items()}


@dataclass(frozen=True)
class VerifiedAuthority:
    authority_schema_version: str
    protocol_id: str
    protocol_checksum: str
    generator_id: str
    generator_checksum: str
    substrate_id: str
    substrate_checksum: str
    corpus_attempt_id: str
    split: str
    semantic_seed_or_entropy_commitment: str
    materialization_sequence: int
    authorization_purpose: str
    allowed_use_count: int
    gate_a_requirement: dict[str, Any] | None
    governance_source: str
    status: str
    record_count: int
    provisioned_at: str
    semantic_source_sha256: str
    artifact_digest: str
    _load_proof: object


class AuthorityVerifier:
    """Load approved artifacts only; this class has no real issuance operation."""

    def __init__(
        self,
        *,
        attempt_id: str = REAL_ATTEMPT_ID,
        protocol_id: str = PROTOCOL_ID,
        generator_id: str = GENERATOR_ID,
        approved_digests: dict[str, str] | None = None,
        authority_root: Path = AUTHORITY_ROOT,
        synthetic: bool = False,
    ):
        if synthetic:
            if attempt_id == REAL_ATTEMPT_ID or "SYNTHETIC" not in attempt_id:
                raise AuthorityError("synthetic authority cannot target the real attempt")
            if protocol_id != PROTOCOL_ID or "SYNTHETIC" not in generator_id:
                raise AuthorityError("synthetic verifier retains exact Protocol@4 binding")
        elif (attempt_id, protocol_id, generator_id) != (
            REAL_ATTEMPT_ID,
            PROTOCOL_ID,
            GENERATOR_ID,
        ):
            raise AuthorityError("canonical verifier identities are fixed")
        elif approved_digests is not None or authority_root.resolve() != AUTHORITY_ROOT.resolve():
            raise AuthorityError("canonical authority root and digest registry are immutable")
        self.attempt_id = attempt_id
        self.protocol_id = protocol_id
        self.generator_id = generator_id
        self.approved_digests = approved_digests or dict(REAL_ARTIFACT_DIGESTS)
        self.authority_root = authority_root.resolve()
        self.synthetic = synthetic
        self._loaded_ids: set[int] = set()

    @classmethod
    def for_synthetic(
        cls,
        *,
        attempt_id: str,
        generator_id: str,
        approved_digests: dict[str, str],
        authority_root: Path,
    ) -> AuthorityVerifier:
        return cls(
            attempt_id=attempt_id,
            protocol_id=PROTOCOL_ID,
            generator_id=generator_id,
            approved_digests=approved_digests,
            authority_root=authority_root,
            synthetic=True,
        )

    def _assert_configuration(self, *, real: bool) -> None:
        if real:
            valid = (
                self.attempt_id == REAL_ATTEMPT_ID
                and self.protocol_id == PROTOCOL_ID
                and self.generator_id == GENERATOR_ID
                and self.approved_digests == REAL_ARTIFACT_DIGESTS
                and self.authority_root == AUTHORITY_ROOT.resolve()
                and not self.synthetic
            )
        else:
            valid = (
                self.synthetic
                and "SYNTHETIC" in self.attempt_id
                and self.protocol_id == PROTOCOL_ID
                and "SYNTHETIC" in self.generator_id
            )
        if not valid:
            raise AuthorityError("authority verifier configuration was modified")

    def load(
        self, path: Path, *, gate_a_path: Path | None = None, store: Any = None
    ) -> VerifiedAuthority:
        real = self.attempt_id == REAL_ATTEMPT_ID
        self._assert_configuration(real=real)
        resolved = path.resolve()
        if resolved.parent != self.authority_root:
            raise AuthorityError("authority is not in the provisioned authority root")
        if real:
            self._assert_repository_provisioned(resolved)
        try:
            raw = json.loads(resolved.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthorityError("authority artifact unavailable or malformed") from exc
        if not isinstance(raw, dict):
            raise AuthorityError("authority artifact must be an object")
        artifact_digest = raw.get("artifact_digest")
        unsigned = dict(raw)
        unsigned.pop("artifact_digest", None)
        if artifact_digest != digest(unsigned):
            raise AuthorityError("authority artifact digest mismatch")
        split = raw.get("split")
        approved = real_artifact_digests() if real else self.approved_digests
        if split not in SPLITS or approved.get(str(split)) != artifact_digest:
            raise AuthorityError("authority artifact was not provisioned")
        if resolved.name != f"{str(split).lower()}-authority.json":
            raise AuthorityError("authority path/split binding mismatch")
        expected = {
            "authority_schema_version": AUTHORITY_SCHEMA,
            "protocol_id": PROTOCOL_ID,
            "protocol_checksum": PROTOCOL_CHECKSUM,
            "generator_id": self.generator_id,
            "generator_checksum": GENERATOR_IDENTITY_CHECKSUM,
            "substrate_id": SUBSTRATE_ID,
            "substrate_checksum": SUBSTRATE_CHECKSUM,
            "corpus_attempt_id": self.attempt_id,
            "split": split,
            "semantic_source_sha256": GENERATOR2_SHA256,
            "materialization_sequence": 1,
            "authorization_purpose": PURPOSE,
            "allowed_use_count": 1,
            "status": "PROVISIONED_NOT_CONSUMED",
            "record_count": REAL_RECORD_COUNTS[str(split)] if real else raw.get("record_count"),
            "governance_source": (
                "AUTH-COVERAGE-002-PROTOCOL@4/FROZEN-SUCCESSOR-GENERATOR-AUTHORITY"
                if real
                else "SYNTHETIC-TEST-GOVERNANCE"
            ),
        }
        if any(raw.get(key) != value for key, value in expected.items()):
            raise AuthorityError("authority binding mismatch")
        if not isinstance(raw.get("record_count"), int) or raw["record_count"] < 2:
            raise AuthorityError("record count must be positive and at least two")
        if raw["record_count"] % 2:
            raise AuthorityError("record count must be even")
        commitment = raw.get("semantic_seed_or_entropy_commitment")
        if not isinstance(commitment, str) or len(commitment) != 64:
            raise AuthorityError("invalid entropy commitment")
        provisioned_at = raw.get("provisioned_at")
        if not isinstance(provisioned_at, str) or not provisioned_at.endswith("Z"):
            raise AuthorityError("invalid provisioning timestamp")
        requirement = raw.get("gate_a_requirement")
        if split == "HELD_OUT":
            self._verify_gate_a(requirement, gate_a_path, store)
        elif requirement is not None or gate_a_path is not None:
            raise AuthorityError("Gate A is only valid for HELD_OUT")
        fields = {
            name: raw[name]
            for name in VerifiedAuthority.__dataclass_fields__
            if name != "_load_proof"
        }
        verified = VerifiedAuthority(**fields, _load_proof=_LOAD_PROOF)
        self._loaded_ids.add(id(verified))
        return verified

    def assert_loaded(self, verified: VerifiedAuthority) -> None:
        real = verified.corpus_attempt_id == REAL_ATTEMPT_ID
        self._assert_configuration(real=real)
        if verified._load_proof is not _LOAD_PROOF or id(verified) not in self._loaded_ids:
            raise AuthorityError("authority was not loaded by this verifier")
        approved = real_artifact_digests() if real else self.approved_digests
        if approved.get(verified.split) != verified.artifact_digest:
            raise AuthorityError("authority verifier mismatch")
        current = {
            key: value
            for key, value in vars(verified).items()
            if key not in {"artifact_digest", "_load_proof"}
        }
        if digest(current) != verified.artifact_digest:
            raise AuthorityError("loaded authority was modified")
        if real:
            self._assert_repository_provisioned(authority_path(verified.split))

    @staticmethod
    def _assert_repository_provisioned(path: Path) -> None:
        try:
            relative = path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
            completed = subprocess.run(
                ["git", "show", f"HEAD:{relative}"],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                check=False,
            )
            working = path.read_bytes()
        except (OSError, ValueError) as exc:
            raise AuthorityError("governance artifact is not repository provisioned") from exc
        if completed.returncode != 0 or completed.stdout != working:
            raise AuthorityError("governance artifact is not repository provisioned")

    def _verify_gate_a(self, requirement: object, path: Path | None, store: Any) -> None:
        if not isinstance(requirement, dict) or path is None or store is None:
            raise AuthorityError("HELD_OUT authority requires Gate A")
        resolved = path.resolve()
        if not self.synthetic and resolved != self.authority_root / "gate-a-approval.json":
            raise AuthorityError("Gate A path is not repository governed")
        if not self.synthetic:
            self._assert_repository_provisioned(resolved)
            self._assert_repository_provisioned(self.authority_root / "gate-a-evidence.json")
        try:
            gate = json.loads(resolved.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthorityError("Gate A unavailable or malformed") from exc
        unsigned = dict(gate) if isinstance(gate, dict) else {}
        recorded = unsigned.pop("artifact_digest", None)
        if recorded != digest(unsigned):
            raise AuthorityError("Gate A digest mismatch")
        expected = {
            "protocol_id": PROTOCOL_ID,
            "generator_id": self.generator_id,
            "corpus_attempt_id": self.attempt_id,
            "decision": requirement.get("decision"),
            "canonical_dev_digest": store.sealed_digest("DEV"),
            "canonical_validation_digest": store.sealed_digest("VALIDATION"),
            "governance_source": "AUTH-COVERAGE-002-GATE-A-INDEPENDENT-AUDIT",
        }
        if any(gate.get(key) != value for key, value in expected.items()):
            raise AuthorityError("Gate A binding mismatch")
        evidence_path = self.authority_root / "gate-a-evidence.json"
        try:
            evidence_digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise AuthorityError("Gate A evidence artifact unavailable") from exc
        if gate.get("evidence_digest") != evidence_digest:
            raise AuthorityError("Gate A evidence binding mismatch")


def authority_path(split: str) -> Path:
    if split not in SPLITS:
        raise AuthorityError("unsupported split")
    return AUTHORITY_ROOT / f"{split.lower()}-authority.json"


def provision_synthetic_authority(
    root: Path,
    *,
    attempt_id: str,
    generator_id: str,
    split: str,
    commitment: str,
    gate_a_requirement: dict[str, Any] | None = None,
    record_count: int = 8,
) -> tuple[Path, str]:
    """Create a non-real test fixture that still binds exact Protocol@4/Substrate@2."""
    if attempt_id == REAL_ATTEMPT_ID or "SYNTHETIC" not in attempt_id:
        raise AuthorityError("synthetic factory cannot target the real attempt")
    if "SYNTHETIC" not in generator_id or generator_id == GENERATOR_ID:
        raise AuthorityError("synthetic factory cannot target Generator@4 reality")
    if split not in SPLITS or len(commitment) != 64 or record_count < 2 or record_count % 2:
        raise AuthorityError("invalid synthetic authority request")
    if (split == "HELD_OUT") != (gate_a_requirement is not None):
        raise AuthorityError("synthetic HELD_OUT authority requires Gate A")
    value: dict[str, Any] = {
        "authority_schema_version": AUTHORITY_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "protocol_checksum": PROTOCOL_CHECKSUM,
        "generator_id": generator_id,
        "generator_checksum": GENERATOR_IDENTITY_CHECKSUM,
        "substrate_id": SUBSTRATE_ID,
        "substrate_checksum": SUBSTRATE_CHECKSUM,
        "corpus_attempt_id": attempt_id,
        "split": split,
        "semantic_seed_or_entropy_commitment": commitment,
        "materialization_sequence": 1,
        "authorization_purpose": PURPOSE,
        "allowed_use_count": 1,
        "gate_a_requirement": gate_a_requirement,
        "governance_source": "SYNTHETIC-TEST-GOVERNANCE",
        "status": "PROVISIONED_NOT_CONSUMED",
        "record_count": record_count,
        "provisioned_at": "2000-01-01T00:00:00Z",
        "semantic_source_sha256": GENERATOR2_SHA256,
    }
    value["artifact_digest"] = digest(value)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{split.lower()}-authority.json"
    path.write_bytes(canonical_json(value) + b"\n")
    return path, str(value["artifact_digest"])
