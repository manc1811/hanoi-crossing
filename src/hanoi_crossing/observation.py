"""What one player can see.

Poles are named player-relative, matching the action space: SOURCE is your pole
1, TARGET your pole 3, SHARED pole 2. The opponent's poles 1 and 3, and the
identity of anything they hold, are absent by construction — there is no field
to read them from.
"""

from __future__ import annotations

from dataclasses import dataclass

from .state import POLES, Player, State

_VIEW: dict[Player, tuple[str, str]] = {
    Player.A: ("pole_1a", "pole_3a"),
    Player.B: ("pole_1b", "pole_3b"),
}

_HANDS: dict[Player, tuple[str, str]] = {
    Player.A: ("hand_a", "hand_b"),
    Player.B: ("hand_b", "hand_a"),
}


@dataclass(frozen=True, slots=True)
class Observation:
    """One player's view of a position. Bottom-to-top tuples, as in State.

    `own_disks` is how many disks the player owns (their parity class), which is
    N and never changes; it is knowledge the player starts with, not a channel
    onto the opponent. `opponent_holding` says *that* the opponent holds a disk,
    never which — you can watch a disk leave the shared pole anyway.
    """

    player: Player
    source: tuple[int, ...]
    shared: tuple[int, ...]
    target: tuple[int, ...]
    hand: int | None
    own_disks: int
    opponent_holding: bool


def observe(state: State, player: Player) -> Observation:
    """The part of `state` that `player` may legitimately act on."""
    source_field, target_field = _VIEW[player]
    own_hand_field, other_hand_field = _HANDS[player]
    own_parity = 1 if player is Player.A else 0
    disks = [d for name in POLES for d in getattr(state, name)]
    disks += [h for h in (state.hand_a, state.hand_b) if h is not None]
    return Observation(
        player=player,
        source=getattr(state, source_field),
        shared=state.pole_2,
        target=getattr(state, target_field),
        hand=getattr(state, own_hand_field),
        own_disks=sum(1 for d in disks if d % 2 == own_parity),
        opponent_holding=getattr(state, other_hand_field) is not None,
    )
