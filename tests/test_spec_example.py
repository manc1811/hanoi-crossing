"""The assignment's own N=1 walkthrough, encoded as an executable spec.

Source: docs/ASSIGNMENT.md, section "Example (N = 1)". This test is written
against the target API before that API exists; it goes green at M4, once win
detection lands.
"""

from __future__ import annotations

from hanoi_crossing.actions import Action
from hanoi_crossing.engine import ActionStatus, apply
from hanoi_crossing.state import Outcome, Player, initial_state

# "Turn order: [A, B, A]" — an explicit sequence, no pattern assumed.
TURN_ORDER = [Player.A, Player.B, Player.A]

# Actions are player-relative: for A, SOURCE/TARGET are 1a/3a; for B, 1b/3b.
MOVES = [
    Action.LIFT_SOURCE,   # 1. A lifts disk 1 from pole 1a
    Action.LIFT_SOURCE,   # 2. B lifts disk 2 from pole 1b
    Action.PLACE_TARGET,  # 3. A places disk 1 onto pole 3a — A wins
]


def test_spec_n1_example() -> None:
    """A wins on step 3 of the spec's N=1 example."""
    state = initial_state(1)
    assert state.pole_1a == (1,)
    assert state.pole_1b == (2,)
    assert state.pole_2 == ()
    assert state.pole_3a == ()
    assert state.pole_3b == ()
    assert state.hand_a is None
    assert state.hand_b is None
    assert state.step == 0
    assert state.outcome is Outcome.IN_PROGRESS

    for step, (player, action) in enumerate(zip(TURN_ORDER, MOVES)):
        result = apply(state, player, action)
        assert result.status is ActionStatus.OK, (step, player, action, result.reason)
        assert result.state.step == step + 1
        state = result.state

    # A's hand is empty and, of A's visible poles, only 3a has disks.
    assert state.hand_a is None
    assert state.pole_1a == ()
    assert state.pole_2 == ()
    assert state.pole_3a == (1,)
    assert state.outcome is Outcome.A_WINS

    # B is still holding disk 2, so B does not win simultaneously.
    assert state.hand_b == 2
    assert state.pole_1b == ()
    assert state.pole_3b == ()
