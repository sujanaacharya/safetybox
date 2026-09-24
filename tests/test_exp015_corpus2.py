"""Corpus@2 offline freeze gate; no ProcessAdapter execution is permitted."""
from __future__ import annotations

import runpy
from pathlib import Path


def test_exp015_corpus2_integrity() -> None:
    runpy.run_path(Path("experiments/EXP-015/corpus2/integrity_check.py"), run_name="__main__")
