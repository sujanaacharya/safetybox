#!/usr/bin/env python3
"""Versioned repair of the frozen Protocol@2 candidate-audit constructor.

All scientific metric derivation and gate evaluation remain delegated to the
frozen substrate.  This successor changes only ``realized_split`` construction:
the exact split schema is emitted even when one or more counts are zero.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any, cast

HERE = Path(__file__).resolve().parent
EXPERIMENT_ROOT = HERE.parent
FROZEN_ROOT = EXPERIMENT_ROOT / "protocol2"
REQUIRED_SPLITS = ("DEV", "VALIDATION", "HELD_OUT")
SUBSTRATE_ID = "AUTH-COVERAGE-002-SUBSTRATE@2"


def _load_frozen_candidate_audit() -> ModuleType:
    """Load the frozen module without retaining ambiguous bare-name imports."""
    local_names = (
        "external_pack",
        "governance",
        "leakage_suite",
        "oracle_a",
        "oracle_b",
        "schema",
    )
    saved: dict[str, ModuleType | None] = {
        name: sys.modules.pop(name, None) for name in local_names
    }
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(FROZEN_ROOT))
        sys.path.insert(0, str(EXPERIMENT_ROOT))
        spec = importlib.util.spec_from_file_location(
            "auth_coverage_002_frozen_candidate_audit", FROZEN_ROOT / "candidate_audit.py"
        )
        if spec is None or spec.loader is None:
            raise ImportError("cannot load frozen candidate audit")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        for name in local_names:
            sys.modules.pop(name, None)
            old_module = saved[name]
            if old_module is not None:
                sys.modules[name] = old_module


_frozen = _load_frozen_candidate_audit()
evaluate_gates = _frozen.evaluate_gates


def construct_realized_split(records: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Construct the frozen exact-key split mapping, retaining explicit zeros."""
    counts = Counter(record["split"] for record in records)
    required = {name: counts[name] for name in REQUIRED_SPLITS}
    # Preserve unexpected keys so the unchanged exact-key validator rejects
    # them with the same classification as the frozen constructor.
    unexpected = {
        str(name): value for name, value in counts.items() if name not in required
    }
    return {**required, **unexpected}


def derive_metrics(candidate: dict[str, Any]) -> dict[str, Any]:
    """Delegate frozen derivation, replacing only the defective representation."""
    metrics = cast(dict[str, Any], _frozen.derive_metrics(candidate))
    metrics["realized_split"] = construct_realized_split(candidate["records"])
    return metrics


def audit_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], evaluate_gates(derive_metrics(candidate)))
