"""The transition function: `legal_actions` and a pure, total `apply`.

No I/O, no randomness, no clock, no globals. An illegal action never raises —
it returns `status=ILLEGAL` with a typed `reason` and burns the turn.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from typing import Any

from .actions import Action
from .state import Player, State

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
    """What became of an action: it took effect, it was a skip, or it was refused."""

    OK = "OK"
    SKIPPED = "SKIPPED"
    ILLEGAL = "ILLEGAL"


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


def _illegality(state: State, player: Player, action: Action) -> IllegalReason | None:
    """Why `action` is refused for `player`, or None if it is allowed.

    Hand state is checked before pole state, so lifting from an empty pole with
    a full hand reports HAND_FULL.
    """
    if action is Action.SKIP:
        return None
    verb, pole_field, hand_field = _fields(player, action)
    pole: tuple[int, ...] = getattr(state, pole_field)
    hand: int | None = getattr(state, hand_field)
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


def legal_actions(state: State, player: Player) -> frozenset[Action]:
    """The actions `player` may take now. `SKIP` is always among them."""
    return frozenset(a for a in Action if _illegality(state, player, a) is None)


def apply(state: State, player: Player, action: Action) -> ActionResult:
    """Play one action. Pure, total, and always advances the step counter."""
    reason = _illegality(state, player, action)
    if reason is not None:
        return ActionResult(replace(state, step=state.step + 1), ActionStatus.ILLEGAL, reason)
    if action is Action.SKIP:
        return ActionResult(replace(state, step=state.step + 1), ActionStatus.SKIPPED)

    verb, pole_field, hand_field = _fields(player, action)
    pole: tuple[int, ...] = getattr(state, pole_field)
    hand: int | None = getattr(state, hand_field)
    moved: dict[str, Any]
    if verb == "LIFT":
        moved = {pole_field: pole[:-1], hand_field: pole[-1]}
    else:
        moved = {pole_field: pole + (hand,), hand_field: None}
    return ActionResult(replace(state, **moved, step=state.step + 1), ActionStatus.OK)
