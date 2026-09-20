#!/usr/bin/env bash
# Start Lofoten coach-bot (Socket Mode + health on PORT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Mangler coach-bot/.env – kjør: git pull origin main (filen skal ligge i repo)."
  exit 1
fi

# GitHub-synk (Atlas): bruk PAT i .env, eller gh CLI på Mac etter `gh auth login`.
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  _gh_tok="$(grep -E '^GITHUB_TOKEN=' .env 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)"
  if [[ -z "${_gh_tok}" ]] && command -v gh >/dev/null 2>&1; then
    if _from_gh="$(gh auth token 2>/dev/null)" && [[ -n "${_from_gh}" ]]; then
      export GITHUB_TOKEN="${_from_gh}"
      echo "GitHub: GITHUB_TOKEN fra gh auth (Atlas-synk aktiv for denne kjøringen)."
    fi
  fi
  unset _gh_tok _from_gh
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
