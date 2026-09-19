# `.env` sjekkliste

```bash
cd coach-bot
cp .env.example .env
```

Fyll inn (ingen av disse i git):

| Variabel | Hvor finner du det |
|----------|-------------------|
| `SLACK_BOT_TOKEN` | Slack app → OAuth → Bot User OAuth Token |
| `SLACK_SIGNING_SECRET` | Slack app → Basic Information |
| `ALLOWED_SLACK_USER_IDS` | Slack profil → Copy member ID |
| `REPO_ROOT` | `/Users/william/XTRI` |
| `INTERVALS_ATHLETE_ID` | intervals.icu Settings |
| `INTERVALS_API_KEY` | intervals.icu Settings → Developer |
| `OPENAI_API_KEY` | platform.openai.com |
| `COACH_MODEL` | `gpt-4o-mini` (standard) |

Valider at filen ikke er tracket:

```bash
git status   # skal ikke vise coach-bot/.env
```
