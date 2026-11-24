# Packaging a Windows build

How to produce the standalone Windows build of Beacon and check it. The MCP has no build, cook or package tool (finding F-066), so the build runs from a shell.

## One command

```powershell
Set-Location C:\docs\git\UnrealTwo; pwsh Tools/package.ps1
```

It builds the game target, cooks the content, puts it into `.pak` and IoStore files, and archives the result to `Packaged/Windows`, which Git ignores. It runs at below-normal priority and writes UAT's output to `Saved/Logs/package.log`. `-Configuration Shipping` makes a Shipping build; the default is Development, which keeps the game's log and console. It needs Visual Studio with the C++ workload, like the editor build in [unreal-mcp.md](unreal-mcp.md). It uses the engine at `C:\Program Files\Epic Games\UE_5.8`, or at `$env:UE_ROOT` if that is set.

The editor can stay open: the script does not rebuild the editor's modules, and the cook runs in its own windowless process. Save first, because the cook reads the assets from disk. With a warm shader cache a build takes about 100 s (73 s to compile the game, 22 s to cook, 3 s to stage), and a rebuild after a content change about 25 s. The first cook on a machine also compiles about 600 shaders: that cook took 93 s here, so expect a first build of about three minutes. Expect about 1 GB of output.

## Run it

```powershell
Set-Location C:\docs\git\UnrealTwo; .\Packaged\Windows\Beacon.exe -windowed -ResX=1280 -ResY=720
```

`Packaged/Windows/Beacon.exe` is a launcher. It starts `Packaged/Windows/Beacon/Binaries/Win64/Beacon.exe` and exits at once, so stop the game with `Get-Process Beacon | Stop-Process`, not through the process the launcher returned. The game writes its log to `Packaged/Windows/Beacon/Saved/Logs/Beacon.log` and its save to `Packaged/Windows/Beacon/Saved/SaveGames/BeaconSave.sav`, apart from the editor's.

## Check it without a person

The packaged game has no MCP server, because the plugin is editor-only. The automated night of [night-playtest.md](night-playtest.md) still works, because its options are level options:

```powershell
Set-Location C:\docs\git\UnrealTwo; .\Packaged\Windows\Beacon.exe "Lvl_Island?AutoNight=1?Layout=Sentry,700,0,Sniper,350,606,Sentry,-350,606,Sniper,-700,0,Sentry,-350,-606,Sniper,350,-606" -windowed
```

Wait for `BEACON_NIGHT_RESULT` in the game's log, read the line, then stop the game. The layout here is comma-separated throughout, the game's own format; `night_playtest.py` uses semicolons only between its turrets. Leave out `Layout` to lose the night and reach game over. Read the log for `Warning:` and `Error:` lines as well: some problems show only in a cooked build (finding F-069).

## Manual check

1. Delete `Packaged/Windows/Beacon/Saved/SaveGames` if it exists, then run the game. The menu shows only **Play**.
2. Click **Play**, press Enter to skip the intro. Day 1 starts with 60 resources.
3. Press E to place a Sentry, then N to start the night. With one or two turrets night 1 is usually lost: "THE LIGHTHOUSE HAS FALLEN".
4. Close the game and run it again. The menu shows **Continue** and **New Game**. Continue opens day 1 with the resources saved at its start.
