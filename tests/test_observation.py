"""M5: `observe` hands a player their own view and nothing more."""

from __future__ import annotations

import dataclasses

import pytest

from hanoi_crossing.observation import Observation, observe
from hanoi_crossing.state import Player, State, initial_state

#: A position where every one of B's hidden disks has a distinct, checkable size.
HIDDEN_FROM_A = State(
    pole_1a=(5,),
    pole_1b=(8,),
    pole_2=(1,),
    pole_3a=(7, 3),
    pole_3b=(6, 4),
    hand_a=None,
    hand_b=2,
)

#: The disks A must not be able to reach: B's poles 1b and 3b, and B's hand.
B_HIDDEN_DISKS = frozenset({8, 6, 4, 2})


def test_observation_for_a_has_no_field_for_bs_poles_or_hand() -> None:
    """Structural: there is nowhere in an Observation for 1b, 3b or hand_b to live."""
    names = {f.name for f in dataclasses.fields(Observation)}
    assert names == {
        "player",
        "source",
        "shared",
        "target",
        "hand",
        "own_disks",
        "opponent_holding",
    }
    assert not any("1b" in n or "3b" in n or n.endswith("_b") for n in names)


def test_observation_for_a_exposes_no_disk_of_bs_hidden_disks() -> None:
    obs = observe(HIDDEN_FROM_A, Player.A)
    reachable = set(obs.source) | set(obs.shared) | set(obs.target)
    if obs.hand is not None:
        reachable.add(obs.hand)
    assert reachable == {5, 1, 7, 3}
    assert reachable.isdisjoint(B_HIDDEN_DISKS)
    assert repr(obs).count("1b") == 0 and repr(obs).count("3b") == 0


def test_a_sees_that_b_holds_a_disk_but_not_which() -> None:
    obs = observe(HIDDEN_FROM_A, Player.A)
    assert obs.opponent_holding is True
    values = [getattr(obs, f.name) for f in dataclasses.fields(obs)]
    assert 2 not in [v for v in values if isinstance(v, int)]


def test_opponent_holding_is_false_with_an_empty_opposing_hand() -> None:
    state = dataclasses.replace(HIDDEN_FROM_A, hand_b=None)
    assert observe(state, Player.A).opponent_holding is False
    assert observe(state, Player.B).opponent_holding is False


def test_the_view_is_player_relative() -> None:
    """Both players see pole 2; SOURCE and TARGET are each player's own poles."""
    for_a = observe(HIDDEN_FROM_A, Player.A)
    for_b = observe(HIDDEN_FROM_A, Player.B)
    assert for_a.shared == for_b.shared == (1,)
    assert (for_a.source, for_a.target, for_a.hand) == ((5,), (7, 3), None)
    assert (for_b.source, for_b.target, for_b.hand) == ((8,), (6, 4), 2)


def test_own_disk_count_is_n_and_survives_a_smuggle() -> None:
    """A's disk count is A's own parity class, wherever those disks have ended up."""
    assert observe(initial_state(3), Player.A).own_disks == 3
    assert observe(initial_state(3), Player.B).own_disks == 3
    smuggled = State(pole_1a=(5, 3), pole_1b=(6, 4, 2), pole_3b=(1,))
    assert observe(smuggled, Player.A).own_disks == 3, "disk 1 is still A's"


def test_observation_is_frozen() -> None:
    obs = observe(HIDDEN_FROM_A, Player.A)
    with pytest.raises(dataclasses.FrozenInstanceError):
        obs.hand = 9  # type: ignore[misc]
