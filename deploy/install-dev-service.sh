#!/usr/bin/env bash
# Install RawTrainer's dev server as a systemd *user* service, so uvicorn stays up
# across logout/reboot and restarts on crash — no more launching it by hand.
#
#   bash deploy/install-dev-service.sh          # host 127.0.0.1, port 8010
#   HOST=0.0.0.0 PORT=8000 bash deploy/install-dev-service.sh
#
# Paths are auto-detected from this script's location (repo root = its parent),
# so it works regardless of where you cloned the repo. Re-run any time to update
# the unit. Manage it with: systemctl --user {status,restart,stop} rawtrainer
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/.venv"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8010}"
UNIT="$HOME/.config/systemd/user/rawtrainer.service"

if [ ! -x "$VENV/bin/uvicorn" ]; then
  echo "! No uvicorn at $VENV/bin/uvicorn" >&2
  echo "  Create the venv and install deps first:" >&2
  echo "    python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

mkdir -p "$(dirname "$UNIT")"
cat > "$UNIT" <<EOF
[Unit]
Description=RawTrainer dev server (uvicorn)
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO
ExecStart=$VENV/bin/uvicorn src.ui.web.api:app --host $HOST --port $PORT --reload
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-$REPO/.env
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF
echo "wrote $UNIT"

systemctl --user daemon-reload
systemctl --user enable --now rawtrainer.service

# Keep the user service running with no active login (survives logout + reboot).
if ! loginctl show-user "$USER" 2>/dev/null | grep -q "Linger=yes"; then
  echo "Enabling linger (needs sudo, once) so it runs without you being logged in..."
  sudo loginctl enable-linger "$USER" || echo "  (skipped — run 'sudo loginctl enable-linger $USER' yourself to persist across reboots)"
fi

echo
echo "RawTrainer is now a service on http://$HOST:$PORT"
echo "  logs:    journalctl --user -u rawtrainer -f"
echo "  restart: systemctl --user restart rawtrainer"
echo "  stop:    systemctl --user stop rawtrainer"
systemctl --user status rawtrainer.service --no-pager || true