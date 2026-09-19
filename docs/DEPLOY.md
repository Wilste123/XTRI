# Deploy – Lofoten Coach

## Lokal (anbefalt nå)

```bash
cd coach-bot
cp .env.example .env
./scripts/start.sh
```

- `REPO_ROOT` = absolutt sti til XTRI-repo
- Slack: Socket Mode (`SLACK_APP_TOKEN`) – **ingen tunnel**
- Health: `http://localhost:3000/health` og `/ready`

## Docker (valgfritt)

```bash
cd coach-bot
docker build -t lofoten-coach .
docker run --env-file .env -p 3000:3000 -v /path/to/XTRI:/repo:ro lofoten-coach
```

Sett `REPO_ROOT=/repo` i container.

## Sky

For morgenbriefing og DM døgnet rundt: kjør container/VM med samme env. Hemmeligheter via platform secrets – aldri i git.
