"""List, or with --delete remove, the nodes of a Blueprint's graphs that nothing can execute.

`BlueprintTools.write_graph_dsl` replaces an event's chain by disconnecting the
old one, and the old nodes stay in the graph (finding F-055). They do not run,
but they are still there to read, search and maintain.

Usage (repo root, editor running):
  python Tools/mcp/graph_orphans.py /Game/Beacon/Blueprints/BP_Creature [--delete]
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from beacon_mcp import Client, ToolError

BLUEPRINT = "editor_toolset.toolsets.blueprint.BlueprintTools"
EXEC = "Exec"

Node = dict[str, Any]


def node_path(node: Node) -> str:
    path: str = node["node"]["refPath"]
    return path


def has_exec(pins: list[Node]) -> bool:
    return any(pin["type_id"] == EXEC for pin in pins)


def linked_paths(pins: list[Node], *, exec_only: bool) -> set[str]:
    return {
        linked["node"]["refPath"]
        for pin in pins
        if not exec_only or pin["type_id"] == EXEC
        for linked in pin["connected_pins"]
    }


def unreachable_nodes(nodes: list[Node]) -> list[str]:
    """Paths of the nodes that no entry point reaches, given `get_node_infos` results for a whole graph.

    An entry point has an exec output and no exec input: an event, an input action
    event or a function entry. A node with exec pins is unreachable when no chain of
    exec links leads to it from an entry point. A node without exec pins is
    unreachable when everything that reads it is.
    """
    by_path = {node_path(node): node for node in nodes}
    executable = {
        path for path, node in by_path.items() if has_exec(node["input_pins"] + node["output_pins"])
    }
    reached = {
        path
        for path in executable
        if has_exec(by_path[path]["output_pins"]) and not has_exec(by_path[path]["input_pins"])
    }
    frontier = list(reached)
    while frontier:
        for path in linked_paths(by_path[frontier.pop()]["output_pins"], exec_only=True) & by_path.keys():
            if path not in reached:
                reached.add(path)
                frontier.append(path)
    dead = executable - reached
    grew = True
    while grew:
        grew = False
        for path, node in by_path.items():
            if path in dead or path in executable:
                continue
            readers = linked_paths(node["output_pins"], exec_only=False)
            if readers and readers <= dead:
                dead.add(path)
                grew = True
    return sorted(dead)


def graph_orphans(client: Client, graph: Node) -> list[str]:
    nodes = client.call(BLUEPRINT, "find_nodes", {"graph": graph, "title": ""})
    if not nodes:
        return []
    return unreachable_nodes(client.call(BLUEPRINT, "get_node_infos", {"nodes": nodes}))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("blueprint", help="package path, for example /Game/Beacon/Blueprints/BP_Creature")
    parser.add_argument("--delete", action="store_true", help="delete the nodes and compile the Blueprint")
    args = parser.parse_args(argv)
    client = Client()
    blueprint = {"refPath": f"{args.blueprint}.{args.blueprint.rsplit('/', 1)[-1]}"}
    total = 0
    for graph in client.call(BLUEPRINT, "list_graphs", {"blueprint": blueprint}):
        orphans = graph_orphans(client, graph)
        if not orphans:
            continue
        total += len(orphans)
        print(f"{graph['refPath'].rsplit(':', 1)[-1]}: {len(orphans)} unreachable nodes")
        for path in orphans:
            print(f"  {path.rsplit('.', 1)[-1]}")
            if args.delete:
                client.call(BLUEPRINT, "delete_node", {"node": {"refPath": path}})
    if args.delete and total:
        client.call(BLUEPRINT, "compile_blueprint", {"blueprint": blueprint, "warnings_as_errors": True})
        print("deleted and compiled; save the Blueprint and check its graphs still read back the same")
    print(f"unreachable nodes: {total}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ToolError as error:
        print(f"TOOL ERROR: {error}", file=sys.stderr)
        sys.exit(1)
