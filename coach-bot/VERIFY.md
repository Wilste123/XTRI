# Verifiser Slack coach (DM)

## Forutsetninger

- [ ] `coach-bot/.env` komplett (inkl. `SLACK_APP_TOKEN`)
- [ ] `./scripts/start.sh` kjører
- [ ] `curl http://localhost:3000/ready` → `ok: true`
- [ ] DM åpnet med appen i Slack

## Tester

| Handling | Forventet |
|----------|-----------|
| DM: `ping` | «Pong – coach-bot er på og mottar DM.» |
| DM: «hvordan ligger jeg an?» | Norsk status med Intervals + CURRENT_STATUS |
| DM: «hva i morgen?» | Events fra Intervals eller «plan mangler» |
| DM: «ukestatus» | Gjennomført, belastning, risiko, neste uke |
| Ukjent Slack-bruker | Blokkert når `ALLOWED_SLACK_USER_IDS` er satt |

## Feil

| Symptom | Sjekk |
|---------|--------|
| Ingen svar i DM | Socket Mode på, `message.im` subscribed, bot kjører |
| Intervals-feil i svar | Athlete ID, API key (uten mellomrom i `.env`) |
| Lang ventetid | OpenAI; se terminal-logg |
