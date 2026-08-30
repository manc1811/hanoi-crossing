"""M7: random play from observations only, and the legality refactor behind it."""

from __future__ import annotations

import inspect
import json
import random
from types import SimpleNamespace
from typing import Any

import pytest

from hanoi_crossing.actions import Action
from hanoi_crossing.engine import ActionStatus, apply, legal_actions, legal_actions_from
from hanoi_crossing.frontends import random_play
from hanoi_crossing.frontends.random_play import (
    Game,
    alternating,
    main,
    play,
    random_agent,
)
from hanoi_crossing.frontends.report import ENDED_BUDGET, ENDED_WIN
from hanoi_crossing.observation import observe
from hanoi_crossing.state import Outcome, Player, State, initial_state

# --- the refactor: one implementation of the rules ---------------------------


def test_state_level_legality_is_the_observation_level_one() -> None:
    """`legal_actions` must be a wrapper, not a second copy of the rules."""
    states = [
        initial_state(3),
        State(pole_1a=(5,), pole_1b=(8,), pole_2=(1,), pole_3a=(7, 3),
              pole_3b=(6, 4), hand_b=2),
        State(pole_1a=(), pole_2=(2,), pole_3a=(3,), hand_a=1, pole_1b=(6, 4)),
        State(pole_2=(1,), pole_3b=(4, 2), pole_1a=(3,)),
    ]
    for state in states:
        for player in Player:
            assert legal_actions(state, player) == legal_actions_from(
                observe(state, player)
            ), (state, player)


def test_a_terminal_state_is_the_only_thing_the_wrapper_adds() -> None:
    won = apply(State(pole_2=(1,), pole_3a=(3,), pole_1b=(2,)), Player.B,
                Action.LIFT_SHARED).state
    assert won.outcome is Outcome.A_WINS
    assert legal_actions(won, Player.A) == frozenset()
    assert legal_actions_from(observe(won, Player.A)), "the observation still allows moves"


# --- the agent sees an observation and nothing else --------------------------


def test_random_agent_signature_mentions_no_state() -> None:
    sig = inspect.signature(random_agent)
    assert [(p.name, p.annotation) for p in sig.parameters.values()] == [
        ("obs", "Observation"),
        ("rng", "random.Random"),
    ]
    assert sig.return_annotation == "Action"


def test_random_agent_works_on_anything_shaped_like_an_observation() -> None:
    """A stand-in with only the seven visible fields: no State to reach, even in principle."""
    stand_in = SimpleNamespace(
        player=Player.A,
        source=(5, 3),
        shared=(),
        target=(),
        hand=None,
        own_disks=3,
        opponent_holding=False,
    )
    picked = {random_agent(stand_in, random.Random(s)) for s in range(50)}  # type: ignore[arg-type]
    assert picked == {Action.LIFT_SOURCE, Action.SKIP}, "exactly the legal actions here"


def test_random_agent_samples_only_legal_actions() -> None:
    rng = random.Random(11)
    state = initial_state(3)
    for step in range(60):
        player = Player.A if step % 2 == 0 else Player.B
        obs = observe(state, player)
        action = random_agent(obs, rng)
        assert action in legal_actions_from(obs)
        state = apply(state, player, action).state
        if state.outcome is not Outcome.IN_PROGRESS:
            break


def test_random_agent_skips_when_nothing_is_legal(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard the spec asks for, though SKIP is in fact always legal."""
    monkeypatch.setattr(random_play, "legal_actions_from", lambda obs: frozenset())
    obs = observe(initial_state(2), Player.A)
    assert random_agent(obs, random.Random(0)) is Action.SKIP


def test_a_random_game_never_plays_an_illegal_action() -> None:
    """The agent masks from the observation, so nothing burns a turn on ILLEGAL."""
    game = play(3, seed=5, schedule=alternating(300))
    assert game.steps, "some turns were played"
    assert all(s.status is not ActionStatus.ILLEGAL for s in game.steps)


# --- determinism and termination ---------------------------------------------


def trace(game: Game) -> list[tuple[Any, ...]]:
    return [(s.step, s.player, s.action, s.status) for s in game.steps]


def test_the_same_seed_gives_an_identical_trace() -> None:
    first = play(3, seed=1234, schedule=alternating(150))
    second = play(3, seed=1234, schedule=alternating(150))
    assert trace(first) == trace(second)
    assert first.final == second.final
    assert first.to_dict() == second.to_dict()


def test_different_seeds_diverge() -> None:
    traces = [trace(play(3, seed=s, schedule=alternating(150))) for s in range(8)]
    assert len({tuple(t) for t in traces}) > 1, "the seed actually drives the play"


def test_a_small_step_budget_ends_unfinished_cleanly() -> None:
    game = play(4, seed=3, schedule=alternating(6))
    assert len(game.steps) == 6
    assert game.ended == ENDED_BUDGET
    assert game.final.outcome is Outcome.UNFINISHED
    assert game.final.step == 6, "every scheduled turn was consumed"


def test_a_win_stops_the_loop_before_the_budget() -> None:
    game = play(1, seed=7, schedule=alternating(12))
    assert game.ended == ENDED_WIN
    assert game.final.outcome is Outcome.A_WINS
    assert len(game.steps) < 12


def test_alternating_is_one_schedule_among_many() -> None:
    schedule = alternating(5)
    assert [schedule.player_at(i) for i in range(5)] == [
        Player.A, Player.B, Player.A, Player.B, Player.A
    ]
    with pytest.raises(IndexError):
        schedule.player_at(5)


def test_play_accepts_any_schedule_not_just_alternating() -> None:
    """Nothing downstream may assume the A/B pattern."""
    from hanoi_crossing.schedule import SequenceSchedule

    game = play(2, seed=1, schedule=SequenceSchedule((Player.A,) * 8))
    assert {s.player for s in game.steps} == {Player.A}


# --- the CLI -----------------------------------------------------------------


def test_cli_prints_the_shared_log_format(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--n", "1", "--seed", "7", "--max-steps", "12"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "n=1  seed=7  max-steps=12"
    assert out[1].split() == ["step", "player", "action", "status", "reason"]
    assert out[-1].startswith("outcome: ")


def test_cli_json_is_reproducible(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--n", "2", "--seed", "99", "--max-steps", "40", "--json"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(["--n", "2", "--seed", "99", "--max-steps", "40", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == first
    assert first["seed"] == 99
    assert first["outcome"] in {o.value for o in Outcome}


def test_cli_rejects_a_bad_n(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--n", "0"])
    assert exc.value.code == 2
    assert "must be at least 1" in capsys.readouterr().err
