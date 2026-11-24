from __future__ import annotations

from typing import Any

from graph_orphans import unreachable_nodes

Pin = dict[str, Any]


def pin(type_id: str, *linked: str, name: str = "pin") -> Pin:
    return {
        "name": name,
        "type_id": type_id,
        "connected_pins": [{"node": {"refPath": path}} for path in linked],
    }


def node(path: str, inputs: list[Pin], outputs: list[Pin]) -> dict[str, Any]:
    return {"node": {"refPath": path}, "input_pins": inputs, "output_pins": outputs}


def test_a_chain_that_no_event_leads_to_is_unreachable_with_the_values_only_it_reads() -> None:
    graph = [
        node("Event", [], [pin("Exec", "SetHealth")]),
        node("SetHealth", [pin("Exec", "Event"), pin("Float", "Health")], [pin("Exec")]),
        node("Health", [], [pin("Float", "SetHealth", "OldBranch")]),
        node("OldPrint", [pin("Exec"), pin("String", "OldText")], [pin("Exec", "OldBranch")]),
        node("OldBranch", [pin("Exec", "OldPrint"), pin("Float", "Health")], [pin("Exec")]),
        node("OldText", [], [pin("String", "OldPrint")]),
    ]

    assert unreachable_nodes(graph) == ["OldBranch", "OldPrint", "OldText"]


def test_an_input_action_event_with_named_exec_outputs_is_an_entry_point() -> None:
    graph = [
        node("IA_Fire", [], [pin("Exec", name="Triggered"), pin("Exec", "Fire", name="Started")]),
        node("Fire", [pin("Exec", "IA_Fire")], [pin("Exec")]),
    ]

    assert unreachable_nodes(graph) == []


def test_a_value_node_that_feeds_nothing_or_a_live_node_is_left_alone() -> None:
    graph = [
        node("Entry", [], [pin("Exec", "Call")]),
        node("Call", [pin("Exec", "Entry"), pin("Object", "Delegate")], [pin("Exec")]),
        node("Delegate", [], [pin("Delegate", "Call")]),
        node("Unused", [], [pin("Float")]),
    ]

    assert unreachable_nodes(graph) == []
