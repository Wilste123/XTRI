# Miljøvariabler

**`coach-bot/.env` ligger i git** – William sitt test-oppsett. Etter `git pull` skal filen være der; rediger og commit når du roterer nøkler.

**Hva du må fylle for nye features:** [ENV_TODO.md](ENV_TODO.md)

```bash
cd coach-bot
./scripts/start.sh
```

| Variabel | Påkrevd? | Hvor |
|----------|----------|------|
| `SLACK_BOT_TOKEN` | ja | Slack app → OAuth (reinstall etter nye scopes) |
| `SLACK_APP_TOKEN` | ja | App-Level Token (`connections:write`) |
| `SLACK_SIGNING_SECRET` | ja | Basic Information |
| `ALLOWED_SLACK_USER_IDS` | ja for briefing | Slack member ID |
| `REPO_ROOT` | ja (lokal) | `/Users/william/XTRI` — på Fly: **ikke** som secret; bruk `/app` via `fly.toml` |
| `INTERVALS_ATHLETE_ID` / `INTERVALS_API_KEY` | ja | intervals.icu Settings |
| `OPENAI_API_KEY` / `COACH_MODEL` | ja | platform.openai.com |
| `MORNING_BRIEFING_ENABLED` | ja for 07:00-DM | `true` på `main`; sett også som Fly secret |
| `GITHUB_TOKEN` / `GITHUB_REPO` / `GITHUB_BRANCH` | ja på Fly | PAT med Contents R/W mot `Wilste123/XTRI`, eller tom + `gh auth login` på Mac (start.sh henter token) |
| `MEMORY_AUTO_LEARN` | nei (default `true`) | lær varige fakta fra DM til `11_ATLAS.md` |
| `TAVILY_API_KEY` | nei | [tavily.com](https://tavily.com) — live web-søk |
| `ADMIN_BRIEFING_SECRET` | nei | låser `POST /admin/briefing` |
| `WEEKLY_BRIEFING_ENABLED` | nei (default `false`) | søndags-ukestatus |

Slack-scopes (`files:write` for grafer): [../docs/SLACK_SETUP.md](../docs/SLACK_SETUP.md)  
Fly secrets: [../docs/DEPLOY.md](../docs/DEPLOY.md)
