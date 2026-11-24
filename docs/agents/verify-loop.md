# The verify loop

How an agent checks a change in the running game without a person touching the editor: start play-in-editor (PIE), act on the game, read its state and the Output Log, capture a screenshot, stop PIE. Every Beacon ticket ends with this loop.

The editor must be running with the MCP server up (see [unreal-mcp.md](unreal-mcp.md)).

## One command

```powershell
Set-Location C:\docs\git\UnrealTwo; python Tools/mcp/beacon_mcp.py verify --png Saved/BeaconScreenshots/check.png --seconds 5
```

It starts PIE in the level viewport, clicks Play on the main menu, skips the intro shot, waits, saves a screenshot of the game, stops PIE, and prints every warning or error the Output Log gained during the run. It exits 0 only when there were none. Add `--menu` to stay on the main menu instead.

## The steps, as MCP tool calls

The command above is a wrapper. These are the calls it makes, for agents that call the server directly.

| Step | Tool | Notes |
|---|---|---|
| Mark the log | `SlateInspectorToolset.Snapshot`, `Click`, `Type` | Types `py print('<marker>')` into the editor's `Cmd` box, so later log reads can ignore everything before the marker. |
| Start PIE | `EditorAppToolset.StartPIE` | `{"options": {"bSimulate": false, "playMode": "PlayMode_InViewPort", "warmupSeconds": 2.0}}`. Returns after BeginPlay and the warm-up. |
| Start a game | `SlateInspectorToolset.Snapshot`, then `Click` on the ref of `button "Play"` | The game opens on its main menu and nothing runs until Play is pressed. The game's widgets are in the snapshot like any editor widget. A ten-second intro shot follows; `Input.+key Enter` skips it. The `started` field of the game state turns true when play begins. |
| Act on the game | `SlateInspectorToolset.Type` into the `Cmd` box | While PIE runs, console commands go to the game. See "Driving the game". |
| Read game state | `Type` into the `Cmd` box: `py "<repo>/Tools/editor_python/pie_state.py"`, then `LogsToolset.GetLogEntries` with pattern `LogPython` | The script prints one JSON line that starts with `PIESTATE`; take the last one. |
| Capture | `SlateInspectorToolset.Screenshot` on the viewport panel | `EditorAppToolset.CaptureViewport` renders the editor world even during PIE, so it cannot show the game. |
| Stop PIE | `EditorAppToolset.StopPIE` | Always stop, even after a failure. |
| Read the log | `LogsToolset.GetLogEntries` with `{"category": "", "pattern": "", "maxEntries": 0}` | Read everything, drop the lines up to the marker, then keep lines containing `Error:` or `Warning:`. Filtering in the tool call would also filter out the marker. The lines listed under "Expected log noise" in [unreal-mcp.md](unreal-mcp.md) are not failures. |

## Driving the game

There is no input tool. Enhanced Input's console commands press and release keys, and they work from the `Cmd` box while PIE is running:

```text
Input.+key W            hold W
Input.-key W            release W
Input.+key SpaceBar     jump
Input.+key Gamepad_RightX 1     turn the camera right
Input.+key LeftMouseButton      fire
Input.+key E            place a turret
Input.+key B            open or close the build menu
Input.+key Enter        skip the intro shot
slomo 0.15              slow the game down to catch a short event; slomo 1 restores it
```

From a script, with the client in `Tools/mcp/beacon_mcp.py`:

```python
client = Client()
marker = client.mark_log()
client.start_pie()
try:
    client.start_game()  # presses Play on the main menu and skips the intro shot
    client.console("Input.+key W")
    time.sleep(1.5)
    client.console("Input.-key W")
    print(client.pie_state())  # {"player": [-385, 0, 92], "yaw": 0.0, ...}
    client.capture_game(Path("Saved/BeaconScreenshots/moved.png"))
finally:
    client.stop_pie()
print(client.problems_since(marker))
```

Screenshots go under `Saved/BeaconScreenshots/`, which Git ignores. Attach them to the pull request with the `pr-screenshots` skill instead of committing them.

## Game buttons and on-screen text

`python Tools/mcp/beacon_mcp.py click "<label>"` presses a button of the running game by the start of its label: `Play`, `Restart`, or a build menu entry such as `Sniper`. It fails if the button is missing or disabled. To read what the HUD shows, take a Slate snapshot and look for the `text "..."` lines.

Blueprint variables cannot be set from editor Python during PIE unless they are instance editable. Put the game in a state by calling a Blueprint function, for example `mode.call_method("AddResources", args=(-30,))`.

## Things that will trip you

- Click the `Cmd` box before typing. `Type` on an unfocused box returns false and does nothing.
- A floating editor window, such as the Message Log, takes focus and makes `Type` fail. Close it with `SlateInspectorToolset.Windows`.
- `CaptureViewport` needs `captureTransform` and `annotations` even though its schema marks them optional.
- PIE runs unsaved changes, so a passing run does not prove anything was saved. After editing a level, run `python Tools/mcp/beacon_mcp.py save` and check `git status`. `AssetTools.save_assets` on the map returns true but skips changed actors unless the map file itself changed (finding F-015).
- The editor drops to about 3 frames a second while its window is in the background. Game time still advances correctly, so compare the `time` field of `pie_state` rather than wall-clock time.
