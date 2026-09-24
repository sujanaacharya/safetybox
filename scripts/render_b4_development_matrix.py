"""Render the frozen-shape development-only B4 capability matrix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class MatrixRow(TypedDict):
    family: str
    b2_parity: bool
    b4_distinguishes: bool
    primitive: str


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    matrix_path = (
        repository
        / "docs"
        / "experiments"
        / "EXP-013-B4-DEVELOPMENT-CAPABILITY-MATRIX.json"
    )
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    rows: list[MatrixRow] = payload["rows"]
    print("| Family | B2 parity achieved? | B4 distinguishes? | Primitive used |")
    print("|---|---:|---:|---|")
    for row in rows:
        parity = "yes" if row["b2_parity"] else "no"
        distinguishes = "yes" if row["b4_distinguishes"] else "no"
        print(
            f"| {row['family']} | {parity} | {distinguishes} | {row['primitive']} |"
        )


if __name__ == "__main__":
    main()
