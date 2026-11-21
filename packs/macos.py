"""Starter macOS tool pack (extend with AppleScript / osascript tools)."""

import re
import subprocess

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launch a macOS application by name (e.g. Safari, Notes, Spotify).",
            "parameters": {
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
        },
    }
]


def _launch_app(args: dict) -> str:
    app = re.sub(r"[^a-zA-Z0-9 ._-]", "", str(args.get("app", "")).strip())
    if not app:
        return "No app specified."
    subprocess.Popen(["open", "-a", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Launched {app}."


HANDLERS = {"launch_app": _launch_app}
