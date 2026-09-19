#!/usr/bin/env bash
# Start Lofoten coach-bot (Socket Mode + health on PORT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Mangler coach-bot/.env – kjør: git pull origin main (filen skal ligge i repo)."
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -q -e ".[dev]"

echo "Starter coach (Slack Socket Mode DM)"
echo "Health: http://localhost:3000/health  ready: http://localhost:3000/ready"
exec python -m coach_bot.main
