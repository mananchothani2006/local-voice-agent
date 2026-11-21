#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG_DIR="${HOME}/.config/local-voice-agent"
CFG_FILE="${CFG_DIR}/config.json"

read -r -p "Name your assistant [Jarvis]: " AGENT_NAME
AGENT_NAME="${AGENT_NAME:-Jarvis}"
CMD_NAME="$(printf '%s' "$AGENT_NAME" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')"
CMD_NAME="${CMD_NAME:-jarvis}"

OS="$(uname -s)"
PACKS='["common"]'
case "$OS" in
  Linux)  PACKS='["common", "linux_hyprland"]' ;;
  Darwin) PACKS='["common", "macos"]' ;;
  MINGW*|MSYS*|CYGWIN*) PACKS='["common", "windows"]' ;;
esac

mkdir -p "$CFG_DIR" "${HOME}/.local/bin"
cat > "$CFG_FILE" <<EOF
{
  "name": "$AGENT_NAME",
  "model": "ibm/granite4",
  "ollama_url": "http://127.0.0.1:11434/api/chat",
  "voice": "af_bella",
  "keep_alive": 0,
  "packs": $PACKS
}
EOF

LAUNCHER="${HOME}/.local/bin/${CMD_NAME}"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 "${REPO_DIR}/agent/core.py" "\$@"
EOF
chmod +x "$LAUNCHER"

echo "Installed '${AGENT_NAME}' -> ${LAUNCHER}"
echo "Config saved at ${CFG_FILE} (packs: ${PACKS})"
