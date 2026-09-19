# Deploy – Lofoten Coach

## Lokal (anbefalt V1)

```bash
cd coach-bot
cp .env.example .env   # fyll inn nøkler
uv sync
uv run python -m coach_bot.main
```

- `REPO_ROOT=/Users/william/XTRI` (absolutt sti til repo)
- Eksponer port **3000** med cloudflared/ngrok for Slack

## Docker (forberedt)

```bash
cd coach-bot
docker build -t lofoten-coach .
docker run --env-file .env -p 3000:3000 -v /Users/william/XTRI:/repo:ro lofoten-coach
```

Sett `REPO_ROOT=/repo` i container.

## Fly.io / Railway (V3+)

1. Push image eller connect repo `coach-bot/`
2. Sett alle env fra `.env.example`
3. For V3: legg til cron som kaller intern endpoint eller separat worker

V1 trenger ikke alltid-på server hvis du kun bruker slash commands mens maskinen kjører.

## Hemmeligheter

Aldri commit `.env`. Bruk platform secrets i sky.
