"""M4: the win predicate, evaluated for BOTH players after every action.

Written before win detection exists. The predicate under test is
hand empty AND pole 1 empty AND pole 2 empty AND pole 3 non-empty.
"""

from __future__ import annotations

import pytest

from hanoi_crossing.actions import Action
from hanoi_crossing.engine import ActionStatus, apply, legal_actions
from hanoi_crossing.state import Outcome, Player, State

# --- the four required cases -------------------------------------------------


def test_b_wins_on_as_turn() -> None:
    """B is set up but blocked by a disk on pole 2. A lifts it; B wins."""
    state = State(
        pole_1a=(3,),
        pole_1b=(),
        pole_2=(1,),
        pole_3a=(),
        pole_3b=(4, 2),
        hand_a=None,
        hand_b=None,
    )
    assert state.outcome is Outcome.IN_PROGRESS

    result = apply(state, Player.A, Action.LIFT_SHARED)

    assert result.status is ActionStatus.OK
    assert result.state.pole_2 == ()
    assert result.state.hand_a == 1, "A now holds the disk, so A cannot win"
    assert result.state.outcome is Outcome.B_WINS


def test_an_occupied_shared_pole_blocks_a_win_for_both_players() -> None:
    """Both sides are otherwise finished; the disk parked on pole 2 stops both."""
    blocked = State(
        pole_1a=(),
        pole_1b=(),
        pole_2=(5,),
        pole_3a=(3, 1),
        pole_3b=(4, 2),
        hand_a=None,
        hand_b=None,
    )
    assert apply(blocked, Player.A, Action.SKIP).state.outcome is Outcome.IN_PROGRESS
    assert apply(blocked, Player.B, Action.SKIP).state.outcome is Outcome.IN_PROGRESS


def test_a_foreign_disk_on_your_pole_3_does_not_block_your_win() -> None:
    """The condition is positional: disk 2 is B's, and A's disk 1 is on 3b."""
    state = State(
        pole_1a=(),
        pole_1b=(4,),
        pole_2=(),
        pole_3a=(3,),
        pole_3b=(1,),
        hand_a=2,
        hand_b=None,
    )
    result = apply(state, Player.A, Action.PLACE_TARGET)

    assert result.status is ActionStatus.OK
    assert result.state.pole_3a == (3, 2)
    assert result.state.outcome is Outcome.A_WINS


def test_everything_clear_but_an_empty_pole_3_is_not_a_win() -> None:
    """Total giveaway is a losing line: pole 3 must hold at least one disk."""
    state = State(
        pole_1a=(),
        pole_1b=(4,),
        pole_2=(),
        pole_3a=(),
        pole_3b=(3, 2, 1),
        hand_a=None,
        hand_b=None,
    )
    assert apply(state, Player.A, Action.SKIP).state.outcome is Outcome.IN_PROGRESS


# --- the rest of the predicate -----------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [("pole_1a", (5,)), ("pole_2", (5,)), ("hand_a", 5)],
)
def test_each_clause_of_the_predicate_blocks_a_win(field: str, value: object) -> None:
    winning = {"pole_3a": (3, 1), "pole_1b": (2,)}
    result = apply(State(**winning, **{field: value}), Player.B, Action.SKIP)
    assert result.state.outcome is Outcome.IN_PROGRESS


def test_a_wins_when_the_predicate_is_met() -> None:
    state = State(pole_1b=(4, 2), pole_3a=(3,), hand_a=1)
    result = apply(state, Player.A, Action.PLACE_TARGET)
    assert result.state.pole_3a == (3, 1)
    assert result.state.outcome is Outcome.A_WINS


def test_the_win_is_evaluated_after_an_illegal_action_too() -> None:
    """The board does not change, so a blocked position stays blocked."""
    state = State(pole_2=(5,), pole_3a=(3, 1), pole_3b=(4, 2))
    result = apply(state, Player.A, Action.PLACE_TARGET)  # hand is empty
    assert result.status is ActionStatus.ILLEGAL
    assert result.state.outcome is Outcome.IN_PROGRESS


def test_simultaneous_win_is_a_draw() -> None:
    """Totality only: B already satisfies the predicate and A completes theirs.

    `apply` would not have produced this position with outcome IN_PROGRESS, so
    this is not a counterexample to the DECISIONS.md unreachability conjecture.
    """
    state = State(pole_1b=(), pole_2=(), pole_3b=(2,), hand_a=1, hand_b=None)
    result = apply(state, Player.A, Action.PLACE_TARGET)
    assert result.state.pole_3a == (1,)
    assert result.state.outcome is Outcome.DRAW


def test_outcome_has_the_five_locked_members() -> None:
    assert [o.name for o in Outcome] == [
        "IN_PROGRESS",
        "A_WINS",
        "B_WINS",
        "DRAW",
        "UNFINISHED",
    ]


# --- terminal states ---------------------------------------------------------


def won() -> State:
    """A position A has already won."""
    state = State(pole_1b=(4, 2), pole_3a=(3,), hand_a=1)
    return apply(state, Player.A, Action.PLACE_TARGET).state


def test_a_terminal_state_accepts_no_further_actions() -> None:
    terminal = won()
    assert terminal.outcome is Outcome.A_WINS
    for player in Player:
        for action in Action:
            result = apply(terminal, player, action)
            assert result.state == terminal, "the board must not move"
            assert result.state.step == terminal.step, "the step must not advance"
            assert result.status is ActionStatus.GAME_OVER
            assert result.reason is None


def test_a_terminal_state_has_no_legal_actions() -> None:
    for player in Player:
        assert legal_actions(won(), player) == frozenset()
