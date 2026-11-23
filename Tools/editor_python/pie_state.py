"""Print the state of the running play-in-editor game as one JSON log line.

Runs inside the editor's Python interpreter while PIE is active:
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/pie_state.py
The line starts with PIESTATE so it is easy to find in the Output Log.
"""

import json

import unreal


def vector(value: unreal.Vector) -> list[int]:
    return [round(value.x), round(value.y), round(value.z)]


def read_state() -> dict[str, object]:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is None:
        return {"error": "PIE is not running"}
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    rotation = controller.get_control_rotation()
    return {
        "player": vector(pawn.get_actor_location()),
        "yaw": round(rotation.yaw, 1),
        "pitch": round(rotation.pitch, 1),
        "falling": pawn.get_movement_component().is_falling(),
    }


print("PIESTATE " + json.dumps(read_state()))
