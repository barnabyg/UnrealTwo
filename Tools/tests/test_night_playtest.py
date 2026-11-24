from __future__ import annotations

import pytest
from night_playtest import (
    Turret,
    parse_layout,
    parse_result,
    result_after,
    result_problems,
    succeeded,
    travel_command,
)

WIN_LINE = (
    "[2026.11.24-10.31.36:647][442]LogBlueprintUserMessages: BEACON_NIGHT_RESULT night=3 outcome=win "
    "lighthouse_health=65.0 lighthouse_max_health=100.0 kills=40 spawned=40 "
    "duration_seconds=93.166672 turrets_placed=4 turrets_standing=3"
)
WIN = {
    "night": 3,
    "outcome": "win",
    "lighthouse_health": 65.0,
    "lighthouse_max_health": 100.0,
    "kills": 40,
    "spawned": 40,
    "duration_seconds": 93.166672,
    "turrets_placed": 4,
    "turrets_standing": 3,
}


def test_parse_layout_reads_turrets_separated_by_semicolons() -> None:
    assert parse_layout("Sentry,600,0; Sniper, -600.5 ,250") == [
        Turret("Sentry", 600.0, 0.0),
        Turret("Sniper", -600.5, 250.0),
    ]


def test_parse_layout_takes_an_empty_string_as_no_turrets() -> None:
    assert parse_layout("") == []
    assert parse_layout(" ; ") == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("Sentry,600", 'a turret is "type,x,y"'),
        ("Sentry,600,0,5", 'a turret is "type,x,y"'),
        ("Sentry,east,0", "is not two numbers"),
        ("Sen?try,600,0", "is not a turret type name"),
        ("Big Gun,600,0", "is not a turret type name"),
    ],
)
def test_parse_layout_refuses_what_the_level_url_cannot_carry(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_layout(text)


def test_travel_command_opens_the_level_with_the_night_and_layout_as_options() -> None:
    turrets = [Turret("Sentry", 600.0, 0.0), Turret("Sniper", -600.5, 250.0)]

    assert travel_command(3, turrets) == "open Lvl_Island?AutoNight=3?Layout=Sentry,600,0,Sniper,-600.5,250"


def test_travel_command_leaves_the_layout_out_when_there_are_no_turrets() -> None:
    assert travel_command(1, []) == "open Lvl_Island?AutoNight=1"


def test_travel_command_refuses_a_night_below_one() -> None:
    with pytest.raises(ValueError, match="numbered from 1"):
        travel_command(0, [])


def test_parse_result_reads_every_field_with_its_type() -> None:
    assert parse_result(WIN_LINE) == WIN


def test_parse_result_ignores_other_lines_and_incomplete_results() -> None:
    assert parse_result("LogBlueprintUserMessages: Night 3: wave 1") is None
    assert parse_result("LogPython: BEACON_NIGHT_RESULT night=3 outcome=win") is None
    assert parse_result(WIN_LINE.replace("kills=40", "kills=many")) is None


def test_result_after_takes_the_result_logged_since_the_marker() -> None:
    earlier = WIN_LINE.replace("night=3", "night=1")
    entries = [earlier, "LogPython: beacon-mark-7", "LogTemp: something else", WIN_LINE]

    assert result_after(entries, "beacon-mark-7") == WIN


def test_result_after_is_none_until_the_night_ends() -> None:
    earlier = WIN_LINE.replace("night=3", "night=1")

    assert result_after([earlier, "LogPython: beacon-mark-7", "LogTemp: wave 2"], "beacon-mark-7") is None


def test_result_after_is_not_fooled_by_the_command_that_printed_the_marker() -> None:
    entries = ["Cmd: py print('beacon-mark-7')", WIN_LINE, "LogPython: beacon-mark-7"]

    assert result_after(entries, "beacon-mark-7") is None


def test_result_problems_is_empty_when_the_game_played_what_was_asked() -> None:
    assert result_problems(WIN, night=3, turrets=4) == []


def test_result_problems_reports_a_skipped_turret_and_a_wrong_night() -> None:
    problems = result_problems(WIN, night=2, turrets=5)

    assert problems[0] == "asked for night 2 but the game played night 3"
    assert problems[1].startswith("the layout has 5 turrets but the game placed 4")


def test_succeeded_needs_a_result_and_no_problems_of_either_kind() -> None:
    report = {"result": WIN, "problems": [], "log_problems": []}

    assert succeeded(report)
    assert not succeeded({**report, "result": None})
    assert not succeeded({**report, "problems": ["asked for night 2"]})
    assert not succeeded({**report, "log_problems": ["LogTemp: Warning: something"]})
