# Din sjekkliste – XTRI Coach V3

Gjør dette **etter** kode er merged/deployet. Kryss av underveis.

## A. Intervals + OpenAI (uendret)

- [ ] [intervals.icu](https://intervals.icu): athlete ID + API key i secrets / `.env`
- [ ] Kalender: gro plan denne + neste uke (events)
- [ ] [platform.openai.com](https://platform.openai.com): `OPENAI_API_KEY`
- [ ] [LOFOTEN-2027/CURRENT_STATUS.md](../LOFOTEN-2027/CURRENT_STATUS.md) oppdatert

## B. Slack-app (Socket Mode – **ikke** slash/tunnel)

- [ ] [api.slack.com/apps](https://api.slack.com/apps) → **XTRI Coach**
- [ ] **Socket Mode** på
- [ ] App-level token `xapp-…` (`connections:write`)
- [ ] Bot scopes: `chat:write`, `im:history`, `im:read`, `im:write`
- [ ] **Event Subscriptions** på → bot event **`message.im`**
- [ ] **Reinstall to Workspace** → ny `xoxb-…`
- [ ] `SLACK_SIGNING_SECRET` notert
- [ ] Slack **member ID** → `ALLOWED_SLACK_USER_IDS` og `SLACK_NOTIFY_USER_IDS`

Detaljer: [SLACK_SETUP.md](SLACK_SETUP.md)

## C. Fly.io (anbefalt – alltid på)

- [ ] `fly auth login`
- [ ] Fra repo root: `fly volumes create coach_data --region ams --size 1`
- [ ] `fly secrets set` (alle nøkler fra `.env.example`)
- [ ] `fly deploy --config coach-bot/fly.toml`
- [ ] `fly logs` uten crash-loop
- [ ] `curl https://<app-name>.fly.dev/health` → ok

Detaljer: [DEPLOY.md](DEPLOY.md)

## D. Test

- [ ] DM til **XTRI Coach**: «Hva bør jeg fokusere på?» → svar ~15–30 s
- [ ] `fly ssh console -C "python -m coach_bot.jobs morning"` → morgenmelding i DM
- [ ] Logg en testøkt til Intervals (Garmin→Intervals) → coach-melding innen ~15 min (ikke 22:00–06:00)
- [ ] Søndag 18:00 (eller juster env): ukentlig oppsummering (første gang: test med `python -m coach_bot.jobs weekly`)

## E. Vedlikehold

- [ ] Etter endring i `LOFOTEN-2027/`: `fly deploy` på nytt
- [ ] Ved «account_inactive»: reinstall Slack-app + oppdater `SLACK_BOT_TOKEN` secret
- [ ] Ukentlig ritual: [WEEKLY_RITUAL.md](WEEKLY_RITUAL.md)

## Valgfritt lokal uten Fly

- [ ] `coach-bot/.env` komplett, `SLACK_MODE=socket`
- [ ] `./coach-bot/scripts/start.sh` (Mac må være på for meldinger)
