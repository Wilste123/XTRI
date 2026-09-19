# Slack-oppsett for XTRI Coach (V3 – Socket Mode)

Ingen cloudflared. Ingen slash-kommandoer påkrevd. **DM-samtale + proaktive meldinger** (når bot kjører på Fly/Mac).

## 1. Opprett / oppdater Slack-app

1. [api.slack.com/apps](https://api.slack.com/apps) → **XTRI Coach** (eller ny app).
2. **Socket Mode** → **Enable**.
3. **Basic Information** → **App-Level Tokens** → Create with scope **`connections:write`** → `SLACK_APP_TOKEN` (`xapp-…`).

## 2. Bot scopes

**OAuth & Permissions** → Bot Token Scopes:

| Scope | Hvorfor |
|-------|---------|
| `chat:write` | Svar og proaktive meldinger |
| `im:history` | Les DM |
| `im:read` | DM |
| `im:write` | DM |

Valgfritt (kanal `@mention`):

| Scope | Env |
|-------|-----|
| `app_mentions:read` | `SLACK_ENABLE_MENTIONS=true` |
| `channels:history` | samme |

**Reinstall to Workspace** → kopier ny **`SLACK_BOT_TOKEN`** (`xoxb-…`).

**Signing Secret** (Basic Information) → `SLACK_SIGNING_SECRET`.

## 3. Event Subscriptions

1. **Event Subscriptions** → **Enable Events**.
2. Under **Subscribe to bot events**, legg til:
   - **`message.im`** (påkrevd for DM-chat)
   - **`app_mention`** hvis du bruker `@XTRI Coach` i kanaler

Med Socket Mode trenger du **ikke** Request URL for events (tilkobling går over WebSocket).

## 4. `.env` (lokal) / Fly secrets (sky)

Se [coach-bot/.env.example](../coach-bot/.env.example). Minimum:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...
SLACK_MODE=socket
ALLOWED_SLACK_USER_IDS=U0BSCE53YF2
SLACK_NOTIFY_USER_IDS=U0BSCE53YF2
REPO_ROOT=/Users/william/XTRI
INTERVALS_ATHLETE_ID=i...
INTERVALS_API_KEY=...
OPENAI_API_KEY=...
```

## 5. Kjøre lokalt (test)

```bash
cd coach-bot
cp .env.example .env   # fyll inn
./scripts/start.sh
```

Åpne **DM med XTRI Coach** → skriv f.eks. «Hva er fokus denne uka?»

Manuell proaktiv test:

```bash
source .venv/bin/activate
python -m coach_bot.jobs morning
python -m coach_bot.jobs poll
```

## 6. Legacy slash (valgfritt)

Sett `SLACK_ENABLE_SLASH=true` og opprett `/status`, `/imorgen`, `/ukestatus` med Request URL kun hvis du bruker `SLACK_MODE=http` + tunnel. **Anbefales ikke** i V3.

## 7. Verifiser

- [ ] DM → svar innen ~30 s
- [ ] `python -m coach_bot.jobs morning` → melding i DM
- [ ] Ny økt i Intervals → melding innen ~`ACTIVITY_POLL_MINUTES` (utenom quiet hours)

Feilsøking: [coach-bot/SETUP_ENV.md](../coach-bot/SETUP_ENV.md)
