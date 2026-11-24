# Play-in-editor verification record

What the agent measured in play-in-editor (PIE) for each acceptance criterion of tickets #4 to #15, on 2026-11-23 and 2026-11-24. Every run was started, driven, read and stopped through the MCP as described in [verify-loop.md](../agents/verify-loop.md). Positions are in centimetres; the lighthouse stands at the origin. Game state was read with `Tools/editor_python/pie_state.py`.

**Clean log.** Each final run below ended with no `Warning:` or `Error:` line added to the Output Log between the start marker and the stop, apart from the expected noise listed in [unreal-mcp.md](../agents/unreal-mcp.md), and apart from the bad save files of #15, where the row says what was logged. A plain `beacon_mcp.py verify` run passed on the final tree, three times in a row (see the last section).

## #4 Walkable island

| Criterion | Evidence |
|---|---|
| Default map loads on Play with no errors | `GameDefaultMap` and `EditorStartupMap` are `Lvl_Island`; PIE started on it with a clean log. |
| Ground, shoreline, sea, lighthouse | Screenshot from the shallows shows grass plateau, sand beach, sea plane and the lighthouse. |
| Move, jump, look | Holding W for 1.5 s moved the player from x = -1500 to x = -385, where the lighthouse base stopped it. SpaceBar: `falling` true and z up by 10 one sample later. `Gamepad_RightX`: control yaw 0 to 10. |
| Cannot walk off into the void | Holding S for 11 s ended at x = -4240, z = 32, standing in the shallows against the boundary wall; holding W for 9 s then walked back up the beach to x = -385. Only the west side was walked; the wall is a ring of 24 identical segments. |

## #5 Creature attacks the lighthouse

| Criterion | Evidence |
|---|---|
| NavMesh covers the walkable ground | A path query from (2400, 1400) to the lighthouse returned a valid three-point path. Creatures landing at random points all round the beach reached the lighthouse in every run. |
| Spawns at the shore and paths round obstacles | First sample of a creature: (1268, 2074), on the beach. The path query above bends round a rock corner at (1045, 817): 2357 cm against 2328 cm straight. |
| Repeating attack in range | Lighthouse health by game time: 100 at 10 s, 85 at 16 s, 65 at 24 s, 50 at 30 s, 35 at 36 s, 20 at 42 s, 5 at 48 s. Log lines "Lighthouse health: 10", "5", "0" two seconds apart. |
| Health visible on screen | HUD line "Lighthouse: 75 / 100" in the screenshot. |
| Game over at zero with a message | At health 0: `game_over` true, game paused, HUD shows "GAME OVER - the lighthouse has fallen". |
| Behaviour Tree, not a tick | `BehaviorTreeTools.list_nodes` on `BT_Creature`: a Sequence with FindLighthouse, MoveTo and AttackTarget. The tree editor shows the same. |

## #6 Player shoots creatures

| Criterion | Evidence |
|---|---|
| Fire input shoots toward the aim point | `Input.+key LeftMouseButton` with the crosshair on the creature damaged it; `IA_Fire` is mapped in `IMC_Beacon`. |
| Hits reduce health, misses do nothing | A burst aimed 40 degrees off: creature stayed at 50. On target: log "Creature health: 25", then "Creature health: 0". |
| Dies and stops attacking | Log "Creature died"; the creature list was empty on the next sample. |
| Killing it leaves the game running | Lighthouse health 30 at the kill and 30 six seconds later; not paused, not game over. |

## #7 Player places a turret

| Criterion | Evidence |
|---|---|
| Build input places a turret ahead | Player at (-900, 0) facing the lighthouse, `Input.+key E`: a turret at (-650, 0, 0), notice "Turret placed". |
| Refused on invalid ground | Same spot again: "Cannot build here: not buildable ground" (the sweep lands on the turret). 120 cm beside it: "too close to another turret". Facing the lighthouse from 600 cm, so the footprint touches its base: "not buildable ground". Standing in the shallows facing the sea: "not buildable ground". Turret count unchanged each time. |
| Targets the nearest creature, tracks, kills | With a turret on a creature's approach line: `has_target` true, creature health 50 down to 10 in the capture and gone two samples later. The screenshot shows the barrel on the creature. |
| Idles with nothing in range | `has_target` false before the creature came within 1200 cm and after it died. |
| One turret beats one creature | Lighthouse at 100 after the creature died (90 in a run where the turret stood on the far side). |

