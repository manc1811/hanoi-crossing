"""M6: the replay CLI — input validation, the four ways a replay ends, output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from hanoi_crossing.actions import Action
from hanoi_crossing.engine import ActionStatus, IllegalReason
from hanoi_crossing.frontends.replay import (
    ENDED_MOVES,
    ENDED_SCHEDULE,
    ENDED_WIN,
    ReplayError,
    main,
    parse_spec,
    run,
)
from hanoi_crossing.state import Outcome, Player

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def write(tmp_path: Path, spec: Any) -> Path:
    path = tmp_path / "replay.json"
    path.write_text(json.dumps(spec))
    return path


# --- the boundary: strings in, enum members out ------------------------------


def test_parse_spec_converts_strings_to_enum_members() -> None:
    n, schedule, moves = parse_spec(
        {"n": 2, "turn_order": ["A", "B"], "moves": ["LIFT_SOURCE", "SKIP"]}
    )
    assert n == 2
    assert schedule.player_at(0) is Player.A and schedule.player_at(1) is Player.B
    assert moves == (Action.LIFT_SOURCE, Action.SKIP)
    assert all(isinstance(m, Action) for m in moves)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ([], "must be a JSON object"),
        ({"turn_order": ["A"], "moves": []}, "missing required key 'n'"),
        ({"n": 0, "turn_order": ["A"], "moves": []}, "'n' must be at least 1"),
        ({"n": "3", "turn_order": ["A"], "moves": []}, "'n' must be int"),
        ({"n": 1, "moves": []}, "missing required key 'turn_order'"),
        ({"n": 1, "turn_order": [], "moves": []}, "must not be empty"),
        ({"n": 1, "turn_order": ["A"]}, "missing required key 'moves'"),
        ({"n": 1, "turn_order": ["C"], "moves": []}, "unknown player 'C'"),
        ({"n": 1, "turn_order": [1], "moves": []}, "turn_order[0] must be a string"),
        ({"n": 1, "turn_order": ["A"], "moves": ["FLY"]}, "unknown action 'FLY'"),
        ({"n": 1, "turn_order": ["A"], "moves": "SKIP"}, "'moves' must be list"),
    ],
)
def test_malformed_input_is_a_clear_error(spec: Any, expected: str) -> None:
    with pytest.raises(ReplayError) as exc:
        parse_spec(spec)
    assert expected in str(exc.value)


# --- the four terminations ---------------------------------------------------


def test_a_win_stops_immediately_and_ignores_remaining_moves() -> None:
    """The spec's N=1 example, with two extra moves that must never be played."""
    replay = run(
        *parse_spec(
            {
                "n": 1,
                "turn_order": ["A", "B", "A", "B", "B"],
                "moves": ["LIFT_SOURCE", "LIFT_SOURCE", "PLACE_TARGET",
                          "PLACE_TARGET", "SKIP"],
            }
        )
    )
    assert replay.final.outcome is Outcome.A_WINS
    assert replay.ended == ENDED_WIN
    assert len(replay.steps) == 3, "the two moves after the win were not played"


def test_moves_running_out_ends_unfinished() -> None:
    _, schedule, moves = parse_spec(
        {"n": 2, "turn_order": ["A", "A", "B", "B"], "moves": ["LIFT_SOURCE"]}
    )
    replay = run(2, schedule, moves)
    assert replay.ended == ENDED_MOVES
    assert len(replay.steps) == 1
    assert replay.final.outcome is Outcome.UNFINISHED
    assert replay.final.hand_a == 1, "the one move played did take effect"


def test_schedule_running_out_ends_unfinished() -> None:
    """More moves than scheduled turns: the schedule is what runs the game."""
    _, schedule, moves = parse_spec(
        {"n": 2, "turn_order": ["A"], "moves": ["LIFT_SOURCE", "PLACE_TARGET"]}
    )
    replay = run(2, schedule, moves)
    assert replay.ended == ENDED_SCHEDULE
    assert len(replay.steps) == 1
    assert replay.final.outcome is Outcome.UNFINISHED


def test_an_illegal_move_burns_a_turn_and_the_replay_continues() -> None:
    """Illegal is not a termination: it is logged with a reason and play goes on."""
    _, schedule, moves = parse_spec(
        {
            "n": 1,
            "turn_order": ["A", "A", "A"],
            "moves": ["PLACE_TARGET", "LIFT_SOURCE", "PLACE_TARGET"],
        }
    )
    replay = run(1, schedule, moves)
    assert [s.status for s in replay.steps] == [
        ActionStatus.ILLEGAL,
        ActionStatus.OK,
        ActionStatus.OK,
    ]
    assert replay.steps[0].reason is IllegalReason.HAND_EMPTY
    assert replay.steps[1].reason is None
    assert replay.final.outcome is Outcome.A_WINS
    assert replay.final.step == 3, "the illegal action still consumed a turn"


def test_skip_is_distinct_from_illegal_in_the_log() -> None:
    _, schedule, moves = parse_spec(
        {"n": 1, "turn_order": ["A", "A"], "moves": ["SKIP", "PLACE_SHARED"]}
    )
    replay = run(1, schedule, moves)
    assert [s.status for s in replay.steps] == [ActionStatus.SKIPPED, ActionStatus.ILLEGAL]
    assert replay.steps[0].reason is None


# --- output ------------------------------------------------------------------


def test_text_output_logs_every_step_and_ends_with_the_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([str(EXAMPLES / "blockade.json")]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].split() == ["step", "player", "action", "status", "reason"]
    assert out[1].split() == ["0", "A", "LIFT_SOURCE", "OK", "-"]
    assert out[-1] == "outcome: B_WINS", "the outcome is the last line"
    assert "3b: 2" in "\n".join(out), "the final board is printed"


def test_json_output_carries_the_same_data(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(EXAMPLES / "blockade.json"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["n"] == 1
    assert data["outcome"] == "B_WINS"
    assert data["ended"] == ENDED_WIN
    assert data["final_state"]["pole_3b"] == [2]
    assert data["final_state"]["hand_a"] == 1
    assert len(data["steps"]) == 5
    assert data["steps"][0] == {
        "step": 0,
        "player": "A",
        "action": "LIFT_SOURCE",
        "status": "OK",
        "reason": None,
    }


# --- the CLI's own failure modes ---------------------------------------------


def test_bad_input_exits_non_zero_with_a_message_not_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, {"n": 1, "turn_order": ["A"], "moves": ["FLY"]})
    assert main([str(path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown action 'FLY'" in captured.err
    assert "Traceback" not in captured.err


def test_invalid_json_exits_non_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json")
    assert main([str(path)]) == 2
    assert "invalid JSON" in capsys.readouterr().err


def test_missing_file_exits_non_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "nope.json")]) == 2
    assert "cannot read" in capsys.readouterr().err


# --- the shipped examples ----------------------------------------------------


@pytest.mark.parametrize(
    ("name", "outcome"),
    [
        ("n1_spec_example.json", Outcome.A_WINS),
        ("blockade.json", Outcome.B_WINS),
        ("smuggle.json", Outcome.A_WINS),
    ],
)
def test_shipped_examples_replay_cleanly(name: str, outcome: Outcome) -> None:
    replay = run(*parse_spec(json.loads((EXAMPLES / name).read_text())))
    assert replay.final.outcome is outcome
    assert all(s.status is ActionStatus.OK for s in replay.steps), "no illegal moves"
