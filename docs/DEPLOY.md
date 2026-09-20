# Deploy – Lofoten Coach (always-on Socket Mode)

Boten må kjøre **kontinuerlig** (Slack Socket Mode). Mac med `./scripts/start.sh` eller sky under.

## Lokal

```bash
cd coach-bot
./scripts/start.sh
```

- `REPO_ROOT` = sti til XTRI-repo (inneholder `LOFOTEN-2027/`)
- Health: `http://localhost:3000/health` og `/ready`

## Docker (fra repo-roten)

```bash
cd /path/to/XTRI
docker build -f coach-bot/Dockerfile -t lofoten-coach .
docker run --env-file coach-bot/.env -p 3000:3000 lofoten-coach
```

Image baker inn `LOFOTEN-2027/` ved build (`REPO_ROOT=/app`). Oppdater plan i git → rebuild image.

## Fly.io (anbefalt sky)

Fra **repo-roten** (ikke bare `coach-bot/`):

Deploy **fra repo-roten** (der `coach-bot/` og `LOFOTEN-2027/` ligger). `fly.toml` bruker `context = ".."` og `dockerfile = "coach-bot/Dockerfile"`.

```bash
cd /path/to/XTRI
fly launch --config coach-bot/fly.toml --no-deploy
fly secrets set \
  SLACK_BOT_TOKEN=... \
  SLACK_APP_TOKEN=... \
  SLACK_SIGNING_SECRET=... \
  ALLOWED_SLACK_USER_IDS=... \
  INTERVALS_ATHLETE_ID=... \
  INTERVALS_API_KEY=... \
  OPENAI_API_KEY=... \
  MORNING_BRIEFING_ENABLED=true
fly deploy --config coach-bot/fly.toml
```

- `fly.toml` setter `min_machines_running = 1` og health check på `/health`.
- `REPO_ROOT=/app` er satt i `fly.toml` – matcher Dockerfile.
- Dockerfile kopierer ikke `.env` – briefing-flagg må settes som secrets (som over).
- `WEEKLY_BRIEFING_ENABLED` er fortsatt av (default); sett `true` som secret hvis søndags-ukebriefing ønskes.
- Endre `app = "lofoten-coach"` i `fly.toml` til unikt app-navn ved første `fly launch`.

## Railway

Connect repo, Dockerfile path `coach-bot/Dockerfile`, build context = repo root, start command `python -m coach_bot.main`, working directory `/app/coach-bot`, env som lokal `.env`, disable sleep on free tier or use paid always-on.

## Hemmeligheter

`coach-bot/.env` kan være tracket lokalt for test; i sky bruk `fly secrets` / Railway variables.
