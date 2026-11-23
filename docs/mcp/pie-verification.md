# Play-in-editor verification record

What the agent measured in play-in-editor (PIE) for each acceptance criterion of tickets #4 to #10, on 2026-11-23. Every run was started, driven, read and stopped through the MCP as described in [verify-loop.md](../agents/verify-loop.md). Positions are in centimetres; the lighthouse stands at the origin. Game state was read with `Tools/editor_python/pie_state.py`.

**Clean log.** Each final run below ended with no `Warning:` or `Error:` line added to the Output Log between the start marker and the stop, apart from the expected noise listed in [unreal-mcp.md](../agents/unreal-mcp.md). The same is true of a plain `beacon_mcp.py verify` run on the final commit.

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
