# Deploy – XTRI Coach V3 (Fly.io)

Anbefalt for **alltid-på**: morgenbrief, ukentlig oppsummering, melding ved ny økt.

Estimat: **~$5/mnd** (Fly shared-cpu-512MB + 1GB volume). Ingen cloudflared.

## Forutsetninger

- Slack-app med **Socket Mode** (se [SLACK_SETUP.md](SLACK_SETUP.md))
- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installert og `fly auth login`
- Repo clone lokalt, **V3 merged** (Dockerfile + `fly.toml` i **repo root**)

## Viktig: hvor du står i terminalen

Fly feiler med *Could not find a Dockerfile* hvis du:

- kjører `fly launch` **inne i `coach-bot/`** uten root Dockerfile, eller
- ikke har **`Dockerfile` og `fly.toml` i `XTRI/` (root)**, eller
- bruker Cursor/Fly «auto detect» uten `--copy-config` fra root

**Alltid:**

```bash
cd /Users/william/XTRI    # repo root – mappe med LOFOTEN-2027/ og Dockerfile
git pull
```

## Første deploy

```bash
cd /Users/william/XTRI

# Opprett app (én gang) – bruker root fly.toml, app-navn xtri
fly launch --no-deploy --copy-config --region ams

# Volume (én gang per app)
fly volumes create coach_data --region ams --size 1 --app xtri

# Secrets (eller ./coach-bot/scripts/fly-secrets-from-env.sh)
fly secrets set --app xtri \
  SLACK_BOT_TOKEN=xoxb-... \
  SLACK_SIGNING_SECRET=... \
  SLACK_APP_TOKEN=xapp-... \
  ALLOWED_SLACK_USER_IDS=U0BSCE53YF2 \
  SLACK_NOTIFY_USER_IDS=U0BSCE53YF2 \
  INTERVALS_ATHLETE_ID=i303008 \
  INTERVALS_API_KEY=... \
  OPENAI_API_KEY=sk-... \
  SUPABASE_URL=https://....supabase.co \
  SUPABASE_SERVICE_ROLE_KEY=eyJ...

fly deploy --app xtri
```

Sjekk:

```bash
fly logs --app xtri
curl https://xtri.fly.dev/health
```

## Oppdater etter kodeendring

```bash
cd /Users/william/XTRI
git pull
fly deploy --app xtri
```

`LOFOTEN-2027/` er bakt inn i image ved hver deploy.

## Manuell jobb på Fly

```bash
fly ssh console --app xtri -C "python -m coach_bot.jobs morning"
fly ssh console --app xtri -C "python -m coach_bot.jobs poll"
```

## Lokal utvikling

```bash
./coach-bot/scripts/start.sh
```

## Docker (test build lokalt)

Fra repo root:

```bash
docker build -t xtri-coach .
docker run --env-file coach-bot/.env -p 8080:8080 -v coach-data:/data xtri-coach
```

## Hemmeligheter

Aldri commit `.env`. Kun `fly secrets set`.
