from __future__ import annotations

import pytest
from beacon_mcp import ToolError, find_image, start_button_ref, strip_images, viewport_panel_ref, widget_ref
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


def test_viewport_panel_ref_picks_innermost_large_splitter_narrower_than_window() -> None:
    snapshot = "\n".join(
        [
            'window "Beacon - Unreal Editor" [pos=0,0 size=1920,1032] [ref=w1]',
            "  splitter [pos=0,0 size=1920,1032] [ref=sp1]",
            "    splitter [pos=4,102 size=1912,894] [ref=sp2]",
            "      splitter [pos=4,102 size=1526,894] [ref=sp3]",
            "        splitter [pos=4,102 size=1526,894] [ref=sp4]",
            "      splitter [pos=1537,431 size=377,563] [ref=sp6]",
        ]
    )

    assert viewport_panel_ref(snapshot) == "sp4"


def test_viewport_panel_ref_falls_back_to_whole_window() -> None:
    assert viewport_panel_ref("nothing useful") == ""
    assert viewport_panel_ref('window "Editor" [pos=0,0 size=800,600] [ref=w1]') == ""


GAME_UI = "\n".join(
    [
        'text "Build - choose a turret" [pos=604,498 size=409,43] [ref=x217]',
        'button "Sentry  -  cost 25   (selected)" [pos=604,532 size=409,42] [ref=b264]',
        'button "Sniper  -  cost 40" [disabled] [pos=604,565 size=409,42] [ref=b265]',
        'button "Play" [pos=655,605 size=280,72] [ref=b250]',
        'button "Play in a new window" [pos=10,10 size=20,20] [ref=b9]',
    ]
)


def test_widget_ref_finds_a_button_by_the_start_of_its_label() -> None:
    assert widget_ref(GAME_UI, "button", "Sentry") == "b264"
    assert widget_ref(GAME_UI, "text", "Build") == "x217"


def test_widget_ref_prefers_an_exact_label_over_a_longer_one() -> None:
    reordered = "\n".join(reversed(GAME_UI.splitlines()))

    assert widget_ref(reordered, "button", "Play") == "b250"


def test_widget_ref_refuses_disabled_and_missing_widgets() -> None:
    with pytest.raises(ToolError, match="disabled"):
        widget_ref(GAME_UI, "button", "Sniper")
    with pytest.raises(ToolError, match="no button"):
        widget_ref(GAME_UI, "button", "Restart")


def test_widget_ref_takes_an_enabled_match_over_a_disabled_one_with_the_same_start() -> None:
    snapshot = "\n".join(
        [
            'button "Sniper  -  cost 40" [disabled] [pos=1,1 size=9,9] [ref=b1]',
            'button "Sniper rifle" [pos=1,1 size=9,9] [ref=b2]',
        ]
    )

    assert widget_ref(snapshot, "button", "Sniper") == "b2"


def test_widget_ref_refuses_to_guess_between_two_enabled_matches() -> None:
    with pytest.raises(ToolError, match="more than one"):
        widget_ref(GAME_UI, "button", "Pla")


def test_widget_ref_with_exact_ignores_longer_labels() -> None:
    longer_only = 'button "Play in a new window" [pos=10,10 size=20,20] [ref=b9]'

    with pytest.raises(ToolError, match="no button"):
        widget_ref(longer_only, "button", "Play", exact=True)


def test_start_button_ref_is_play_without_a_save_and_new_game_with_one() -> None:
    with_save = "\n".join(
        [
            'button "Continue" [pos=655,560 size=280,72] [ref=b3]',
            'button "New Game" [pos=655,690 size=280,72] [ref=b4]',
            'button "Play in a new window" [pos=10,10 size=20,20] [ref=b9]',
        ]
    )

    assert start_button_ref(GAME_UI) == "b250"
    assert start_button_ref(with_save) == "b4"


def test_start_button_ref_says_when_the_menu_is_not_showing() -> None:
    with pytest.raises(ToolError, match="main menu"):
        start_button_ref('button "Restart" [pos=1,1 size=9,9] [ref=b7]')
