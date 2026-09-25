"""Corpus-authorship gate against exact reuse of substrate DEV fixtures."""

from __future__ import annotations

import json
from pathlib import Path

CONTAMINATION_REGISTRY_ID = "AUTH-COVERAGE-002-DEV-CONTAMINATION-REGISTRY@1"
DEV_SCENARIO_IDENTIFIER_INVENTORY = frozenset(
    {
        "dev-inconsistent",
        "dev-missing",
        "dev-only",
        "dev-opaque-7bd37f2b",
        "dev-random-a1",
        "dev-random-b2",
        "dev-random-c3",
        "dev-random-d4",
        "dev-random-e5",
        "dev-random-id-one",
        "dev-random-id-two",
        "dev-unknown",
        "opaque",
        "opaque-dev-0",
        "opaque-dev-1",
        "opaque-dev-correlation-a",
        "opaque-dev-correlation-z",
        "opaque-dev-id-498762b1",
        "opaque-dev-id-a75cc70f",
        "opaque-dev-id-other",
        "opaque-dev-scoring-1",
        "opaque-heldout-id-two",
    }
)
DEV_CANONICAL_INPUT_DIGEST_INVENTORY = frozenset(
    {
        "1ad468fd394a7143d830fa872a14da356a14fc1083c1a40315b822d5fc9b7e9e",
        "53a6522b7f6348b02d202fd8e1385a6ca302ff8db3fc3721808071da3b2ef37e",
        "8fec7a9099e0611d4066443cbe287efd073dbdb5fb73a3c76124f7de1fd8673b",
        "905924730dfd59ab5dfa1a59b7b452c77c2eefb482f3a5f8533a247bfe3f653a",
        "fcff42b4e91c8ee02a716586af8485b77ed4bb435ac2a5d226c214734b3f3f5b",
    }
)


class DevelopmentContaminationError(ValueError):
    """A proposed corpus input exactly reuses registered development material."""


def assert_not_development_contaminated(
    *,
    scenario_id: str,
    canonical_input_digest: str,
    registry_path: Path,
) -> None:
    value = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("registry_id") != CONTAMINATION_REGISTRY_ID:
        raise DevelopmentContaminationError("unknown contamination registry")
    identifiers = value.get("scenario_identifiers")
    digests = value.get("canonical_input_digests")
    if not isinstance(identifiers, list) or not isinstance(digests, list):
        raise DevelopmentContaminationError("malformed contamination registry")
    if scenario_id in identifiers:
        raise DevelopmentContaminationError("scenario identifier reuses a DEV fixture")
    if canonical_input_digest in digests:
        raise DevelopmentContaminationError("authorization input exactly reuses a DEV fixture")
