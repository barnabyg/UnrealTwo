"""Play one night of Beacon with nobody at the keyboard and report what happened.

The game starts straight into a night when its level is opened with the options
`?AutoNight=<n>?Layout=<type,x,y,...>`: it places the turrets, plays the night with
the player's input off, and writes one line starting with BEACON_NIGHT_RESULT to
the log when the night is won or the lighthouse falls. This script starts that run
in play-in-editor through the MCP, waits for the line, and stops the run.

A night can outlast the two minutes an agent's single tool call is allowed, so the
run is three short commands. `run` does all three for a shell with no such limit.

Usage (repo root, editor running):
  python Tools/mcp/night_playtest.py start --night 3 --layout "Sentry,600,0;Sniper,-600,0"
  python Tools/mcp/night_playtest.py poll [--png Saved/BeaconScreenshots/night3.png]
  python Tools/mcp/night_playtest.py stop
  python Tools/mcp/night_playtest.py run --night 3 --layout "Sentry,600,0;Sniper,-600,0"

A layout is turrets separated by semicolons, each `type,x,y` in centimetres with the
lighthouse at the origin. `poll` exits 0 once the night is over and 3 while it is
still being played. `stop` and `run` print the report as JSON and exit 0 only if the
night reached an outcome, every turret of the layout was placed and the log is clean.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from beacon_mcp import APP, Client, ToolError

LEVEL = "Lvl_Island"
RESULT_TAG = "BEACON_NIGHT_RESULT"
SETTINGS = "ConfigSettingsToolset.ConfigSettingsToolset"
# The editor setting that drops it to about three frames a second while its window is in
# the background. A turret fires at most once a frame, so a throttled night is a weaker one.
THROTTLE_SECTION = {
    "containerName": "Editor",
    "categoryName": "General",
    "sectionName": "EditorPerformanceSettings",
}
THROTTLE_PROPERTY = "bThrottleCPUWhenNotForeground"

REPO = Path(__file__).resolve().parents[2]
# What `start` leaves for `poll` and `stop`. Saved/ is not tracked.
STATE_FILE = REPO / "Saved" / "BeaconPlaytest" / "run.json"
SCREENSHOT_DIR = REPO / "Saved" / "BeaconScreenshots"

STILL_RUNNING = 3
# How long the game may take to reach the night after the level is opened.
ARRIVAL_TIMEOUT_SECONDS = 30.0

RESULT_FIELDS: dict[str, type] = {
    "night": int,
    "outcome": str,
    "lighthouse_health": float,
    "lighthouse_max_health": float,
    "kills": int,
    "spawned": int,
    "duration_seconds": float,
    "turrets_placed": int,
    "turrets_standing": int,
}


@dataclass(frozen=True)
class Turret:
    type: str
    x: float
    y: float


def parse_layout(text: str) -> list[Turret]:
    """Turrets from `type,x,y;type,x,y`. An empty string is a night with no turrets."""
    turrets = []
    for entry in filter(None, (part.strip() for part in text.split(";"))):
        fields = [field.strip() for field in entry.split(",")]
        if len(fields) != 3:  # noqa: PLR2004 (a turret is a type and two coordinates)
            raise ValueError(f'a turret is "type,x,y", not "{entry}"')
        name, x, y = fields
        # The layout travels inside a level URL, where ? = , and spaces all mean something.
        if not re.fullmatch(r"\w+", name):
            raise ValueError(f'"{name}" is not a turret type name')
        try:
            position = (float(x), float(y))
        except ValueError:
            position = (math.nan, math.nan)
        # float() also reads "nan" and "inf", which are not places.
        if not all(math.isfinite(coordinate) for coordinate in position):
            raise ValueError(f'the position in "{entry}" is not two numbers')
        turrets.append(Turret(name, *position))
    return turrets


def travel_command(night: int, turrets: list[Turret]) -> str:
    """The console command that opens the level straight into the night."""
    if night < 1:
        raise ValueError(f"nights are numbered from 1, not {night}")
    command = f"open {LEVEL}?AutoNight={night}"
    if turrets:
        # .10g writes 600.0 as 600 and keeps a position's digits; plain g would round to six.
        command += "?Layout=" + ",".join(
            f"{turret.type},{turret.x:.10g},{turret.y:.10g}" for turret in turrets
        )
    return command


def parse_result(line: str) -> dict[str, Any] | None:
    """The fields of a BEACON_NIGHT_RESULT log line, or None if the line is not a whole one."""
    if RESULT_TAG not in line:
        return None
    pairs = dict(re.findall(r"(\w+)=(\S+)", line.split(RESULT_TAG, 1)[1]))
    try:
        return {name: kind(pairs[name]) for name, kind in RESULT_FIELDS.items()}
    except (KeyError, ValueError):
        return None


def result_after(entries: list[str], marker: str) -> dict[str, Any] | None:
    """The night result logged after the marker line, if there is one yet."""
    after_marker: list[str] = []
    for entry in entries:
        if marker in entry:
            after_marker = []
        else:
            after_marker.append(entry)
    for entry in reversed(after_marker):
        result = parse_result(entry)
        if result is not None:
            return result
    return None


def result_problems(result: dict[str, Any], night: int, turret_count: int) -> list[str]:
    """Ways the night that was played differs from the night that was asked for."""
    problems = []
    if result["night"] != night:
        problems.append(f"asked for night {night} but the game played night {result['night']}")
    if result["turrets_placed"] != turret_count:
        problems.append(
            f"the layout has {turret_count} turrets but the game placed {result['turrets_placed']}: "
            "a type name the game does not know is skipped"
        )
    return problems


def read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        raise ToolError("no night is being played: run `start` first")
    state: dict[str, Any] = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return state


def write_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def set_throttle(client: Client, *, enabled: bool) -> None:
    client.call(
        SETTINGS,
        "SetSectionProperties",
        {**THROTTLE_SECTION, "propertiesJson": json.dumps({THROTTLE_PROPERTY: enabled})},
    )


def throttle_enabled(client: Client) -> bool:
    values = client.call(
        SETTINGS, "GetSectionPropertyValues", {**THROTTLE_SECTION, "propertyNames": [THROTTLE_PROPERTY]}
    )
    return bool(json.loads(values)[THROTTLE_PROPERTY])


def logged_result(client: Client, marker: str) -> dict[str, Any] | None:
    """The result of the night that began at the marker, read from the log, if it is over."""
    return result_after(client.logs(f"{RESULT_TAG}|{marker}", 0), marker)


def start(client: Client, night: int, turrets: list[Turret]) -> dict[str, Any]:
    """Start play-in-editor, open the level into the night and leave a record for `poll` and `stop`.

    If the night cannot be started, the run is stopped again before the error is passed on.
    """
    if STATE_FILE.exists():
        # Its record holds the editor setting to put back, which a second start would overwrite.
        raise ToolError("a night is already being played: run `stop` first")
    command = travel_command(night, turrets)
    state = {
        "marker": client.mark_log(),
        "night": night,
        "turret_count": len(turrets),
        "command": command,
        "throttle_was_on": throttle_enabled(client),
        "screenshots": [],
    }
    write_state(state)
    try:
        set_throttle(client, enabled=False)
        client.start_pie()
        client.console(command)
        deadline = time.monotonic() + ARRIVAL_TIMEOUT_SECONDS
        while not client.pie_state().get("auto_run"):
            if time.monotonic() >= deadline:
                raise ToolError(f"the game did not start the night after: {command}")
            time.sleep(1.0)
    except BaseException:
        stop(client)
        raise
    return state


def poll(client: Client, png: Path | None = None) -> dict[str, Any] | None:
    """The night's result if it is over, else None.

    While the night is still being played, a picture of the game is saved to `png` when one is
    given, and listed in the report that `stop` returns.
    """
    state = read_state()
    result = logged_result(client, state["marker"])
    if result is not None:
        return result
    if not client.call(APP, "IsPIERunning"):
        raise ToolError("play-in-editor stopped before the night ended")
    if png is not None:
        client.capture_game(png)
        state["screenshots"].append(str(png))
        write_state(state)
    return None


def stop(client: Client) -> dict[str, Any]:
    """Stop play-in-editor, put the editor back as it was and return the report."""
    state = read_state()
    result = logged_result(client, state["marker"])
    try:
        # Play may have ended by itself or by hand, and stopping what is not playing is an error.
        if client.call(APP, "IsPIERunning"):
            client.stop_pie()
    finally:
        set_throttle(client, enabled=state["throttle_was_on"])
        STATE_FILE.unlink()
    if result is None:
        problems = ["the night was stopped before it ended"]
    else:
        problems = result_problems(result, state["night"], state["turret_count"])
    if not state["screenshots"]:
        problems.append("no screenshot was taken while the night was being played")
    return {
        "result": result,
        "screenshots": state["screenshots"],
        "problems": problems,
        "log_problems": client.problems_since(state["marker"]),
    }


@dataclass(frozen=True)
class Watch:
    """How `run` waits for a night: how long, and how often and where it takes a picture."""

    timeout: float
    shot_every: float
    png_dir: Path


def run(client: Client, night: int, turrets: list[Turret], watch: Watch) -> dict[str, Any]:
    """Start the night, take a picture at each interval until it ends, stop and report."""
    start(client, night, turrets)
    try:
        deadline = time.monotonic() + watch.timeout
        shots = 0
        while time.monotonic() < deadline:
            time.sleep(watch.shot_every)
            shots += 1
            if poll(client, watch.png_dir / f"night{night}_{shots:02}.png") is not None:
                break
    finally:
        report = stop(client)
    return report


def succeeded(report: dict[str, Any]) -> bool:
    return report["result"] is not None and not report["problems"] and not report["log_problems"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("start", "start the night and return"), ("run", "play the whole night and report")):
        command = commands.add_parser(name, help=text)
        command.add_argument("--night", type=int, required=True, help="night number, from 1")
        command.add_argument("--layout", default="", help='turrets as "type,x,y;type,x,y"')
        if name == "run":
            command.add_argument("--timeout", type=float, default=600.0, help="seconds to wait for the night")
            command.add_argument("--shot-every", type=float, default=10.0, help="seconds between screenshots")
            command.add_argument("--png-dir", type=Path, default=SCREENSHOT_DIR)
    poll_command = commands.add_parser("poll", help="report whether the night is over")
    poll_command.add_argument("--png", type=Path, help="save a screenshot here if the night is still on")
    commands.add_parser("stop", help="stop the run and print the report")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    client = Client()
    if args.command == "start":
        print(json.dumps(start(client, args.night, parse_layout(args.layout))))
        return 0
    if args.command == "poll":
        result = poll(client, args.png)
        print(json.dumps({"finished": result is not None, "result": result}))
        return 0 if result is not None else STILL_RUNNING
    if args.command == "stop":
        report = stop(client)
    else:
        watch = Watch(args.timeout, args.shot_every, args.png_dir)
        report = run(client, args.night, parse_layout(args.layout), watch)
    print(json.dumps(report, indent=1))
    return 0 if succeeded(report) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main(sys.argv[1:]))
    except (ToolError, ValueError) as error:
        print(f"TOOL ERROR: {error}", file=sys.stderr)
        sys.exit(1)
