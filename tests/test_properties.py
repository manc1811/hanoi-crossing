"""M8: invariants that must hold over every reachable state, plus the size guard.

Plain pytest with seeded loops — no hypothesis: the state space here is small
and a seeded walk is reproducible without the dependency. Trajectories are
driven two ways. The *masked* walk plays like the random frontend, through
`legal_actions_from`; the *unmasked* walk samples all seven actions uniformly,
so roughly half its turns are illegal. The invariants must survive both, since
an illegal action is an ordinary outcome of `apply`, not an error path.

Turn order is drawn at random per seed, not alternated: the engine is not
allowed to assume a pattern.
"""

from __future__ import annotations

import ast
import json
import random
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pytest

import hanoi_crossing
from hanoi_crossing.actions import Action
from hanoi_crossing.engine import ActionResult, ActionStatus, apply
from hanoi_crossing.frontends.random_play import alternating, play, random_agent
from hanoi_crossing.observation import observe
from hanoi_crossing.schedule import SequenceSchedule
from hanoi_crossing.state import POLES, Outcome, Player, State, initial_state

#: Enough seeds and depth to visit wins, blockades and every illegal reason.
SEEDS = range(25)
DEPTH = 120
SIZES = (1, 2, 3, 4)


def walk(n: int, seed: int, masked: bool) -> Iterator[tuple[State, Player, Action, ActionResult]]:
    """Yield (state before, player, action, result) along one seeded trajectory."""
    rng = random.Random(seed)
    schedule = SequenceSchedule(tuple(rng.choice((Player.A, Player.B)) for _ in range(DEPTH)))
    state = initial_state(n)
    for step in range(DEPTH):
        player = schedule.player_at(step)
        if masked:
            action = random_agent(observe(state, player), rng)
        else:
            action = rng.choice(list(Action))
        result = apply(state, player, action)
        yield state, player, action, result
        state = result.state
        if state.outcome is not Outcome.IN_PROGRESS:
            return


def disks(state: State) -> Counter[int]:
    """Every disk in play, wherever it is: on a pole or in a hand."""
    counts = Counter(d for name in POLES for d in getattr(state, name))
    counts.update(h for h in (state.hand_a, state.hand_b) if h is not None)
    return counts


# --- the three required properties -------------------------------------------


@pytest.mark.parametrize("masked", [True, False], ids=["masked", "unmasked"])
@pytest.mark.parametrize("n", SIZES)
def test_disks_are_conserved(n: int, masked: bool) -> None:
    """No action creates, destroys or duplicates a disk."""
    expected = Counter(range(1, 2 * n + 1))
    for seed in SEEDS:
        assert disks(initial_state(n)) == expected
        for before, player, action, result in walk(n, seed, masked):
            assert disks(result.state) == expected, (seed, before, player, action)


@pytest.mark.parametrize("masked", [True, False], ids=["masked", "unmasked"])
@pytest.mark.parametrize("n", SIZES)
def test_every_pole_is_strictly_decreasing_bottom_to_top(n: int, masked: bool) -> None:
    """A disk never rests on one the same size or smaller."""
    for seed in SEEDS:
        for _, player, action, result in walk(n, seed, masked):
            for name in POLES:
                pole: tuple[int, ...] = getattr(result.state, name)
                assert all(a > b for a, b in zip(pole, pole[1:])), (
                    seed, name, pole, player, action
                )


@pytest.mark.parametrize("n", SIZES)
def test_the_same_seed_gives_the_same_trace(n: int) -> None:
    """Every visited state, not just the last one, is reproducible from the seed."""
    for seed in SEEDS:
        first = [(s.step, p, a, r.status, r.state) for s, p, a, r in walk(n, seed, True)]
        second = [(s.step, p, a, r.status, r.state) for s, p, a, r in walk(n, seed, True)]
        assert first == second
    trace = lambda g: [(s.step, s.player, s.action, s.status) for s in g.steps]
    assert trace(play(n, 77, alternating(DEPTH))) == trace(play(n, 77, alternating(DEPTH)))


def test_different_seeds_do_not_all_agree() -> None:
    """Guards the determinism test above from passing on a degenerate walk."""
    traces = [
        tuple((p, a, r.status) for _, p, a, r in walk(3, seed, True)) for seed in SEEDS
    ]
    assert len(set(traces)) > 1


# --- invariants the locked decisions imply -----------------------------------


@pytest.mark.parametrize("masked", [True, False], ids=["masked", "unmasked"])
def test_the_step_counter_always_advances_by_one(masked: bool) -> None:
    """Decision 11: illegal actions and skips consume a turn like any other."""
    for seed in SEEDS:
        for before, _, _, result in walk(3, seed, masked):
            assert result.state.step == before.step + 1


def test_an_illegal_action_changes_nothing_but_the_step() -> None:
    """It burns the turn and leaves the board and both hands exactly as they were."""
    seen: set[object] = set()
    for seed in SEEDS:
        for before, _, _, result in walk(3, seed, False):
            if result.status is not ActionStatus.ILLEGAL:
                continue
            seen.add(result.reason)
            assert result.state == before.__class__(
                **{name: getattr(before, name) for name in POLES},
                hand_a=before.hand_a,
                hand_b=before.hand_b,
                step=before.step + 1,
                outcome=result.state.outcome,
            )
    assert len(seen) >= 4, f"the unmasked walk should hit most illegal reasons, hit {seen}"


@pytest.mark.parametrize("n", SIZES)
def test_every_reachable_state_round_trips_through_json(n: int) -> None:
    """Not just the start position: serialisation is total over reachable states."""
    for seed in SEEDS:
        for _, _, _, result in walk(n, seed, False):
            assert State.from_dict(json.loads(json.dumps(result.state.to_dict()))) == result.state


# --- the size guard ----------------------------------------------------------

#: The core engine. Frontends and tests are deliberately not counted.
CORE = ("state.py", "actions.py", "engine.py", "observation.py", "schedule.py")
LIMIT = 500


def code_lines(path: Path) -> int:
    """Non-blank, non-comment lines. Docstrings count: they are code you maintain."""
    return sum(
        1 for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def test_the_core_engine_stays_under_the_line_limit() -> None:
    root = Path(hanoi_crossing.__file__).parent
    counts = {name: code_lines(root / name) for name in CORE}
    total = sum(counts.values())
    assert total < LIMIT, f"core engine is {total} lines: {counts}"


def test_the_core_engine_imports_only_the_standard_library() -> None:
    """No third-party dependency may creep into the engine."""
    root = Path(hanoi_crossing.__file__).parent
    allowed = set(sys.stdlib_module_names)
    for name in CORE:
        for node in ast.walk(ast.parse((root / name).read_text())):
            if isinstance(node, ast.Import):
                modules = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                modules = [(node.module or "").split(".")[0]]
            else:
                continue  # a relative import: within this package
            for module in modules:
                assert module in allowed, f"{name} imports third-party {module!r}"
