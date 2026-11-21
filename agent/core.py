"""Core Ollama JSON tool-calling loop with dynamic OS pack loading."""

import importlib
import json
import os
import sys
import urllib.request

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)


def load_config() -> dict:
    cfg_path = os.path.expanduser("~/.config/local-voice-agent/config.json")
    if os.path.isfile(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    with open(os.path.join(REPO_DIR, "config.example.json"), encoding="utf-8") as f:
        return json.load(f)


def load_packs(pack_names: list[str]) -> tuple[list[dict], dict, list[str]]:
    tools, handlers, contexts = [], {}, []
    for name in pack_names:
        mod = importlib.import_module(f"packs.{name}")
        tools.extend(getattr(mod, "TOOLS", []))
        handlers.update(getattr(mod, "HANDLERS", {}))
        if hasattr(mod, "get_context"):
            ctx = mod.get_context()
            if ctx:
                contexts.append(ctx)
    return tools, handlers, contexts


def call_ollama(cfg: dict, messages: list[dict], tools: list[dict], use_tools: bool = True) -> dict:
    body = {
        "model": cfg.get("model", "ibm/granite4"),
        "messages": messages,
        "stream": False,
        "keep_alive": cfg.get("keep_alive", 0),
        "options": {"num_ctx": 4096, "temperature": 0.1},
    }
    if use_tools and tools:
        body["tools"] = tools
    req = urllib.request.Request(
        cfg.get("ollama_url", "http://127.0.0.1:11434/api/chat"),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode()).get("message", {})


def run_prompt(user_prompt: str) -> str:
    cfg = load_config()
    tools, handlers, contexts = load_packs(cfg.get("packs", ["common"]))
    assistant_name = cfg.get("name", "Jarvis")

    ctx_block = "\n\nCurrent desktop state:\n" + "\n".join(contexts) if contexts else ""
    system_prompt = (
        f"You are {assistant_name}, a concise local desktop assistant. "
        "Use the provided tools to perform all requested actions. "
        "Keep your final reply to 1-2 short plain sentences suitable for speech (no markdown)."
        f"{ctx_block}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    seen_calls: set[tuple[str, str]] = set()

    for turn in range(4):
        msg = call_ollama(cfg, messages, tools, use_tools=(turn < 3))
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return (msg.get("content") or "").strip()
        messages.append(msg)
        ran_new = False
        for tc in tool_calls:
            fn = tc.get("function", {})
            tname = fn.get("name", "")
            targs = fn.get("arguments") or {}
            if isinstance(targs, str):
                try:
                    targs = json.loads(targs)
                except Exception:
                    targs = {}
            key = (tname, json.dumps(targs, sort_keys=True))
            if key in seen_calls:
                messages.append({"role": "tool", "content": "Already executed."})
                continue
            seen_calls.add(key)
            ran_new = True
            handler = handlers.get(tname)
            res = handler(targs) if handler else f"Unknown tool: {tname}"
            messages.append({"role": "tool", "content": str(res)})
        if not ran_new:
            return (call_ollama(cfg, messages, tools, use_tools=False).get("content") or "").strip()
    return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m agent.core \"<prompt>\"", file=sys.stderr)
        sys.exit(1)
    print(run_prompt(" ".join(sys.argv[1:])))
