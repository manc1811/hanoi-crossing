"""M2: the start position, the seven-action space, and JSON round-tripping."""

from __future__ import annotations

import dataclasses
import json

import pytest

from hanoi_crossing.actions import Action
from hanoi_crossing.state import Outcome, Player, State, initial_state


def test_initial_state_stacks_largest_at_bottom() -> None:
    state = initial_state(3)
    assert state.pole_1a == (5, 3, 1)
    assert state.pole_1b == (6, 4, 2)
    assert state.pole_2 == ()
    assert state.pole_3a == ()
    assert state.pole_3b == ()
    assert state.hand_a is None
    assert state.hand_b is None
    assert state.step == 0
    assert state.outcome is Outcome.IN_PROGRESS


def test_initial_state_n1_matches_the_spec_example() -> None:
    state = initial_state(1)
    assert state.pole_1a == (1,)
    assert state.pole_1b == (2,)


def test_initial_state_rejects_n_below_one() -> None:
    with pytest.raises(ValueError):
        initial_state(0)


def test_state_is_frozen() -> None:
    state = initial_state(2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.pole_2 = (1,)  # type: ignore[misc]


@pytest.mark.parametrize(
    "state",
    [
        initial_state(1),
        initial_state(4),
        State(
            pole_1a=(5,),
            pole_1b=(),
            pole_2=(4, 2),
            pole_3a=(6, 3, 1),
            pole_3b=(),
            hand_a=None,
            hand_b=7,
            step=17,
            outcome=Outcome.A_WINS,
        ),
    ],
)
def test_dict_round_trip_through_json_is_identity(state: State) -> None:
    assert State.from_dict(json.loads(json.dumps(state.to_dict()))) == state


def test_action_space_is_seven_fixed_members() -> None:
    assert [a.name for a in Action] == [
        "LIFT_SOURCE",
        "LIFT_SHARED",
        "LIFT_TARGET",
        "PLACE_SOURCE",
        "PLACE_SHARED",
        "PLACE_TARGET",
        "SKIP",
    ]
    assert all(a.value == a.name for a in Action)


def test_players_round_trip_by_value() -> None:
    assert [Player(p.value) for p in Player] == [Player.A, Player.B]
