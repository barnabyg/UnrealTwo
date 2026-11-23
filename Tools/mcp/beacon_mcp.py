"""Small streamable-HTTP client for the Unreal Editor MCP server.

Agents normally call the server through their own MCP integration. This client
exists for the cases that integration handles badly: saving a base64 viewport
capture to a PNG file, batching many calls, and running an editor console
command. Every call still goes through the server's `call_tool`, so it is the
same tool surface.

Usage (run from the repo root, editor running):
  python Tools/mcp/beacon_mcp.py describe <toolset>
  python Tools/mcp/beacon_mcp.py call <toolset> <tool> '<json-args>' [--png out.png]
  python Tools/mcp/beacon_mcp.py console "<console command>"
  python Tools/mcp/beacon_mcp.py py <script.py>
  python Tools/mcp/beacon_mcp.py logs "<regex>" [--max 40]
  python Tools/mcp/beacon_mcp.py save
  python Tools/mcp/beacon_mcp.py verify --png out.png [--seconds 5]
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

URL = "http://127.0.0.1:8000/mcp"

APP = "EditorToolset.EditorAppToolset"
LOGS = "EditorToolset.LogsToolset"
SLATE = "SlateInspectorToolset.SlateInspectorToolset"

# Log lines that a clean PIE run must not contain, apart from the MCP's own
# noise (see docs/agents/unreal-mcp.md).
PROBLEM_PATTERN = r"Error:|Warning:"
EXPECTED_NOISE = (
    'Call to unknown method "server/discover"',
    "is Licensed Technology under the UE EULA",
)


# The level viewport panel covers at least this share of the editor window.
VIEWPORT_MIN_AREA = 0.4
# A base64 payload shorter than this is not a screenshot worth special handling.
MIN_IMAGE_CHARS = 200


class ToolError(Exception):
    """The server reported a failure for a tool call."""


class Client:
    """One MCP session against the editor."""

    def __init__(self, url: str = URL) -> None:
        self.url = url
        self.session_id: str | None = None
        self.next_id = 0

    def _post(self, payload: dict[str, Any], timeout: float = 180.0) -> dict[str, Any] | None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(  # noqa: S310 - fixed loopback http URL
            self.url, data=json.dumps(payload).encode("utf-8"), headers=headers
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            self.session_id = response.headers.get("Mcp-Session-Id") or self.session_id
            body = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
        if not body.strip():
            return None
        if "text/event-stream" in content_type:
            last: dict[str, Any] | None = None
            for line in body.splitlines():
                if line.startswith("data:"):
                    last = json.loads(line[5:].strip())
            return last
        result: dict[str, Any] = json.loads(body)
        return result

    def _rpc(self, method: str, params: dict[str, Any] | None = None, *, notify: bool = False) -> Any:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if not notify:
            self.next_id += 1
            message["id"] = self.next_id
        return self._post(message)

    def connect(self) -> None:
        if self.next_id:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "beacon-mcp-client", "version": "1.0"},
            },
        )
        self._rpc("notifications/initialized", notify=True)

    def top_level(self, name: str, arguments: dict[str, Any]) -> str:
        """Call one of the three top-level tools and return its text content."""
        self.connect()
        response = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if response is None:
            raise ToolError(f"{name}: empty response")
        if "error" in response:
            raise ToolError(json.dumps(response["error"]))
        result = response["result"]
        text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise ToolError(text)
        return text

    def call(self, toolset: str, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call a toolset tool and return its `returnValue` (or the whole result)."""
        text = self.top_level(
            "call_tool",
            {"toolset_name": toolset, "tool_name": tool, "arguments": arguments or {}},
        )
        try:
            parsed = json.loads(text) if text else None
        except json.JSONDecodeError:
            return text
        if isinstance(parsed, dict) and set(parsed) == {"returnValue"}:
            return parsed["returnValue"]
        return parsed

    def list_toolsets(self) -> list[str]:
        listing = self.top_level("list_toolsets", {})
        # Toolset names are dotted; bullet lines inside descriptions are not.
        return [n for n in re.findall(r"^- ([\w.]+): ", listing, flags=re.MULTILINE) if "." in n]

    def describe(self, toolset: str) -> dict[str, Any]:
        described: dict[str, Any] = json.loads(self.top_level("describe_toolset", {"toolset_name": toolset}))
        return described

    def logs(self, pattern: str, max_entries: int = 40, category: str = "") -> list[str]:
        entries: list[str] = self.call(
            LOGS,
            "GetLogEntries",
            {"category": category, "pattern": pattern, "maxEntries": max_entries},
        )
        return entries

    def console(self, command: str) -> None:
        """Run an editor console command by typing it into the status-bar Cmd box.

        The server has no console-command tool, so this drives the editor UI
        through the Slate inspector toolset. The box must be clicked first:
        typing into an unfocused box returns false and does nothing.
        """
        snapshot: str = self.call(SLATE, "Snapshot", {"ref": "", "maxDepth": 40})
        lines = snapshot.splitlines()
        ref = None
        for index, line in enumerate(lines):
            if 'text "Cmd"' in line:
                for following in lines[index : index + 6]:
                    match = re.search(r"textbox .*\[ref=(tb\d+)\]", following)
                    if match:
                        ref = match.group(1)
                        break
                break
        if ref is None:
            raise ToolError("console input box not found in the editor status bar")
        self.call(SLATE, "Click", {"ref": ref})
        if not self.call(SLATE, "Type", {"ref": ref, "text": command, "submit": True}):
            raise ToolError(f"console did not accept: {command}")

    def run_python(self, script: Path, wait_seconds: float = 1.0) -> list[str]:
        """Run an editor Python script through the console and return its log lines."""
        marker = f"beacon-py-{time.time_ns()}"
        self.console(f"py print('{marker}')")
        self.console(f'py "{script.resolve().as_posix()}"')
        time.sleep(wait_seconds)
        entries = self.logs("LogPython", 400)
        for index, entry in enumerate(entries):
            if marker in entry:
                return entries[index + 1 :]
        return entries

    def capture(self, png: Path, transform: dict[str, Any] | None = None) -> dict[str, Any]:
        """Capture the level viewport to a PNG file and return the capture metadata."""
        # The schema marks captureTransform and annotations optional, but the
        # server rejects a call without them. Default to the viewport's current
        # camera and to an overlay with the grid and the labels switched off.
        if transform is None:
            transform = self.call(APP, "GetCameraTransform")
        no_overlay = {
            "gridSpacing": 0,
            "gridExtent": 0,
            "gridHeight": 0,
            "maxLabelDistance": 0,
            "classFilter": {"refPath": "/Script/Engine.Actor"},
            "maxLabels": 0,
        }
        capture: dict[str, Any] = self.call(
            APP,
            "CaptureViewport",
            {"captureTransform": transform, "annotations": no_overlay, "bShowUI": False},
        )
        image = capture.pop("image")
        if not image.get("data"):
            raise ToolError("CaptureViewport returned no image")
        png.parent.mkdir(parents=True, exist_ok=True)
        png.write_bytes(base64.b64decode(image["data"]))
        return capture

    def capture_game(self, png: Path) -> None:
        """Save what the level viewport shows right now, including a running PIE game.

        `CaptureViewport` renders the editor world even while PIE is running, so
        this takes a Slate screenshot of the viewport panel instead.
        """
        snapshot: str = self.call(SLATE, "Snapshot", {"ref": "", "maxDepth": 40})
        image = self.call(SLATE, "Screenshot", {"ref": viewport_panel_ref(snapshot)})
        png.parent.mkdir(parents=True, exist_ok=True)
        png.write_bytes(base64.b64decode(image["data"]))

    def pie_state(self) -> dict[str, Any]:
        """Read the running game's state through Tools/editor_python/pie_state.py."""
        script = Path(__file__).resolve().parents[1] / "editor_python" / "pie_state.py"
        for line in reversed(self.run_python(script, 0.3)):
            if "PIESTATE " in line:
                state: dict[str, Any] = json.loads(line.split("PIESTATE ", 1)[1])
                return state
        raise ToolError("pie_state.py printed no PIESTATE line")

    def save_all(self) -> str:
        """Save every unsaved map, actor and asset through Tools/editor_python/save_dirty.py.

        `AssetTools.save_assets` on a map skips changed actors unless the map
        package itself is dirty, so level edits are saved with this instead.
        """
        script = Path(__file__).resolve().parents[1] / "editor_python" / "save_dirty.py"
        for line in reversed(self.run_python(script, 2.0)):
            if "SAVEDIRTY " in line:
                summary = line.split("SAVEDIRTY ", 1)[1]
                if not summary.endswith("after=0"):
                    raise ToolError(f"packages are still unsaved: {summary}")
                return summary
        raise ToolError("save_dirty.py printed no SAVEDIRTY line")

    def start_pie(self, warmup_seconds: float = 2.0) -> None:
        options = {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": warmup_seconds}
        self.call(APP, "StartPIE", {"options": options})

    def stop_pie(self) -> None:
        self.call(APP, "StopPIE")

    def problems_since(self, marker: str) -> list[str]:
        """Warning and error log lines written after the marker line, minus expected noise."""
        entries = self.logs("", 0)
        for index, entry in enumerate(entries):
            if marker in entry:
                entries = entries[index + 1 :]
                break
        return [
            entry
            for entry in entries
            if re.search(PROBLEM_PATTERN, entry) and not any(noise in entry for noise in EXPECTED_NOISE)
        ]

    def mark_log(self) -> str:
        marker = f"beacon-mark-{time.time_ns()}"
        self.console(f"py print('{marker}')")
        return marker

    def verify(self, png: Path, seconds: float) -> list[str]:
        """The verify loop: start PIE, wait, capture, stop PIE, return problem log lines."""
        marker = self.mark_log()
        self.start_pie()
        try:
            time.sleep(seconds)
            self.capture_game(png)
        finally:
            self.stop_pie()
        return self.problems_since(marker)


def viewport_panel_ref(snapshot: str) -> str:
    """Ref of the level viewport panel in a Slate snapshot, or "" for the whole window.

    The viewport has no name in the snapshot. It is the innermost splitter that
    still covers most of the window without spanning its full width.
    """
    window = re.search(r"window .*size=(\d+),(\d+)\]", snapshot)
    if not window:
        return ""
    window_width, window_height = int(window.group(1)), int(window.group(2))
    best = ""
    for match in re.finditer(r"splitter \[pos=\d+,\d+ size=(\d+),(\d+)\] \[ref=(sp\d+)\]", snapshot):
        width, height = int(match.group(1)), int(match.group(2))
        covers_most = width * height >= VIEWPORT_MIN_AREA * window_width * window_height
        if covers_most and width < window_width:
            best = match.group(3)
    return best


def strip_images(value: Any) -> Any:
    """Replace base64 image payloads so results stay printable."""
    if isinstance(value, dict):
        data = value.get("data")
        if "mimeType" in value and isinstance(data, str) and len(data) > MIN_IMAGE_CHARS:
            return {"mimeType": value["mimeType"], "data": f"<{len(data)} base64 chars>"}
        return {key: strip_images(item) for key, item in value.items()}
    if isinstance(value, list):
        return [strip_images(item) for item in value]
    return value


def find_image(value: Any) -> str | None:
    if isinstance(value, dict):
        data = value.get("data")
        if "mimeType" in value and isinstance(data, str) and len(data) > MIN_IMAGE_CHARS:
            return data
        value = list(value.values())
    if isinstance(value, list):
        for item in value:
            found = find_image(item)
            if found:
                return found
    return None


def print_signatures(described: dict[str, Any]) -> None:
    print(f"# {described['name']} ({len(described['tools'])} tools)")
    for tool in described["tools"]:
        schema = tool.get("inputSchema", {})
        required = set(schema.get("required", []))
        arguments = ", ".join(
            name if name in required else f"{name}?" for name in schema.get("properties", {})
        )
        first_line = tool.get("description", "").strip().split("\n")[0]
        print(f"{tool['name'].split('.')[-1]}({arguments}): {first_line}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    describe = commands.add_parser("describe", help="print a toolset's tool signatures")
    describe.add_argument("toolset")
    describe.add_argument("--json", action="store_true", help="print the full schema")
    call = commands.add_parser("call", help="call one toolset tool")
    call.add_argument("toolset")
    call.add_argument("tool")
    call.add_argument("arguments", nargs="?", default="{}", help="JSON object, or @file.json")
    call.add_argument("--png", type=Path, help="save the first image in the result here")
    console = commands.add_parser("console", help="run an editor console command")
    console.add_argument("text")
    python = commands.add_parser("py", help="run an editor Python script")
    python.add_argument("script", type=Path)
    python.add_argument("--wait", type=float, default=1.0)
    logs = commands.add_parser("logs", help="print matching Output Log lines")
    logs.add_argument("pattern")
    logs.add_argument("--max", type=int, default=40)
    commands.add_parser("save", help="save every unsaved map, actor and asset")
    verify = commands.add_parser("verify", help="start PIE, capture, stop PIE, report log problems")
    verify.add_argument("--png", type=Path, required=True)
    verify.add_argument("--seconds", type=float, default=5.0)
    return parser


def run_call(client: Client, args: argparse.Namespace) -> None:
    raw = args.arguments
    arguments = json.loads(Path(raw[1:]).read_text(encoding="utf-8") if raw.startswith("@") else raw)
    result = client.call(args.toolset, args.tool, arguments)
    if args.png:
        data = find_image(result)
        if data is None:
            raise ToolError("the result contains no image")
        args.png.parent.mkdir(parents=True, exist_ok=True)
        args.png.write_bytes(base64.b64decode(data))
    print(json.dumps(strip_images(result), indent=1))


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    client = Client()
    if args.command == "describe":
        described = client.describe(args.toolset)
        if args.json:
            print(json.dumps(described, indent=1))
        else:
            print_signatures(described)
    elif args.command == "call":
        run_call(client, args)
    elif args.command == "console":
        client.console(args.text)
    elif args.command == "py":
        for line in client.run_python(args.script, args.wait):
            print(line)
    elif args.command == "logs":
        for line in client.logs(args.pattern, args.max):
            print(line)
    elif args.command == "save":
        print(client.save_all())
    elif args.command == "verify":
        problems = client.verify(args.png, args.seconds)
        for line in problems:
            print(line)
        print(f"screenshot: {args.png}  log problems: {len(problems)}")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main(sys.argv[1:]))
    except ToolError as error:
        print(f"TOOL ERROR: {error}", file=sys.stderr)
        sys.exit(1)
