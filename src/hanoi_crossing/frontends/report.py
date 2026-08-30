"""Shared output for both frontends: one step-log format, one board format.

A run is a list of `Step` records plus a final `State` and a note on why the
loop stopped. Replay and random play differ in how they choose actions, not in
how they report them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..actions import Action
from ..engine import ActionStatus, IllegalReason
from ..state import Player, State

#: Why a run stopped. Not an engine concept: the engine has no schedule.
ENDED_WIN = "game ended"
ENDED_MOVES = "moves exhausted"
ENDED_SCHEDULE = "schedule exhausted"
ENDED_BUDGET = "step budget exhausted"

#: Board rows, printed in this order: label and the State field behind it.
_ROWS = (("1a", "pole_1a"), ("2", "pole_2"), ("3a", "pole_3a"),
         ("1b", "pole_1b"), ("3b", "pole_3b"))


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


def _pole(disks: tuple[int, ...]) -> str:
    return " ".join(str(d) for d in disks) if disks else "-"


def render(steps: tuple[Step, ...], final: State, ended: str) -> str:
    """The human-readable report: step log, final board, outcome on the last line.

    This is a god view — both players' poles. `observe` is what a *player* gets.
    """
    lines = [f"{'step':>4}  {'player':<6}  {'action':<13}  {'status':<8}  reason"]
    for s in steps:
        reason = "-" if s.reason is None else s.reason.value
        lines.append(
            f"{s.step:>4}  {s.player.value:<6}  {s.action.value:<13}  "
            f"{s.status.value:<8}  {reason}"
        )
    if not steps:
        lines.append("(no moves played)")
    lines += ["", "final board (bottom to top)"]
    lines += [f"  {label:>2}: {_pole(getattr(final, field))}" for label, field in _ROWS]
    held = [f"{p.value}={'-' if h is None else h}"
            for p, h in ((Player.A, final.hand_a), (Player.B, final.hand_b))]
    lines += [f"  hands: {'  '.join(held)}", ""]
    lines.append(f"stopped after {len(steps)} step(s): {ended}")
    lines.append(f"outcome: {final.outcome.value}")
    return "\n".join(lines)


def summary(steps: tuple[Step, ...], final: State, ended: str) -> dict[str, Any]:
    """The same data as `render`, as JSON-compatible primitives."""
    return {
        "steps": [s.to_dict() for s in steps],
        "final_state": final.to_dict(),
        "ended": ended,
        "outcome": final.outcome.value,
    }
