"""Keep flat, versioned research-module namespaces isolated during collection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

FLAT_RESEARCH_MODULES = frozenset({"schema", "oracle_a", "oracle_b", "exhaustive_verify"})


def pytest_collectstart(collector: pytest.Collector) -> None:
    """Discard aliases before collecting another independently versioned experiment."""
    path = Path(str(getattr(collector, "path", "")))
    if path.suffix == ".py" and "auth_coverage" in path.name.casefold():
        for name in FLAT_RESEARCH_MODULES:
            sys.modules.pop(name, None)
