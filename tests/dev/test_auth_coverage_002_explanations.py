"""Full-component structured explanation contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "experiments/AUTH-COVERAGE-002/explanation_scoring.py"


def test_explanation_scorer_exports_frozen_full_component_path() -> None:
    spec = importlib.util.spec_from_file_location("auth002_explanation", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.RULE_MAP["POL-COMPOUND-DENY"] == "AUTH.ANY_COMPONENT_DENIED"
    assert module.explanation_summary([[], ["component[cwd].rule"]]) == {
        "contract_id": "AUTH-COVERAGE-002-EXPLANATION-CONTRACT@1",
        "complete": 1,
        "denominator": 2,
        "rate": 0.5,
        "errors": 1,
    }
