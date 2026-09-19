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

# python.org on macOS often lacks CA bundle for urllib (Slack SDK auth.test).
if SSL_CERT=$(python -c "import certifi; print(certifi.where())" 2>/dev/null); then
  export SSL_CERT_FILE="$SSL_CERT"
  export REQUESTS_CA_BUNDLE="$SSL_CERT"
fi

echo "Starter coach på http://localhost:3000 (health: /health)"
echo "Tunnel: cloudflared tunnel --url http://localhost:3000"
echo "Slack Request URL: https://<tunnel-host>/slack/events"
exec python -m coach_bot.main
