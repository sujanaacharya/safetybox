"""Scoring-only records for EXP-015-CORPUS@2; never imported by materialization."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class PairStrength(StrEnum):
    STRONG = "STRONG"
    WEAK = "WEAK"


@dataclass(frozen=True, slots=True)
class ScoringLabel:
    scenario_id: str
    expected_exec_authority: str
    expected_cwd_authority: str
    expected_compound_authority: str
    expected_validation: str
    expected_terminal: str
    expected_spawn: str
    expected_argv_preservation: str
    expected_environment: str
    expected_output_metadata: str
    expected_failure_semantics: str
    authorization_quality: str
    difficulty: str
    requirement_coverage: tuple[str, ...]
    threat_coverage: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PairRecord:
    pair_id: str
    scenario_a: str
    scenario_b: str
    changed_dimension: str
    strength: PairStrength


ALLOWED_CHANGED_DIMENSIONS = frozenset(
    {"EXEC_CAPABILITY", "CWD_CAPABILITY", "TASK_BINDING", "EXEC_RESOURCE", "CWD_RESOURCE"}
)


def derive_manifest(labels: Iterable[ScoringLabel], pairs: Iterable[PairRecord]) -> dict[str, int]:
    """Compute all counts; no count is an author-entered manifest value."""

    labels = tuple(labels)
    pairs = tuple(pairs)
    if len({label.scenario_id for label in labels}) != len(labels):
        raise ValueError("scoring labels must have unique scenario IDs")
    if len({pair.pair_id for pair in pairs}) != len(pairs):
        raise ValueError("pair registry must have unique pair IDs")
    if any(pair.changed_dimension not in ALLOWED_CHANGED_DIMENSIONS for pair in pairs):
        raise ValueError("pair uses an unfrozen changed dimension")
    difficulty = Counter(label.difficulty for label in labels)
    terminal = Counter(label.expected_terminal for label in labels)
    return {
        "scenario_count": len(labels),
        "authorization_positive": sum(
            label.expected_compound_authority == "ALLOW" for label in labels
        ),
        "authorization_negative": sum(
            label.expected_compound_authority != "ALLOW" for label in labels
        ),
        "hard_benign": difficulty["HARD_BENIGN"],
        "hard_unauthorized": difficulty["HARD_UNAUTHORIZED"],
        "pair_count": len(pairs),
        "strong_pair_count": sum(pair.strength is PairStrength.STRONG for pair in pairs),
        "validation_case_count": sum(label.expected_validation != "SUCCEEDED" for label in labels),
        "execution_failure_count": sum(
            "FAIL" in value or "NONZERO" in value or "TIMEOUT" in value or "SIGNALED" in value
            for value in terminal
        ),
        "control_count": difficulty["PMED_L1_CONTROL"],
    }
