from __future__ import annotations

from beacon_mcp import find_image, strip_images
from gen_inventory import one_line, render

IMAGE = {"mimeType": "image/png", "data": "A" * 400}


def test_strip_images_replaces_payload_and_keeps_other_fields() -> None:
    result = strip_images({"image": IMAGE, "cameraFOV": 90, "labels": [{"name": "Cube"}]})

    assert result["image"] == {"mimeType": "image/png", "data": "<400 base64 chars>"}
    assert result["cameraFOV"] == 90
    assert result["labels"] == [{"name": "Cube"}]


def test_find_image_looks_inside_nested_results() -> None:
    assert find_image({"returnValue": {"capture": [1, {"image": IMAGE}]}}) == "A" * 400
    assert find_image({"returnValue": {"mimeType": "text/plain", "data": "short"}}) is None


def test_one_line_takes_first_sentence_and_escapes_table_pipes() -> None:
    description = (
        "Finds node types such as 'Utilities|Operators|Add' in a graph.\n\n    Args:\n        graph: g"
    )

    assert one_line(description) == r"Finds node types such as 'Utilities\|Operators\|Add' in a graph."


def test_one_line_truncates_long_text_and_handles_missing_description() -> None:
    assert one_line("word " * 80, limit=40).endswith("…")
    assert len(one_line("word " * 80, limit=40)) == 40
    assert one_line(None) == "(no description)"


def test_render_lists_every_toolset_and_reports_describe_failures() -> None:
    described = {
        "description": "Works with actors.",
        "tools": [{"name": "a.b.ActorTools.get_label", "description": "Returns the actor's label."}],
    }

    text = render([("a.b.ActorTools", described, None), ("a.b.Broken", None, "boom")], "2026-01-01")

    assert "**2 toolsets** and **1 tools**" in text
    assert "| `get_label` | Returns the actor's label. |" in text
    assert "`describe_toolset` failed: `boom`" in text
