"""Offline construction audits for AUTH-COVERAGE-001.

Nothing in this package imports or invokes SafetyBox production authorization.
"""

from .audit_core import (
    AuditFailure,
    audit_corpus,
    audit_duplicates,
    audit_leakage,
    audit_pairs,
    baseline_attacks,
    score_predictions,
)

__all__ = [
    "AuditFailure",
    "audit_corpus",
    "audit_duplicates",
    "audit_leakage",
    "audit_pairs",
    "baseline_attacks",
    "score_predictions",
]
