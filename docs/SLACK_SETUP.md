# Slack-oppsett – DM-coach (Socket Mode)

## 1. Opprett Slack-app

1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch.
2. Navn f.eks. `Lofoten Coach`, workspace ditt.

## 2. Socket Mode

1. **Socket Mode** → Enable.
2. **Basic Information** → **App-Level Tokens** → Create token med scope `connections:write` → `SLACK_APP_TOKEN` (`xapp-…`).

## 3. OAuth & Bot Token Scopes

Under **OAuth & Permissions** → Bot Token Scopes:

- `chat:write`
- `im:history`
- `im:read`
- `im:write`
- `reactions:write` (valgfritt – ⏳ mens coach tenker)

Install app to workspace. Kopier **Bot User OAuth Token** → `SLACK_BOT_TOKEN`.

## 4. Signing secret

**Basic Information** → **Signing Secret** → `SLACK_SIGNING_SECRET`.

## 5. Event Subscriptions

1. **Event Subscriptions** → Enable.
2. Under **Subscribe to bot events**, legg til:
   - `message.im` (DM til bot)

Socket Mode trenger **ikke** Request URL / tunnel.

## 6. Åpne DM med boten

I Slack: **Apps** → Lofoten Coach → **Messages** → skriv første melding.

Sett `ALLOWED_SLACK_USER_IDS` i `.env` (din member ID).

## 7. Intervals plan

Legg **ukentlig plan som events** i intervals.icu. Coach leser disse når du spør om i morgen / uke / plan.

## 8. Start bot

```bash
cd coach-bot
cp .env.example .env   # fyll inn tokens
./scripts/start.sh
```

`curl http://localhost:3000/ready` – sjekk Intervals + repo.

## 9. Eksempler i DM

- «Hvordan ligger jeg an?»
- «Ukestatus»
- «Hva skal jeg gjøre i morgen?»

## Valgfritt: morgenbriefing

I `.env`:

```
MORNING_BRIEFING_ENABLED=true
MORNING_BRIEFING_HOUR=7
MORNING_BRIEFING_MINUTE=0
```

Bot må kjøre på det tidspunktet (lokalt eller sky).
