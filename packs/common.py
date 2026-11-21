"""Cross-platform starter tools: open_url, set_timer, find_file, open_path."""

import os
import re
import shutil
import subprocess
import sys
import webbrowser

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a web URL in the default browser (or a specified browser).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full http/https URL"},
                    "browser": {"type": "string", "description": "Optional browser executable"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a background countdown timer in seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer", "description": "Duration in seconds"},
                    "label": {"type": "string", "description": "Short label for the timer"},
                },
                "required": ["seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_file",
            "description": "Search for files in Downloads/Documents using short space-separated keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short keywords, e.g. 'module 6'"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_path",
            "description": "Open a file or its containing folder inside the user's home directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path inside home directory"},
                    "parent": {"type": "boolean", "description": "True to open the parent folder"},
                },
                "required": ["path"],
            },
        },
    },
]


def _open_url(args: dict) -> str:
    url = str(args.get("url", "")).strip()
    if not re.match(r"^https?://\S+$", url):
        return "Invalid URL."
    browser = str(args.get("browser", "")).strip()
    if browser and re.match(r"^[a-zA-Z0-9._-]+$", browser) and shutil.which(browser):
        subprocess.Popen([browser, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return f"Opened {url} in {browser}."
    webbrowser.open(url)
    return f"Opened {url}."


def _set_timer(args: dict) -> str:
    secs = max(1, min(int(args.get("seconds", 10)), 86400))
    label = re.sub(r"[^a-zA-Z0-9 .,!?_-]", "", str(args.get("label", "Timer finished")))
    cmd = [
        sys.executable,
        "-c",
        f"import time, shutil, subprocess; time.sleep({secs}); "
        f"shutil.which('notify-send') and subprocess.run(['notify-send', '-a', 'Agent', 'Timer', {label!r}])",
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return f"Timer set for {secs} seconds ({label})."


def _find_file(args: dict) -> str:
    raw_q = re.sub(r"[^a-zA-Z0-9._ -]", " ", str(args.get("name", ""))).replace("_", " ").replace("-", " ")
    words = [w for w in raw_q.split() if w.lower() not in {"file", "the", "of", "in", "a", "an"}]
    if not words:
        return "No filename provided."
    dl_dir = os.path.expanduser("~/Downloads")
    if not os.path.isdir(dl_dir):
        return "Downloads folder not found."

    if shutil.which("fd") and shutil.which("fzf"):
        all_files = subprocess.run(
            ["fd", "--type", "f", "--max-depth", "4", "--exclude", "node_modules", "--exclude", ".git", ".", dl_dir],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10,
        ).stdout.decode(errors="ignore")
        if all_files.strip():
            r = subprocess.run(
                ["fzf", "--filter", " ".join(words)],
                input=all_files.encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5,
            )
            lines = r.stdout.decode(errors="ignore").strip().splitlines()[:15]
            if lines:
                return "\n".join(lines)

    matches = []
    for root, dirs, files in os.walk(dl_dir):
        dirs[:] = [d for d in dirs if d not in {"node_modules", ".git"}]
        for f in files:
            if all(w.lower() in f.lower() for w in words):
                matches.append(os.path.join(root, f))
                if len(matches) >= 15:
                    return "\n".join(matches)
    return "\n".join(matches) if matches else f"No files matching {' '.join(words)} found."


def _open_path(args: dict) -> str:
    home = os.path.realpath(os.path.expanduser("~"))
    target = os.path.realpath(os.path.expanduser(str(args.get("path", "")).strip()))
    if args.get("parent"):
        target = os.path.dirname(target)
    if not (target == home or target.startswith(home + os.sep)) or not os.path.exists(target):
        return "Invalid or missing path."
    if sys.platform == "darwin":
        subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif os.name == "nt":
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return f"Opened {target}."


HANDLERS = {
    "open_url": _open_url,
    "set_timer": _set_timer,
    "find_file": _find_file,
    "open_path": _open_path,
}
