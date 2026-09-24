"""Public real-filesystem mediation API."""

from safetybox.filesystem.adapter import FilesystemAdapter
from safetybox.filesystem.canonicalization import LOGICAL_ROOT, canonicalize_logical_path
from safetybox.filesystem.errors import (
    CanonicalizationError,
    FilesystemIndeterminateError,
    FilesystemMediationError,
    FilesystemPrimitiveError,
    FilesystemToolError,
    TargetValidationError,
)
from safetybox.filesystem.mapping import LogicalHostMapper
from safetybox.filesystem.models import (
    AuthorizationEvidence,
    FilesystemAuditEnvelope,
    FilesystemEntryType,
    FilesystemOperation,
    FilesystemRequest,
    FilesystemResult,
    FilesystemResultCategory,
    FilesystemStat,
    PhysicalValidationStatus,
    StateDigest,
)
from safetybox.filesystem.primitives import RealFilesystemPrimitives
from safetybox.filesystem.state_digest import digest_manifest
from safetybox.filesystem.versions import (
    FILESYSTEM_ADAPTER_VERSION,
    FILESYSTEM_AUDIT_ENVELOPE_VERSION,
    FILESYSTEM_CANONICALIZATION_VERSION,
    STATE_DIGEST_VERSION,
)

__all__ = [
    "AuthorizationEvidence",
    "CanonicalizationError",
    "FILESYSTEM_ADAPTER_VERSION",
    "FILESYSTEM_AUDIT_ENVELOPE_VERSION",
    "FILESYSTEM_CANONICALIZATION_VERSION",
    "FilesystemAdapter",
    "FilesystemAuditEnvelope",
    "FilesystemEntryType",
    "FilesystemIndeterminateError",
    "FilesystemMediationError",
    "FilesystemOperation",
    "FilesystemPrimitiveError",
    "FilesystemRequest",
    "FilesystemResult",
    "FilesystemResultCategory",
    "FilesystemStat",
    "FilesystemToolError",
    "LOGICAL_ROOT",
    "LogicalHostMapper",
    "PhysicalValidationStatus",
    "RealFilesystemPrimitives",
    "STATE_DIGEST_VERSION",
    "StateDigest",
    "TargetValidationError",
    "canonicalize_logical_path",
    "digest_manifest",
]