## #8 Data-driven waves and turret types

| Criterion | Evidence |
|---|---|
| Waves in data, played in order | Notices "Wave 1", "Wave 2", "Wave 3" in that order; 16 "Creature died" lines for the 3 + 5 + 8 then defined. |
| Three waves of rising difficulty | `DA_Night_1` lists three wave assets with rising counts and shorter spawn intervals. |
| Turret types in data, player picks | Placed with Q between presses: Sentry (range 1200), Sniper (2400), Sprayer (700), then Sentry again as the selection wrapped. |
| Night won when the last wave is dead | With five turrets: all 16 dead, lighthouse at 80, HUD "NIGHT SURVIVED - the lighthouse stands". Since #10 the same moment starts the next day. |
| Editing a row changes the next run | `Count` on `DA_Wave_N1_1` set from 3 to 1 with `ObjectTools.set_properties`: the next run spawned one creature in wave one and moved to wave two by 8 s. Restored to 3. |

## #9 Creature variants

| Criterion | Evidence |
|---|---|
| Three types differ in speed, health, look | Approach speeds over a whole night: Shambler 256 to 265 cm/s (nine creatures), Runner 467 and 501, Hunter 165 to 168. Health at spawn 50, 20 and 220. The line-up screenshot shows small yellow, medium purple and large red. |
| A variant picks a different target | A Hunter that landed at (-1788, -1618) walked to a turret at (650, 0) on the far side of the lighthouse, took it from 60 health to destroyed, and only then went for the lighthouse. |
| A decision uses an EQS query | The Hunter's tree runs `EQS_NearestTurret` (made by hand, finding F-034) to choose its turret. With turrets at (-650, 0) and (650, 0) and a Hunter landing at (-1631, 2354), 2550 cm and 3278 cm away, it attacked the nearer one first at 30 s and the other at 46 s. `BehaviorTreeTools.list_nodes` shows `BTTask_RunEQSQuery` in the tree, with that query and the `TargetActor` key. |
| Wave data mixes types | Types alive while each wave was current: wave one Shambler; wave two Runner and Shambler; wave three Hunter, Runner and Shambler. |

## #10 Day/night loop

| Criterion | Evidence |
|---|---|
| Explicit phases in a loop | HUD "Day 1 night falls in 40 s", then "Night 1", then "Day 2", then "Night 2" in one run. |
| Pickups by day add to a count | Eight pickups at the start of the day. Walking onto one: resources 60 to 70, seven left, notice "Resources +10". None left at night; eight again on day two. |
| Turrets cost resources, refused when short | Sentry: 70 to 45. Sniper: to 15 (after one more pickup). Sprayer at 15: "Not enough resources: Sprayer costs 30", turret count unchanged. |
| Night runs that night's waves, each harder | Night one played `DA_Night_1` (3, 6, 9 creatures), night two `DA_Night_2` (6, 9, 12). `DA_Night_3` is 9, 13, 18. Past night three the count scale rises by half per night; that branch was not played. |
| Lighting differs | Sun intensity 3.0 by day and 0.3 at night; the day and night screenshots. |
| Beam rotates at night | Beam off by day. At night `bBeamOn` true and its yaw went from -180 to 90 between two samples; the night screenshot shows its pool of light on the ground. |

## #11 HUD and menus

Buttons were pressed with `SlateInspectorToolset.Click` on the game's own widgets, and on-screen text was read from the Slate snapshot (finding F-037).

