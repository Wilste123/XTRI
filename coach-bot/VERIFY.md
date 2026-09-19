# Verifiser Slack coach (DM)

## Forutsetninger

- [ ] `coach-bot/.env` komplett (inkl. `SLACK_APP_TOKEN`)
- [ ] `./scripts/start.sh` kjører
- [ ] `curl http://localhost:3000/ready` → `ok: true`
- [ ] DM åpnet med appen i Slack
- [ ] Slack app-scopes: `chat:write`, `im:write`, `im:history`, `files:write` (grafer)
- [ ] Kjører **V2**-kode (merge PR / restart `./scripts/start.sh` eller `fly deploy`)

## Tester

| Handling | Forventet |
|----------|-----------|
| DM: `ping` | «Pong – coach-bot er på og mottar DM.» |
| DM: `briefing: test` | Proaktiv test-melding (uten å vente på cron) |
| DM: `briefing: morgen` | Morgenbriefing med Block Kit |
| DM: `briefing: uke` | Ukestatus + grafer hvis data finnes |
| DM: «hvordan ligger jeg an?» | Norsk status med Intervals + CURRENT_STATUS |
| DM: «ukestatus» | Gjennomført, belastning, risiko, neste uke |
| DM: `nullstill` | Tømmer samtalehistorikk |
| DM: «synk kalender» → `ja` | Preview, deretter events i Intervals |
| DM: «legg inn økt i morgen i intervals» | Øktforslag + preview; så `ja` eller «legg den inn» |
| DM: etter forslag: «legg den inn i intervals» | Oppretter økt i Intervals (fra forrige melding) |
| DM: `legg inn sykkel 60 min i morgen` | Direkte inn i Intervals (enkeltøkt) |
| Ukjent Slack-bruker | Blokkert når `ALLOWED_SLACK_USER_IDS` er satt |

## Proaktiv (cron)

1. Sett `MORNING_BRIEFING_ENABLED=true` og/eller `WEEKLY_BRIEFING_ENABLED=true`
2. Sett `ALLOWED_SLACK_USER_IDS` til din Slack user ID
3. Bot må kjøre kontinuerlig (lokal eller Fly `min_machines_running = 1`)
4. Sjekk logger for `Morning briefing at …` og `Morgenbriefing sent user_id=… message_ts=…`

## Admin HTTP (valgfritt)

Med `ADMIN_BRIEFING_SECRET` i `.env`:

```bash
curl -X POST "http://localhost:3000/admin/briefing?type=test" \
  -H "X-Admin-Secret: ditt-hemmelig"
```

## Feil

| Symptom | Sjekk |
|---------|--------|
| Ingen svar i DM | Socket Mode på, `message.im` subscribed, bot kjører |
| Proaktiv sendes ikke | `ALLOWED_SLACK_USER_IDS`, briefing flags, alltid-på deploy |
| Intervals-feil i svar | Athlete ID, API key (uten mellomrom i `.env`) |
| Ingen grafer | Wellness/økter i Intervals; matplotlib installert |
| Melding om files:write | Legg til scope, reinstall app, nytt bot token, restart bot |
| DM: `legg inn ukeplanen` → `ja` | Hele uke fra repo til Intervals |
| Lang ventetid | OpenAI; se terminal-logg |
