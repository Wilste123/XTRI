# Din sjekkliste – XTRI Coach V3

Gjør dette **etter** kode er merged/deployet. Kryss av underveis.

## A. Intervals + OpenAI

- [ ] [intervals.icu](https://intervals.icu): athlete ID + API key i secrets / `.env`
- [ ] Kalender: gro plan denne + neste uke (events)
- [ ] [platform.openai.com](https://platform.openai.com): `OPENAI_API_KEY`
- [ ] [LOFOTEN-2027/CURRENT_STATUS.md](../LOFOTEN-2027/CURRENT_STATUS.md) oppdatert (kilde for første import)

## B. Supabase (database)

- [ ] Nytt Supabase-prosjekt opprettet
- [ ] Kjør SQL: [coach-bot/supabase/schema.sql](../coach-bot/supabase/schema.sql) i SQL Editor
- [ ] `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` i `.env` / Fly secrets
- [ ] `python -m coach_bot.jobs sync-status` (eller første bot-start seed)
- [ ] Verifiser rad i `coach_status_snapshots` (Table Editor eller SQL)

Detaljer: [SUPABASE_SETUP.md](SUPABASE_SETUP.md)

## C. Slack-app (Socket Mode)

- [ ] [api.slack.com/apps](https://api.slack.com/apps) → **XTRI Coach**
- [ ] **Socket Mode** på + `SLACK_APP_TOKEN` (`connections:write`)
- [ ] Bot scopes: `chat:write`, `im:history`, `im:read`, `im:write`
- [ ] **Event Subscriptions** → bot event **`message.im`**
- [ ] **Reinstall to Workspace** → `SLACK_BOT_TOKEN` + `SLACK_SIGNING_SECRET`
- [ ] `ALLOWED_SLACK_USER_IDS` + `SLACK_NOTIFY_USER_IDS` = din member ID

Detaljer: [SLACK_SETUP.md](SLACK_SETUP.md)

## D. Fly.io (anbefalt – alltid på)

- [ ] `fly auth login`
- [ ] `fly volumes create coach_data --region ams --size 1` (fallback state hvis Supabase nede)
- [ ] `./coach-bot/scripts/bootstrap-env.sh` + fyll Slack/OpenAI/Supabase
- [ ] `./coach-bot/scripts/fly-secrets-from-env.sh`
- [ ] `fly deploy --config coach-bot/fly.toml`
- [ ] `fly logs` uten crash
- [ ] `curl https://<app>.fly.dev/health` → ok

Detaljer: [DEPLOY.md](DEPLOY.md)

## E. Test

- [ ] DM til **XTRI Coach** → svar ~15–30 s
- [ ] Supabase: nye rader i `coach_messages` etter DM
- [ ] `python -m coach_bot.jobs morning` → DM + rad i `coach_messages`
- [ ] Ny økt i Intervals → melding + rad i `coach_activity_dedup`
- [ ] `python -m coach_bot.jobs weekly` → ny rad i `coach_status_snapshots`

## F. Vedlikehold

- [ ] Oppdater status: rediger markdown **eller** la ukentlig brief skrive snapshot; `sync-status` etter manuelle endringer i fil
- [ ] Ved Slack `account_inactive`: reinstall + oppdater secrets
- [ ] Ukentlig: [WEEKLY_RITUAL.md](WEEKLY_RITUAL.md)

## Valgfritt lokal uten Fly

- [ ] `./coach-bot/scripts/start.sh` (Mac må være på)
