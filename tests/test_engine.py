"""M3: legality and `apply`. Written before engine.py exists.

Win detection is M4 — nothing here asserts an outcome other than the
`IN_PROGRESS` the state started with.
"""

from __future__ import annotations

import dataclasses

import pytest

from hanoi_crossing.actions import Action
from hanoi_crossing.engine import (
    ActionStatus,
    IllegalReason,
    apply,
    legal_actions,
)
from hanoi_crossing.state import Player, State, initial_state

HAND = {Player.A: "hand_a", Player.B: "hand_b"}

# (player, place action, destination pole field) for all six visible destinations.
DESTINATIONS = [
    (Player.A, Action.PLACE_SOURCE, "pole_1a"),
    (Player.A, Action.PLACE_SHARED, "pole_2"),
    (Player.A, Action.PLACE_TARGET, "pole_3a"),
    (Player.B, Action.PLACE_SOURCE, "pole_1b"),
    (Player.B, Action.PLACE_SHARED, "pole_2"),
    (Player.B, Action.PLACE_TARGET, "pole_3b"),
]

# (player, lift action, source pole field) for all six visible sources.
SOURCES = [
    (Player.A, Action.LIFT_SOURCE, "pole_1a"),
    (Player.A, Action.LIFT_SHARED, "pole_2"),
    (Player.A, Action.LIFT_TARGET, "pole_3a"),
    (Player.B, Action.LIFT_SOURCE, "pole_1b"),
    (Player.B, Action.LIFT_SHARED, "pole_2"),
    (Player.B, Action.LIFT_TARGET, "pole_3b"),
]

# A spread of positions for the sweep-style tests.
SAMPLE_STATES = [
    initial_state(1),
    initial_state(3),
    State(pole_1a=(5, 3), pole_1b=(6,), pole_2=(4,), pole_3a=(2,), pole_3b=(8, 7)),
    State(pole_1a=(3,), pole_2=(2,), pole_3b=(9,), hand_a=1, hand_b=6),
]


# --- the five illegal reasons ------------------------------------------------


def test_empty_pole_lifting_from_a_pole_with_no_disks() -> None:
    result = apply(State(pole_1a=(3,)), Player.A, Action.LIFT_SHARED)
    assert result.status is ActionStatus.ILLEGAL
    assert result.reason is IllegalReason.EMPTY_POLE


def test_hand_full_lifting_while_already_holding() -> None:
    result = apply(State(pole_1a=(3,), hand_a=1), Player.A, Action.LIFT_SOURCE)
    assert result.status is ActionStatus.ILLEGAL
    assert result.reason is IllegalReason.HAND_FULL


def test_hand_empty_placing_with_nothing_in_hand() -> None:
    result = apply(State(pole_1a=(3,)), Player.A, Action.PLACE_TARGET)
    assert result.status is ActionStatus.ILLEGAL
    assert result.reason is IllegalReason.HAND_EMPTY


def test_size_violation_placing_a_larger_disk_on_a_smaller_one() -> None:
    result = apply(State(pole_3a=(1,), hand_a=3), Player.A, Action.PLACE_TARGET)
    assert result.status is ActionStatus.ILLEGAL
    assert result.reason is IllegalReason.SIZE_VIOLATION


def test_pole_not_visible_is_unreachable_through_the_relative_action_space() -> None:
    """The member exists for totality; the seven relative actions cannot produce it.

    Every action names a pole the acting player can see, by construction. The
    substance of the rule is asserted by the hidden-pole test below.
    """
    assert IllegalReason.POLE_NOT_VISIBLE in IllegalReason
    for state in SAMPLE_STATES:
        for player in Player:
            for action in Action:
                result = apply(state, player, action)
                assert result.reason is not IllegalReason.POLE_NOT_VISIBLE


def test_no_action_touches_the_opponents_hidden_poles_or_hand() -> None:
    hidden = {Player.A: ("pole_1b", "pole_3b", "hand_b"),
              Player.B: ("pole_1a", "pole_3a", "hand_a")}
    for state in SAMPLE_STATES:
        for player in Player:
            for action in Action:
                after = apply(state, player, action).state
                for field in hidden[player]:
                    assert getattr(after, field) == getattr(state, field)


def test_illegal_reason_has_exactly_the_five_locked_members() -> None:
    assert [r.name for r in IllegalReason] == [
        "EMPTY_POLE",
        "HAND_FULL",
        "HAND_EMPTY",
        "SIZE_VIOLATION",
        "POLE_NOT_VISIBLE",
    ]


# --- strictly-larger placement, on every pole --------------------------------


@pytest.mark.parametrize(("player", "action", "field"), DESTINATIONS)
def test_larger_onto_smaller_is_illegal_on_every_pole(
    player: Player, action: Action, field: str
) -> None:
    state = State(**{field: (3,), HAND[player]: 5})
    result = apply(state, player, action)
    assert result.status is ActionStatus.ILLEGAL
    assert result.reason is IllegalReason.SIZE_VIOLATION
    assert getattr(result.state, field) == (3,)


