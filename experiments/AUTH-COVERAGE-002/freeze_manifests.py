"""Materialize the checksum graph for the frozen AUTH-COVERAGE-002 corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments/AUTH-COVERAGE-002"
CORPUS = EXPERIMENT / "corpus"
MANIFESTS = CORPUS / "manifests"
FREEZE_DECISION = "BLOCKED_PREREGISTRATION_AND_EXPLANATION_COMPATIBILITY"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(name: str, identity: str, paths: list[Path], **metadata: object) -> Path:
    value = {
        "manifest_id": identity,
        "artifacts": [
            {"path": relative(path), "sha256": digest(path), "size_bytes": path.stat().st_size}
            for path in sorted(paths)
        ],
        **metadata,
    }
    destination = MANIFESTS / name
    destination.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination


def package_files(split_dir: str) -> list[Path]:
    directory = CORPUS / "runtime" / split_dir
    return list(directory.glob("*"))


def main() -> None:
    if FREEZE_DECISION != "FREEZE_READY_NOT_RUN":
        raise SystemExit(f"refusing to create freeze manifests: {FREEZE_DECISION}")
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    components = [
        write_manifest(
            "protocol_manifest.json",
            "AUTH-COVERAGE-002-PROTOCOL-MANIFEST@1",
            [
                ROOT / "docs/experiments/AUTH-COVERAGE-002_PROTOCOL.md",
                EXPERIMENT / "protocol.json",
                EXPERIMENT / "PROTOCOL_SHA256SUMS",
            ],
            protocol_first_commit="7840c0e",
        ),
        write_manifest(
            "normative_spec_manifest.json",
            "AUTH-COVERAGE-002-NORMATIVE-SPEC-MANIFEST@1",
            [ROOT / "docs/experiments/AUTH-COVERAGE-002_AUTHORIZATION_SPEC.md"],
        ),
        write_manifest(
            "oracles_manifest.json",
            "AUTH-COVERAGE-002-ORACLES-MANIFEST@1",
            [EXPERIMENT / "oracle_a.py", EXPERIMENT / "oracle_b.py"],
            oracle_agreement="4000/4000",
            production_imports=0,
        ),
        write_manifest(
            "dev_runtime_manifest.json",
            "AUTH-COVERAGE-002-DEV-RUNTIME-MANIFEST@1",
            package_files("DEV"),
            scenario_count=800,
        ),
        write_manifest(
            "validation_runtime_manifest.json",
            "AUTH-COVERAGE-002-VALIDATION-RUNTIME-MANIFEST@1",
            package_files("VALIDATION"),
            scenario_count=800,
        ),
        write_manifest(
            "held_out_runtime_manifest.json",
            "AUTH-COVERAGE-002-HELD-OUT-RUNTIME-MANIFEST@1",
            package_files("HELD_OUT-runtime"),
            scenario_count=2400,
            production_exposure=0,
        ),
        write_manifest(
            "analysis_manifest.json",
            "AUTH-COVERAGE-002-ANALYSIS-MANIFEST@1",
            [
                CORPUS / "analysis/analysis.json",
                CORPUS / "analysis/labels.json",
                CORPUS / "analysis/audit_report.json",
                CORPUS / "analysis/invalid_structure_controls.json",
                CORPUS / "analysis/scorer_compatibility.json",
                CORPUS / "analysis/fresh_process_isolation.json",
                CORPUS / "analysis/zero_exposure_audit.json",
            ],
            physically_separate_from_runtime=True,
        ),
        write_manifest(
            "pair_manifest.json",
            "AUTH-COVERAGE-002-PAIR-MANIFEST@1",
            [
                CORPUS / "analysis/pairs.json",
                CORPUS / "analysis/pairs.unreviewed.json",
            ],
            registered_pairs=2000,
            strict_strong=1600,
            weak=0,
            auditor_independent_of_generator=True,
        ),
        write_manifest(
            "difficulty_manifest.json",
            "AUTH-COVERAGE-002-DIFFICULTY-MANIFEST@1",
            [CORPUS / "analysis/difficulty.json"],
            assignment="independent structural audit",
        ),
        write_manifest(
            "split_manifest.json",
            "AUTH-COVERAGE-002-SPLIT-MANIFEST@1",
            [CORPUS / "analysis/split_assignment.json"],
            split_counts={"DEV": 800, "VALIDATION": 800, "HELD_OUT": 2400},
        ),
        write_manifest(
            "cross_tool_manifest.json",
            "AUTH-COVERAGE-002-CROSS-TOOL-MANIFEST@1",
            [
                CORPUS / "analysis/cross_tool_groups.json",
                CORPUS / "analysis/cross_tool_groups.unreviewed.json",
            ],
            strictly_comparable_groups=250,
            partial_groups=0,
            weak_groups=0,
        ),
        write_manifest(
            "external_pack_manifest.json",
            "AUTH-COVERAGE-002-EXTERNAL-PACK-MANIFEST@1",
            [EXPERIMENT / "contracts/external_pack.schema.json"],
            dual_oracle_verification_required=True,
        ),
        write_manifest(
            "research_contracts_manifest.json",
            "AUTH-COVERAGE-002-RESEARCH-CONTRACTS-MANIFEST@1",
            sorted((EXPERIMENT / "contracts").glob("*.json")),
        ),
        write_manifest(
            "construction_manifest.json",
            "AUTH-COVERAGE-002-CONSTRUCTION-MANIFEST@1",
            [
                EXPERIMENT / name
                for name in (
                    "schema.py",
                    "build_corpus.py",
                    "audit_corpus.py",
                    "bind_runtime.py",
                    "build_invalid_controls.py",
                    "validate_scorer_compatibility.py",
                    "audit_zero_exposure.py",
                    "audit_fresh_process_isolation.py",
                    "statistical_reporting.py",
                )
            ]
            + [EXPERIMENT / "formal/exhaustive_verify.py", CORPUS / "construction_receipt.json"],
        ),
        write_manifest(
            "review_manifest.json",
            "AUTH-COVERAGE-002-REVIEW-MANIFEST@1",
            [
                ROOT / "docs/engineering/AUTH-COVERAGE-002_ORACLE_INDEPENDENCE.md",
                ROOT / "docs/engineering/AUTH-COVERAGE-002_ADVERSARIAL_REVIEW.md",
                ROOT / "docs/engineering/AUTH-COVERAGE-002_PRE_RUN_VALIDITY_AUDIT.md",
                ROOT / "docs/engineering/AUTH-COVERAGE-002_FREEZE_REPORT.md",
            ],
            blocking_findings=0,
        ),
    ]
    root = {
        "manifest_id": "AUTH-COVERAGE-002-ROOT-MANIFEST@1",
        "protocol_id": "AUTH-COVERAGE-002-PROTOCOL@1",
        "corpus_id": "AUTH-COVERAGE-002-CORPUS@1",
        "substrate_sha": "8e3ba29bbadcdc9c4de4c0d306e8eaaf013dab78",
        "freeze_decision": "FREEZE_READY_NOT_RUN",
        "held_out_production_exposure": 0,
        "canonical_result_package": "ABSENT",
        "components": [
            {"path": relative(path), "sha256": digest(path)} for path in sorted(components)
        ],
    }
    (MANIFESTS / "root_manifest.json").write_text(
        json.dumps(root, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksum_paths = sorted(
        path
        for path in EXPERIMENT.rglob("*")
        if path.is_file()
        and path.name != "CORPUS_SHA256SUMS"
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )
    (EXPERIMENT / "CORPUS_SHA256SUMS").write_text(
        "".join(f"{digest(path)}  {relative(path)}\n" for path in checksum_paths),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
