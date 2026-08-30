"""Immutable game state: five poles, two hands, a step index and an outcome.

A disk is its integer size. Sizes are globally unique and parity encodes
ownership (A odd, B even), so no owner field is needed.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

#: Pole fields, bottom-to-top tuples. Also the key order used by `to_dict`.
POLES = ("pole_1a", "pole_1b", "pole_2", "pole_3a", "pole_3b")


class Player(enum.Enum):
    """The two players. A owns the odd disks, B the even ones."""

    A = "A"
    B = "B"


class Outcome(enum.Enum):
    """The game result, carried on the state after every action."""

    IN_PROGRESS = "IN_PROGRESS"
    A_WINS = "A_WINS"
    B_WINS = "B_WINS"
    DRAW = "DRAW"
    UNFINISHED = "UNFINISHED"


@dataclass(frozen=True, slots=True)
class State:
    """A complete position. Frozen: transitions return a new State."""

    pole_1a: tuple[int, ...] = ()
    pole_1b: tuple[int, ...] = ()
    pole_2: tuple[int, ...] = ()
    pole_3a: tuple[int, ...] = ()
    pole_3b: tuple[int, ...] = ()
    hand_a: int | None = None
    hand_b: int | None = None
    step: int = 0
    outcome: Outcome = Outcome.IN_PROGRESS

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-compatible primitives."""
        data: dict[str, Any] = {name: list(getattr(self, name)) for name in POLES}
        data["hand_a"] = self.hand_a
        data["hand_b"] = self.hand_b
        data["step"] = self.step
        data["outcome"] = self.outcome.value
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> State:
        """Rebuild a State from `to_dict` output."""
        return cls(
            **{name: tuple(data[name]) for name in POLES},
            hand_a=data["hand_a"],
            hand_b=data["hand_b"],
            step=data["step"],
            outcome=Outcome(data["outcome"]),
        )


def initial_state(n: int) -> State:
    """Start position for N disks each: odds on 1a, evens on 1b, largest at bottom."""
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    return State(
        pole_1a=tuple(2 * i - 1 for i in range(n, 0, -1)),
        pole_1b=tuple(2 * i for i in range(n, 0, -1)),
    )
