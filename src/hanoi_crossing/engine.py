"""The transition function: `legal_actions` and a pure, total `apply`.

No I/O, no randomness, no clock, no globals. An illegal action never raises —
it returns `status=ILLEGAL` with a typed `reason` and burns the turn.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from typing import Any

from .actions import Action
from .observation import Observation, observe
from .state import Outcome, Player, State

#: Which pole each player-relative slot names, per player.
_POLE_OF: dict[tuple[Player, str], str] = {
    (Player.A, "SOURCE"): "pole_1a",
    (Player.A, "SHARED"): "pole_2",
    (Player.A, "TARGET"): "pole_3a",
    (Player.B, "SOURCE"): "pole_1b",
    (Player.B, "SHARED"): "pole_2",
    (Player.B, "TARGET"): "pole_3b",
}

_HAND_OF: dict[Player, str] = {Player.A: "hand_a", Player.B: "hand_b"}


class ActionStatus(enum.Enum):
    """What became of an action.

    GAME_OVER means the game had already ended: nothing happened at all, not
    even the step counter. It is not an illegal action, so it carries no
    IllegalReason.
    """

    OK = "OK"
    SKIPPED = "SKIPPED"
    ILLEGAL = "ILLEGAL"
    GAME_OVER = "GAME_OVER"


class IllegalReason(enum.Enum):
    """Why an action was refused. `POLE_NOT_VISIBLE` is unreachable via `Action`."""

    EMPTY_POLE = "EMPTY_POLE"
    HAND_FULL = "HAND_FULL"
    HAND_EMPTY = "HAND_EMPTY"
    SIZE_VIOLATION = "SIZE_VIOLATION"
    POLE_NOT_VISIBLE = "POLE_NOT_VISIBLE"


@dataclass(frozen=True, slots=True)
class ActionResult:
    """The state after an action, plus what the engine made of that action."""

    state: State
    status: ActionStatus
    reason: IllegalReason | None = None


def _fields(player: Player, action: Action) -> tuple[str, str, str]:
    """Split an action into (verb, pole field, hand field) for this player."""
    verb, _, slot = action.name.partition("_")
    return verb, _POLE_OF[player, slot], _HAND_OF[player]


def _illegality(obs: Observation, action: Action) -> IllegalReason | None:
    """Why `action` is refused, or None if it is allowed. The only copy of the rules.

    Takes an Observation, not a State: legality never depends on anything the
    acting player cannot see. Hand state is checked before pole state, so
    lifting from an empty pole with a full hand reports HAND_FULL.
    """
    if action is Action.SKIP:
        return None
    verb, _, slot = action.name.partition("_")
    pole: tuple[int, ...] = getattr(obs, slot.lower())
    hand: int | None = obs.hand
    if verb == "LIFT":
        if hand is not None:
            return IllegalReason.HAND_FULL
        if not pole:
            return IllegalReason.EMPTY_POLE
        return None
    if hand is None:
        return IllegalReason.HAND_EMPTY
    if pole and pole[-1] < hand:
        return IllegalReason.SIZE_VIOLATION
    return None


def _has_won(state: State, player: Player) -> bool:
    """True if `player`'s hand is empty and, of their visible poles, only 3 has disks."""
    return (
        getattr(state, _HAND_OF[player]) is None
        and not getattr(state, _POLE_OF[player, "SOURCE"])
        and not state.pole_2
        and bool(getattr(state, _POLE_OF[player, "TARGET"]))
    )


def _settle(state: State) -> State:
    """Stamp the outcome, testing the win predicate for both players."""
    won_a, won_b = _has_won(state, Player.A), _has_won(state, Player.B)
    if won_a and won_b:
        return replace(state, outcome=Outcome.DRAW)
    if won_a:
        return replace(state, outcome=Outcome.A_WINS)
    if won_b:
        return replace(state, outcome=Outcome.B_WINS)
    return state


def _advance(state: State) -> State:
    """Burn a turn, leaving the board alone."""
    return replace(state, step=state.step + 1)


def legal_actions_from(obs: Observation) -> frozenset[Action]:
    """The actions this observation allows. `SKIP` is always among them.

    An agent needs nothing else: what a player may legally do is a function of
    what they can see.
    """
    return frozenset(a for a in Action if _illegality(obs, a) is None)


def legal_actions(state: State, player: Player) -> frozenset[Action]:
    """The actions `player` may take now, as `legal_actions_from` sees them.

    A terminal state has none: the episode is over. That is the only thing this
    knows which an observation does not.
    """
    if state.outcome is not Outcome.IN_PROGRESS:
        return frozenset()
    return legal_actions_from(observe(state, player))


def apply(state: State, player: Player, action: Action) -> ActionResult:
    """Play one action. Pure, total, and never raises.

    The win predicate is evaluated for both players after every action, so a
    player can win on their opponent's turn.
    """
    if state.outcome is not Outcome.IN_PROGRESS:
        return ActionResult(state, ActionStatus.GAME_OVER)
    reason = _illegality(observe(state, player), action)
    if reason is not None:
        return ActionResult(_settle(_advance(state)), ActionStatus.ILLEGAL, reason)
    if action is Action.SKIP:
        return ActionResult(_settle(_advance(state)), ActionStatus.SKIPPED)

    verb, pole_field, hand_field = _fields(player, action)
    pole: tuple[int, ...] = getattr(state, pole_field)
    hand: int | None = getattr(state, hand_field)
    moved: dict[str, Any]
    if verb == "LIFT":
        moved = {pole_field: pole[:-1], hand_field: pole[-1]}
    else:
        moved = {pole_field: pole + (hand,), hand_field: None}
    return ActionResult(_settle(_advance(replace(state, **moved))), ActionStatus.OK)
