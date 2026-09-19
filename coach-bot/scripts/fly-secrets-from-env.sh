#!/usr/bin/env bash
# Les coach-bot/.env og sett Fly secrets (krever flyctl + .env med alle nøkler).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Mangler $ENV_FILE – kjør ./scripts/bootstrap-env.sh først"
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

required=(
  SLACK_BOT_TOKEN
  SLACK_SIGNING_SECRET
  SLACK_APP_TOKEN
  ALLOWED_SLACK_USER_IDS
  SLACK_NOTIFY_USER_IDS
  INTERVALS_ATHLETE_ID
  INTERVALS_API_KEY
  OPENAI_API_KEY
)

for v in "${required[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "Mangler $v i .env"
    exit 1
  fi
done

fly secrets set \
  SLACK_BOT_TOKEN="$SLACK_BOT_TOKEN" \
  SLACK_SIGNING_SECRET="$SLACK_SIGNING_SECRET" \
  SLACK_APP_TOKEN="$SLACK_APP_TOKEN" \
  ALLOWED_SLACK_USER_IDS="$ALLOWED_SLACK_USER_IDS" \
  SLACK_NOTIFY_USER_IDS="$SLACK_NOTIFY_USER_IDS" \
  INTERVALS_ATHLETE_ID="$INTERVALS_ATHLETE_ID" \
  INTERVALS_API_KEY="$INTERVALS_API_KEY" \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  COACH_MODEL="${COACH_MODEL:-gpt-4o-mini}"

echo "Fly secrets satt."
