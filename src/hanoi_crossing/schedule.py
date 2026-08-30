"""Turn order, kept outside the engine.

The engine never asks whose turn it is: a schedule is an external sequence with
no assumed pattern, so `[A, A, B, A, A, A]` is as valid as strict alternation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .state import Player


@runtime_checkable
class Schedule(Protocol):
    """Answers whose turn step `step` is."""

    def player_at(self, step: int) -> Player:
        """The player to act at `step`, or raise IndexError if there is no such step."""
        ...


@dataclass(frozen=True, slots=True)
class SequenceSchedule:
    """A schedule backed by an explicit, finite list of players."""

    players: tuple[Player, ...]

    @classmethod
    def from_names(cls, names: list[str]) -> SequenceSchedule:
        """Build from player names, e.g. `["A", "B", "A"]`."""
        return cls(tuple(Player(name) for name in names))

    def player_at(self, step: int) -> Player:
        """The player to act at `step`; IndexError once the sequence is exhausted.

        Callers turn that exhaustion into the terminal outcome UNFINISHED.
        """
        if not 0 <= step < len(self.players):
            raise IndexError(f"no step {step} in a schedule of {len(self.players)}")
        return self.players[step]

    def __len__(self) -> int:
        return len(self.players)
