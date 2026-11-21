"""Starter Windows tool pack (extend with PowerShell / Start-Process tools)."""

import re
import shutil
import subprocess

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launch a Windows application by executable name.",
            "parameters": {
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
        },
    }
]


def _launch_app(args: dict) -> str:
    app = str(args.get("app", "")).strip()
    if re.match(r"^[a-zA-Z0-9._-]+$", app) and shutil.which(app):
        subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Launched {app}."
    return f"App '{app}' not found."


HANDLERS = {"launch_app": _launch_app}
