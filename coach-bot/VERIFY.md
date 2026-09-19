# Verifiser Slack coach (V1)

Kjør når bot og tunnel er aktive.

## Forutsetninger

- [ ] `coach-bot/.env` komplett
- [ ] `python -m coach_bot.main` eller `./scripts/start.sh` kjører
- [ ] `curl http://localhost:3000/health` → `{"ok": true, ...}`
- [ ] cloudflared/ngrok peker til port 3000
- [ ] Slack slash URL = `https://<tunnel>/slack/events`

## Tester

| Kommando | Forventet |
|----------|-----------|
| `/status` | Norsk LOFOTEN 2027 STATUS; bruker Intervals 28d + CURRENT_STATUS |
| `/imorgen` | Plan fra Intervals events i morgen + anbefaling; eller tydelig «plan mangler» |
| `/ukestatus` | Seksjoner: Gjennomført, Belastning, Hva gikk bra/dårlig, Risiko, Hva bør endres, Neste uke |

## Feil

| Symptom | Sjekk |
|---------|--------|
| `dispatch_failed` | Tunnel URL, signing secret, bot kjører |
| Intervals-feil | Athlete ID, API key |
| Timeout | OpenAI key; se terminal-logg |
