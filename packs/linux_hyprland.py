"""Optional Linux / Hyprland / PipeWire desktop pack."""

import json
import re
import shutil
import subprocess
import time

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launch a desktop application by executable name, optionally on a workspace (1-10).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "Executable name (e.g. firefox, spotify, nautilus)"},
                    "workspace": {"type": "integer", "description": "Optional workspace 1-10"},
                },
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_window",
            "description": "Close the currently active window.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_workspace",
            "description": "Switch to a Hyprland workspace (1-10).",
            "parameters": {
                "type": "object",
                "properties": {"workspace": {"type": "integer"}},
                "required": ["workspace"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Adjust or set system volume via PipeWire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "'up', 'down', 'mute', '+10'/'-10', or '0'-'100'"},
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "media_control",
            "description": "Control media playback via playerctl.",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": ["play-pause", "next", "previous", "stop"]}},
                "required": ["action"],
            },
        },
    },
]


def get_context() -> str:
    def hypr_json(cmd):
        try:
            return json.loads(subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode())
        except Exception:
            return None

    active = hypr_json(["hyprctl", "activewindow", "-j"]) or {}
    clients = hypr_json(["hyprctl", "clients", "-j"]) or []
    lines = [f"Active: [{active.get('class','')}] {active.get('title','')} (ws {active.get('workspace',{}).get('name','')})"]
    for c in clients:
        lines.append(f"- ws {c.get('workspace',{}).get('name','')}: [{c.get('class','')}] {c.get('title','')}")
    return "\n".join(lines)


def _focus_ws(ws_val):
    if ws_val is not None:
        ws = int(ws_val)
        if 1 <= ws <= 10:
            subprocess.run(["hyprctl", "dispatch", f"hl.dsp.focus({{ workspace = '{ws}' }})"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.2)
            return ws
    return None


def _launch_app(args: dict) -> str:
    raw = str(args.get("app", "")).strip()
    aliases = {"files": "nautilus", "file manager": "nautilus", "browser": "firefox", "terminal": "foot"}
    mapped = aliases.get(raw.lower(), raw)
    candidates = [mapped, raw, raw.replace(" ", "").lower(), raw.replace(" ", "-").lower()]
    app = next((c for c in candidates if re.match(r"^[a-zA-Z0-9._-]+$", c) and shutil.which(c)), "")
    if not app:
        return f"App '{raw}' not found."
    ws = _focus_ws(args.get("workspace"))
    cmd = [app, "--new-window"] if (ws and "firefox" in app) else [app]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    if ws:
        time.sleep(1.2)
    return f"Launched {app}" + (f" on workspace {ws}." if ws else ".")


def _close_window(_args: dict) -> str:
    subprocess.run(["hyprctl", "dispatch", "hl.dsp.window.close()"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "Closed active window."


def _switch_workspace(args: dict) -> str:
    ws = int(args.get("workspace", 1))
    if 1 <= ws <= 10:
        _focus_ws(ws)
        return f"Switched to workspace {ws}."
    return "Workspace must be 1-10."


def _set_volume(args: dict) -> str:
    lvl = str(args.get("level", "")).strip().rstrip("%")
    if lvl == "up":
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Volume increased by 5%."
    if lvl == "down":
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Volume decreased by 5%."
    if re.match(r"^[+-]\d+$", lvl):
        step = max(1, min(int(lvl[1:]), 100))
        sign = "+" if lvl[0] == "+" else "-"
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{step}%{sign}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Volume {'increased' if sign == '+' else 'decreased'} by {step}%."
    if lvl == "mute":
        subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Toggled mute."
    if lvl.isdigit():
        pct = max(0, min(int(lvl), 100))
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Volume set to {pct}%."
    return "Invalid volume level."


def _media_control(args: dict) -> str:
    act = str(args.get("action", ""))
    if act in {"play-pause", "next", "previous", "stop"}:
        subprocess.run(["playerctl", act], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Media: {act}."
    return "Invalid media action."


HANDLERS = {
    "launch_app": _launch_app,
    "close_window": _close_window,
    "switch_workspace": _switch_workspace,
    "set_volume": _set_volume,
    "media_control": _media_control,
}