| Criterion | Evidence |
|---|---|
| Main menu on launch, Play starts the game | At PIE start the snapshot lists `text "BEACON"` and `button "Play"`; `started` false, no phase text. After a click on Play: `started` true, phase text "Day 1  -  night 1 falls in 42 s", the HUD on screen. |
| HUD shows health, phase and night, wave progress, resources, live | Day: "Lighthouse  100 / 100", "Day 1  -  night 1 falls in 41 s", "Resources  60", "Waves: none until nightfall". At night, with the lighthouse already down to 85 from creature attacks, 40 more damage: "Lighthouse  45 / 100", "Night 1", "Wave 2 / 3  -  creatures left: 3", "Resources  30". The countdown fell from 42 to 33 between two captures and the health bar shortened. |
| Build menu lists types with costs, disables unaffordable | B opens it: buttons "Sentry  -  cost 25   (selected)", "Sniper  -  cost 40", "Sprayer  -  cost 30". A click on Sniper closed the menu and set the selection to Sniper; E then placed a Sniper and resources fell from 60 to 20. With 30 resources the Sniper button is marked `[disabled]` and drawn dimmed, and a click on it changed nothing. |
| Game over shows the night reached, restart works | Lighthouse to 0 during night one: game paused, "THE LIGHTHOUSE HAS FALLEN", "You reached night 1", `button "Restart"`. After a click on Restart: game time back to 6 s, `started` true with no menu, day one, 60 resources, lighthouse 100, no turrets, and holding W moved the player. |
| UMG widgets, debug text removed | Five Widget Blueprints under `Content/Beacon/UI`. The HUD's game-over text block is gone. `find_nodes` over every graph of every Beacon Blueprint finds no print node, and since #12 no debug-draw node. The first check of this read the graphs back as DSL and missed six disconnected `PrintString` nodes, which have since been deleted (finding F-055). |

## #12 Combat feedback

| Criterion | Evidence |
|---|---|
| Creatures flash on damage, from a material parameter on a material instance | The creature's body material in PIE is a dynamic instance of `MI_Creature`. Its `Flash` parameter read 1.0 on the sample after each hit (health 30, then 10) and 0.0 on the samples between. In the capture taken at `Flash` 1.0 the creature is white instead of purple. |
| Player and turret shots show a Niagara muzzle effect | With a Sentry firing (the other two turret types share its graph and were not captured), the live Niagara components were `NS_MuzzleFlash`, one per recent shot; the capture shows the burst at the end of the barrel. Holding fire as the player for one second listed twelve `NS_MuzzleFlash` components. |
| Creature deaths show a Niagara burst | `NS_DeathBurst` appeared in the component list on the sample where the creature's health reached 0, and the capture shows the burst where it stood. |
| Sounds, or a finding | Three generated sounds are imported as `SFX_Shot`, `SFX_Hit` and `SFX_Death` and played from the shot, damage and death graphs (finding F-043). The agent cannot hear them; the log is clean while they play. |
| Effects clean up, frame rate holds through a wave | Five turrets, the player firing throughout, night one played to the end. Frames per second over six-second samples: 115 by day with no combat, then 115, 115, 115, 114, 115, 115 through waves one to three. Live Niagara components counted at the end of each sample peaked at 10 during wave three and were 0 four seconds after the night ended. Measured with the editor's background throttle off (finding F-045). The rate never moved off 115, which is probably the editor's frame limit, so this shows no drop below the limit and not how much headroom is left. Only night one was played. |

## #13 PCG scatter

Instance positions were read with `Tools/editor_python/scatter_state.py`. The plateau is a disc of radius 2800 with its top at z = 0; the beach and the sea lie below it.

| Criterion | Evidence |
|---|---|
| A PCG graph places rock and foliage placeholders | `PCG_IslandScatter` on the `IslandScatter` volume, seed 42: 6 cube rocks, 10 sphere rocks and 69 cone bushes. The overview screenshot shows them across the plateau. |
| Nothing in the sea, in the lighthouse or blocking the route | Every instance is on the plateau top (rocks at z = 0, foliage at z = 25) between 721 and 2591 cm from the lighthouse, which has a radius of 350. None is on the path from the west shore: over eight seeds the nearest rock centre was 530 cm from the path's centre line (half-width 200). In PIE, path queries from twelve points round the shore to the lighthouse were all valid and complete, 2720 to 2893 cm against 2720 straight, and with no turrets the creatures of night one took the lighthouse from 100 to 60. |
| A new seed changes the layout | Seed 42 twice: the same sixteen rock positions. Seed 7: sixteen rocks, none at a seed 42 position. Seeds 1 to 6 gave 14 to 18 rocks; for those seeds only the rock count and the distances to the path were recorded. |
| Player can walk the island, rocks have collision | Holding W from the start for 1.5 s walked the path to x = -385, as before the scatter. Walking at a rock at (712, 992) from 450 cm away: stopped short of it and slid aside, 352 cm in 2 s, against 1115 cm in 1.5 s on open ground. Walking at a bush at (-788, -2420): straight through, x from -1088 to 36. The rock components report the `BlockAll` profile and the foliage `NoCollision`. |

## #14 Intro flyover

Times are game seconds from a per-frame trace (finding F-051), to the nearest third of a second.

