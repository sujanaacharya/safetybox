"""Verification of pre-provisioned Generator@3 materialization authority.

This is a cooperative research-governance boundary.  It detects accidental or
ordinary caller substitution; it is not a hardware root of trust and cannot
defend against a privileged actor who rewrites the repository and verifier.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL_ID = "AUTH-COVERAGE-002-PROTOCOL@3"
PROTOCOL_CHECKSUM = "6959866f9ddb298e9cf5153544dc8a4551a83265"
GENERATOR_ID = "AUTH-COVERAGE-002-GENERATOR@3"
GENERATOR_IDENTITY_CHECKSUM = (
    "e792195d841a664137bc4c31bcfb83be0be421fe394c029d9c4feee96b953a94"
)
REAL_ATTEMPT_ID = "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"
AUTHORITY_SCHEMA = "AUTH-COVERAGE-002-MATERIALIZATION-AUTHORITY@1"
PURPOSE = "CANONICAL_MATERIALIZATION"
SPLITS = frozenset({"DEV", "VALIDATION", "HELD_OUT"})
GENERATOR2_SHA256 = "36b6ef0b0887b10627053087fdf156b62bdf4ff8caddd7798d1d2d8b1012b0a5"
AUTHORITY_ROOT = Path(__file__).resolve().parent / "materialization_authority"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REAL_ARTIFACT_DIGESTS = {
    "DEV": "207a3dc86beef6451d532a454ae2f8aee874dda3d4be01364e03900c6af3f65e",
    "VALIDATION": "277b8e2543c30a41d476983b75999be781b86c1811bdc7b925599793510713de",
    "HELD_OUT": "6a546cfc3b0c646b8dedf2498a185227f14636a57392fd9f8c05426f76180f45",
}
_LOAD_PROOF = object()


class AuthorityError(ValueError):
    pass


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class VerifiedAuthority:
    authority_schema_version: str
    protocol_id: str
    protocol_checksum: str
    generator_id: str
    generator_checksum: str
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
    """Loads exact pre-existing artifacts; it has no issuance operation."""

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
            if "SYNTHETIC" not in protocol_id or "SYNTHETIC" not in generator_id:
                raise AuthorityError("synthetic identities must be explicit")
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

    def _assert_configuration(self, *, real: bool) -> None:
        if real:
            if (
                self.attempt_id != REAL_ATTEMPT_ID
                or self.protocol_id != PROTOCOL_ID
                or self.generator_id != GENERATOR_ID
                or self.approved_digests != REAL_ARTIFACT_DIGESTS
                or self.authority_root != AUTHORITY_ROOT.resolve()
                or self.synthetic
            ):
                raise AuthorityError("canonical verifier configuration was modified")
        elif (
            not self.synthetic
            or "SYNTHETIC" not in self.attempt_id
            or "SYNTHETIC" not in self.protocol_id
            or "SYNTHETIC" not in self.generator_id
        ):
            raise AuthorityError("synthetic verifier configuration was modified")

    @classmethod
    def synthetic(
        cls,
        *,
        attempt_id: str,
        protocol_id: str,
        generator_id: str,
        approved_digests: dict[str, str],
        authority_root: Path,
    ) -> AuthorityVerifier:
        return cls(
            attempt_id=attempt_id,
            protocol_id=protocol_id,
            generator_id=generator_id,
            approved_digests=approved_digests,
            authority_root=authority_root,
            synthetic=True,
        )

    def load(
        self, path: Path, *, gate_a_path: Path | None = None, store: Any = None
    ) -> VerifiedAuthority:
        self._assert_configuration(real=self.attempt_id == REAL_ATTEMPT_ID)
        resolved = path.resolve()
        if resolved.parent != self.authority_root:
            raise AuthorityError("authority is not in the provisioned authority root")
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
        if split not in SPLITS or self.approved_digests.get(str(split)) != artifact_digest:
            raise AuthorityError("authority artifact was not provisioned")
        expected = {
            "authority_schema_version": AUTHORITY_SCHEMA,
            "protocol_id": self.protocol_id,
            "corpus_attempt_id": self.attempt_id,
            "split": split,
            "materialization_sequence": 1,
            "authorization_purpose": PURPOSE,
            "allowed_use_count": 1,
            "status": "PROVISIONED_NOT_CONSUMED",
            "semantic_source_sha256": GENERATOR2_SHA256,
        }
        if not self.synthetic:
            expected.update(
                protocol_checksum=PROTOCOL_CHECKSUM,
                generator_id=GENERATOR_ID,
                generator_checksum=GENERATOR_IDENTITY_CHECKSUM,
                governance_source=(
                    "AUTH-COVERAGE-002-PROTOCOL@3/FROZEN-SUCCESSOR-GENERATOR-AUTHORITY"
                ),
                record_count=800,
            )
        else:
            expected["generator_id"] = self.generator_id
        if any(raw.get(key) != value for key, value in expected.items()):
            raise AuthorityError("authority binding mismatch")
        if self.synthetic and (
            not isinstance(raw.get("record_count"), int)
            or raw["record_count"] < 2
            or raw["record_count"] % 2
        ):
            raise AuthorityError("synthetic record count must be positive and even")
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

    def assert_loaded(self, authority: VerifiedAuthority) -> None:
        real = authority.corpus_attempt_id == REAL_ATTEMPT_ID
        self._assert_configuration(real=real)
        if authority._load_proof is not _LOAD_PROOF or id(authority) not in self._loaded_ids:
            raise AuthorityError("authority was not loaded by the verifier")
        if self.approved_digests.get(authority.split) != authority.artifact_digest:
            raise AuthorityError("authority verifier mismatch")
        current = {
            key: value
            for key, value in vars(authority).items()
            if key not in {"artifact_digest", "_load_proof"}
        }
        if digest(current) != authority.artifact_digest:
            raise AuthorityError("loaded authority was modified")
        if real:
            self._assert_repository_provisioned(authority_path(authority.split))

    @staticmethod
    def _assert_repository_provisioned(path: Path) -> None:
        """Require bytes anchored in HEAD, outside the ordinary Python caller API."""
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
            raise AuthorityError("provisioned HELD_OUT authority is unusable without Gate A")
        resolved = path.resolve()
        # Gate A is a later governance artifact and must be installed at this fixed
        # repository location.  A caller-supplied object or alternate path is not authority.
        expected_path = self.authority_root / "gate-a-approval.json"
        if not self.synthetic and resolved != expected_path:
            raise AuthorityError("Gate A is not installed by repository governance")
        if not self.synthetic:
            self._assert_repository_provisioned(resolved)
            self._assert_repository_provisioned(self.authority_root / "gate-a-evidence.json")
        try:
            gate = json.loads(resolved.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthorityError("Gate A unavailable or malformed") from exc
        gate_digest = gate.get("artifact_digest") if isinstance(gate, dict) else None
        unsigned = dict(gate) if isinstance(gate, dict) else {}
        unsigned.pop("artifact_digest", None)
        if gate_digest != digest(unsigned):
            raise AuthorityError("Gate A digest mismatch")
        expected = {
            "protocol_id": self.protocol_id,
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
            evidence = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise AuthorityError("Gate A evidence artifact unavailable") from exc
        if gate.get("evidence_digest") != evidence:
            raise AuthorityError("Gate A evidence binding mismatch")


def authority_path(split: str) -> Path:
    if split not in SPLITS:
        raise AuthorityError("unsupported split")
    return AUTHORITY_ROOT / f"{split.lower()}-authority.json"


def provision_synthetic_authority(
    root: Path,
    *,
    attempt_id: str,
    protocol_id: str,
    generator_id: str,
    split: str,
    commitment: str,
    gate_a_requirement: dict[str, Any] | None = None,
    record_count: int = 8,
) -> tuple[Path, str]:
    """Test-only factory; synthetic identities are structurally unable to target reality."""
    if (
        attempt_id == REAL_ATTEMPT_ID
        or "SYNTHETIC" not in attempt_id
        or "SYNTHETIC" not in protocol_id
        or "SYNTHETIC" not in generator_id
    ):
        raise AuthorityError("test authority factory accepts synthetic identities only")
    if split not in SPLITS or len(commitment) != 64:
        raise AuthorityError("invalid synthetic authority request")
    if (split == "HELD_OUT") != (gate_a_requirement is not None):
        raise AuthorityError("synthetic HELD_OUT authority requires Gate A bindings")
    value: dict[str, Any] = {
        "authority_schema_version": AUTHORITY_SCHEMA,
        "protocol_id": protocol_id,
        "protocol_checksum": "synthetic-protocol-checksum",
        "generator_id": generator_id,
        "generator_checksum": GENERATOR_IDENTITY_CHECKSUM,
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
