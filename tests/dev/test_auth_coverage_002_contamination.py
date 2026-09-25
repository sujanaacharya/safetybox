import json
from pathlib import Path

import pytest

from safetybox.research.auth_coverage_contamination import (
    DEV_CANONICAL_INPUT_DIGEST_INVENTORY,
    DEV_SCENARIO_IDENTIFIER_INVENTORY,
    DevelopmentContaminationError,
    assert_not_development_contaminated,
)

REGISTRY = Path("experiments/AUTH-COVERAGE-002/dev/contamination_registry.json")


def test_registered_dev_identifier_and_input_are_rejected() -> None:
    with pytest.raises(DevelopmentContaminationError, match="identifier"):
        assert_not_development_contaminated(
            scenario_id="dev-opaque-7bd37f2b",
            canonical_input_digest="0" * 64,
            registry_path=REGISTRY,
        )
    with pytest.raises(DevelopmentContaminationError, match="input"):
        assert_not_development_contaminated(
            scenario_id="new-opaque-id",
            canonical_input_digest=(
                "8fec7a9099e0611d4066443cbe287efd073dbdb5fb73a3c76124f7de1fd8673b"
            ),
            registry_path=REGISTRY,
        )


def test_novel_fixture_passes_contamination_gate() -> None:
    assert_not_development_contaminated(
        scenario_id="novel-opaque-id",
        canonical_input_digest="f" * 64,
        registry_path=REGISTRY,
    )


def test_frozen_registry_matches_maintained_fixture_inventory() -> None:
    value = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert set(value["scenario_identifiers"]) == DEV_SCENARIO_IDENTIFIER_INVENTORY
    assert set(value["canonical_input_digests"]) == DEV_CANONICAL_INPUT_DIGEST_INVENTORY
    assert value["held_out_scenarios_authored"] == 0
    assert value["held_out_prediction_exposure"] == 0