| Criterion | Evidence |
|---|---|
| A Level Sequence with an animated camera plays when the game starts | After a click on Play the view target changed from the character to `CineCameraActor` at 6.33 s. Camera positions one second apart: (4911, 2214, 1275) over the sea to the east, (3117, 1610, 1028), (2165, -192, 905), (1383, -2430, 818) south of the lighthouse, (-160, -2365, 701), (-1686, -1975, 572), (-2174, -1009, 431), (-2196, -119, 265) behind the player. That is about half a circle round the lighthouse, from east through south to west. |
| Runs 5 to 15 seconds and ends by blending to the player camera | The sequence is nine seconds long and the blend one second, ten in all. Measured: the shot ran from 6.33 s to 15.0 s, then the view blended to the character's camera at (-1900, 75, 168) and the game began at 15.67 s, which is 9.3 s at the trace's resolution of a third of a second. |
| Input disabled during the shot, restored after | Holding W during the shot left the player at (-1500, 0). After the hand-off, W for one second moved the player to x = -386. The other inputs were tried on the final tree (see the last section). |
| Skip ends the shot early with the same state | Enter at 10.67 s: the view went to the character at once, blending from (235, -1828, 622), and the game began at 11.33 s. The state two seconds later was the same in both runs: started, day 1, 60 resources, 8 pickups, no turrets, lighthouse 100, view target the character, camera at (-1900, 75, 168), player at (-1500, 0, 94). |

## #15 Save between nights

Stopping PIE and starting it again stands for quitting and relaunching. The save is `Saved/SaveGames/BeaconSave.sav`; its contents were read by loading the slot in editor Python.

| Criterion | Evidence |
|---|---|
| Saves automatically at the start of each day | No save file before the run. After Play, at the start of day one: the file exists and holds version 1, night 0, 60 resources, no turrets. After night one, at the start of day two: night 1, 130 resources and five turrets. |
| Continue restores night, resources and every turret with type and position | Before quitting on day two: 130 resources, Sentry at (-723, -723) and (723, 723), Sniper at (-1250, 0) and (-723, 723), Sprayer at (723, -723). After a relaunch the menu offers "Continue" and "New Game"; after Continue the game is on day 2 with night number 1, 130 resources and the same five types at the same five positions. The lighthouse is back at 100; its health is not part of the save. |
| New Game discards the save | With that save present, New Game started day 1 with 60 resources and no turrets, and the file then held night 0, 60 resources, no turrets. |
| Missing or unreadable save falls back to a new game | No file: the menu offers only "Play". An empty file, a save cut to half its length, a file of zeros and a save with version 99: Continue started day 1 with 60 resources and no turrets and showed "The saved game could not be read. Starting a new game."; the day's autosave then replaced the file. The cut and zeroed files each logged one engine warning. **Not met for one case:** a file of plain text crashed the engine inside `LoadGameFromSlot` (finding F-053). The project owner accepted this gap on 2026-11-24 rather than add C++ or change the save format. |
| The format carries a version number | `SaveVersion` is 1 in every file the game wrote. A file written as version 99 was refused by a game whose current version is 1. |

## Re-checks on the final tree

Run after all five tickets, the review fixes and the removal of the unreachable graph nodes (finding F-055).

| Check | Evidence |
|---|---|
| Verify loop, with and without a save | `beacon_mcp.py verify` three times in a row, the first with no save file and the next two with the save the run before left: exit 0 and no log problems each time. |
| Input during the intro (#14) | With the shot slowed so that it was still playing afterwards, E, B, left mouse, Q, N, W and a look input were pressed: no turret, build menu closed, selection unchanged, no muzzle effect, still day, player at (-1500, 0), yaw 0. After Enter and the hand-off, E placed a turret. |
| Combat effects (#12) | A Sentry killed a creature: `Flash` read 1.0, `NS_MuzzleFlash` and `NS_DeathBurst` components were seen, the creature was removed. The notice read "Sentry turret placed". |
| Game over then Restart (#11, #15) | Lighthouse to 0: paused, "THE LIGHTHOUSE HAS FALLEN", "You reached night 0", `button "Restart"`. After Restart: play began with no menu and no intro, game time 6 s, day 1, 60 resources, lighthouse 100, no turrets, view on the character, and W moved the player to x = -386. The save file then held version 1, night 0, 60 resources, no turrets. |
