# Slack-oppsett for Lofoten Coach (V1)

## 1. Opprett Slack-app

1. Gå til [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch.
2. Navn f.eks. `Lofoten Coach`, workspace ditt.

## 2. OAuth & scopes (Bot Token)

Under **OAuth & Permissions** → Bot Token Scopes:

- `chat:write`
- `commands`

Install app to workspace. Kopier **Bot User OAuth Token** → `SLACK_BOT_TOKEN` i `.env`.

## 3. Signing secret

**Basic Information** → **Signing Secret** → `SLACK_SIGNING_SECRET`.

## 4. Slash commands

Under **Slash Commands**, opprett tre kommandoer (samme Request URL):

| Command | Short description |
|---------|-------------------|
| `/status` | Lofoten 2027 status |
| `/imorgen` | Plan og anbefaling i morgen |
| `/ukestatus` | Ukentlig oppsummering |

**Request URL (lokal utvikling):**

1. Start bot: `cd coach-bot && uv run python -m coach_bot.main`
2. Tunnel: `cloudflared tunnel --url http://localhost:3000` (eller ngrok)
3. Sett Request URL til `https://<tunnel-host>/slack/events`

Bolt bruker én endpoint for events og slash commands når appen er konfigurert med `SLACK_SIGNING_SECRET`.

For **Socket Mode** (alternativ, ingen tunnel): aktiver Socket Mode, app-level token, og endre `main.py` – V1 leveres med HTTP på port 3000.

## 5. Intervals plan

Legg **ukentlig plan som events** i intervals.icu-kalenderen. `/imorgen` og plan-delen av `/ukestatus` leser disse – grov plan er OK i V1.

## 6. Tillat kun deg (anbefalt)

Finn Slack user ID (profil → … → Copy member ID). Sett i `.env`:

```
ALLOWED_SLACK_USER_IDS=U01234567
```

Kommaseparert for flere.

## 7. Verifiser

- `/status` → svar innen ~30 s (LLM)
- Tom plan i Intervals → bot skal si at plan mangler, ikke finne på økt

## 8. @mention vs slash (V1)

**Lofoten coach-bot svarer ikke på `@XTRI Coach` eller vanlige kanalmeldinger.** Koden har kun slash-kommandoer (`/status`, `/imorgen`, `/ukestatus`).

Bruk f.eks.:

```
/status
```

Forutsetninger samme som over: bot kjører lokalt, **cloudflared** peker på port 3000, slash **Request URL** = `https://<tunnel>/slack/events`, bot invitert i kanalen (`/invite @XTRI Coach`).

Dette er **ikke** Cursor-agenten i Slack – det er en egen app som må kjøre på Macen din mens du tester.
