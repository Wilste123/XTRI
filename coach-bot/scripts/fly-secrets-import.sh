#!/usr/bin/env bash
# Import coach-bot/.env to Fly secrets (never REPO_ROOT).
set -euo pipefail

BOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP="${FLY_APP:-lofoten-coach}"
ENV_FILE="${BOT_DIR}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Mangler $ENV_FILE"
  exit 1
fi

if ! command -v fly >/dev/null 2>&1; then
  echo "Installer flyctl først."
  exit 1
fi

grep -v '^REPO_ROOT=' "$ENV_FILE" | grep -v '^#' | grep '=' | fly secrets import -a "$APP"
echo "Importert (uten REPO_ROOT). Verifiser: fly secrets list -a $APP | grep REPO"
