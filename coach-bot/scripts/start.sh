#!/usr/bin/env bash
# Start Lofoten coach-bot (Socket Mode + health on PORT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Mangler coach-bot/.env (filen er kun lokalt – ikke i git)."
  echo ""
  echo "  cp .env.example .env"
  echo "  open -e .env    # eller nano .env"
  echo ""
  echo "Fyll inn minst:"
  echo "  SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET"
  echo "  ALLOWED_SLACK_USER_IDS, REPO_ROOT=/Users/william/XTRI"
  echo "  INTERVALS_ATHLETE_ID, INTERVALS_API_KEY, OPENAI_API_KEY"
  echo ""
  echo "Guide: SETUP_ENV.md og ../docs/SLACK_SETUP.md"
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
