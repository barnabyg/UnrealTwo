"""Create the creature Blackboard and Behaviour Tree assets.

The Unreal MCP's Behaviour Tree toolset can only inspect a tree, so this is the
editor Python fallback (finding F-017). It runs inside the editor:
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/build_creature_ai.py
Running it again rebuilds the assets in place. The last log line starts with
BUILDAI and says what was written.

A plan is one Sequence: find a target and a point to stand at, walk there, hit
the target once. The find and attack steps are Blueprint task classes, authored
through the MCP. A tree with one plan runs it in a loop. A tree with several
tries them in order under a Selector, so the hunter goes for a turret while one
stands and for the lighthouse otherwise.
"""

import unreal

AI_FOLDER = "/Game/Beacon/AI"
BLACKBOARD = "BB_Creature"
ATTACK_TASK = "BTTask_AttackTarget"
# Tree name -> its plans, as (plan name, Blueprint task that chooses the target).
TREES = {
    "BT_Creature": [("Attack lighthouse", "BTTask_FindLighthouse")],
    "BT_Hunter": [("Hunt turret", "BTTask_FindTurret"), ("Attack lighthouse", "BTTask_FindLighthouse")],
}
# How close to the stand point MoveTo must get, in cm. The attack task's range
# check (BP_Creature.AttackRange) must be larger than this.
ACCEPTABLE_RADIUS = 60.0


def load_or_create(name: str, asset_class: type, factory: unreal.Factory) -> unreal.Object:
    path = f"{AI_FOLDER}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, AI_FOLDER, asset_class, factory)


def blackboard_entry(blackboard: unreal.BlackboardData, name: str, key_type: str) -> unreal.BlackboardEntry:
    # The key type classes are not exposed to Python by name, so load them by path.
    key_class = unreal.load_class(None, f"/Script/AIModule.BlackboardKeyType_{key_type}")
    entry = unreal.BlackboardEntry()
    entry.set_editor_property("entry_name", name)
    entry.set_editor_property("key_type", unreal.new_object(key_class, outer=blackboard))
    return entry


def build_blackboard() -> unreal.BlackboardData:
    blackboard = load_or_create(BLACKBOARD, unreal.BlackboardData, unreal.BlackboardDataFactory())
    blackboard.set_editor_property(
        "keys",
        [
            blackboard_entry(blackboard, "TargetActor", "Object"),
            blackboard_entry(blackboard, "MoveGoal", "Vector"),
        ],
    )
    return blackboard


def blueprint_task(tree: unreal.BehaviorTree, name: str) -> unreal.BTTaskNode:
    task_class = unreal.load_class(None, f"{AI_FOLDER}/{name}.{name}_C")
    task = unreal.new_object(task_class, outer=tree)
    task.set_editor_property("node_name", name.removeprefix("BTTask_"))
    return task


def move_to_goal(tree: unreal.BehaviorTree) -> unreal.BTTask_MoveTo:
    move = unreal.new_object(unreal.BTTask_MoveTo, outer=tree)
    move.set_editor_property("node_name", "Move to stand point")
    # Edit the existing selector so its allowed key types are kept.
    key = move.get_editor_property("blackboard_key")
    key.set_editor_property("selected_key_name", "MoveGoal")
    move.set_editor_property("blackboard_key", key)
    # In 5.8 the radius is a "value or blackboard key" struct, not a plain float.
    radius = move.get_editor_property("acceptable_radius")
    radius.set_editor_property("default_value", ACCEPTABLE_RADIUS)
    move.set_editor_property("acceptable_radius", radius)
    return move


def composite_child(
    composite: unreal.BTCompositeNode | None = None, task: unreal.BTTaskNode | None = None
) -> unreal.BTCompositeChild:
    child = unreal.BTCompositeChild()
    if composite is not None:
        child.set_editor_property("child_composite", composite)
    if task is not None:
        child.set_editor_property("child_task", task)
    return child


def build_plan(tree: unreal.BehaviorTree, name: str, find_task: str) -> unreal.BTComposite_Sequence:
    sequence = unreal.new_object(unreal.BTComposite_Sequence, outer=tree)
    sequence.set_editor_property("node_name", name)
    steps = [blueprint_task(tree, find_task), move_to_goal(tree), blueprint_task(tree, ATTACK_TASK)]
    sequence.set_editor_property("children", [composite_child(task=step) for step in steps])
    return sequence


def build_tree(
    name: str, plans: list[tuple[str, str]], blackboard: unreal.BlackboardData
) -> unreal.BehaviorTree:
    tree = load_or_create(name, unreal.BehaviorTree, unreal.BehaviorTreeFactory())
    tree.set_editor_property("blackboard_asset", blackboard)
    sequences = [build_plan(tree, plan_name, find_task) for plan_name, find_task in plans]
    if len(sequences) == 1:
        root: unreal.BTCompositeNode = sequences[0]
    else:
        root = unreal.new_object(unreal.BTComposite_Selector, outer=tree)
        root.set_editor_property("node_name", "First plan that works")
        root.set_editor_property("children", [composite_child(composite=sequence) for sequence in sequences])
    tree.set_editor_property("root_node", root)
    return tree


def main() -> None:
    blackboard = build_blackboard()
    written = [blackboard.get_path_name()]
    unreal.EditorAssetLibrary.save_loaded_asset(blackboard)
    for name, plans in TREES.items():
        tree = build_tree(name, plans, blackboard)
        unreal.EditorAssetLibrary.save_loaded_asset(tree)
        written.append(tree.get_path_name())
    print("BUILDAI wrote " + ", ".join(written))


main()
