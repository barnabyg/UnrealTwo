"""Print the state of the running play-in-editor game as one JSON log line.

Runs inside the editor's Python interpreter while PIE is active:
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/pie_state.py
The line starts with PIESTATE so it is easy to find in the Output Log.
"""

import json

import unreal


def vector(value: unreal.Vector) -> list[int]:
    return [round(value.x), round(value.y), round(value.z)]


BLUEPRINTS = "/Game/Beacon/Blueprints"


def actors_of(world: unreal.World, blueprint: str) -> list[unreal.Actor]:
    """Live actors of a Beacon Blueprint class, or none if the class does not exist yet."""
    # EditorAssetLibrary refuses to run during PIE, so probe by loading the class.
    try:
        actor_class = unreal.load_class(None, f"{BLUEPRINTS}/{blueprint}.{blueprint}_C")
    except Exception:
        return []
    if actor_class is None:
        return []
    return list(unreal.GameplayStatics.get_all_actors_of_class(world, actor_class))


def variable(target: unreal.Object, name: str, default: object = None) -> object:
    """A Blueprint variable's value, or the default when the class has no such variable."""
    try:
        return target.get_editor_property(name)
    except Exception:
        return default


def type_name(creature: unreal.Actor) -> str:
    kind = variable(creature, "CreatureType")
    return str(variable(kind, "DisplayName", "")) if kind else ""


def read_state() -> dict[str, object]:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is None:
        return {"error": "PIE is not running"}
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    rotation = controller.get_control_rotation()
    mode = unreal.GameplayStatics.get_game_mode(world)
    state: dict[str, object] = {
        "player": vector(pawn.get_actor_location()),
        "yaw": round(rotation.yaw, 1),
        "pitch": round(rotation.pitch, 1),
        "falling": pawn.get_movement_component().is_falling(),
        "paused": unreal.GameplayStatics.is_game_paused(world),
        "started": variable(mode, "bStarted", False),
        "intro_playing": variable(mode, "bIntroPlaying", False),
        "game_over": variable(mode, "bGameOver", False),
        "time": round(unreal.GameplayStatics.get_time_seconds(world), 1),
    }
    camera = unreal.GameplayStatics.get_player_camera_manager(world, 0)
    state["camera"] = vector(camera.get_camera_location())
    state["view_target"] = controller.get_view_target().get_class().get_name()
    lighthouses = actors_of(world, "BP_Lighthouse")
    if lighthouses:
        state["lighthouse_health"] = variable(lighthouses[0], "Health")
    state["creatures"] = [
        {
            "name": creature.get_name(),
            "at": vector(creature.get_actor_location()),
            "health": variable(creature, "Health"),
            "dead": variable(creature, "bDead", False),
            "type": type_name(creature),
        }
        for creature in actors_of(world, "BP_Creature")
    ]
    state["turrets"] = [
        {
            "at": vector(turret.get_actor_location()),
            "has_target": variable(turret, "bHasTarget", False),
            "type": variable(turret, "TypeName", ""),
            "health": variable(turret, "Health"),
            "range": variable(turret, "Range"),
        }
        for turret in actors_of(world, "BP_Turret")
    ]
    state["notice"] = variable(mode, "Notice", "")
    state["wave"] = {
        "index": variable(mode, "WaveIndex", 0),
        "spawned": variable(mode, "SpawnedInWave", 0),
        "alive": variable(mode, "AliveCreatures", 0),
        "all_spawned": variable(mode, "bAllWavesSpawned", False),
        "text": variable(mode, "WaveText", ""),
    }
    state["turret_text"] = variable(pawn, "TurretText", "")
    state["selected_turret"] = variable(pawn, "SelectedTurret", 0)
    state["build_menu_open"] = variable(pawn, "bBuildMenuOpen", False)
    state["phase"] = {
        "night": variable(mode, "bIsNight", False),
        "night_number": variable(mode, "NightNumber", 0),
        "text": variable(mode, "PhaseText", ""),
        "count_scale": variable(mode, "CountScale", 1.0),
    }
    state["resources"] = variable(mode, "Resources", 0)
    state["pickups"] = [
        vector(pickup.get_actor_location()) for pickup in actors_of(world, "BP_ResourcePickup")
    ]
    if lighthouses:
        state["beam_on"] = variable(lighthouses[0], "bBeamOn", False)
        beams = lighthouses[0].get_components_by_class(unreal.SpotLightComponent)
        if beams:
            state["beam_yaw"] = round(beams[0].get_world_rotation().yaw)
    night = variable(mode, "Night")
    state["night_data"] = night.get_name() if night else ""
    suns = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.DirectionalLight)
    if suns:
        state["sun_intensity"] = round(suns[0].get_component_by_class(unreal.LightComponent).intensity, 2)
    return state


print("PIESTATE " + json.dumps(read_state()))
