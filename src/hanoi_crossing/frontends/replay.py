"""Replay a recorded game from JSON and print the step log, board and outcome.

Input file:  {"n": 3, "turn_order": ["A", "B", ...], "moves": ["LIFT_SOURCE", ...]}

Strings are converted to enum members here, at the boundary; the engine is only
ever handed `Player` and `Action` members. This is a god-view tool: it prints
both players' poles, unlike `observe`, which is what a *player* is allowed.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..actions import Action
from ..engine import ActionStatus, IllegalReason, apply
from ..schedule import Schedule, SequenceSchedule
from ..state import Outcome, Player, State, initial_state

#: Why the replay loop stopped. Not an engine concept: the engine has no schedule.
ENDED_WIN = "game ended"
ENDED_MOVES = "moves exhausted"
ENDED_SCHEDULE = "schedule exhausted"

#: Board rows, printed in this order: label and the State field behind it.
_ROWS = (("1a", "pole_1a"), ("2", "pole_2"), ("3a", "pole_3a"),
         ("1b", "pole_1b"), ("3b", "pole_3b"))


class ReplayError(Exception):
    """Malformed input. Reported as a message and a non-zero exit, never a traceback."""


@dataclass(frozen=True, slots=True)
class Step:
    """One line of the log: what was attempted at `step` and what came of it."""

    step: int
    player: Player
    action: Action
    status: ActionStatus
    reason: IllegalReason | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-compatible primitives."""
        return {
            "step": self.step,
            "player": self.player.value,
            "action": self.action.value,
            "status": self.status.value,
            "reason": None if self.reason is None else self.reason.value,
        }


@dataclass(frozen=True, slots=True)
class Replay:
    """A finished replay: the log, the final state, and why the loop stopped."""

    n: int
    steps: tuple[Step, ...]
    final: State
    ended: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-compatible primitives."""
        return {
            "n": self.n,
            "steps": [s.to_dict() for s in self.steps],
            "final_state": self.final.to_dict(),
            "ended": self.ended,
            "outcome": self.final.outcome.value,
        }


def _require(data: Any, key: str, kind: type) -> Any:
    """Fetch `key` from a spec mapping, checking its type."""
    if key not in data:
        raise ReplayError(f"missing required key {key!r}")
    value = data[key]
    if not isinstance(value, kind) or isinstance(value, bool):
        raise ReplayError(f"{key!r} must be {kind.__name__}, got {type(value).__name__}")
    return value


def _members(names: list[Any], kind: type, key: str) -> list[Any]:
    """Convert a list of strings into enum members, or explain which one is wrong."""
    out = []
    for i, name in enumerate(names):
        if not isinstance(name, str):
            raise ReplayError(f"{key}[{i}] must be a string, got {type(name).__name__}")
        try:
            out.append(kind(name))
        except ValueError:
            allowed = ", ".join(m.value for m in kind)
            noun = kind.__name__.lower()
            raise ReplayError(
                f"{key}[{i}]: unknown {noun} {name!r} (expected: {allowed})") from None
    return out


def parse_spec(data: Any) -> tuple[int, SequenceSchedule, tuple[Action, ...]]:
    """Validate a decoded replay file into (n, schedule, moves)."""
    if not isinstance(data, dict):
        raise ReplayError(f"replay file must be a JSON object, got {type(data).__name__}")
    n = _require(data, "n", int)
    if n < 1:
        raise ReplayError(f"'n' must be at least 1, got {n}")
    turn_order = _require(data, "turn_order", list)
    if not turn_order:
        raise ReplayError("'turn_order' must not be empty")
    moves = _require(data, "moves", list)
    _members(turn_order, Player, "turn_order")  # validated here for a pointed message
    schedule = SequenceSchedule.from_names(turn_order)
    return n, schedule, tuple(_members(moves, Action, "moves"))


def run(n: int, schedule: Schedule, moves: tuple[Action, ...]) -> Replay:
    """Play `moves` against `schedule` from the start position for `n` disks.

    Stops on a decided game; otherwise runs until either the moves or the
    schedule runs out, which is the terminal outcome UNFINISHED.
    """
    state = initial_state(n)
    steps: list[Step] = []
    ended = ENDED_MOVES
    step = 0
    while True:
        try:
            player = schedule.player_at(step)
        except IndexError:
            ended = ENDED_SCHEDULE
            break
        if step >= len(moves):
            ended = ENDED_MOVES
            break
        result = apply(state, player, moves[step])
        steps.append(Step(step, player, moves[step], result.status, result.reason))
        state = result.state
        if state.outcome is not Outcome.IN_PROGRESS:
            ended = ENDED_WIN
            break
        step += 1
    if state.outcome is Outcome.IN_PROGRESS:
        state = dataclasses.replace(state, outcome=Outcome.UNFINISHED)
    return Replay(n, tuple(steps), state, ended)


def _pole(disks: tuple[int, ...]) -> str:
    return " ".join(str(d) for d in disks) if disks else "-"


def render(replay: Replay) -> str:
    """The human-readable report: step log, final board, outcome on the last line."""
    lines = [f"{'step':>4}  {'player':<6}  {'action':<13}  {'status':<8}  reason"]
    for s in replay.steps:
        reason = "-" if s.reason is None else s.reason.value
        lines.append(
            f"{s.step:>4}  {s.player.value:<6}  {s.action.value:<13}  "
            f"{s.status.value:<8}  {reason}"
        )
    if not replay.steps:
        lines.append("(no moves played)")
    state = replay.final
    lines.append("")
    lines.append("final board (bottom to top)")
    lines += [f"  {label:>2}: {_pole(getattr(state, field))}" for label, field in _ROWS]
    held = [f"{p.value}={'-' if h is None else h}"
            for p, h in ((Player.A, state.hand_a), (Player.B, state.hand_b))]
    lines.append(f"  hands: {'  '.join(held)}")
    lines.append("")
    lines.append(f"stopped after {len(replay.steps)} step(s): {replay.ended}")
    lines.append(f"outcome: {state.outcome.value}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Entry point for `hanoi-replay`. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="hanoi-replay", description="Replay a recorded Hanoi Crossing game.")
    parser.add_argument("file", type=Path, help="replay JSON: n, turn_order, moves")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    try:
        try:
            data = json.loads(args.file.read_text())
        except OSError as exc:
            raise ReplayError(f"cannot read {args.file}: {exc.strerror}") from None
        except json.JSONDecodeError as exc:
            raise ReplayError(f"{args.file}: invalid JSON: {exc}") from None
        replay = run(*parse_spec(data))
    except ReplayError as exc:
        print(f"hanoi-replay: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(replay.to_dict(), indent=2) if args.json else render(replay))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
