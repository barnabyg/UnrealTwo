# Automated night playtest

How an agent answers "run night 3 and tell me what happened" with no person at the keyboard. The game starts straight into a chosen night with a given turret layout, plays it with the player's input off, and writes the result to the log. The agent starts the run in play-in-editor (PIE) through the MCP, polls the log, and stops PIE.

The editor must be running with the MCP server up (see [unreal-mcp.md](unreal-mcp.md)).

## The recipe

A night takes one to two minutes, and a single tool call is cut off at about two, so the run is three short commands.

```powershell
Set-Location C:\docs\git\UnrealTwo; python Tools/mcp/night_playtest.py start --night 3 --layout "Sentry,700,0;Sniper,350,606;Sentry,-350,606;Sniper,-700,0;Sentry,-350,-606;Sniper,350,-606"
```

```powershell
Set-Location C:\docs\git\UnrealTwo; python Tools/mcp/night_playtest.py poll --png Saved/BeaconScreenshots/night3.png
```

```powershell
Set-Location C:\docs\git\UnrealTwo; python Tools/mcp/night_playtest.py stop
```

1. **`start`** begins PIE, opens the level into the night and returns once the game confirms it is playing it. It prints the console command it used.
2. **`poll`** exits 3 and prints `{"finished": false, ...}` while the night is being played, and exits 0 with the result once it is over. With `--png` it saves a picture of the game if the night is still being played, so that every picture is a mid-run one. Poll every 20 seconds or so, with `--png` at least once.
3. **`stop`** stops PIE, puts the editor's settings back and prints the report. Always run it, even when a poll failed. `start` refuses to begin a second run until the first has been stopped.

From a shell with no time limit, `run` does all three and takes a screenshot at each interval:

```powershell
Set-Location C:\docs\git\UnrealTwo; python Tools/mcp/night_playtest.py run --night 3 --layout "Sentry,700,0;Sniper,0,700;Sentry,-700,0;Sniper,0,-700"
```

`stop` and `run` exit 0 when the night reached an outcome, the game placed every turret of the layout, at least one screenshot was taken during the night and the log gained no warning or error. A lost night is still exit 0: losing is a result.

## The layout

Turrets are separated by semicolons, each `type,x,y`. The type is a turret type's display name (`Sentry`, `Sniper`, `Sprayer`). Positions are in centimetres with the lighthouse at the origin. The turret is placed at height 0, the top of the plateau the lighthouse stands on. The lighthouse's base is 350 cm in radius and the plateau 2800 cm, so a turret belongs between those distances from the origin. The game does not check: a position inside the lighthouse, on a rock or out past the plateau still gets a turret. `SimulateWave` does check the two distances. The layouts tested so far stand 600 to 700 cm from the lighthouse. An empty layout plays the night with no turrets.

The game skips a type name it does not know. The report says so under `problems`, because it compares the number of turrets the game placed with the number asked for.

## The report

```json
{
 "result": {
  "night": 3,
  "outcome": "win",
  "lighthouse_health": 100.0,
  "lighthouse_max_health": 100.0,
  "kills": 40,
  "spawned": 40,
  "duration_seconds": 64.279665,
  "turrets_placed": 6,
  "turrets_standing": 6
 },
 "screenshots": ["Saved/BeaconScreenshots/night3.png"],
 "problems": [],
 "log_problems": []
}
```

`outcome` is `win` or `loss`. `duration_seconds` is game time from the start of the night to its end. `kills` counts creatures that died, and `spawned` those that had appeared when the night ended, which is fewer than the night's total when the lighthouse falls early. `screenshots` lists the pictures taken while the night was being played. `problems` says what stops the report from counting: the night was stopped early, a turret was skipped, or no picture was taken.

To predict the same night without playing it, call the `SimulateWave` tool of `BeaconEditor.BeaconBalanceToolset` with the same night and layout.

## How it works

| Step | What happens |
|---|---|
| Start the night | The console command `open Lvl_Island?AutoNight=3?Layout=Sentry,700,0,Sniper,350,606`, typed into the `Cmd` box while PIE runs. The game mode reads the two options when it begins play: it skips the menu and the intro, leaves the player's input off, places the turrets and starts the night after one second. The layout option is a flat list of `type,x,y` triples. |
| The result line | When the night is won or the lighthouse falls, the game mode logs one line: `LogBlueprintUserMessages: BEACON_NIGHT_RESULT night=3 outcome=win lighthouse_health=100.0 lighthouse_max_health=100.0 kills=40 spawned=40 duration_seconds=64.279665 turrets_placed=6 turrets_standing=6`. Every night writes it, not only an automated one. |
| Poll | `LogsToolset.GetLogEntries` with the pattern `BEACON_NIGHT_RESULT\|<marker>`, where the marker is a line `start` printed to the log. Only a result after the marker counts, so an earlier night's line is not mistaken for this one's. |
| After the night | An automated night does not go on to the next day and does not write the save file. A win leaves the game running at night with nothing spawning; a loss shows the usual game over screen. |

## Things that will trip you

- **The background throttle changes the outcome.** With its window in the background the editor runs at about 3 frames a second, and a turret fires at most once a frame. `start` switches the editor's "Use Less CPU when in Background" setting off through `ConfigSettingsToolset` and `stop` puts it back. If `start` cannot reach the night it stops the run itself. A run ended any other way than `stop`, such as closing the editor, leaves the setting off and the run's record behind; run `stop` to clear it.
- Each creature spawns at a random bearing, so the same night and layout can end differently. Run a close call more than once.
- `start` keeps what `poll` and `stop` need in `Saved/BeaconPlaytest/run.json`. One run at a time.
- The game reads the options only when the level opens, so `open` with other options, or the Restart button, leaves the automated run.
- The usual verify loop cautions apply: the editor window must not be minimised, and a floating editor window can take the focus the console box needs ([verify-loop.md](verify-loop.md)).
