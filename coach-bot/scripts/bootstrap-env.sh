#!/usr/bin/env bash
# Oppretter coach-bot/.env med verdier du har brukt tidligere (kjør på Mac etter git pull).
# Slack/OpenAI-linjer er tomme til du limer inn etter reinstall av Slack-app.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
  echo "Finnes allerede: $ENV_FILE"
  echo "Slett filen først hvis du vil overskrive."
  exit 1
fi

cat > "$ENV_FILE" <<'EOF'
# Generert av scripts/bootstrap-env.sh – committes ikke til git
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_APP_TOKEN=
SLACK_MODE=socket
SLACK_ENABLE_SLASH=false
SLACK_ENABLE_MENTIONS=false
ALLOWED_SLACK_USER_IDS=U0BSCE53YF2
SLACK_NOTIFY_USER_IDS=U0BSCE53YF2
REPO_ROOT=/Users/william/XTRI
INTERVALS_ATHLETE_ID=i303008
INTERVALS_API_KEY=6ru8f3coqpt5g2p3k6o4y0n1d
OPENAI_API_KEY=
COACH_MODEL=gpt-4o-mini
PORT=8080
TZ=Europe/Oslo
STATE_PATH=./data/coach_state.json
MORNING_BRIEF_HOUR=7
MORNING_BRIEF_MINUTE=0
WEEKLY_BRIEF_ENABLED=true
WEEKLY_BRIEF_WEEKDAY=6
WEEKLY_BRIEF_HOUR=18
WEEKLY_BRIEF_MINUTE=0
ACTIVITY_POLL_MINUTES=15
QUIET_HOURS_START=22
QUIET_HOURS_END=6
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
EOF

chmod 600 "$ENV_FILE"
echo "Skrev $ENV_FILE"
echo "Fyll inn: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN, OPENAI_API_KEY, SUPABASE_*"
echo "Fly: ./scripts/fly-secrets-from-env.sh (etter fly auth)"
