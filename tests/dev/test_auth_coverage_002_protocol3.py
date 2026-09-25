import importlib.util
import sys
from pathlib import Path

P = Path("experiments/AUTH-COVERAGE-002/protocol3/governance.py")
spec = importlib.util.spec_from_file_location("protocol3_governance", P)
assert spec and spec.loader
g = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = g
spec.loader.exec_module(g)


def token(split="VALIDATION"):
    return g.Authorization(
        g.PROTOCOL_ID, g.GENERATOR_ID, g.CORPUS_ATTEMPT_ID, split, "a" * 40, "b" * 64
    )


def test_validation_one_shot_and_terminal_blocking():
    state = g.seal(g.complete(g.start(g.authorize("NOT_AUTHORIZED", token()))))
    assert state == "SEALED"
    for action in (lambda: g.authorize(state, token()), lambda: g.block(state)):
        try:
            action()
        except g.GovernanceError:
            pass
        else:
            raise AssertionError("terminal realization reopened")


def test_heldout_requires_gate_a_and_production_requires_gate_b():
    try:
        g.authorize("NOT_AUTHORIZED", token("HELD_OUT"))
    except g.GovernanceError:
        pass
    else:
        raise AssertionError("HELD_OUT bypassed Gate A")
    state = g.authorize_held_out(
        "AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE", "NOT_AUTHORIZED", token("HELD_OUT")
    )
    assert state == "AUTHORIZED_ONCE"
    assert not g.production_authorized(
        "AUTHORIZED_TO_EXECUTE_HELDOUT_PRODUCTION_ONCE", "MATERIALIZED"
    )
    assert g.production_authorized("AUTHORIZED_TO_EXECUTE_HELDOUT_PRODUCTION_ONCE", "SEALED")


def test_partial_is_spent_and_cannot_resume_or_change_seed():
    state = g.partial(g.start(g.authorize("NOT_AUTHORIZED", token())))
    assert g.block(state) == "BLOCKED"
    try:
        g.start(state)
    except g.GovernanceError:
        pass
    else:
        raise AssertionError("partial realization resumed")
