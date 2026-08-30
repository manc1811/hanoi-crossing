"""M5: turn order as an external sequence with no assumed pattern."""

from __future__ import annotations

import pytest

from hanoi_crossing.schedule import Schedule, SequenceSchedule
from hanoi_crossing.state import Player


def test_an_irregular_sequence_is_replayed_exactly() -> None:
    schedule = SequenceSchedule.from_names(["A", "A", "B", "A", "A", "A"])
    played = [schedule.player_at(step) for step in range(len(schedule))]
    assert played == [Player.A, Player.A, Player.B, Player.A, Player.A, Player.A]


def test_exhaustion_raises_index_error() -> None:
    """Past the end is IndexError; callers turn that into UNFINISHED."""
    schedule = SequenceSchedule((Player.A, Player.B))
    assert schedule.player_at(1) is Player.B
    with pytest.raises(IndexError):
        schedule.player_at(2)


def test_negative_steps_do_not_wrap() -> None:
    schedule = SequenceSchedule((Player.A, Player.B))
    with pytest.raises(IndexError):
        schedule.player_at(-1)


def test_sequence_schedule_satisfies_the_protocol() -> None:
    assert isinstance(SequenceSchedule((Player.A,)), Schedule)


def test_any_player_at_implementation_satisfies_the_protocol() -> None:
    """The engine depends on the protocol, not on the sequence-backed class."""

    class Alternating:
        def player_at(self, step: int) -> Player:
            return Player.A if step % 2 == 0 else Player.B

    schedule: Schedule = Alternating()
    assert isinstance(schedule, Schedule)
    assert [schedule.player_at(s) for s in range(3)] == [Player.A, Player.B, Player.A]
