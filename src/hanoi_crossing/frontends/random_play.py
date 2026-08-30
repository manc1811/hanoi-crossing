"""Two uniformly random agents playing each other from an observation only.

`random_agent` is the whole policy. It takes an `Observation` and nothing else:
it cannot see the opponent's poles, cannot see which disk they hold, and has no
route to the `State` the driver is holding. A random player reading god-state
would not be a random player of *this* game.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
from dataclasses import dataclass
from typing import Any

from ..actions import Action
from ..engine import apply, legal_actions_from
from ..observation import Observation, observe
from ..schedule import Schedule, SequenceSchedule
from ..state import Outcome, Player, State, initial_state
from .report import ENDED_BUDGET, ENDED_WIN, Step, render, summary


def random_agent(obs: Observation, rng: random.Random) -> Action:
    """Pick uniformly among the actions `obs` allows; SKIP if somehow none do.

    Iterating `Action` rather than the frozenset keeps the draw reproducible:
    set iteration order is not a promise, declaration order is.
    """
    legal = legal_actions_from(obs)
    candidates = [a for a in Action if a in legal]
    if not candidates:
        return Action.SKIP
    return rng.choice(candidates)


@dataclass(frozen=True, slots=True)
class Game:
    """A finished random game: the log, the final state, and how it ended."""

    n: int
    seed: int
    steps: tuple[Step, ...]
    final: State
    ended: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-compatible primitives."""
        return {"n": self.n, "seed": self.seed,
                **summary(self.steps, self.final, self.ended)}


def alternating(max_steps: int) -> SequenceSchedule:
    """A, B, A, B, … for `max_steps` turns.

    One schedule among many: nothing downstream may assume this shape. The
    engine is never told whose turn it is, and the agent is never told who it is
    playing.
    """
    return SequenceSchedule(
        tuple(Player.A if i % 2 == 0 else Player.B for i in range(max_steps))
    )


def play(n: int, seed: int, schedule: Schedule) -> Game:
    """Play until someone wins or the schedule runs out, which is UNFINISHED."""
    rng = random.Random(seed)
    state = initial_state(n)
    steps: list[Step] = []
    ended = ENDED_BUDGET
    step = 0
    while True:
        try:
            player = schedule.player_at(step)
        except IndexError:
            break
        action = random_agent(observe(state, player), rng)
        result = apply(state, player, action)
        steps.append(Step(step, player, action, result.status, result.reason))
        state = result.state
        if state.outcome is not Outcome.IN_PROGRESS:
            ended = ENDED_WIN
            break
        step += 1
    if state.outcome is Outcome.IN_PROGRESS:
        state = dataclasses.replace(state, outcome=Outcome.UNFINISHED)
    return Game(n, seed, tuple(steps), state, ended)


def _positive(text: str) -> int:
    """An argparse type for counts that must be at least 1."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def main(argv: list[str] | None = None) -> int:
    """Entry point for `hanoi-random`. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="hanoi-random", description="Play Hanoi Crossing with two random agents.")
    parser.add_argument("--n", type=_positive, default=3, help="disks per player")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed; omitted means pick one and report it")
    parser.add_argument("--max-steps", type=_positive, default=200,
                        help="turns to schedule before giving up")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    seed = random.randrange(2**32) if args.seed is None else args.seed
    game = play(args.n, seed, alternating(args.max_steps))
    if args.json:
        print(json.dumps(game.to_dict(), indent=2))
    else:
        print(f"n={game.n}  seed={game.seed}  max-steps={args.max_steps}")
        print(render(game.steps, game.final, game.ended))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
