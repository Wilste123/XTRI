#!/usr/bin/env bash
# Start Lofoten coach-bot locally (port 3000).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Mangler .env – kopier fra .env.example og fyll inn nøkler:"
  echo "  cp .env.example .env"
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -q -e ".[dev]"

echo "Starter coach på http://localhost:3000 (health: /health)"
echo "Tunnel: cloudflared tunnel --url http://localhost:3000"
echo "Slack Request URL: https://<tunnel-host>/slack/events"
exec python -m coach_bot.main
