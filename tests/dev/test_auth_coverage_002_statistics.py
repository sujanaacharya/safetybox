"""Tests for the preregistered AUTH-COVERAGE-002 sensitivity intervals."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "experiments/AUTH-COVERAGE-002/statistical_reporting.py"
SPEC = importlib.util.spec_from_file_location("auth_coverage_002_statistics", MODULE_PATH)
assert SPEC and SPEC.loader
statistics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(statistics)


def test_clopper_pearson_known_boundary_and_symmetry() -> None:
    low, high = statistics.clopper_pearson(0, 100)
    assert low == 0.0
    assert high == pytest.approx(0.0362166926)
    reflected = statistics.clopper_pearson(100, 100)
    assert reflected[0] == pytest.approx(1.0 - high)
    assert reflected[1] == 1.0


def test_exact_zero_error_bound() -> None:
    assert statistics.exact_zero_error_upper_bound(100) == pytest.approx(0.0295130496)


def test_cluster_bootstrap_is_deterministic_and_preserves_clusters() -> None:
    observations = [("a", True), ("a", True), ("b", False), ("b", False)]
    first = statistics.clustered_accuracy_interval(
        observations, seed_label="unit", replicates=1_000
    )
    second = statistics.clustered_accuracy_interval(
        reversed(observations), seed_label="unit", replicates=1_000
    )
    assert first == second
    assert first == (0.0, 1.0)


@pytest.mark.parametrize("successes,trials", [(-1, 10), (11, 10), (0, 0)])
def test_exact_interval_rejects_invalid_counts(successes: int, trials: int) -> None:
    with pytest.raises(ValueError):
        statistics.clopper_pearson(successes, trials)
