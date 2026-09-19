#!/usr/bin/env bash
# Start XTRI coach (Socket Mode by default – no tunnel).
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

if SSL_CERT=$(python -c "import certifi; print(certifi.where())" 2>/dev/null); then
  export SSL_CERT_FILE="$SSL_CERT"
  export REQUESTS_CA_BUNDLE="$SSL_CERT"
fi

mkdir -p ./data
echo "Starter coach (SLACK_MODE=socket anbefalt – se docs/SLACK_SETUP.md)"
echo "Health: http://localhost:${PORT:-8080}/health"
exec python -m coach_bot.main
