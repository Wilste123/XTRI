# `.env` sjekkliste

```bash
cd coach-bot
cp .env.example .env
```

Fyll inn lokalt (**aldri commit** `coach-bot/.env`).

| Variabel | Hvor finner du det |
|----------|-------------------|
| `SLACK_BOT_TOKEN` | Slack app → OAuth → Bot User OAuth Token |
| `SLACK_APP_TOKEN` | Slack app → Basic Information → App-Level Token (`connections:write`) |
| `SLACK_SIGNING_SECRET` | Slack app → Basic Information |
| `ALLOWED_SLACK_USER_IDS` | Slack profil → Copy member ID |
| `REPO_ROOT` | Absolutt sti til XTRI-repo (inneholder `LOFOTEN-2027/`) |
| `INTERVALS_ATHLETE_ID` | intervals.icu Settings |
| `INTERVALS_API_KEY` | intervals.icu Settings → Developer |
| `OPENAI_API_KEY` | platform.openai.com |
| `COACH_MODEL` | `gpt-4o-mini` (standard) |
| `MORNING_BRIEFING_*` | Valgfritt – se `.env.example` |

## Nøkler har lekket i git?

Hvis `.env` har vært pushet: **roter** Slack tokens, Intervals API key og OpenAI key i respektive dashboards, og oppdater kun lokal `.env`.

```bash
git status   # skal ikke vise coach-bot/.env
```
