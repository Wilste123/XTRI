# Deploy – XTRI Coach V3 (Fly.io)

Anbefalt for **alltid-på**: morgenbrief, ukentlig oppsummering, melding ved ny økt.

Estimat: **~$5/mnd** (Fly shared-cpu-512MB + 1GB volume). Ingen cloudflared.

## Forutsetninger

- Slack-app med **Socket Mode** (se [SLACK_SETUP.md](SLACK_SETUP.md))
- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installert og `fly auth login`
- Repo clone lokalt

## Første deploy

Fra **repo root** (`XTRI/`):

```bash
fly launch --no-deploy --config coach-bot/fly.toml --name lofoten-coach --region ams
fly volumes create coach_data --region ams --size 1
fly secrets set \
  SLACK_BOT_TOKEN=xoxb-... \
  SLACK_SIGNING_SECRET=... \
  SLACK_APP_TOKEN=xapp-... \
  ALLOWED_SLACK_USER_IDS=U0BSCE53YF2 \
  SLACK_NOTIFY_USER_IDS=U0BSCE53YF2 \
  INTERVALS_ATHLETE_ID=i... \
  INTERVALS_API_KEY=... \
  OPENAI_API_KEY=sk-...
fly deploy --config coach-bot/fly.toml
```

Sjekk:

```bash
fly logs
curl https://lofoten-coach.fly.dev/health
```

## Oppdater LOFOTEN-2027 i sky

`LOFOTEN-2027/` er **bakt inn i Docker-image** ved deploy. Etter du endrer `CURRENT_STATUS` i git:

```bash
git pull
fly deploy --config coach-bot/fly.toml
```

(Senere: git pull i container eller volume-sync – ikke i V3.)

## Manuell jobb på Fly

```bash
fly ssh console -C "python -m coach_bot.jobs morning"
fly ssh console -C "python -m coach_bot.jobs poll"
```

## Lokal utvikling

```bash
./coach-bot/scripts/start.sh
```

`SLACK_MODE=socket`, `STATE_PATH=./data/coach_state.json`.

## Docker (uten Fly)

Fra repo root:

```bash
docker build -f coach-bot/Dockerfile -t lofoten-coach .
docker run --env-file coach-bot/.env -p 8080:8080 -v coach-data:/data lofoten-coach
```

Sett `STATE_PATH=/data/coach_state.json`, `PORT=8080`.

## Hemmeligheter

Aldri commit `.env`. Kun `fly secrets set`.
