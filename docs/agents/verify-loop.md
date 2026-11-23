# The verify loop

How an agent checks a change in the running game without a person touching the editor: start play-in-editor (PIE), act on the game, read its state and the Output Log, capture a screenshot, stop PIE. Every Beacon ticket ends with this loop.

The editor must be running with the MCP server up (see [unreal-mcp.md](unreal-mcp.md)).

## One command

```powershell
Set-Location C:\docs\git\UnrealTwo; python Tools/mcp/beacon_mcp.py verify --png Saved/BeaconScreenshots/check.png --seconds 5
```

It starts PIE in the level viewport, waits, saves a screenshot of the game, stops PIE, and prints every warning or error the Output Log gained during the run. It exits 0 only when there were none.

## The steps, as MCP tool calls

The command above is a wrapper. These are the calls it makes, for agents that call the server directly.

| Step | Tool | Notes |
|---|---|---|
| Mark the log | `SlateInspectorToolset.Snapshot`, `Click`, `Type` | Types `py print('<marker>')` into the editor's `Cmd` box, so later log reads can ignore everything before the marker. |
| Start PIE | `EditorAppToolset.StartPIE` | `{"options": {"bSimulate": false, "playMode": "PlayMode_InViewPort", "warmupSeconds": 2.0}}`. Returns after BeginPlay and the warm-up. |
| Act on the game | `SlateInspectorToolset.Type` into the `Cmd` box | While PIE runs, console commands go to the game. See "Driving the game". |
| Read game state | `Type` into the `Cmd` box: `py "Tools/editor_python/pie_state.py"` (absolute path), then `LogsToolset.GetLogEntries` with pattern `PIESTATE` | The script prints one JSON line. |
| Capture | `SlateInspectorToolset.Screenshot` on the viewport panel | `EditorAppToolset.CaptureViewport` renders the editor world even during PIE, so it cannot show the game. |
| Stop PIE | `EditorAppToolset.StopPIE` | Always stop, even after a failure. |
| Read the log | `LogsToolset.GetLogEntries` with `{"category": "", "pattern": "Error:\|Warning:", "maxEntries": 0}` | Keep only lines after the marker. The lines listed under "Expected log noise" in [unreal-mcp.md](unreal-mcp.md) are not failures. |

## Driving the game

There is no input tool. Enhanced Input's console commands press and release keys, and they work from the `Cmd` box while PIE is running:

```text
Input.+key W            hold W
Input.-key W            release W
Input.+key SpaceBar     jump
Input.+key Gamepad_RightX 1     turn the camera right
```

From a script, with the client in `Tools/mcp/beacon_mcp.py`:

```python
client = Client()
marker = client.mark_log()
client.start_pie()
try:
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

## Things that will trip you

- Click the `Cmd` box before typing. `Type` on an unfocused box returns false and does nothing.
- A floating editor window, such as the Message Log, takes focus and makes `Type` fail. Close it with `SlateInspectorToolset.Windows`.
- `CaptureViewport` needs `captureTransform` and `annotations` even though its schema marks them optional.
- Save the level before starting PIE if the change must survive an editor restart. PIE runs unsaved changes, so a passing run does not prove the level was saved.
