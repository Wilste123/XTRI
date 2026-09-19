# Verifiser XTRI Coach (V3)

## Forutsetninger

- [ ] Slack Socket Mode + `message.im` (se [SLACK_SETUP.md](../docs/SLACK_SETUP.md))
- [ ] Fly deploy eller `./scripts/start.sh` lokalt
- [ ] `curl http://localhost:8080/health` eller Fly `/health` → ok

## Tester

| Test | Forventet |
|------|-----------|
| DM: «Hva er fokus denne uka?» | Norsk coachesvar med Intervals + repo |
| `python -m coach_bot.jobs morning` | Proaktiv morgenmelding i DM |
| `python -m coach_bot.jobs weekly` | Ukentlig struktur (ukestatus) |
| Ny aktivitet i Intervals | DM innen `ACTIVITY_POLL_MINUTES` (utenom quiet hours) |

## Feil

| Symptom | Sjekk |
|---------|--------|
| Ingen svar i DM | Event `message.im`, bot kjører, `ALLOWED_SLACK_USER_IDS` |
| `account_inactive` | Reinstall Slack-app, oppdater `xoxb` token |
| Ingen morgenmelding | Fly maskin kjører, timezone `Europe/Oslo`, logs |
| Ingen økt-melding | Bootstrap første gang; Garmin→Intervals (ikke bare Strava uten webhook) |