@pytest.mark.parametrize(("player", "action", "field"), DESTINATIONS)
def test_smaller_onto_larger_is_legal_on_every_pole(
    player: Player, action: Action, field: str
) -> None:
    state = State(**{field: (5,), HAND[player]: 3})
    result = apply(state, player, action)
    assert result.status is ActionStatus.OK
    assert result.reason is None
    assert getattr(result.state, field) == (5, 3)
    assert getattr(result.state, HAND[player]) is None


@pytest.mark.parametrize(("player", "action", "field"), DESTINATIONS)
def test_placing_onto_an_empty_pole_is_legal_everywhere(
    player: Player, action: Action, field: str
) -> None:
    state = State(**{HAND[player]: 4})
    result = apply(state, player, action)
    assert result.status is ActionStatus.OK
    assert getattr(result.state, field) == (4,)


def test_size_rule_ignores_ownership() -> None:
    """Placement is positional: a foreign disk is just a disk of that size."""
    onto_foreign = apply(State(pole_2=(2,), hand_a=1), Player.A, Action.PLACE_SHARED)
    assert onto_foreign.status is ActionStatus.OK
    assert onto_foreign.state.pole_2 == (2, 1)

    under_foreign = apply(State(pole_2=(2,), hand_a=3), Player.A, Action.PLACE_SHARED)
    assert under_foreign.reason is IllegalReason.SIZE_VIOLATION


# --- interpretations 6 and "lift from your own pole 3" -----------------------


def test_placing_onto_your_own_pole_1_is_legal() -> None:
    result = apply(State(pole_1a=(5, 3), hand_a=1), Player.A, Action.PLACE_SOURCE)
    assert result.status is ActionStatus.OK
    assert result.state.pole_1a == (5, 3, 1)
    assert result.state.hand_a is None


def test_lifting_from_your_own_pole_3_is_legal() -> None:
    result = apply(State(pole_3b=(6, 2)), Player.B, Action.LIFT_TARGET)
    assert result.status is ActionStatus.OK
    assert result.state.pole_3b == (6,)
    assert result.state.hand_b == 2


@pytest.mark.parametrize(("player", "action", "field"), SOURCES)
def test_lifting_the_top_disk_is_legal_from_every_visible_pole(
    player: Player, action: Action, field: str
) -> None:
    state = State(**{field: (7, 3)})
    result = apply(state, player, action)
    assert result.status is ActionStatus.OK
    assert getattr(result.state, field) == (7,)
    assert getattr(result.state, HAND[player]) == 3


@pytest.mark.parametrize(("player", "action", "field"), SOURCES)
def test_lifting_from_an_empty_pole_is_illegal_everywhere(
    player: Player, action: Action, field: str
) -> None:
    result = apply(State(), player, action)
    assert result.reason is IllegalReason.EMPTY_POLE


# --- purity, step accounting, SKIP -------------------------------------------


def test_illegal_action_leaves_the_input_state_unmutated_but_advances_step() -> None:
    before = State(pole_1a=(3,), pole_2=(2,), hand_a=1, step=7)
    snapshot = dataclasses.replace(before)
    result = apply(before, Player.A, Action.LIFT_SOURCE)

    assert result.status is ActionStatus.ILLEGAL
    assert before == snapshot, "apply must not mutate its input"
    assert result.state is not before
    assert result.state == dataclasses.replace(snapshot, step=8)


def test_step_advances_on_every_action_including_skips_and_illegals() -> None:
    for state in SAMPLE_STATES:
        for player in Player:
            for action in Action:
                assert apply(state, player, action).state.step == state.step + 1


def test_skip_is_its_own_status_and_changes_nothing_but_the_step() -> None:
    before = State(pole_1a=(3,), hand_b=2, step=4)
    result = apply(before, Player.A, Action.SKIP)
    assert result.status is ActionStatus.SKIPPED
    assert result.reason is None
    assert result.state == dataclasses.replace(before, step=5)


def test_apply_never_raises() -> None:
    for state in SAMPLE_STATES:
        for player in Player:
            for action in Action:
                apply(state, player, action)


# --- legal_actions -----------------------------------------------------------


def test_legal_actions_at_the_start_is_lift_source_or_skip() -> None:
    assert legal_actions(initial_state(3), Player.A) == frozenset(
        {Action.LIFT_SOURCE, Action.SKIP}
    )


def test_legal_actions_while_holding_a_disk_is_places_or_skip() -> None:
    state = State(pole_1a=(3,), hand_a=1)
    assert legal_actions(state, Player.A) == frozenset(
        {Action.PLACE_SOURCE, Action.PLACE_SHARED, Action.PLACE_TARGET, Action.SKIP}
    )


def test_legal_actions_agrees_with_apply() -> None:
    for state in SAMPLE_STATES:
        for player in Player:
            expected = frozenset(
                action
                for action in Action
                if apply(state, player, action).status is not ActionStatus.ILLEGAL
            )
            assert legal_actions(state, player) == expected


def test_skip_is_always_legal() -> None:
    for state in SAMPLE_STATES:
        for player in Player:
            assert Action.SKIP in legal_actions(state, player)
