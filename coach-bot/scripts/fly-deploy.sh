#!/usr/bin/env bash
# Deploy lofoten-coach to Fly.io from XTRI repo root.
set -euo pipefail

XTRI_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="lofoten-coach"

if ! command -v fly >/dev/null 2>&1; then
  echo "Installer flyctl: https://fly.io/docs/hands-on/install-flyctl/"
  exit 1
fi

cd "$XTRI_ROOT"
if [[ ! -f coach-bot/fly.toml ]]; then
  echo "Kjør fra XTRI-clone (fant ikke coach-bot/fly.toml)."
  exit 1
fi

if fly secrets list -a "$APP" 2>/dev/null | grep -qE '^\s*REPO_ROOT\s'; then
  echo "→ Fjerner REPO_ROOT secret (Mac-sti ødelegger ukeplan i container)."
  fly secrets unset REPO_ROOT -a "$APP"
fi

echo "→ Deploy $APP …"
fly deploy --config coach-bot/fly.toml -a "$APP"

echo "→ Status"
fly status -a "$APP"

echo "→ Health"
curl -sf "https://${APP}.fly.dev/health" | head -c 200
echo ""

echo "Ferdig. Sjekk logs: fly logs -a $APP"
