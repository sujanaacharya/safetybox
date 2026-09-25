"""DEV-only proofs for AUTH-COVERAGE-002-GENERATOR@2."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P2 = ROOT / "experiments/AUTH-COVERAGE-002/protocol2"
sys.path.insert(0, str(P2))
sys.path.insert(0, str(P2.parent))

from candidate_audit import _predicates  # noqa: E402
from generator2 import (  # noqa: E402
    DEV_SEEDS,
    dev_summary,
    generate_dev,
    materialize_runtime,
    runtime_fixture,
)
from governance import pair_audit, structural_hash  # noqa: E402
from leakage_suite import ATTACKS, run_secondary_targets, run_suite  # noqa: E402
from oracle_a import evaluate as oracle_a  # noqa: E402
from oracle_b import evaluate as oracle_b  # noqa: E402


def leakage_records(seed: int) -> list[dict[str, object]]:
    result = []
    for record in generate_dev(seed):
        runtime = runtime_fixture(record)
        predicates = _predicates(runtime)
        result.append(
            {
                **record,
                "runtime": runtime,
                "difficulty": "HARD" if predicates["difficulty"] >= 5 else "MODERATE",
                "input_digest": hashlib.sha256(
                    json.dumps(runtime, sort_keys=True).encode()
                ).hexdigest(),
            }
        )
    return result


def test_five_dev_seeds_are_deterministic_balanced_diverse_and_oracle_valid() -> None:
    digests: set[str] = set()
    for seed in DEV_SEEDS:
        first = generate_dev(seed)
        assert first == generate_dev(seed)
        summary = dev_summary(first)
        assert summary["count"] == 800
        assert summary["labels"] == {"ALLOW": 400, "DENY": 400}
        assert summary["tools"] == {"FILESYSTEM": 400, "PROCESS": 400}
        assert summary["semantic_templates"] == 800
        assert summary["largest_cluster"] == 1
        assert summary["max_branch_label_rate_deviation"] == 0.0
        assert summary["presentation"]["BENIGN_LOOKING_UNAUTHORIZED"] >= 130
        assert summary["presentation"]["SUSPICIOUS_AUTHORIZED"] >= 130
        assert summary["families"]["TASK_BINDING"] >= 120
        assert summary["families"]["RESOURCE_BOUNDARY"] >= 160
        assert summary["families"]["ACTION_BOUNDARY"] >= 120
        assert summary["families"]["CAPABILITY_SYNTHESIS"] >= 120
        assert summary["families"]["CAPABILITY_PRESENCE"] >= 140
        assert summary["families"]["CAPABILITY_DISTRACTOR"] >= 140
        digests.add(summary["semantic_digest"])
        for record in first:
            runtime = runtime_fixture(record)
            a, b = oracle_a(runtime), oracle_b(runtime)
            assert a == b
            assert a["decision"] == record["label"]
        by_pair: dict[str, list[dict[str, object]]] = {}
        for record in first:
            by_pair.setdefault(record["pair_id"], []).append(record)
        grades = Counter()
        for pair in by_pair.values():
            left, right = sorted(pair, key=lambda item: item["label"] == "DENY")
            grades[
                pair_audit(left["generator_pair_intention"], left, right)["quality_classification"]
            ] += 1
        assert grades == {"STRICT_STRONG": 400}
    assert len(digests) == len(DEV_SEEDS)


def test_dev_only_leakage_suite_executes_all_frozen_attacks_without_tuning() -> None:
    train, validation = leakage_records(DEV_SEEDS[0]), leakage_records(DEV_SEEDS[1])
    result = run_suite(train, validation, permutations=3)
    assert tuple(result) == ATTACKS
    assert max(value["accuracy"] for value in result.values()) <= 0.555
    assert all(value["evaluation_n"] == 800 for value in result.values())
    secondary = run_secondary_targets(train, validation)
    assert all(value["max_label_rate_deviation"] <= 0.05 for value in secondary.values())


def test_runtime_fixture_ids_are_dev_only_and_semantics_do_not_depend_on_id() -> None:
    record = generate_dev(DEV_SEEDS[0], 2)[0]
    fixture = runtime_fixture(record)
    changed = copy.deepcopy(fixture)
    changed["scenario_id"] = "f" * 64
    fixture.pop("scenario_id")
    changed.pop("scenario_id")
    assert fixture == changed
    invalid = copy.deepcopy(record)
    invalid["split"] = "HELD_OUT"
    try:
        runtime_fixture(invalid)
    except ValueError as error:
        assert "only DEV" in str(error)
    else:
        raise AssertionError("deterministic HELD_OUT fixture ID was incorrectly permitted")
    future = copy.deepcopy(record)
    future["split"] = "VALIDATION"
    first, second = materialize_runtime(future), materialize_runtime(future)
    assert first["scenario_id"] != second["scenario_id"]
    assert len(first["scenario_id"]) == 64
    try:
        materialize_runtime(future, lambda _: "constant")  # type: ignore[call-arg]
    except TypeError:
        pass
    else:
        raise AssertionError("non-DEV materialization accepted an injected ID allocator")


def test_dev_only_lane_simulation_proves_full_target_structural_capacity() -> None:
    lanes = (
        generate_dev(3002101, 800, template_root_offset=0),
        generate_dev(3002102, 800, template_root_offset=400),
        generate_dev(3002103, 2400, template_root_offset=800),
    )
    hashes = [[structural_hash(record["runtime"]) for record in lane] for lane in lanes]
    combined = Counter(value for lane in hashes for value in lane)
    assert len(combined) >= 3200
    assert max(combined.values()) <= 4
    assert len(set(hashes[0]) & set(hashes[1])) / len(set(hashes[1])) <= 0.25
    all_records = [record for lane in lanes for record in lane]
    quadrants = Counter()
    hard = Counter()
    cross_task_values: dict[tuple[str, str], set[str]] = {}
    for record in all_records:
        evaluated = oracle_a(runtime_fixture(record))
        decisions = "".join(value["decision"][0] for value in evaluated["components"].values())
        if len(decisions) == 2:
            quadrants[decisions] += 1
        hard[record["label"]] += _predicates(record["runtime"])["difficulty"] >= 5
        for capability in record["runtime"]["capabilities"]:
            cross_task_values.setdefault(
                (capability["action"], capability["resource"]), set()
            ).add(record["runtime"]["contract_task_id"])
    cross_task = sum(
        any(
            len(cross_task_values[(cap["action"], cap["resource"])]) > 1
            for cap in record["runtime"]["capabilities"]
        )
        for record in all_records
    )
    assert min(quadrants[name] for name in ("AA", "AD", "DA", "DD")) >= 250
    assert hard["ALLOW"] >= 1500 and hard["DENY"] >= 1500
    assert cross_task >= 300
