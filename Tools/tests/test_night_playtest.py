from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import night_playtest
import pytest
from beacon_mcp import Client, ToolError
from night_playtest import (
    THROTTLE_PROPERTY,
    Turret,
    Watch,
    parse_layout,
    parse_result,
    poll,
    result_after,
    result_problems,
    run,
    start,
    stop,
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
        ("Sentry,nan,0", "is not two numbers"),
        ("Sentry,600,inf", "is not two numbers"),
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


def test_travel_command_keeps_every_digit_of_a_position() -> None:
    assert travel_command(1, [Turret("Sentry", 1234.5678, -2000.25)]) == (
        "open Lvl_Island?AutoNight=1?Layout=Sentry,1234.5678,-2000.25"
    )


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
    assert result_problems(WIN, night=3, turret_count=4) == []


def test_result_problems_reports_a_skipped_turret_and_a_wrong_night() -> None:
    problems = result_problems(WIN, night=2, turret_count=5)

    assert problems[0] == "asked for night 2 but the game played night 3"
    assert problems[1].startswith("the layout has 5 turrets but the game placed 4")


def test_succeeded_needs_a_result_and_no_problems_of_either_kind() -> None:
    report = {"result": WIN, "screenshots": ["during.png"], "problems": [], "log_problems": []}

    assert succeeded(report)
    assert not succeeded({**report, "result": None})
    assert not succeeded({**report, "problems": ["asked for night 2"]})
    assert not succeeded({**report, "log_problems": ["LogTemp: Warning: something"]})


class FakeEditor(Client):
    """Stands in for the editor: answers the calls a playtest makes and remembers what it was asked."""

    def __init__(self) -> None:
        super().__init__()
        self.pie_running = False
        self.throttle_on = True
        self.arrives = True
        self.log: list[str] = []
        self.commands: list[str] = []
        self.captured: list[Path] = []

    def mark_log(self) -> str:
        self.log.append("LogPython: beacon-mark-7")
        return "beacon-mark-7"

    def call(self, toolset: str, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        if tool == "GetSectionPropertyValues":
            return json.dumps({THROTTLE_PROPERTY: self.throttle_on})
        if tool == "SetSectionProperties":
            assert arguments is not None
            self.throttle_on = json.loads(arguments["propertiesJson"])[THROTTLE_PROPERTY]
            return True
        if tool == "IsPIERunning":
            return self.pie_running
        raise AssertionError(f"unexpected tool call: {toolset}.{tool}")

    def start_pie(self, warmup_seconds: float = 2.0) -> None:
        self.pie_running = True

    def stop_pie(self) -> None:
        if not self.pie_running:
            raise ToolError("A play session is not currently running")
        self.pie_running = False

    def console(self, command: str) -> None:
        self.commands.append(command)

    def pie_state(self) -> dict[str, Any]:
        return {"auto_run": self.arrives}

    def logs(self, pattern: str, max_entries: int = 40) -> list[str]:
        return list(self.log)

    def capture_game(self, png: Path) -> None:
        self.captured.append(png)

    def problems_since(self, marker: str) -> list[str]:
        return []


@pytest.fixture
def state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Each test keeps its run record in its own folder, so tests can run side by side."""
    path = tmp_path / "playtest" / "run.json"
    monkeypatch.setattr(night_playtest, "STATE_FILE", path)
    return path


SIX_TURRETS = [Turret("Sentry", 700.0, 0.0)] * 4


def test_start_opens_the_night_with_the_throttle_off_and_leaves_a_record(state_file: Path) -> None:
    editor = FakeEditor()

    state = start(editor, 3, [Turret("Sentry", 700.0, 0.0)])

    assert editor.pie_running
    assert not editor.throttle_on
    assert editor.commands == ["open Lvl_Island?AutoNight=3?Layout=Sentry,700,0"]
    assert state["throttle_was_on"] is True
    assert json.loads(state_file.read_text(encoding="utf-8")) == state


def test_start_refuses_while_another_night_is_being_played(state_file: Path) -> None:
    editor = FakeEditor()
    start(editor, 3, [])
    record = state_file.read_text(encoding="utf-8")

    with pytest.raises(ToolError, match="already being played"):
        start(editor, 1, [])

    assert state_file.read_text(encoding="utf-8") == record


def test_start_puts_the_editor_back_when_the_game_never_reaches_the_night(
    state_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(night_playtest, "ARRIVAL_TIMEOUT_SECONDS", 0.0)
    editor = FakeEditor()
    editor.arrives = False

    with pytest.raises(ToolError, match="did not start the night"):
        start(editor, 3, [])

    assert not editor.pie_running
    assert editor.throttle_on
    assert not state_file.exists()


@pytest.mark.usefixtures("state_file")
def test_poll_takes_a_picture_only_while_the_night_is_being_played() -> None:
    editor = FakeEditor()
    start(editor, 3, SIX_TURRETS)

    assert poll(editor, Path("during.png")) is None
    editor.log.append(WIN_LINE)
    assert poll(editor, Path("after.png")) == WIN

    assert editor.captured == [Path("during.png")]


@pytest.mark.usefixtures("state_file")
def test_poll_fails_if_play_stopped_without_a_result() -> None:
    editor = FakeEditor()
    start(editor, 3, [])
    editor.pie_running = False

    with pytest.raises(ToolError, match="stopped before the night ended"):
        poll(editor)


def test_stop_reports_the_night_and_puts_the_editor_back(state_file: Path) -> None:
    editor = FakeEditor()
    start(editor, 3, SIX_TURRETS)
    poll(editor, Path("during.png"))
    editor.log.append(WIN_LINE)

    report = stop(editor)

    assert report == {"result": WIN, "screenshots": ["during.png"], "problems": [], "log_problems": []}
    assert succeeded(report)
    assert not editor.pie_running
    assert editor.throttle_on
    assert not state_file.exists()


def test_stop_still_reports_when_play_has_already_ended(state_file: Path) -> None:
    editor = FakeEditor()
    start(editor, 3, SIX_TURRETS)
    poll(editor, Path("during.png"))
    editor.log.append(WIN_LINE)
    editor.pie_running = False

    report = stop(editor)

    assert report["result"] == WIN
    assert editor.throttle_on
    assert not state_file.exists()


@pytest.mark.usefixtures("state_file")
def test_stop_leaves_the_throttle_off_if_it_was_off_before() -> None:
    editor = FakeEditor()
    editor.throttle_on = False
    start(editor, 3, [])

    stop(editor)

    assert not editor.throttle_on


@pytest.mark.usefixtures("state_file")
def test_stop_says_when_the_night_did_not_end_or_was_never_pictured() -> None:
    editor = FakeEditor()
    start(editor, 3, [])

    report = stop(editor)

    assert report["result"] is None
    assert report["problems"] == [
        "the night was stopped before it ended",
        "no screenshot was taken while the night was being played",
    ]
    assert not succeeded(report)


@pytest.mark.usefixtures("state_file")
def test_run_pictures_the_night_at_each_interval_until_it_ends(monkeypatch: pytest.MonkeyPatch) -> None:
    editor = FakeEditor()
    waits: list[float] = []

    def wait(seconds: float) -> None:
        waits.append(seconds)
        if len(waits) == 3:
            editor.log.append(WIN_LINE)

    monkeypatch.setattr(time, "sleep", wait)

    report = run(editor, 3, SIX_TURRETS, Watch(timeout=600.0, shot_every=10.0, png_dir=Path("shots")))

    assert waits == [10.0, 10.0, 10.0]
    assert report["result"] == WIN
    assert report["screenshots"] == [str(Path("shots/night3_01.png")), str(Path("shots/night3_02.png"))]
    assert not editor.pie_running
