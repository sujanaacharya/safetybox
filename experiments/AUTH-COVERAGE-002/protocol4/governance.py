"""Protocol@4 state model; this module creates no materialization authority."""

from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_ID = "AUTH-COVERAGE-002-PROTOCOL@4"
CORPUS_ATTEMPT_ID = "AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1"
GENERATOR_ID = "AUTH-COVERAGE-002-GENERATOR@4"
SPLITS = frozenset({"DEV", "VALIDATION", "HELD_OUT"})
STATES = frozenset(
    {
        "NOT_AUTHORIZED",
        "AUTHORIZED_ONCE",
        "MATERIALIZING",
        "MATERIALIZED",
        "SEALED",
        "PARTIAL",
        "BLOCKED",
    }
)


class GovernanceError(ValueError):
    pass


@dataclass(frozen=True)
class Authorization:
    protocol_id: str
    generator_id: str
    attempt_id: str
    split: str
    source_sha: str
    seed_commitment: str


def authorize(state: str, token: Authorization) -> str:
    if (
        state != "NOT_AUTHORIZED"
        or token.protocol_id != PROTOCOL_ID
        or token.generator_id != GENERATOR_ID
        or token.attempt_id != CORPUS_ATTEMPT_ID
        or token.split not in SPLITS
    ):
        raise GovernanceError("invalid or reused Protocol@4 materialization authorization")
    if token.split == "HELD_OUT":
        raise GovernanceError("Gate A authorization is required for HELD_OUT")
    return "AUTHORIZED_ONCE"


def start(state: str) -> str:
    if state != "AUTHORIZED_ONCE":
        raise GovernanceError("materialization may start only once from authorization")
    return "MATERIALIZING"


def complete(state: str) -> str:
    if state != "MATERIALIZING":
        raise GovernanceError("completion requires materializing state")
    return "MATERIALIZED"


def seal(state: str) -> str:
    if state != "MATERIALIZED":
        raise GovernanceError("sealing requires completed materialization")
    return "SEALED"


def partial(state: str) -> str:
    if state != "MATERIALIZING":
        raise GovernanceError("partial state requires materializing state")
    return "PARTIAL"


def block(state: str) -> str:
    if state not in STATES - {"SEALED", "BLOCKED"}:
        raise GovernanceError("terminal state cannot reopen")
    return "BLOCKED"


def authorize_held_out(gate_a: str, state: str, token: Authorization) -> str:
    if gate_a != "AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE":
        raise GovernanceError("Gate A is the sole HELD_OUT authority")
    if token.split != "HELD_OUT":
        raise GovernanceError("wrong split")
    if state != "NOT_AUTHORIZED" or (
        token.protocol_id,
        token.generator_id,
        token.attempt_id,
    ) != (PROTOCOL_ID, GENERATOR_ID, CORPUS_ATTEMPT_ID):
        raise GovernanceError("invalid Protocol@4 held-out authorization")
    return "AUTHORIZED_ONCE"


def production_authorized(gate_b: str, held_out_state: str) -> bool:
    return gate_b == "AUTHORIZED_TO_EXECUTE_HELDOUT_PRODUCTION_ONCE" and held_out_state == "SEALED"
